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

from openerp import models, fields, exceptions, api, _
from openerp.exceptions import Warning, ValidationError
import openerp.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)

# TODO: L SPRING 12 GAP 499

class grp_account_invoice(models.Model):
    _inherit = 'account.invoice'

    # TODO: K SPRING 12 GAP 205
    # RAGU: Mensaje de alerta de cesiones y retenciones en facturas de contratos
    @api.one
    def _compute_contrato_id(self):
        if self.type == 'in_invoice' and self.doc_type == 'obligacion_invoice':
            contrato_id = self.afectacion_id.contrato_id
        else:
            contrato_id = self.orden_compra_id.contrato_id

        self.show_msg_cesion = True if contrato_id and contrato_id.cession_ids else False
        self.show_msg_retencion = True if contrato_id and contrato_id.retenciones_ids else False
        self.contrato_id = contrato_id.id

    contrato_id = fields.Many2one("grp.contrato.proveedores", string=u'N° Contrato', compute='_compute_contrato_id', multi='contrato', readonly=True)
    show_msg_retencion = fields.Boolean(u"Mostar mensaje de retenciones", compute='_compute_contrato_id', multi='contrato', readonly=True)  # TODO: L SPRING 12 GAP 87
    show_msg_cesion = fields.Boolean(u"Mostar mensaje de cesiones", compute='_compute_contrato_id', multi='contrato', readonly=True)  # TODO: L SPRING 12 GAP 87
    not_show_msg_retencion = fields.Boolean(u"No mostar mensaje de retenciones", default=False)  # RAGU: ocultando alerta de retenciones
    not_show_msg_cesion = fields.Boolean(u"No mostar mensaje de cesiones", default=False)  # RAGU: ocultando alerta de retenciones

    fecha_devengamiento_contrato = fields.Date('Fecha de devengamiento del contrato')
    show_msg_parametrica = fields.Boolean(u'Mostrar alerta paramétrica', compute='_compute_show_msg_parametrica')

    @api.one
    @api.constrains('compromiso_id','doc_type','partner_id','date_invoice')
    def _constrains_contract_habilitation(self):
        if self.compromiso_id and self.doc_type == 'obligacion_invoice' and self.compromiso_id.contrato_id.control_proveedores:
            flag = False
            for proveedores_hab_id in self.compromiso_id.contrato_id.proveedores_hab_ids:
                if proveedores_hab_id.proveedor.id == self.partner_id.id and (self.date_invoice <= proveedores_hab_id.fecha_inactivo or not proveedores_hab_id.fecha_inactivo):
                    flag = True
            if not flag:
                raise exceptions.ValidationError(_(u'El proveedor seleccionado no es un proveedor habilitado del Contrato %s') % (self.compromiso_id.contrato_id.nro_interno))
        return True

    @api.one
    @api.constrains('fecha_devengamiento_contrato')
    def _constrains_contrato_parametrica(self):
        if self.contrato_id and self.fecha_devengamiento_contrato and (fields.Date.from_string(
                self.fecha_devengamiento_contrato) < fields.Date.from_string(
                self.contrato_id.fecha_inicio) or fields.Date.from_string(
                self.fecha_devengamiento_contrato) > fields.Date.from_string(self.contrato_id.fecha_fin)):
            raise ValidationError(_("La fecha de devengamiento seleccionada está fuerá del rango de fechas definido en el Contrato!"))

    @api.onchange('fecha_devengamiento_contrato')
    def onchange_fecha_devengamiento_contrato(self):
        if self.fecha_devengamiento_contrato:
            for line_id in self.invoice_line:
                parametrica_id = line_id.orden_compra_linea_id.get_parametrica_historica(self.fecha_devengamiento_contrato)
                if parametrica_id:
                    line_id.price_unit = parametrica_id.precio_ajustado

    @api.one
    def _compute_show_msg_parametrica(self):
        self.show_msg_parametrica = self.doc_type == 'obligacion_invoice' and self.contrato_id and self.env['grp.parametrica.historica'].search_count([('contrato_proveedor_id','in',self.contrato_id.contrato_particular_ids.ids)])

    # TODO: M SPRING 12 GAP 77
    @api.multi
    def invoice_validate(self):
        # self.check_contract_seccion()
        # TODO: L SPRING 12 GAP 87
        for rec in self:
            if rec.invoice_ret_global_line_ids:
                for item in rec.invoice_ret_global_line_ids:
                    if item.retencion_id and item.amount_ret_pesos > item.retencion_id.importe_pesos:
                        raise exceptions.ValidationError(
                            _(u'No se puede retener por un importe mayor a %s') % item.retencion_id.importe_pesos)
        res = super(grp_account_invoice, self).invoice_validate()
        return res


    # TODO: K SPRING 12 GAP 205
    @api.multi
    def abrir_contratos_form_view(self):
        for rec in self:
            if not rec.contrato_id:
                return
            else:
                context = dict(self._context)
                mod_obj = self.env['ir.model.data']
                res = mod_obj.get_object_reference('grp_contrato_proveedores', 'view_contract_proveedores_form')
                models = 'grp.contrato.proveedores'
                res_id = res and res[1] or False
                ctx = context.copy()
                return {
                    'name': "Contrato de condiciones generales",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': models,
                    'res_id': rec.contrato_id.id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': ctx,
                }
        return True

    # TODO: K SPRING 12 GAP 205
    @api.model
    def create(self, vals):
        # TODO: L SPRING 12 GAP 87
        if vals.get('orden_compra_id'):
                _oc = self.env['purchase.order'].search([('id', '=', vals['orden_compra_id'])])
                if _oc:
                    if _oc.contrato_id:
                        _retenciones = self.env['grp.retenciones'].search([('contrato_id', '=', _oc.contrato_id.id)])
                        ret_list = []
                        if _retenciones:
                            for item in _retenciones:
                                ret_list.append((0, 0, {'product_id': item.producto_id.id, 'account_id': item.cuenta_id.id,
                                                        'amount_ret_pesos': item.importe_pesos, 'retencion_id': item.id}))
                            vals['invoice_ret_global_line_ids'] = ret_list
        return super(grp_account_invoice, self).create(vals)

    # TODO: K SPRING 12 GAP 205
    @api.multi
    def btn_obligar(self):
        res = super(grp_account_invoice, self).btn_obligar()
        for rec in self:
            if rec.contrato_id and rec.contrato_id[0].control_proveedores:
                for prov in rec.contrato_id.proveedores_hab_ids:
                    if prov.proveedor.id == rec.partner_id.id and rec.amount_total > prov.monto_mensual:
                        context = dict(self._context)
                        mod_obj = self.env['ir.model.data']
                        res = mod_obj.get_object_reference('grp_contrato_proveedores', 'grp_motivo_desvios_montos_wizard_view')
                        models = 'grp.motivo.desvios.montos.wizard'
                        res_id = res and res[1] or False
                        ctx = context.copy()
                        ctx.update({'default_contrato_id': rec.contrato_id.id, 'default_invoice_id': rec.id, })
                        return {
                            'name': u"Motivo de desvío entre monto facturado y pactado",
                            'view_mode': 'form',
                            'view_id': res_id,
                            'view_type': 'form',
                            'res_model': models,
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            'context': ctx,
                        }
        return res

    # TODO: M SPRING 12 GAP 81
    @api.constrains('cesion_ids')
    def _check_cesion_ids(self):
        for rec in self:
            for cesion in rec.cesion_ids:
                if cesion.contract_cesion_id:
                    if cesion.monto_cedido_embargado > cesion.contract_cesion_id.saldo_ceder:
                        if cesion.contract_cesion_id.cession_type == 'amout_cession' or cesion.contract_cesion_id.cession_type == 'total_cession' and rec.currency_id.base:
                            raise exceptions.ValidationError(
                                _(u'El monto que quiere ceder al proveedor es superior al importe pendiente de ceder ingresado en el contrato.'))

                    if not rec.currency_id.base and cesion.contract_cesion_id.cession_type == 'total_cession':
                        monto_ajustado_moneda = cesion.contract_cesion_id._compute_saldo_ceder_moneda(rec.currency_id)
                        if rec.currency_id.type_ref_base == 'smaller':
                            monto_cedido_en_moneda = cesion.monto_cedido_embargado * rec.currency_id.rate
                        elif rec.currency_id.type_ref_base == 'bigger':
                            monto_cedido_en_moneda = cesion.monto_cedido_embargado / rec.currency_id.rate

                        if monto_cedido_en_moneda > monto_ajustado_moneda:
                            raise exceptions.ValidationError(
                                _( u'El monto que quiere ceder al proveedor en la moneda es superior al importe pendiente de ceder ingresado en el contrato'
                                   u' para esa moneda.'))

    # TODO: L SPRING 12 GAP 87
    # RAGU
    @api.one
    def do_not_show_msg_retencion(self):
        self.write({'not_show_msg_retencion': True})

    # RAGU
    @api.one
    def do_not_show_msg_cesion(self):
        self.write({'not_show_msg_cesion': True})



# TODO: K SPRING 12 GAP
class account_invoice_line_ext_api(models.Model):
    _inherit = 'account.invoice.line'

    orden_compra_linea_id = fields.Many2one('purchase.order.line', string=u'Línea de la orden de compra')
    date_invoice = fields.Date('Fecha de factura', related='invoice_id.date_invoice', readonly=True)
    comment = fields.Text('Observaciones', related='invoice_id.comment', readonly=True)
    supplier_invoice_number = fields.Char('Nº de factura del proveedor', related='invoice_id.supplier_invoice_number', readonly=True)


# TODO: L SPRING 12 GAP 87
class GrpAccountGlobalRetentionLine(models.Model):
    _inherit = 'account.global.retention.line'

    retencion_id = fields.Many2one('grp.retenciones', string=u'Retención')
