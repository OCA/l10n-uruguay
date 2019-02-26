# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 Datamatic. All rights reserved.
#    @author Roberto Garcés
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api
from openerp.exceptions import ValidationError
import math
import logging


_logger = logging.getLogger(__name__)


class grp_pep_receta(models.Model):
    _name = 'grp.pep.receta'

    # máxima cantidad de niveles
    MAXIMA_PROFUNDIDAD = 10

    @api.one
    def _compute_atendida(self):
        self.atendida_view = self.atendida

    @api.one
    def _compute_path_texto(self):
        self.path_texto = self.path

    name = fields.Char(string='Nombre')
    active = fields.Boolean(string='Activo', default=True)
    create_date = fields.Datetime(string=u'Fecha de creación', readonly=True)
    codigo = fields.Integer(string='Código')
    descripcion = fields.Char(string='Descripción', required=True)
    concepto_id = fields.Many2one(comodel_name='grp.pep.concepto', string='Concepto', required=True)
    plan_id = fields.Many2one(comodel_name='grp.pep.anual', string='Plan anual', required=True)
    estructura_id = fields.Many2one(related='plan_id.estructura_de_servicios_id', string=u'Estructura de servicios')
    es_compatible_con_es = fields.Boolean(string='Es compatible', compute='computo_compatibilidad',default=True)
    usar_receta = fields.Boolean(string='Usar receta', readonly=True)
    receta_id = fields.Many2one(comodel_name='grp.pep.receta', string='Receta relacionada', readonly=True)
    coeficiente = fields.Float(string='Coeficiente', default=1.0)
    path = fields.Char(string='path')
    path_texto = fields.Char(string='Unidades de servicio', compute='_compute_path_texto', readonly=True)
    es_poblacion_atendida = fields.Boolean(string=u'Es población atendida', default=True)
    atributo_id = fields.Many2one(comodel_name='grp.pep.estructura.atributo', string=u'Tipo de población')
    atendida = fields.Integer(string=u'Población atendida')
    atendida_view = fields.Integer(string=u'Población atendida', readonly=True, compute="_compute_atendida", store=False)
    texto_nivel_1 = fields.Char(string=u'Unidades del nivel 1', readonly=True)
    texto_nivel_2 = fields.Char(string=u'Unidades del nivel 2', readonly=True)
    texto_nivel_3 = fields.Char(string=u'Unidades del nivel 3', readonly=True)
    texto_nivel_4 = fields.Char(string=u'Unidades del nivel 4', readonly=True)
    texto_nivel_5 = fields.Char(string=u'Unidades del nivel 5', readonly=True)
    texto_nivel_6 = fields.Char(string=u'Unidades del nivel 6', readonly=True)
    texto_nivel_7 = fields.Char(string=u'Unidades del nivel 7', readonly=True)
    texto_nivel_8 = fields.Char(string=u'Unidades del nivel 8', readonly=True)
    texto_nivel_9 = fields.Char(string=u'Unidades del nivel 9', readonly=True)
    texto_nivel_10 = fields.Char(string=u'Unidades del nivel 10', readonly=True)
    niveles_estructura = fields.Char(string='Niveles de la estructura')
    atributo_estructura = fields.Char(string='Atributo de la estructura')
    path_por_niveles = fields.Char(string='Path por niveles')
    gasto_ids = fields.One2many(comodel_name='grp.pep.receta.distribucion', inverse_name='receta_id',
                                string=u'Distribución del gasto', copy=True, required=False)
    product_ids = fields.One2many(comodel_name='grp.pep.receta.producto', inverse_name='receta_id', string='Productos',
                                  copy=True, required=False)

    @api.onchange('es_poblacion_atendida')
    def onchange_es_poblacion_atendida(self):
        atributo = None
        if not self.es_poblacion_atendida:
            atributo = self.atributo_id.name
        if self.path:
            lista = self.estructura_id.obtener_info_niveles_por_path(self.path, atributo)
            cant_atendida = lista[0]['cantidad']
            self.atendida = cant_atendida
            self.atendida_view = self.atendida
        self.actualizo_necesidades()

    @api.onchange('atributo_id')
    def onchange_atributo_id(self):
        self.atributo_estructura = ''
        if self.atributo_id:
            self.atributo_estructura = self.atributo_id.name
            lista = self.estructura_id.obtener_info_niveles_por_path(self.path, self.atributo_estructura)
            self.atendida = lista[0]['cantidad']
            self.atendida_view = self.atendida
        self.actualizo_necesidades()

    @api.onchange('atributo_id', 'path')
    def onchange_niveles(self):
        if self.path:
            self.computo_niveles()

    @api.onchange('coeficiente')
    def onchange_coeficiente(self):
        self.computo_niveles()

    @api.one
    def computo_compatibilidad(self):
        atributo_ok = True
        niveles_ok = True
        recetas_ok = True
        if self.estructura_id:
            # valido los niveles
            str_niveles_actual = '|'.join(self.estructura_id.obtener_lista_niveles())
            if not self.niveles_estructura or len(self.niveles_estructura) == 0 or len(str_niveles_actual) == 0:
                niveles_ok = False
            else:
                niveles_ok = str_niveles_actual.startswith(str(self.niveles_estructura))
            # valido el atributo
            if not self.es_poblacion_atendida:
                atributo_ok = self.estructura_id._existe_atributo(self.atributo_estructura)
            # valido las recetas
            ultimo_nivel = str_niveles_actual.count('|') + 1
            primer_nivel_valido = 0
            if self.path_texto:
                primer_nivel_valido = self.path_texto.count('|') + 2
            for producto in self.product_ids:
                nivel = producto.criterio_nivel
                necesidad = producto.necesidad
                if not producto.es_criterio_usuario and (nivel < primer_nivel_valido or nivel > ultimo_nivel):
                    recetas_ok = False
                    break
                if necesidad <= 0:
                    recetas_ok = False
                    break
            self.es_compatible_con_es = niveles_ok and atributo_ok and recetas_ok

    @api.one
    @api.onchange('path', 'path_texto', 'atributo_id', 'es_poblacion_atendida')
    def computo_niveles(self):
        atributo = None
        cant_atendida = 0
        if not self.es_poblacion_atendida:
            atributo = self.atributo_estructura
        if self.path:
            lista = self.estructura_id.obtener_info_niveles_por_path(self.path, atributo)
            if lista:
                cant_atendida = lista[0]['cantidad']
                self.atendida = cant_atendida
                self.atendida_view = self.atendida
                for elemento in lista[1:]:
                    nivel_nombre = elemento['nivel_nombre']
                    nivel_nro = elemento['nivel_numero']
                    cantidad = elemento['cantidad']
                    setattr(self, 'texto_nivel_'+str(nivel_nro), nivel_nombre + ': ' + str(cantidad))
            else:
                cant_atendida = 0
                self.atendida = cant_atendida
                self.atendida_view = self.atendida
                for i in range(1, 13):
                    setattr(self, 'texto_nivel_' + str(i), False)
            self._set_datos_estructura()
            self.actualizo_necesidades()

    @api.one
    @api.onchange('path')
    def _set_datos_estructura(self):
        if self.estructura_id:
            lista_niveles = self.estructura_id.obtener_lista_niveles()
            ultimo_nivel_path = self.path.count('|') + 1
            self.niveles_estructura = '|'.join(lista_niveles[0:ultimo_nivel_path])

    @api.one
    def actualizo_compatibilidad(self):
        self.computo_compatibilidad()
        if self.es_compatible_con_es:
            self.computo_niveles()

    def actualizo_necesidades(self):
        for linea in self.product_ids:
            linea.calculo_necesidad()

    @api.multi
    def productos_sin_necesidad(self):
        res = ""
        for record in self:
            for linea in record.product_ids:
                if not linea.necesidad:
                    res += "%s " % (record.name)
        return res

    @api.multi
    def button_get_path(self):
        wiz_id = self.env['grp.pep.receta.us.wizard'].create({
            'receta_id': self.id,
        })
        return {
            'name': "Unidades de servicio",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.receta.us.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    @api.model
    def create(self, values):
        codigo = self.env['ir.sequence'].next_by_code('grp.pep.receta.code')
        values['codigo'] = codigo
        values['name'] = codigo + '-' + values['descripcion']
        res = super(grp_pep_receta, self).create(values)
        return res

    @api.one
    def copy(self, default=None):
        default = default or {}
        default.update({
            'usar_receta': True,
            'receta_id': self.id,
        })
        new = super(grp_pep_receta, self).copy(default)
        return new

grp_pep_receta()


class grp_pep_receta_producto(models.Model):
    _name = 'grp.pep.receta.producto'

    CR_USUARIO = 'usuario'
    CR_CANT_FIJA = 'cantidad_fija'
    CR_CANT_VARIABLE = 'cantidad_variable'

    LISTA_NIVELES = [(1, 'nivel 1'),
                     (2, 'nivel 2'),
                     (3, 'nivel 3'),
                     (4, 'nivel 4'),
                     (5, 'nivel 5'),
                     (6, 'nivel 6'),
                     (7, 'nivel 7'),
                     (8, 'nivel 8'),
                     (9, 'nivel 9'),
                     (10, 'nivel 10')]

    def _get_criterios(self):
        criterios = []
        if self.estructura_id:
            criterios = self.estructura_id.obtener_lista_niveles()
        return criterios

    def _get_ultimo_nivel(self):
        return len(self.receta_id.estructura_id.obtener_lista_niveles())

    receta_id = fields.Many2one(comodel_name='grp.pep.receta', string='Receta', ondelete='cascade')
    estructura_id = fields.Many2one(related='receta_id.plan_id.estructura_de_servicios_id', string=u'Estructura de servicios')
    product_id = fields.Many2one(comodel_name='product.product', string='Producto')
    uom_id = fields.Many2one(related='product_id.uom_id', string=u'Unidad')
    pres_id = fields.Many2one(related='product_id.pres_id', string=u'Presentación')
    es_criterio_usuario = fields.Boolean(string='Beneficiario')
    criterio_nivel = fields.Selection(selection=LISTA_NIVELES, string='Criterio')
    criterio_tipo = fields.Selection(selection=[(CR_CANT_FIJA, 'Fija'),
                                                (CR_CANT_VARIABLE, 'Variable')], default=CR_CANT_FIJA, string='Tipo Cantidad')
    cantidad = fields.Integer(string=u'Cantidad', required=True)
    necesidad = fields.Integer(string='Necesidad')
    necesidad_readonly = fields.Integer(string='Necesidad', compute='computo_necesidad')

    def valido_criterio(self):
        if self.product_id:
            if self.criterio_nivel:
                ultimo_nivel = self._get_ultimo_nivel()
                receta = self.receta_id
                primer_nivel_valido = receta.path_texto.count('|') + 2
                if self.criterio_nivel < primer_nivel_valido or self.criterio_nivel > ultimo_nivel:
                    return False
        return True

    @api.onchange('product_id', 'cantidad', 'criterio_nivel', 'es_criterio_usuario', 'criterio_tipo')
    def calculo_necesidad(self):
        if self.valido_criterio():
            if self.product_id:
                nueva_necesidad = 0
                receta_id = self.receta_id
                # CRITERIO USUARIO
                if self.es_criterio_usuario:
                    if receta_id.atendida >= 0 and self.cantidad >= 0:
                        nueva_necesidad = receta_id.atendida * self.cantidad
                elif self.criterio_nivel and self.criterio_tipo:
                    total_unidades = 0.0
                    texto_unidades = getattr(receta_id, 'texto_nivel_' + str(self.criterio_nivel))
                    if texto_unidades:
                        unidad, unidades = texto_unidades.split(':')
                        total_unidades = float(unidades)
                    # CRITERIO FIJO
                    if self.criterio_tipo == self.CR_CANT_FIJA:
                        nueva_necesidad = total_unidades * self.cantidad
                    elif self.criterio_tipo == self.CR_CANT_VARIABLE:
                        if self.cantidad > 0:
                            nueva_necesidad = math.ceil(receta_id.atendida / float(self.cantidad)) * total_unidades
                self.necesidad = math.ceil(nueva_necesidad * receta_id.coeficiente)
                self.necesidad_readonly = self.necesidad
                self.write({'necesidad': self.necesidad})
        else:
            self.criterio_nivel = self.receta_id.path_texto.count('|') + 2
            return {
                'warning': {'title': 'Error', 'message': u'Este criterio elegido no es válido.'},
            }

    @api.one
    def computo_necesidad(self):
        self.necesidad_readonly = self.necesidad

grp_pep_receta_producto()


class grp_pep_receta_distribucion(models.Model):
    _name = 'grp.pep.receta.distribucion'

    receta_id = fields.Many2one(comodel_name='grp.pep.receta', string='Receta', ondelete='cascade')
    programa_id = fields.Many2one(comodel_name='grp.estruc_pres.programa', string='Programa')
    proyecto_id = fields.Many2one(comodel_name='grp.estruc_pres.proyecto', string='Proyecto')

grp_pep_receta_distribucion()


class grp_pep_nivel_de_aplicacion(models.Model):
    _name = 'grp.pep.nivel.de.aplicacion'

    unidad_nombre = fields.Char(string='Nombre')
    nivel_nro = fields.Integer(string=u'Número')

grp_pep_nivel_de_aplicacion()
