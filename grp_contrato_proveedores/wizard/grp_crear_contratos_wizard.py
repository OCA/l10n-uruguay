# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Enterprise Management Solution
#    GRP Estado Uruguay
#    Copyright (C) 2017 Quanam (ATEL SA., Uruguay)
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

from openerp import fields, models, api, _
from openerp.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

# TODO: K SPRING 12 GAP 67
class GrpCrearContratosWizard(models.TransientModel):
    _name = 'grp.crear.contratos.wizard'

    # TODO: K SPRING 12 GAP 67
    @api.model
    def _domain_proveedor_cot_ids(self):
        proveedor_cot_ids = [('id', 'in', [])]
        lineas_ids = self._context.get('lineas_cotizacion_ids', False)
        if lineas_ids:
            lineas = self.env['grp.cotizaciones.lineas.aceptadas'].browse(lineas_ids)
            proveedor_cot_ids = [('id', 'in', [x.proveedor_cot_id.id for x in lineas if x.proveedor_cot_id])]
        return proveedor_cot_ids

    proveedor_id = fields.Many2one('res.partner', 'Proveedor', domain=lambda self: self._domain_proveedor_cot_ids())
    lineas_ids = fields.One2many('grp.crear.contratos.linea.wizard', "wizard_id", 'Lineas')

    # TODO: K SPRING 12 GAP 67
    @api.onchange('proveedor_id')
    def onchange_lineas_retenciones_manuales_ids(self):
        if self._context.get('lineas_cotizacion_ids'):
            lineas_ids = self._context.get('lineas_cotizacion_ids')
            lineas = self.env['grp.cotizaciones.lineas.aceptadas'].browse(lineas_ids)
            details_ids = []
            for linea in lineas:
                if linea.proveedor_cot_id == self.proveedor_id:
                    details_ids.append([0, False, {'nro_line_adj_id': linea.id}])
            self.lineas_ids = details_ids

    # TODO: K SPRING 12 GAP 67
    @api.multi
    def crear_contratos(self):
        contrato_obj = self.env['grp.contrato.proveedores']
        for rec in self:
            if self.lineas_ids:
                contratos_ids = []
                vals_contrato ={
                    'proveedor' : rec.proveedor_id.id,
                    'fecha_resolucion': fields.Date.today(),
                    'operating_unit_id': self.lineas_ids[0].nro_line_adj_id.pedido_cot_id.operating_unit_id.id,
                    'nro_adj_id': self.lineas_ids[0].nro_line_adj_id.pedido_cot_id.id,
                    'pedido_compra': self.lineas_ids[0].nro_line_adj_id.pedido_cot_id.pedido_compra_id.id,
                    'currency':self.lineas_ids[0].nro_line_adj_id.pedido_cot_id.pedido_compra_id.moneda.id,
                    'moneda':self.lineas_ids[0].nro_line_adj_id.pedido_cot_id.pedido_compra_id.moneda.id,
                    'convenio': False,
                }
                contrato_gen_id = contrato_obj.create(vals_contrato)
                contratos_ids.append(contrato_gen_id.id)
                for linea in self.lineas_ids:
                    vals_contrato_part ={
                        'proveedor' : rec.proveedor_id.id,
                        'fecha_resolucion': fields.Date.today(),
                        'operating_unit_id': contrato_gen_id.operating_unit_id.id,
                        'nro_adj_id': linea.nro_line_adj_id.pedido_cot_id.id,
                        'pedido_compra': linea.nro_line_adj_id.pedido_cot_id.pedido_compra_id.id,
                        'contrato_general_id': contrato_gen_id.id,
                        'nro_line_adj_id': linea.nro_line_adj_id.id,
                        'codigo_articulo': linea.nro_line_adj_id.codigo_articulo,
                        'cantidad': linea.nro_line_adj_id.cantidad,
                        'currency': linea.nro_line_adj_id.currency.id,
                        'moneda': linea.nro_line_adj_id.currency.id,
                        'precio': round(linea.nro_line_adj_id.precio,2),
                        'precio_ajustado': round(linea.nro_line_adj_id.precio,2),
                        'convenio': False,
                    }
                    contrato_part_id = contrato_obj.create(vals_contrato_part)
                    contratos_ids.append(contrato_part_id.id)
                    # linea.nro_line_adj_id.write({'contrato_generado': True})

                # lineas_sin_cont = self.env['grp.cotizaciones.lineas.aceptadas'].search([('pedido_cot_id', '=', self.lineas_ids[0].nro_line_adj_id.pedido_cot_id.id),
                #                                        ('contrato_generado', '=', False)])
                # if not lineas_sin_cont:
                #     self.lineas_ids[0].nro_line_adj_id.pedido_cot_id.write({'contrato_generado': True})

                # TODO: K VARIANZA GRP
                orden_compra_ids = self.env['purchase.order'].search([('doc_origen', '=', vals_contrato['nro_adj_id']),
                                                       ('partner_id', '=', vals_contrato['proveedor'])])

                if orden_compra_ids:
                    orden_compra_ids.write({'contrato_id':contrato_gen_id.id})

                if contratos_ids:
                    data_pool = self.pool.get('ir.model.data')
                    action_model, action_id = data_pool.get_object_reference(self._cr, self._uid, 'grp_contrato_proveedores',
                                                                             'action_contract_proveedores_form')
                    if action_model:
                        action_pool = self.pool.get(action_model)
                        action = action_pool.read(self._cr, self._uid, action_id, context=self._context)
                        action['domain'] = "[('id','in', [" + ','.join(map(str, contratos_ids)) + "])]"
                    return action
        return True

class GrpCrearContratosLineaWizard(models.TransientModel):
    _name = 'grp.crear.contratos.linea.wizard'

    nro_line_adj_id = fields.Many2one('grp.cotizaciones.lineas.aceptadas', string=u'Línea de adjudicación')
    product_id = fields.Many2one(related='nro_line_adj_id.product_id', string='Producto', store=False, readonly=True)
    cantidad = fields.Float(related='nro_line_adj_id.cantidad', string='Cantidad', store=False, readonly=True)
    currency = fields.Many2one('res.currency', related='nro_line_adj_id.currency', string='Moneda', store=False, readonly=True)
    precio = fields.Float(related='nro_line_adj_id.precio', string='Precio', store=False, readonly=True)
    subtotal = fields.Float(related='nro_line_adj_id.subtotal', string='Subtotal', store=False, readonly=True)
    wizard_id = fields.Many2one('grp.crear.contratos.wizard', 'Crear contratos')



