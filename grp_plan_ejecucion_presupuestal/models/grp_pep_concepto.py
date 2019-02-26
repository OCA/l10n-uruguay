# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2018 Datamatic All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging
from collections import defaultdict
from openerp import models, fields, api, tools
from openerp.exceptions import Warning, ValidationError

_logger = logging.getLogger(__name__)


# Query para obtener el precio de referencia
price_unit_query  = "select l.price_unit "
price_unit_query += "from purchase_order p "
price_unit_query += "join purchase_order_line l on p.id = l.order_id "
price_unit_query += "where p.state in ('confirmed','closed') "
price_unit_query += "and l.product_id = %(producto)s "
price_unit_query += "order by p.date_order desc "
price_unit_query += "limit 1; "


def get_odg_aux_ff(odg_id, aux_id, ff_id):
    """
    Retorna la combinación ODG-SUX-FF de la línea de gasto (llave))
    """
    res = odg_id.display_name + '-' + aux_id.display_name + '-' + ff_id.display_name
    return res


class grp_pep_concepto(models.Model):
    _name = 'grp.pep.concepto'
    _rec_name = 'display_name'

    # Métodos de cálculo
    METODO_IMPORTE       = 'importe'
    METODO_RECETA        = 'receta'
    METODO_FORMULA       = 'formula'
    metodo_calculo = [
        (METODO_IMPORTE, u'Importe Predefinido'),
        (METODO_RECETA, u'Recetas'),
        (METODO_FORMULA, u'Fórmula')
    ]

    # Tipos de control
    ALERTA_NO_BLOQUEANTE = 'alerta_no_bloqueante'
    ALERTA_BLOQUEANTE    = 'alerta_bloqueante'
    tipo_control = [
        (ALERTA_NO_BLOQUEANTE, 'Alerta no bloqueante'),
        (ALERTA_BLOQUEANTE, 'Alerta bloqueante')
    ]

    estados = [
        ('borrador', u'Borrador'),
        ('elaboracion', u'Elaboración'),
        ('revision', u'Revisión'),
        ('completo',u'Completo'),
        ('plan', u'En Plan'),
    ]

    state = fields.Selection(string='Estado', selection=estados, default='borrador')
    codigo = fields.Char(string=u'Código')
    name = fields.Char(string=u'Nombre', required=True)
    display_name = fields.Char(string='Nombre', compute='compute_display_name')
    plan_id = fields.Many2one(comodel_name='grp.pep.anual', string='Plan anual')
    plan_state = fields.Selection(related='plan_id.state', string='Estado del Plan')
    anio_fiscal_plan = fields.Many2one(related='plan_id.anio_fiscal')
    concepto_origen_id = fields.Many2one(string=u'Concepto origen', comodel_name='grp.pep.concepto')
    coeficiente_de_ajuste = fields.Float(string='Coeficiente')
    metodo_calculo = fields.Selection(string=u'Método de Cálculo', selection=metodo_calculo, required=True)
    importe = fields.Float(string='Importe', compute='compute_importe')
    importe_original = fields.Float(string='Importe original')
    importe_ingresado = fields.Float(string='Importe')
    posicion_en_plan = fields.Integer(string=u'Posición en el Plan')
    tipo_control = fields.Selection(string=u'Tipo de Control', selection=tipo_control)
    active = fields.Boolean(string=u'Activo', default=True)
    en_plan_adquisiciones = fields.Boolean(string=u'En Plan de Adquisiciones', default=True)
    es_compra_innovadora = fields.Boolean(string=u'Es compra innovadora', default=False)
    compuesto_por_productos = fields.Boolean(string=u'Compuesto por productos', default=False)
    compuesto_por_productos_visible = fields.Boolean(default=True)
    lineas_producto = fields.One2many(string=u'Productos', comodel_name='grp.pep.concepto.linea.producto', inverse_name='grp_pep_concepto_id', copy=True)
    lineas_gasto = fields.One2many(string=u'Distribución del gasto', comodel_name='grp.pep.concepto.linea.gasto', inverse_name='grp_pep_concepto_id', copy=True)
    historia_llaves = fields.One2many(string=u'Llaves por períóodo', comodel_name='grp.pep.concepto.historia.llaves', inverse_name='grp_pep_concepto_id')
    lineas_formula = fields.One2many(string=u'Fórmula', comodel_name='grp.pep.formula.linea', inverse_name='parent_concepto_id', copy=True)
    lineas_receta = fields.One2many(string='Recetas', comodel_name='grp.pep.receta', inverse_name='concepto_id')
    productos_receta = fields.One2many(string='Productos receta', comodel_name='grp.pep.concepto.producto.receta', inverse_name='grp_pep_concepto_id', copy=True)
    cant_llaves = fields.Integer(string='Llaves', compute='_compute_cant_llaves')

    @api.multi
    def get_monto_por_odg_aux_ff(self, id_odg, id_aux, id_ff):
        """
            Obtiene el monto que sale de las lineas de gasto, agregando por las
            odg, auxiliar y fuente de financiamiento recibidas
        """
        lineas_relevantes_ids = self.lineas_gasto.filtered(lambda l: l.odg_id.id == id_odg and
                                                                     l.aux_id.id == id_aux and
                                                                     l.ff_id.id == id_ff)
        monto = 0
        for linea in lineas_relevantes_ids:
            monto += self.importe * (linea.porcentaje_del_gasto/100.0)

        return monto

    @api.multi
    def btn_borrador_elaboracion(self):
        for record in self:
            record.state = 'elaboracion'

    @api.multi
    def btn_elaboracion_revision(self):
        for record in self:
            if record.metodo_calculo == 'receta' and not len(record.productos_receta):
                raise ValidationError("Error: Es necesario tener las recetas asociadas y sus productos consolidados.")
            record.state = 'revision'

    @api.multi
    def btn_revision_completo(self):
        for record in self:
            # Posición en el plan
            if self.posicion_en_plan <= 0:
                raise ValidationError(u"La posición en el plan debe ser mayor a 0")
            record.state = 'completo'

    @api.multi
    def set_completo(self):
        for record in self:
            record.state = 'completo'

    @api.multi
    def set_en_plan(self):
        for record in self:
            record.state = 'plan'

    @api.one
    @api.depends('codigo','name')
    def compute_display_name(self):
        if self.name and self.codigo:
            self.display_name = self.name + ' [' + self.codigo + ']'

    @api.one
    @api.depends('lineas_gasto')
    def _compute_cant_llaves(self):
        self.cant_llaves = len(self.lineas_gasto)

    @api.model
    def name_search(self, name=None, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()

        if name.isdigit():
            recs = self.search([('codigo', operator, name)] + args, limit=limit)
        else:
            recs = self.search([('name', '=', name)] + args, limit=limit)

        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)

        return recs.name_get()

    @api.onchange('metodo_calculo','es_compra_innovadora')
    def _hide_compuesto_por_productos(self):
        """
        Establece si 'compuesto_por_productos' sera visible en función del
        metodo de calculo y 'es_compra_innovadora'
        """
        # Metodos de calculo para los cuales ocultar el campo
        metodos = (self.METODO_RECETA,self.METODO_FORMULA)
        self.compuesto_por_productos_visible = True
        if self.es_compra_innovadora or self.metodo_calculo in metodos:
            self.compuesto_por_productos_visible = False
            self.compuesto_por_productos = False
            # Por si había productos elegidos ...
            lista_lineas = []
            for linea in self.lineas_producto:
                lista_lineas.append((2,linea.id))   # Desvincular y borrar
            self.lineas_producto = lista_lineas

    @api.onchange('compuesto_por_productos')
    def _unlink_productos(self):
        # Si deja de estar compuesto por productos y hay productos
        if not self.compuesto_por_productos and len(self.lineas_producto):
            # Los elimino
            self.lineas_producto = [(5, 0, 0)]

    @api.model
    def create(self, values):
        codigo = self.env['ir.sequence'].next_by_code('grp.pep.concepto.code')
        values['codigo'] = codigo
        res = super(grp_pep_concepto, self).create(values)
        return res

    @api.one
    def copy(self, default=None):
        # Datos pertinenetes a la copia
        default = default or {}
        default.update({
            'concepto_origen_id': self.id,
            'importe_original': self.importe_ingresado if self.importe_ingresado else self.importe,
            'coeficiente_de_ajuste': 1
        })
        new_concept = super(grp_pep_concepto, self).copy(default)

        # Datos en las líneas de producto
        if len(new_concept.lineas_producto):
            for producto in new_concept.lineas_producto:
                producto.cantidad_original = producto.cantidad_estimada
                precio_actual = producto.precio_de_referencia
                producto.get_precio_de_referencia()
                if not producto.precio_de_referencia:
                    producto.precio_de_referencia = precio_actual
                producto.calculo_por_cantidad = True
                producto.actualizacion = 0

        # Clonación de las recetas completas
        if len(self.lineas_receta):
            for receta in self.lineas_receta:
                new_receta = receta.copy({'concepto_id':new_concept.id, 'plan_id':new_concept.plan_id.id})

        if len(new_concept.productos_receta):
            for producto in new_concept.productos_receta:
                producto.actualizacion = 0

        # Actualización del importe
        new_concept.compute_importe()

        return new_concept

    @api.one
    @api.constrains('concepto_origen_id','metodo_calculo','coeficiente_de_ajuste')
    def _coeficiente_positivo(self):
        if self.concepto_origen_id and self.metodo_calculo == 'importe' and self.coeficiente_de_ajuste <= 0:
            raise ValidationError(u"Debe proporcionar un coeficiente mayor a 0")

    @api.one
    @api.constrains('posicion_en_plan')
    def _posicion_positiva(self):
        if self.state not in ('borrador','elaboracion'):
            if self.posicion_en_plan <= 0:
                raise ValidationError(u"La posición en el plan debe ser mayor a 0")

    @api.one
    @api.constrains('importe_ingresado')
    def _importe_positivo(self):
        if self.metodo_calculo == 'importe' and not self.compuesto_por_productos:
            if self.importe_ingresado <= 0:
                raise ValidationError(u"El importe debe ser mayor a 0")

    @api.one
    def compute_importe(self):

        # Fórmula
        if self.metodo_calculo == 'formula' and len(self.lineas_formula):
            self.importe = sum(linea.subtotal for linea in self.lineas_formula)
        # Productos propios
        elif self.compuesto_por_productos and len(self.lineas_producto):
            self.importe = sum(linea.importe_calculado for linea in self.lineas_producto)
        # Recetas
        elif self.metodo_calculo == 'receta' and len(self.productos_receta):
            importe = 0
            for linea in self.productos_receta:
                if linea.importe_ajustado:
                    importe += linea.importe_ajustado
                else:
                    importe += linea.importe
            self.importe = importe
        # Importe ingresado
        elif self.metodo_calculo == 'importe' and not self.compuesto_por_productos:
            self.importe = self.importe_ingresado

    @api.depends('lineas_formula','lineas_producto','lineas_receta','importe_ingresado','coeficiente_de_ajuste')
    @api.onchange('lineas_formula','lineas_producto','lineas_receta','importe_ingresado','coeficiente_de_ajuste')
    def depends_importe(self):
        self.ensure_one()
        self.compute_importe()

    @api.one
    def consolidar_productos(self):

        # Eliminar los renglones existentes
        movimientos = []
        for linea in self.productos_receta:
            linea.unlink()
            # El movimiento que desvincula la linea
            movimientos.append((3,linea.id))

        # Consolidar productos y necesidad
        consolidados = defaultdict(int)
        for una_receta in self.lineas_receta:
            for un_producto in una_receta.product_ids:
                consolidados[un_producto.product_id.id ] += un_producto.necesidad

        # Crear renglones consolidados con valores calculados
        for un_consolidado in consolidados.keys():
            valores = {}
            valores['product_id'] = un_consolidado
            valores['necesidad'] = consolidados[un_consolidado]
            nueva_linea = self.env['grp.pep.concepto.producto.receta'].create(valores)
            nueva_linea.get_precio_de_referencia()
            nueva_linea.compute_importe()
            # El movimiento que añade la tupla creada
            movimientos.append((4,nueva_linea.id))

        # Ejecutar movimientos (eliminar y añadir)
        self.productos_receta = movimientos

    @api.one
    def ajustar_valores(self):
        if self.compuesto_por_productos:
            for linea in self.lineas_producto:
                linea.cantidad_estimada = linea.cantidad_original * self.coeficiente_de_ajuste
                linea.set_cantidad_importe()
        else:
            self.importe = self.importe_original * self.coeficiente_de_ajuste
            self.importe_ingresado = self.importe_original * self.coeficiente_de_ajuste

        self.compute_importe()

    @api.multi
    def productos_sin_precio(self):
        """
        Es capaz de determinar si los conceptos tienen entre sus lineas
        (propias o de receta), al menos un producto sin precio de referencia.
        Retorna la lista de códigos de los conceptos con esa característica.
        """
        res = ""
        for record in self:
            if record.compuesto_por_productos:
                if next((p for p in record.lineas_producto if p.precio_de_referencia == 0), False):
                    res += "%s " % (record.codigo)
            elif record.metodo_calculo == 'receta' and len(record.productos_receta):
                if next((p for p in record.productos_receta if p.precio_de_referencia == 0), False):
                    res += "%s " % (record.codigo)
        return res

    @api.multi
    def llaves_no_suman_100(self):
        """
        Es capaz de determinar si las llaves de cada concepto no totalizan 100%.
        Retorna la lista de códigos de los conceptos con esa característica.
        """
        res = ""
        for record in self:
            total = 0
            for item in record.lineas_gasto:
                total = total + item.porcentaje_del_gasto
            if round(total, 2) != 100:
                res += "%s " % (record.codigo)
        return res

    @api.multi
    def llaves_sin_porcentaje(self):
        """
        Es capaz de determinar si hay llaves de cada concepto sin porcetaje ingresado.
        Retorna la lista de códigos de los conceptos con esa característica.
        """
        res = ""
        for record in self:
            for item in record.lineas_gasto:
                if item.porcentaje_del_gasto == 0:
                    res += "%s " % (record.codigo)
        return res

    @api.multi
    def llaves_ausentes(self, fiscal_year):
        # Se construye un diccionario cuayas claves son las llaves
        llaves_del_presupuesto = {}
        lineas_presupuesto = self.env['presupuesto.linea'].search([('budget_fiscal_year','=',fiscal_year.id)])
        for linea in lineas_presupuesto:
            llave_str = linea.budget_inciso
            llave_str += '-'
            llave_str += linea.ue
            llave_str += '-'
            llave_str += linea.objeto_gasto
            llave_str += '-'
            llave_str += linea.auxiliar
            llave_str += '-'
            llave_str += linea.financiamiento
            llave_str += '-'
            llave_str += linea.programa
            llave_str += '-'
            llave_str += linea.proyecto
            llave_str += '-'
            llave_str += linea.moneda
            llave_str += '-'
            llave_str += linea.tipo_credito
            llaves_del_presupuesto[llave_str] = True

        # Busco las llaves
        llaves_ausentes = ""
        for record in self:
            for linea in record.lineas_gasto:
                if linea.display_name not in llaves_del_presupuesto:
                    llaves_ausentes += "%s" % (record.codigo)

        return llaves_ausentes

    @api.multi
    def total_mov_periodo_llave(self, periodo, llave):
        # Movimientos con su signo (las cancelaciones son negativas)
        condicion = []
        condicion.append(('plan_anual_id','=',self.plan_id.id))
        condicion.append(('periodo','=',periodo))
        condicion.append(('concepto_id','=',self.id))
        condicion.append(('llave_str','=',llave))
        movimientos = self.env['grp.pep.movimiento.ejecucion'].search(condicion)
        total_movimientos = sum(linea.importe for linea in movimientos)
        return total_movimientos

    @api.multi
    def historia_llave_periodo(self, periodo):
        for record in self:
            for linea in record.lineas_gasto:
                values = {}
                values['grp_pep_concepto_id'] = record.id
                values['plan_periodo'] = periodo
                values['llave_str'] = linea.display_name
                values['importe'] = record.total_mov_periodo_llave(periodo, linea.display_name)
                self.env['grp.pep.concepto.historia.llaves'].create(values)

    @api.multi
    def tiene_el_producto(self,product_id):
        """
        Es capaz de determinar si el concepto tiene entre sus lineas (propias o
        de receta), un producto dado.
        """
        self.ensure_one()

        res = False
        if self.compuesto_por_productos:
            if next((p for p in self.lineas_producto if p.product_id.id == product_id), False):
                res = True
        elif self.metodo_calculo == 'receta' and len(self.productos_receta):
            if next((p for p in self.productos_receta if p.product_id.id == product_id), False):
                res = True

        return res

    @api.multi
    def get_linea_producto(self,product_id):
        """
        Retorna un diccionario con los datos pertinentes a un producto dado, tanto
        sea que se encuentre entre los propios o en las recetas.
        """
        self.ensure_one()

        values = {}
        if self.compuesto_por_productos:
            producto = next((p for p in self.lineas_producto if p.product_id.id == product_id), None)
            if producto:
                values['concepto_id'] = self.id
                values['cantidad_original'] = producto.cantidad_estimada
                values['cantidad_a_restar'] = producto.actualizacion
                values['precio_de_referencia'] = producto.precio_de_referencia
                values['importe_original_producto'] = values['cantidad_original'] * values['precio_de_referencia']
        elif self.metodo_calculo == 'receta' and len(self.productos_receta):
            producto = next((p for p in self.productos_receta if p.product_id.id == product_id), None)
            if producto:
                values['concepto_id'] = self.id
                values['cantidad_original'] = producto.necesidad_ajustada if producto.necesidad_ajustada else producto.necesidad
                values['cantidad_a_restar'] = producto.actualizacion
                values['precio_de_referencia'] = producto.precio_de_referencia
                values['importe_original_producto'] = values['cantidad_original'] * values['precio_de_referencia']

        return values

    @api.multi
    def set_linea_producto_actualizacion(self,product_id,actualizacion):
        """
        Graba el campo actualización en la línea del producto
        """
        self.ensure_one()

        if self.compuesto_por_productos:
            producto = next((p for p in self.lineas_producto if p.product_id.id == product_id), None)
            if producto:
                producto.write({'actualizacion': actualizacion})
                producto.set_cantidad_importe()
                self.compute_importe()
        elif self.metodo_calculo == 'receta' and len(self.productos_receta):
            producto = next((p for p in self.productos_receta if p.product_id.id == product_id), None)
            if producto:
                producto.write({'actualizacion': actualizacion})

    @api.multi
    def get_distribucion_gasto_producto(self,product_id):
        """
        Recibe un product_id para el cual retornar la distribución del gasto.
        Retorna un diccionario cuya clave es la combinación ODG-AUX-FF de las
        llaves presentes y como valor el porcentaje correspondiente del importe.
        Además retorna otro diccionario que retorna las cantidades por llave.
        """
        distribucion_del_gasto = defaultdict(float)
        distribucion_de_cantidades = defaultdict(float)

        for record in self:
            if record.compuesto_por_productos:
                producto = next((p for p in record.lineas_producto if p.product_id.id == product_id), None)
                if producto:
                    for llave in record.lineas_gasto:
                        mult_llave = llave.porcentaje_del_gasto / 100.0
                        distribucion_del_gasto[llave.get_odg_aux_ff()] += producto.importe_calculado * mult_llave
                        distribucion_del_gasto[llave.display_name] += producto.importe_calculado * mult_llave
                        distribucion_de_cantidades[llave.get_odg_aux_ff()] += (producto.cantidad_estimada + producto.actualizacion) * mult_llave
                        distribucion_de_cantidades[llave.display_name] += (producto.cantidad_estimada + producto.actualizacion) * mult_llave
            elif record.metodo_calculo == 'receta' and len(record.productos_receta):
                producto = next((p for p in record.productos_receta if p.product_id.id == product_id), None)
                if producto:
                    importe_producto = producto.importe_ajustado if producto.necesidad_ajustada else producto.importe
                    for llave in record.lineas_gasto:
                        mult_llave = llave.porcentaje_del_gasto / 100.0
                        distribucion_del_gasto[llave.get_odg_aux_ff()] += importe_producto * mult_llave
                        distribucion_del_gasto[llave.display_name] += importe_producto * mult_llave
                        if producto.necesidad_ajustada > 0:
                            distribucion_de_cantidades[llave.get_odg_aux_ff()] += producto.necesidad_ajustada
                            distribucion_de_cantidades[llave.display_name] += producto.necesidad_ajustada
                        else:
                            distribucion_de_cantidades[llave.get_odg_aux_ff()] += (producto.necesidad + producto.actualizacion) * mult_llave
                            distribucion_de_cantidades[llave.display_name] += (producto.necesidad + producto.actualizacion) * mult_llave

        # Redondeo a int los valores de las cantidades
        distribucion_de_cantidades_aux = dict()
        for k, v in distribucion_de_cantidades.iteritems():
            distribucion_de_cantidades_aux[k] = int(round(v))

        return distribucion_del_gasto, distribucion_de_cantidades_aux

    @api.multi
    def get_producto_necesidad(self):
        """
            Retorna un diccionario { product_id: <necesidad para ese producto> }
            que mapea los ids de los productos que aparecen en conceptos de self y sus recetas
            con la necesidad estipulada para dicho producto en el conjunto de conceptos
            considerado
        """
        necesidad = defaultdict(int)
        for record in self:
            if record.compuesto_por_productos:
                for linea in record.lineas_producto:
                    necesidad[linea.product_id.id] += linea.cantidad_estimada
            elif record.metodo_calculo == 'receta' and len(record.productos_receta):
                for linea in record.productos_receta:
                    if linea.necesidad_ajustada:
                        necesidad[linea.product_id.id] += linea.necesidad_ajustada
                    else:
                        necesidad[linea.product_id.id] += linea.necesidad
        return necesidad

    @api.multi
    def get_producto_necesidad_actualizada(self):
        """
            Retorna un diccionario { product_id: <necesidad actualizada para ese producto> }
            que mapea los ids de los productos que aparecen en conceptos de self y sus recetas
            con la necesidad estipulada para dicho producto en el conjunto de conceptos
            considerado teniendo en cuenta la actualización.
        """
        necesidad = defaultdict(int)
        for record in self:
            if record.compuesto_por_productos:
                for linea in record.lineas_producto:
                    necesidad[linea.product_id.id] += (linea.cantidad_estimada + linea.actualizacion)
            elif record.metodo_calculo == 'receta' and len(record.productos_receta):
                for linea in record.productos_receta:
                    if linea.necesidad_ajustada:
                        necesidad[linea.product_id.id] += (linea.necesidad_ajustada + linea.actualizacion)
                    else:
                        necesidad[linea.product_id.id] += (linea.necesidad + linea.actualizacion)
        return necesidad

    @api.multi
    def get_productos_y_sus_conceptos(self):
        """
            Retorna un diccionario que mapea los id de producto de
            conceptos considerados en self con el set de ids de conceptos
            en los que aparece cada producto.
        """
        dict_prod_conceptos = defaultdict(set)
        for record in self:
            if record.compuesto_por_productos:
                for linea in record.lineas_producto:
                    dict_prod_conceptos[linea.product_id.id].add(record.id)
            elif record.metodo_calculo == 'receta' and len(record.productos_receta):
                for linea in record.productos_receta:
                    dict_prod_conceptos[linea.product_id.id].add(record.id)

        return dict_prod_conceptos

    @api.multi
    def filtrar_sin_productos(self):
        """
            Retorna un recordset de conceptos que se forma partiendo del original
            quedandome solo con aquellos conceptos que no tienen productos.
        """
        # La condición de filtrado es lo que sería el ELSE en la función get_productos
        # o sea que los conceptos que se consideran allí, son los que se excluyen acá
        conceptos_sin_productos = self.filtered(lambda x: not x.compuesto_por_productos and not (x.metodo_calculo == 'receta' and len(x.productos_receta)))
        return conceptos_sin_productos

grp_pep_concepto()


class grp_pep_concepto_linea_producto(models.Model):
    _name = 'grp.pep.concepto.linea.producto'

    grp_pep_concepto_id = fields.Many2one(string=u'Concepto', comodel_name='grp.pep.concepto', ondelete='cascade')
    product_id = fields.Many2one(string='Producto', comodel_name='product.product', required=True)
    grp_sice_cod = fields.Integer(related='product_id.grp_sice_cod')
    uom_id = fields.Many2one(related='product_id.uom_id', string=u'Unidad')
    pres_id = fields.Many2one(related='product_id.pres_id')
    med_cod_pres_id = fields.Many2one(related='product_id.med_cod_pres_id')
    precio_de_referencia = fields.Float(string=u'Precio de referencia', help='Impuestos incluidos', required=True)
    cantidad_estimada = fields.Integer(string='Cantidad estimada')
    cantidad_original = fields.Integer(string='Cantidad original')
    importe_total = fields.Float(string='Importe ingresado', default=None)
    importe_calculado = fields.Float(string='Total', compute='_compute_importe')
    calculo_por_cantidad = fields.Boolean(string=u'Cálculo', default=True, help=u'Se calcula el importe a partir de la cantidad estimada')
    necesidad = fields.Integer(string='Necesidad')
    actualizacion = fields.Integer(string=u'Actualización', help=u'Surge de la actualización del plan')


    @api.one
    @api.onchange('product_id')
    def get_precio_de_referencia(self):
        if self.product_id:
            self._cr.execute(price_unit_query,{'producto':self.product_id.id})
            self.precio_de_referencia = self._cr.fetchone()[0] if self._cr.rowcount else 0.0

    @api.one
    @api.depends('precio_de_referencia','cantidad_estimada','importe_total','calculo_por_cantidad','actualizacion')
    @api.onchange('precio_de_referencia','cantidad_estimada','importe_total','calculo_por_cantidad','actualizacion')
    def set_cantidad_importe(self):
        if not self.calculo_por_cantidad:
            if self.precio_de_referencia and self.importe_total:
                self.cantidad_estimada = self.importe_total / self.precio_de_referencia
                self.necesidad = self.cantidad_estimada + self.actualizacion

    @api.one
    @api.constrains('precio_de_referencia','cantidad_estimada','importe_total')
    def _valores_positivos(self):
        if self.precio_de_referencia < 0:
            raise ValidationError(u"El precio debe ser mayor a 0")
        if self.cantidad_estimada <= 0:
            raise ValidationError(u"La cantidad debe ser mayor a 0")
        if self.importe_calculado <= 0:
            raise ValidationError(u"El importe debe ser mayor a 0")

    @api.multi
    def _compute_importe(self):
        for rec in self:
            if rec.calculo_por_cantidad:
                if rec.precio_de_referencia and rec.cantidad_estimada:
                    rec.importe_calculado = rec.precio_de_referencia * (rec.cantidad_estimada + rec.actualizacion)
                    rec.importe_total = rec.importe_calculado
            else:
                if rec.precio_de_referencia and rec.importe_total:
                    rec.cantidad_estimada = rec.importe_total / rec.precio_de_referencia
                    rec.necesidad = rec.cantidad_estimada + rec.actualizacion
                    rec.importe_calculado = rec.importe_total

grp_pep_concepto_linea_producto()


class grp_pep_concepto_linea_receta(models.Model):
    _name = 'grp.pep.concepto.linea.receta'

    grp_pep_concepto_id = fields.Many2one(string=u'Concepto', comodel_name='grp.pep.concepto', ondelete='cascade')
    receta_id = fields.Many2one(string='Receta', comodel_name='grp.pep.receta', required=True)
    es_poblacion_atendida = fields.Boolean(related='receta_id.es_poblacion_atendida')
    atributo_id = fields.Many2one(related='receta_id.atributo_id')
    active = fields.Boolean(related='receta_id.active')
    receta_create_date = fields.Datetime(related='receta_id.create_date')

grp_pep_concepto_linea_receta()


class grp_pep_concepto_producto_receta(models.Model):
    _name = 'grp.pep.concepto.producto.receta'

    grp_pep_concepto_id = fields.Many2one(string=u'Concepto', comodel_name='grp.pep.concepto', ondelete='cascade')
    product_id = fields.Many2one(string='Producto', comodel_name='product.product', required=True)
    grp_sice_cod = fields.Integer(related='product_id.grp_sice_cod')
    uom_id = fields.Many2one(related='product_id.uom_id', string=u'Unidad')
    pres_id = fields.Many2one(related='product_id.pres_id')
    med_cod_pres_id = fields.Many2one(related='product_id.med_cod_pres_id')
    precio_de_referencia = fields.Float(string=u'Precio de referencia', help='Impuestos incluidos')
    necesidad = fields.Integer(string='Necesidad')
    importe = fields.Float(string='Importe', compute='compute_importe')
    necesidad_ajustada = fields.Integer(string='Necesidad ajustada')
    importe_ajustado = fields.Float(string='Importe ajustado', compute='compute_importe_ajustado')
    actualizacion = fields.Integer(string=u'Actualización', help=u'Surge de la actualización del plan')

    @api.one
    @api.depends('product_id')
    def get_precio_de_referencia(self):
        if self.product_id:
            self._cr.execute(price_unit_query,{'producto':self.product_id.id})
            self.precio_de_referencia = self._cr.fetchone()[0] if self._cr.rowcount else 0.0

    @api.one
    @api.depends('precio_de_referencia', 'necesidad','actualizacion')
    def compute_importe(self):
        if self.necesidad:
            self.importe = self.precio_de_referencia * (self.necesidad + self.actualizacion)

    @api.one
    @api.depends('precio_de_referencia', 'necesidad_ajustada','actualizacion')
    @api.onchange('precio_de_referencia', 'necesidad_ajustada')
    def compute_importe_ajustado(self):
        if self.necesidad_ajustada:
            self.importe_ajustado = self.precio_de_referencia * (self.necesidad_ajustada + self.actualizacion)

grp_pep_concepto_producto_receta()


class grp_pep_concepto_linea_gasto(models.Model):
    _name = 'grp.pep.concepto.linea.gasto'

    display_name = fields.Char(string='Nombre', compute='compute_display_name')
    grp_pep_concepto_id = fields.Many2one(string=u'Concepto', comodel_name='grp.pep.concepto', ondelete='cascade')
    plan_id = fields.Many2one(related='grp_pep_concepto_id.plan_id', store=True)
    porcentaje_del_gasto = fields.Float(string='Porcentaje')
    inciso_id = fields.Many2one(string=u'Inciso', comodel_name='grp.estruc_pres.inciso', required=True)
    ue_id = fields.Many2one(string=u'Unidad ejecutora', comodel_name='grp.estruc_pres.ue', required=True)
    odg_id = fields.Many2one(string=u'ODG', comodel_name='grp.estruc_pres.odg', required=True)
    aux_id = fields.Many2one(string=u'Auxiliar', comodel_name='grp.estruc_pres.aux', required=True)
    ff_id = fields.Many2one(string=u'Fuente de financiamiento', comodel_name='grp.estruc_pres.ff', required=True)
    programa_id = fields.Many2one(string=u'Programa', comodel_name='grp.estruc_pres.programa', required=True)
    proyecto_id = fields.Many2one(string=u'Proyecto', comodel_name='grp.estruc_pres.proyecto', required=True)
    moneda_id = fields.Many2one(string=u'Moneda', comodel_name='grp.estruc_pres.moneda', required=True)
    tc_id = fields.Many2one(string=u'Tipo de crédito', comodel_name='grp.estruc_pres.tc', required=True)
    importe_anual = fields.Float(string='Importe anual', compute='compute_importe_anual')
    saldo = fields.Float(string='Saldo', compute='compute_saldo')


    @api.one
    def compute_importe_anual(self):
        # Si hay línea de ejecución
        linea_ejecucion = next((linea for linea in self.plan_id.lineas_ejecucion if self.grp_pep_concepto_id.id == linea.concepto_id.id),None)
        if linea_ejecucion:
            # El importe inicial se toma de la ejecución y sus ajustes
            self.importe_anual = linea_ejecucion.importe_anual_llave(self.display_name)

    @api.one
    def compute_saldo(self):
        # Si hay línea de ejecución
        linea_ejecucion = next((linea for linea in self.plan_id.lineas_ejecucion if self.grp_pep_concepto_id.id == linea.concepto_id.id),None)
        if linea_ejecucion:
            # El importe inicial se toma de la ejecución y sus ajustes
            importe_anual = linea_ejecucion.importe_anual_llave(self.display_name)

            # Aplico los movimientos con su signo (las cancelaciones son negativas)
            condicion = []
            condicion.append(('plan_anual_id','=',self.plan_id.id))
            condicion.append(('concepto_id','=',self.grp_pep_concepto_id.id))
            condicion.append(('llave_str','=',self.display_name))
            movimientos = self.env['grp.pep.movimiento.ejecucion'].search(condicion)
            total_movimientos = sum(linea.importe for linea in movimientos)
            self.saldo = importe_anual - total_movimientos

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(grp_pep_concepto_linea_gasto, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        if 'importe_anual' in fields:
            for linea in res:
                if '__domain' in linea:
                    total = 0.0
                    for llave in self.search(linea['__domain']):
                        total += llave.importe_anual
                    linea['importe_anual'] = total

        if 'saldo' in fields:
            for linea in res:
                if '__domain' in linea:
                    total = 0.0
                    for llave in self.search(linea['__domain']):
                        total += llave.saldo
                    linea['saldo'] = total

        return res

    @api.model
    def create(self, values):
        res = super(grp_pep_concepto_linea_gasto, self).create(values)
        # Si ya tengo plan
        if res.grp_pep_concepto_id.plan_id:
            # Y el plan está en ejecución
            if res.grp_pep_concepto_id.plan_state == 'en_ejecucion':
                # Notifico que hay llave nueva a la linea de ejecución pertinente
                linea_ejecucion = next((linea for linea in res.grp_pep_concepto_id.plan_id.lineas_ejecucion if res.grp_pep_concepto_id.id == linea.concepto_id.id),None)
                if linea_ejecucion:
                    linea_ejecucion.nueva_llave(res.display_name)

        return res

    @api.multi
    def write(self, values):
        for record in self:
            # Si ya tengo plan
            if record.grp_pep_concepto_id.plan_id:
                # Y el plan está en ejecución
                if record.grp_pep_concepto_id.plan_state == 'en_ejecucion':
                    # No se pueden modificar las llaves
                    campos_llave = ['inciso_id','ue_id','odg_id','aux_id','ff_id','programa_id','proyecto_id','moneda_id','tc_id']
                    if set(values.keys()) & set(campos_llave):
                        raise ValidationError(u"No puede modificar llaves durante la ejecución del Plan.")
            super(grp_pep_concepto_linea_gasto, record).write(values)

        return True

    @api.multi
    def unlink(self):
        for record in self:
            # Si ya tengo plan
            if record.grp_pep_concepto_id.plan_id:
                # Y el plan está en ejecución
                if record.grp_pep_concepto_id.plan_state == 'en_ejecucion':
                    raise ValidationError(u"No puede eliminar llaves durante la ejecución del Plan.")
            super(grp_pep_concepto_linea_gasto, record).unlink()

    @api.one
    @api.depends('inciso_id','ue_id','odg_id','aux_id','ff_id','programa_id','proyecto_id','moneda_id','tc_id')
    def compute_display_name(self):
        display_name  = self.inciso_id.display_name
        display_name += '-'
        display_name += self.ue_id.display_name
        display_name += '-'
        display_name += self.odg_id.display_name
        display_name += '-'
        display_name += self.aux_id.display_name
        display_name += '-'
        display_name += self.ff_id.display_name
        display_name += '-'
        display_name += self.programa_id.display_name
        display_name += '-'
        display_name += self.proyecto_id.display_name
        display_name += '-'
        display_name += self.moneda_id.display_name
        display_name += '-'
        display_name += self.tc_id.display_name
        self.display_name = display_name

    @api.multi
    def get_odg_aux_ff(self):
        """
        Retorna la combinación ODG-SUX-FF de la línea de gasto (llave))
        """
        self.ensure_one()
        res = get_odg_aux_ff(self.odg_id, self.aux_id, self.ff_id)
        return res

    @api.onchange('programa_id','proyecto_id')
    def verify_programa_proyecto(self):

        # Si estan los valores ingresado sy hay recetas
        if self.programa_id and self.proyecto_id and len(self.grp_pep_concepto_id.lineas_receta):

            # La dupla a buscar
            programa_proyecto = self.programa_id.display_name + '-' + self.proyecto_id.display_name

            # El query
            query  = "select r.programa_proyecto from ( "
            query += "    select g.id, g.receta_id, g.programa_id, g.proyecto_id, "
            query += "        m.programa, t.proyecto, concat(m.programa,'-',t.proyecto) as programa_proyecto "
            query += "    from grp_pep_receta_distribucion g "
            query += "    join grp_estruc_pres_programa m ON m.id = g.programa_id "
            query += "    join grp_estruc_pres_proyecto t ON t.id = g.proyecto_id "
            query += "    where receta_id = %(receta_id)s "
            query += ") r where r.programa_proyecto = %(programa_proyecto)s; "

            # La bandera de advertencia
            advertir = True

            # Buscar
            for receta in self.grp_pep_concepto_id.lineas_receta:
                self._cr.execute(query,{'receta_id': receta.id, 'programa_proyecto': programa_proyecto})
                if self._cr.rowcount:
                    advertir = False

            # Advertencia
            if advertir:
                return {
                    'warning': {
                        'title': 'Programa - Proyecto',
                        'message': 'Esta combinación no se encuantra en ninguna receta asoicada.'
                    },
                }

grp_pep_concepto_linea_gasto()


class grp_pep_concepto_historia_llaves(models.Model):
    _name = 'grp.pep.concepto.historia.llaves'
    _order = 'plan_periodo'


    grp_pep_concepto_id = fields.Many2one(string=u'Concepto', comodel_name='grp.pep.concepto', ondelete='cascade')
    plan_periodo = fields.Integer(string=u'Período')
    periodo_par = fields.Boolean(string=u'Período par', compute='_periodo_es_par')
    llave_str = fields.Char(string='Llave')
    importe = fields.Float(string='Importe', help='Total de movimientos en el período.')


    @api.multi
    def _periodo_es_par(self):
        for record in self:
            record.periodo_par = (record.plan_periodo % 2) == 0

grp_pep_concepto_historia_llaves()
