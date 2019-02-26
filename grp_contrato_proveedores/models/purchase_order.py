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

from openerp import api, fields, models, exceptions, _
from openerp import SUPERUSER_ID
import time
from collections import defaultdict
from openerp.exceptions import ValidationError
from openerp.tools import float_round


# ================================================================
## COTIZACIONES
# ================================================================
#
# TODO: SPRING 12 GAP 67 K
class GrpPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    contrato_id = fields.Many2one(
        comodel_name="grp.contrato.proveedores",
        string=u"Nº Contrato",
        readonly=True
    )

    # Se hereda el estandar y se agregan nuevos campos
    @api.model
    def _prepare_inv_line(self, account_id, order_line):
        res = super(GrpPurchaseOrder, self)._prepare_inv_line(account_id, order_line)
        res['orden_compra_linea_id'] = order_line.id or False
        return res

    # TODO: L SPRING 12 GAP 499
    @api.multi  # TODO: K VARIANZA GRP
    def abrir_contratos_tree_view(self):
        contratos_ids = []
        contratos = self.env['grp.contrato.proveedores'].search(
            [('nro_adj_id', '=', self.doc_origen.id), ('proveedor', '=', self.partner_id.id)])
        for item in contratos:
            contratos_ids.append(item.id)
        if contratos_ids:
            data_pool = self.pool.get('ir.model.data')
            action_model, action_id = data_pool.get_object_reference(self._cr, self._uid, 'grp_contrato_proveedores',
                                                                     'action_contract_proveedores_form')
            if action_model:
                action_pool = self.pool.get(action_model)
                action = action_pool.read(self._cr, self._uid, action_id, context=self._context)
                action['domain'] = "[('id','in', [" + ','.join(map(str, contratos_ids)) + "])]"
            return action
        return

    #MVARELA 05/06/2018 - Se mueve a grp_compras_estatales
    # # RAGU chequeando cantidades pendientes antes de confirmar compra
    # # TODO: C SPRING 13 GAP 451
    # def _check_product_qty(self):
    #     for line in self.order_line:
    #         if line.cotizaciones_linea_id and line.product_qty > line.cotizaciones_linea_id.cantidad_pendiente_oc:
    #             raise ValidationError(
    #                 u'No puede confirmar la orden de compra, la cantidad de la linea es mayor que la cantidad pendiente en oc de la linea adjudicada')
    #
    # # RAGU chequeando cantidades pendientes antes de confirmar compra
    # def wkf_confirm_order(self):
    #     self.ensure_one()
    #     self._check_product_qty()
    #     super(GrpPurchaseOrder, self).wkf_confirm_order()

    # TODO C SPRING 12 GAP_218
    @api.one
    @api.constrains('state')
    def _check_order_confirm(self):
        if self.state == 'confirmed':
            lines = self.order_line.mapped('cotizaciones_linea_id').ids
            contracts = self.env['grp.contrato.proveedores'].search(
                [('nro_line_adj_id', 'in', lines), ('contrato_general_id', '!=', False)])
            for contract in contracts:
                if float_round(contract.total_oc,2) > float_round(contract.total_ajustado,2):
                    raise ValidationError(
                        u'No puede confirmar la orden de compra, el total en OC es mayor que el total contratado ajustado')

    def _update_price_fromcontract(self):
        if self.contrato_id and self.date_order:
            for line in self.order_line:
                param_historica_id = line.get_parametrica_historica(self.date_order)
                if param_historica_id:
                    line.write({'price_unit': param_historica_id.precio_ajustado})

    @api.model
    def create(self, vals):
        res = super(GrpPurchaseOrder, self).create(vals)
        res._update_price_fromcontract()
        return res

    @api.multi
    def write(self, values):
        result = super(GrpPurchaseOrder, self).write(values)
        if values.get('date_order'):
            for rec in self:
                rec._update_price_fromcontract()
        return result


class GrpPurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    #MVARELA 05/06/2018 - Se mueve a grp_compras_estatales
    # cotizaciones_linea_id = fields.Many2one('grp.cotizaciones.lineas.aceptadas', string=u'Línea de adjudicación')
    contrato_particular_id = fields.Many2one('grp.contrato.proveedores', string=u'Contrato particular asociado', compute = '_compute_contrato_particular_id')

    @api.one
    def _compute_contrato_particular_id(self):
        contrato_obj = self.env['grp.contrato.proveedores']
        self.contrato_particular_id = contrato_obj.search([
            ('contrato_general_id', '=', self.order_id.contrato_id.id),
            ('codigo_articulo', '=', self.product_id.grp_sice_cod)], limit=1).id

    def get_parametrica_historica(self, date):
        if self.exists():
            self.ensure_one()
            return self.env['grp.parametrica.historica'].search([('contrato_proveedor_id', '=', self.contrato_particular_id.id),
                                                             ('fecha_planificada_ejecutada', '<=', date)],
                                                            order='fecha_planificada_ejecutada DESC', limit=1)
        else:
            return False



