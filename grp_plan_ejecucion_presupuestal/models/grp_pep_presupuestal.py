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

from openerp import models, fields, api, tools
from openerp.exceptions import Warning, ValidationError
import openerp.addons.decimal_precision as dp


class grp_pep_anual_linea_concepto(models.Model):
    _name = 'grp.pep.anual.linea.concepto'

    plan_anual_id = fields.Many2one(string=u'Plan Anual', comodel_name='grp.pep.anual')
    concepto_id = fields.Many2one(string=u'Concepto', comodel_name='grp.pep.concepto', domain=[('plan_id', '=', None)])
    posicion_en_plan = fields.Integer(related='concepto_id.posicion_en_plan', string=u'Posición')
    metodo_calculo = fields.Selection(related='concepto_id.metodo_calculo', string=u'Método de cálculo', readonly=True)
    importe_anual = fields.Float(related='concepto_id.importe', string=u'Importe anual', readonly=True)
    periodicidad = fields.Selection(related='plan_anual_id.periodicidad', string='Periodicidad', readonly=True)
    periodo1_porc = fields.Float(string=u'Período 1', digits=dp.get_precision('PEP Porcentajes'))
    periodo2_porc = fields.Float(string=u'Período 2', digits=dp.get_precision('PEP Porcentajes'))
    periodo3_porc = fields.Float(string=u'Período 3', digits=dp.get_precision('PEP Porcentajes'))
    periodo4_porc = fields.Float(string=u'Período 4', digits=dp.get_precision('PEP Porcentajes'))
    periodo5_porc = fields.Float(string=u'Período 5', digits=dp.get_precision('PEP Porcentajes'))
    periodo6_porc = fields.Float(string=u'Período 6', digits=dp.get_precision('PEP Porcentajes'))
    periodo7_porc = fields.Float(string=u'Período 7', digits=dp.get_precision('PEP Porcentajes'))
    periodo8_porc = fields.Float(string=u'Período 8', digits=dp.get_precision('PEP Porcentajes'))
    periodo9_porc = fields.Float(string=u'Período 9', digits=dp.get_precision('PEP Porcentajes'))
    periodo10_porc = fields.Float(string=u'Período 10', digits=dp.get_precision('PEP Porcentajes'))
    periodo11_porc = fields.Float(string=u'Período 11', digits=dp.get_precision('PEP Porcentajes'))
    periodo12_porc = fields.Float(string=u'Período 12', digits=dp.get_precision('PEP Porcentajes'))

    # Restricción en la base de datos para garantizar que no se repitan conceptos
    _sql_constraints=[('unique_concept','unique(plan_anual_id,concepto_id)',"Este concepto ya existe en este plan.")]

    def controlo_maximo(self):
        if self.concepto_id:
            total = 0
            rango = int(self.periodicidad) + 1
            for i in range(1, rango):
                porcentaje = getattr(self, 'periodo' + str(i) + '_porc')
                total = total + porcentaje
            if round(total, 2) != 100:
                raise ValidationError(u'La suma de los porcentajes para el concepto %s no es igual a 100.' % self.concepto_id.name)

    @api.onchange('periodo1_porc', 'periodo2_porc', 'periodo3_porc', 'periodo4_porc', 'periodo5_porc',
                  'periodo6_porc', 'periodo7_porc', 'periodo8_porc', 'periodo9_porc', 'periodo10_porc',
                  'periodo11_porc', 'periodo12_porc', 'periodicidad')
    def controlo_rango(self):
        if self.concepto_id:
            rango = int(self.periodicidad) + 1
            for i in range(1, rango):
                porcentaje = getattr(self, 'periodo' + str(i) + '_porc')
                if porcentaje < 0:
                    raise ValidationError(u'El porcentaje no puede menor que cero.')
                if porcentaje > 100:
                    raise ValidationError(u'El porcentaje no puede ser mayor a 100.')

    @api.one
    def carga_porcentajes_por_defecto(self):
        valores = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        tope = int(self.periodicidad) - 1
        for i in range(0, tope):
            valores[i] = int(float(100) / (tope+1))
        suma = sum(valores)
        valores[tope] = 100 - suma
        for i in range(1, 13):
            setattr(self, 'periodo' + str(i) + '_porc', valores[i-1])

    @api.multi
    def porcentajes_no_100(self):
        """
        Es capaz de determinar si los porcentajes no suman 100%.
        Retorna la lista de códigos de los conceptos con esa característica.
        """
        res = ""
        for record in self:
            total = 0
            rango = int(record.periodicidad) + 1
            for i in range(1, rango):
                porcentaje = getattr(record, 'periodo' + str(i) + '_porc')
                total = total + porcentaje
            if round(total, 2) != 100:
                res += "%s " % (record.concepto_id.codigo)
        return res

    @api.model
    def create(self, values):
        res = super(grp_pep_anual_linea_concepto, self).create(values)
        # Notifico al concepto
        res.concepto_id.write({'state': 'plan'})
        vals = {'linea_concepto_id': res.id,
                'plan_anual_id': res.plan_anual_id.id,
                'concepto_id': res.concepto_id.id,
                'metodo_calculo': res.metodo_calculo,
                'importe_anual': res.importe_anual,
                'periodicidad': res.periodicidad,
                'periodo1_importe': (res.importe_anual * res.periodo1_porc) / 100,
                'periodo2_importe': (res.importe_anual * res.periodo2_porc) / 100,
                'periodo3_importe': (res.importe_anual * res.periodo3_porc) / 100,
                'periodo4_importe': (res.importe_anual * res.periodo4_porc) / 100,
                'periodo5_importe': (res.importe_anual * res.periodo5_porc) / 100,
                'periodo6_importe': (res.importe_anual * res.periodo6_porc) / 100,
                'periodo7_importe': (res.importe_anual * res.periodo7_porc) / 100,
                'periodo8_importe': (res.importe_anual * res.periodo8_porc) / 100,
                'periodo9_importe': (res.importe_anual * res.periodo9_porc) / 100,
                'periodo10_importe': (res.importe_anual * res.periodo10_porc) / 100,
                'periodo11_importe': (res.importe_anual * res.periodo11_porc) / 100,
                'periodo12_importe': (res.importe_anual * res.periodo12_porc) / 100,
                }
        llave = self.env['grp.pep.anual.linea.gasto'].create(vals)
        return res

    @api.multi
    def write(self, values):
        res = super(grp_pep_anual_linea_concepto, self).write(values)
        llave = self.env['grp.pep.anual.linea.gasto'].search([('plan_anual_id', '=', self.plan_anual_id.id),
                                                              ('concepto_id', '=', self.concepto_id.id)])
        vals = {'periodo1_importe': (self.importe_anual * self.periodo1_porc) / 100,
                'periodo2_importe': (self.importe_anual * self.periodo2_porc) / 100,
                'periodo3_importe': (self.importe_anual * self.periodo3_porc) / 100,
                'periodo4_importe': (self.importe_anual * self.periodo4_porc) / 100,
                'periodo5_importe': (self.importe_anual * self.periodo5_porc) / 100,
                'periodo6_importe': (self.importe_anual * self.periodo6_porc) / 100,
                'periodo7_importe': (self.importe_anual * self.periodo7_porc) / 100,
                'periodo8_importe': (self.importe_anual * self.periodo8_porc) / 100,
                'periodo9_importe': (self.importe_anual * self.periodo9_porc) / 100,
                'periodo10_importe': (self.importe_anual * self.periodo10_porc) / 100,
                'periodo11_importe': (self.importe_anual * self.periodo11_porc) / 100,
                'periodo12_importe': (self.importe_anual * self.periodo12_porc) / 100,
                }
        llave.write(vals)
        return res

    @api.multi
    def unlink(self):
        llave = self.env['grp.pep.anual.linea.gasto'].search([('plan_anual_id', '=', self.plan_anual_id.id),
                                                              ('concepto_id', '=', self.concepto_id.id)])
        llave.unlink()
        # Notifico al concepto
        self.concepto_id.write({'state': 'completo'})
        return super(grp_pep_anual_linea_concepto, self).unlink()

    _sql_constraints = [
        ('linea_concepto_uniq', 'unique(plan_anual_id, concepto_id)', 'No se puede repetir el mismo concepto para el mismo plan'),
    ]

grp_pep_anual_linea_concepto()


class grp_pep_anual_linea_gasto(models.Model):
    _name = 'grp.pep.anual.linea.gasto'

    linea_concepto_id = fields.Many2one(comodel_name='grp.pep.anual.linea.concepto', ondelete='cascade')
    plan_anual_id = fields.Many2one(string=u'Plan Anual', comodel_name='grp.pep.anual', ondelete='cascade')
    concepto_id = fields.Many2one(string=u'Concepto', comodel_name='grp.pep.concepto')
    posicion_en_plan = fields.Integer(related='concepto_id.posicion_en_plan', string=u'Posición')
    metodo_calculo = fields.Selection(related='concepto_id.metodo_calculo', string=u'Método de cálculo', readonly=True)
    importe_anual = fields.Float(related='concepto_id.importe', string=u'Importe anual')
    periodicidad = fields.Selection(related='plan_anual_id.periodicidad', string='Periodicidad', readonly=True)
    plan_state = fields.Selection(related='plan_anual_id.state', string='Estado', readonly=True)
    cant_llaves = fields.Integer(related='concepto_id.cant_llaves', string='Llaves')
    periodo1_importe = fields.Float(string=u'Período 1', compute='_compute_periodo1_importe')
    periodo2_importe = fields.Float(string=u'Período 2', compute='_compute_periodo2_importe')
    periodo3_importe = fields.Float(string=u'Período 3', compute='_compute_periodo3_importe')
    periodo4_importe = fields.Float(string=u'Período 4', compute='_compute_periodo4_importe')
    periodo5_importe = fields.Float(string=u'Período 5', compute='_compute_periodo5_importe')
    periodo6_importe = fields.Float(string=u'Período 6', compute='_compute_periodo6_importe')
    periodo7_importe = fields.Float(string=u'Período 7', compute='_compute_periodo7_importe')
    periodo8_importe = fields.Float(string=u'Período 8', compute='_compute_periodo8_importe')
    periodo9_importe = fields.Float(string=u'Período 9', compute='_compute_periodo9_importe')
    periodo10_importe = fields.Float(string=u'Período 10', compute='_compute_periodo10_importe')
    periodo11_importe = fields.Float(string=u'Período 11', compute='_compute_periodo11_importe')
    periodo12_importe = fields.Float(string=u'Período 12', compute='_compute_periodo12_importe')

    @api.one
    @api.depends('importe_anual', 'linea_concepto_id.periodo1_porc')
    def _compute_periodo1_importe(self):
        importe = self.importe_anual
        porcentaje = self.linea_concepto_id.periodo1_porc
        self.periodo1_importe = (importe * porcentaje) / 100

    @api.one
    @api.depends('importe_anual', 'linea_concepto_id.periodo2_porc')
    def _compute_periodo2_importe(self):
        importe = self.importe_anual
        porcentaje = self.linea_concepto_id.periodo2_porc
        self.periodo2_importe = (importe * porcentaje) / 100

    @api.one
    @api.depends('importe_anual', 'linea_concepto_id.periodo3_porc')
    def _compute_periodo3_importe(self):
        importe = self.importe_anual
        porcentaje = self.linea_concepto_id.periodo3_porc
        self.periodo3_importe = (importe * porcentaje) / 100

    @api.one
    @api.depends('importe_anual', 'linea_concepto_id.periodo4_porc')
    def _compute_periodo4_importe(self):
        importe = self.importe_anual
        porcentaje = self.linea_concepto_id.periodo4_porc
        self.periodo4_importe = (importe * porcentaje) / 100

    @api.one
    @api.depends('importe_anual', 'linea_concepto_id.periodo5_porc')
    def _compute_periodo5_importe(self):
        importe = self.importe_anual
        porcentaje = self.linea_concepto_id.periodo5_porc
        self.periodo5_importe = (importe * porcentaje) / 100

    @api.one
    @api.depends('importe_anual', 'linea_concepto_id.periodo6_porc')
    def _compute_periodo6_importe(self):
        importe = self.importe_anual
        porcentaje = self.linea_concepto_id.periodo6_porc
        self.periodo6_importe = (importe * porcentaje) / 100

    @api.one
    @api.depends('importe_anual', 'linea_concepto_id.periodo7_porc')
    def _compute_periodo7_importe(self):
        importe = self.importe_anual
        porcentaje = self.linea_concepto_id.periodo7_porc
        self.periodo7_importe = (importe * porcentaje) / 100

    @api.one
    @api.depends('importe_anual', 'linea_concepto_id.periodo8_porc')
    def _compute_periodo8_importe(self):
        importe = self.importe_anual
        porcentaje = self.linea_concepto_id.periodo8_porc
        self.periodo8_importe = (importe * porcentaje) / 100

    @api.one
    @api.depends('importe_anual', 'linea_concepto_id.periodo9_porc')
    def _compute_periodo9_importe(self):
        importe = self.importe_anual
        porcentaje = self.linea_concepto_id.periodo9_porc
        self.periodo9_importe = (importe * porcentaje) / 100

    @api.one
    @api.depends('importe_anual', 'linea_concepto_id.periodo10_porc')
    def _compute_periodo10_importe(self):
        importe = self.importe_anual
        porcentaje = self.linea_concepto_id.periodo10_porc
        self.periodo10_importe = (importe * porcentaje) / 100

    @api.one
    @api.depends('importe_anual', 'linea_concepto_id.periodo11_porc')
    def _compute_periodo11_importe(self):
        importe = self.importe_anual
        porcentaje = self.linea_concepto_id.periodo11_porc
        self.periodo11_importe = (importe * porcentaje) / 100

    @api.one
    @api.depends('importe_anual', 'linea_concepto_id.periodo12_porc')
    def _compute_periodo12_importe(self):
        importe = self.importe_anual
        porcentaje = self.linea_concepto_id.periodo12_porc
        self.periodo12_importe = (importe * porcentaje) / 100

    @api.multi
    def button_llaves_wizard(self):
        xml_id_obj = self.env['ir.model.data']

        # Si el usuario tiene el grupo pep_elaboracion abro la vista wizard de edicion
        display_readonly = True
        if self.env.user.has_group('grp_plan_ejecucion_presupuestal.pep_elaboracion'):
            display_readonly = False

        vista = 'grp_pep_presupuestal_llaves_'+self.periodicidad+'_wizard'
        view_id = xml_id_obj.get_object_reference('grp_plan_ejecucion_presupuestal', vista)[1]
        wiz_id = self.env['grp.pep.presupuestal.llaves.wizard'].create({
            'concepto_id': self.concepto_id.id,
            'linea_concepto_id': self.linea_concepto_id.id,
            'periodo_activo': self.plan_anual_id.periodo_activo,
            'display_readonly': display_readonly})

        return {
            'name': "Llaves presupuestales del concepto %s" % self.concepto_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.presupuestal.llaves.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'view_id': view_id,
            'target': 'new',
        }

    @api.one
    def compute_importe_periodo(self):
        self.periodo1_importe = (self.importe_anual * self.linea_concepto_id.periodo1_porc) / 100
        self.periodo2_importe = (self.importe_anual * self.linea_concepto_id.periodo2_porc) / 100
        self.periodo3_importe = (self.importe_anual * self.linea_concepto_id.periodo3_porc) / 100
        self.periodo4_importe = (self.importe_anual * self.linea_concepto_id.periodo4_porc) / 100
        self.periodo5_importe = (self.importe_anual * self.linea_concepto_id.periodo5_porc) / 100
        self.periodo6_importe = (self.importe_anual * self.linea_concepto_id.periodo6_porc) / 100
        self.periodo7_importe = (self.importe_anual * self.linea_concepto_id.periodo7_porc) / 100
        self.periodo8_importe = (self.importe_anual * self.linea_concepto_id.periodo8_porc) / 100
        self.periodo9_importe = (self.importe_anual * self.linea_concepto_id.periodo9_porc) / 100
        self.periodo10_importe = (self.importe_anual * self.linea_concepto_id.periodo10_porc) / 100
        self.periodo11_importe = (self.importe_anual * self.linea_concepto_id.periodo11_porc) / 100
        self.periodo12_importe = (self.importe_anual * self.linea_concepto_id.periodo12_porc) / 100

grp_pep_anual_linea_gasto()


class grp_pep_anual_linea_actualizacion(models.Model):
    _name = 'grp.pep.anual.linea.actualizacion'

    plan_anual_id = fields.Many2one(string=u'Plan Anual', comodel_name='grp.pep.anual')
    product_id = fields.Many2one(string='Producto', comodel_name='product.product', required=True)
    existencia = fields.Integer(string='Cantidad a ajustar', help=u'Ajuste surgido del análisis')
    conceptos = fields.One2many(string='Conceptos', comodel_name='grp.pep.anual.actualizacion.concepto', inverse_name='linea_actualizacion_id', ondelete='cascade')
    procesado = fields.Boolean(default=False)

    @api.multi
    def set_procesado_true(self):
        self.ensure_one()
        total_a_ajustar = sum(linea.actualizacion for linea in self.conceptos)
        if total_a_ajustar <> self.existencia:
            raise ValidationError(u'La suma de las actualizaciones no puede ser distinta a la cantidad a ajustar.')
        else:
            self.procesado = True

grp_pep_anual_linea_actualizacion()


class grp_pep_anual_actualizacion_concepto(models.Model):
    _name = 'grp.pep.anual.actualizacion.concepto'

    linea_actualizacion_id = fields.Many2one(string=u'Línea actualización', comodel_name='grp.pep.anual.linea.actualizacion')
    concepto_id = fields.Many2one(string=u'Concepto', comodel_name='grp.pep.concepto')
    importe_anual = fields.Float(related='concepto_id.importe', string=u'Importe anual del concepto', readonly=True)
    cantidad_original = fields.Integer(string='Cantidad original')
    actualizacion = fields.Integer(string='Cantidad a ajustar')
    cantidad_actualizada = fields.Integer(string='Cantidad actualizada', compute='compute_cantidad_actualizada')
    precio_de_referencia = fields.Float(string=u'Precio de referencia', help='Impuestos incluidos')
    importe_original_producto = fields.Float(string='Importe original')
    importe_actualizado_producto = fields.Float(string='Importe actualizado', compute='compute_importe_actualizado')

    @api.multi
    @api.onchange('actualizacion')
    def onchange_actualizacion(self):
        for record in self:
            if record.actualizacion < 0:
                if abs(record.actualizacion) > self.cantidad_original:
                    self.actualizacion = 0
                    return {
                        'warning':{
                            'title':"Cantidad inválida",
                            'message':"La cantidad a restar no puede ser mayor a la cantidad actual."
                        }
                    }

    @api.one
    @api.depends('actualizacion')
    @api.onchange('actualizacion')
    def compute_cantidad_actualizada(self):
        self.cantidad_actualizada = self.cantidad_original + self.actualizacion
        self.concepto_id.set_linea_producto_actualizacion(self.linea_actualizacion_id.product_id.id,self.actualizacion)

    @api.one
    @api.depends('actualizacion')
    @api.onchange('actualizacion')
    def compute_importe_actualizado(self):
        self.importe_actualizado_producto = self.cantidad_actualizada * self.precio_de_referencia

grp_pep_anual_actualizacion_concepto()
