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

from openerp import models, fields, api, exceptions, _
import amount_to_text_es
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.exceptions import ValidationError
import openerp.addons.decimal_precision as dp


class GrpAccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.depends("total_pesos_no_round", "amount_total", "type")
    def convert(self):
        if self.type and self.type in ['out_invoice']:
            self.amount_in_word = amount_to_text_es.amount_to_text(round(self.total_pesos_no_round), 'es', '')
        else:
            self.amount_in_word = amount_to_text_es.amount_to_text(self.amount_total, 'es', '')

    @api.multi
    @api.depends('invoice_line', 'invoice_line.monto_moneda_base', 'date_invoice', 'entry_date', 'journal_id')
    def _get_total_pesos_no_round(self):
        for rec in self:
            rec.total_pesos_no_round = sum(rec.invoice_line.mapped('monto_moneda_base'))

    @api.depends('total_pesos_no_round')
    def _get_importe_con_ajuste(self):
        for rec in self:
            ajuste = 0
            for pay_line in rec.payment_ids:
                for mov_line in pay_line.move_id.line_id:
                    if mov_line.name in ['Ajuste por redondeo', u'Write-Off']:
                        ajuste = mov_line.credit - mov_line.debit
                        break
            rec.importe_con_ajuste_report = rec.total_pesos_no_round + ajuste

    amount_in_word = fields.Char(compute='convert', string="Amount in Word", readonly=True)
    voucher_state = fields.Selection(selection_add=[('confirm', 'Confirmado'), ('issue', 'Emitido')])
    in_box = fields.Boolean(string=u'En caja', default=False,compute='_compute_in_box')  # TODO: SPRING 11 GAP 292 M
    caja_recaudadora_id = fields.Many2one('grp.caja.recaudadora.tesoreria',
                                          string=u'Caja recaudadora') # TODO: SPRING 11 GAP 292 M
    boleto_siif_id = fields.Many2one('grp.caja.recaudadora.tesoreria.boleto.siif',
                                          string=u'Boleto SIIF')  # TODO: SPRING 11 GAP 292 M
    registrar_en_caja = fields.Boolean(compute='_compute_registrar_en_caja',
                                       string=u'Registrar factura en caja recaudadora', default=False,store=True) # TODO: SPRING 11 GAP 292 M
    origin_id = fields.Many2one('grp.origen.factura', string=u'Origen',readonly=True,
                                states={'draft': [('readonly', False)]}) # TODO: M SPRING 11 GAP 292.A
    department_id = fields.Many2one('hr.department', string=u'Oficina') # TODO: M SPRING 11 GAP 292.A
    nro_receipt = fields.Char(u'Nro recibo', size=50)# TODO: M SPRING 11 GAP 292.A

    # TODO: C SPRING 12 GAP_301
    doc_type = fields.Selection(selection_add=[('vales_caja', 'Vales de caja')])
    total_pesos_no_round = fields.Float(string=u'Total en pesos', compute='_get_total_pesos_no_round', store=True)
    ret_sueldo = fields.Boolean(string='Incluido Ret. Sueldo', default=False)
    importe_con_ajuste_report = fields.Float(string=u'Importe con ajuste reporte',
                                             compute='_get_importe_con_ajuste',
                                             store=False, digits=dp.get_precision('Account'))
    doc_type_computed = fields.Char(string=u"Tipo Documento", compute="_compute_doc_type", store=True)

    # TODO: SPRING 10 GAP 274.275 K
    @api.onchange('siif_concepto_gasto')
    def onchange_siif_concepto_gasto(self):
        if (self.doc_type == 'obligacion_invoice' or self.doc_type == '3en1_invoice') and self.partner_id.es_inciso_default == True and self.siif_concepto_gasto.concepto == '1':
            self.account_id = self.partner_id.cuenta_sueldos_a_pagar.id

    # TODO: SPRING 10 GAP 274.275 K
    @api.multi
    def onchange_partner_id(self, type, partner_id, date_invoice=False, payment_term=False, partner_bank_id=False,
                             company_id=False, siif_concepto_gasto=False, doc_type=False):
        result = super(GrpAccountInvoice, self).onchange_partner_id(type, partner_id, date_invoice, payment_term, partner_bank_id, company_id)
        partner_obj = self.env['res.partner']
        if partner_id:
            partner = partner_obj.browse(partner_id)
            if (doc_type == 'obligacion_invoice' or doc_type == '3en1_invoice') and \
                partner.es_inciso_default == True and self.env['presupuesto.concepto'].browse(siif_concepto_gasto).concepto == '1':
                result['value'].update({'account_id': partner.cuenta_sueldos_a_pagar.id})
            #Incidencia 1689 y 1780
            if self.env.context.get('journal_id', False) and company_id and type:
                journal = self.env['account.journal'].browse(self.env.context['journal_id'])
                if journal.currency and journal.currency.id != self.env['res.company'].browse(company_id).currency_id.id:
                    #Salida
                    if type in ['out_invoice','in_refund']:
                        result['value'].update({'account_id': partner.cuenta_a_cobrar_me and partner.cuenta_a_cobrar_me.id or False})
                    #Entrada
                    if type in ['in_invoice','out_refund']:
                        result['value'].update({'account_id': partner.cuenta_a_pagar_me and partner.cuenta_a_pagar_me.id or False})
        return result


    # TODO: M SPRING 11 GAP 292.A
    @api.multi
    def onchange_date_invoice(self, payment_term_id, date_invoice):
        result = {'value': {}}
        if not date_invoice:
            date_invoice = fields.Date.context_today(self)
        result['value']['entry_date'] = date_invoice
        if not payment_term_id:
            # return {'value': {'date_due': self.date_due or date_invoice}}
            result['value']['date_due'] = self.date_due or date_invoice
            return result
        pterm = self.env['account.payment.term'].browse(payment_term_id)
        pterm_list = pterm.compute(value=1, date_ref=date_invoice)[0]
        if pterm_list:
            # return {'value': {'date_due': max(line[0] for line in pterm_list)}}
            result['value']['date_due'] =  max(line[0] for line in pterm_list)
            return result
        else:
            raise except_orm(_('Insufficient Data!'),
                             _('The payment term of supplier does not have a payment term line.'))



    # TODO: SPRING 11 GAP 292 M
    @api.multi
    @api.depends('state','payment_ids')
    def _compute_registrar_en_caja(self):
        for rec in self:
            rec.registrar_en_caja = False
            if rec.state == 'paid' and rec.caja_recaudadora_id:
                move_id = rec.payment_ids.mapped('move_id')
                account_voucher = self.env['account.voucher'].search([('move_id','in',move_id.ids)])
                if account_voucher:
                    rec.registrar_en_caja = True

        return True

    @api.multi
    def _compute_in_box(self):
        for rec in self:
            rec.in_box = (rec.caja_recaudadora_id and rec.state =='paid') or rec.boleto_siif_id

    # TODO: SPRING 11 GAP 292 M
    @api.multi
    def action_cancel(self):
        for rec in self:
            if rec.in_box:
                raise ValidationError(_(
                    u'Para cancelar este comprobante debe eliminar el registro de la caja.'))
        return super(GrpAccountInvoice, self).action_cancel()


    # TODO: M SPRING 11 GAP 292
    @api.multi
    def action_caja(self):
        self.ensure_one()
        return {
            'name': _('Caja recaudadora de tesoreria'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.caja_recaudadora_id.id,
            'res_model': 'grp.caja.recaudadora.tesoreria',
            # 'context': ctx,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    # TODO: M SPRING 11 GAP 292
    @api.multi
    def action_move_create(self):
        res = super(GrpAccountInvoice, self).action_move_create()
        if self.move_id:
            self.move_id.write({'operating_unit_id': self.operating_unit_id and self.operating_unit_id.id or False})
        return res

    @api.multi
    def action_link_related_document(self):
        self.ensure_one()
        voucher_id = self.env['account.voucher'].search([('invoice_id', '=', self.id)], limit=1)
        if voucher_id:
            _related_info_dict = voucher_id._get_related_document()
            if _related_info_dict['related_model'] and _related_info_dict['related_id']:
                dict_toreturn = {
                    'type': 'ir.actions.act_window',
                    'res_model': _related_info_dict['related_model'],
                    'display_name': 'Documento relacionado',
                    'view_type': 'form',
                    'name': 'Documento relacionado',
                    'target': 'current',
                    'view_mode': 'form',
                    'res_id': _related_info_dict['related_id']
                }

                if _related_info_dict.get('view_id') and _related_info_dict['view_id']:
                    res = self.env['ir.model.data'].get_object_reference(_related_info_dict['module_name'],
                                                                         _related_info_dict['view_id'])
                    res_id = res and res[1] or False
                    dict_toreturn.update({
                        'view_id': res_id
                    })
                return dict_toreturn
            else:
                return super(GrpAccountInvoice, self).action_link_related_document()
        else:
            vale_caja_id = self.env['grp.vale.caja'].search([('aprobacion_pago_id','=',self.id)])
            if vale_caja_id:
                dict_toreturn = {
                    'type': 'ir.actions.act_window',
                    'res_model': u'grp.vale.caja',
                    'display_name': 'Documento relacionado',
                    'view_type': 'form',
                    'name': 'Documento relacionado',
                    'target': 'current',
                    'view_mode': 'form',
                    'res_id': vale_caja_id.id
                }
                return dict_toreturn
            return super(GrpAccountInvoice, self).action_link_related_document()

    @api.one
    def _compute_related_document(self):
        voucher_obj = self.env['account.voucher']
        voucher_id = voucher_obj.search([('invoice_id', '=', self.id)], limit=1)
        if voucher_id:
            self.related_document = voucher_id._get_related_document()['related_document']
            self.related_document2 = voucher_id._get_related_document()['related_document2']
        else:
            vale_caja_id = self.env['grp.vale.caja'].search([('aprobacion_pago_id', '=', self.id)])
            if vale_caja_id:
                self.related_document = vale_caja_id.number
            else:
                super(GrpAccountInvoice, self)._compute_related_document()

    # TODO: M INCIDENCIA 788
    def invoice_pay_customer(self, cr, uid, ids, context=None):
        if not ids: return []
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher',
                                                                             'view_vendor_receipt_dialog_form')
        ctx = context.copy()
        inv = self.browse(cr, uid, ids[0], context=context)
        ctx.update({
            'payment_expected_currency': inv.currency_id.id,
            'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(inv.partner_id).id,
            'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
            'default_reference': inv.name,
            'close_after_process': True,
            'invoice_type': inv.type,
            'invoice_id': inv.id,
            'default_type': inv.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
            'type': inv.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
        })

        if inv.caja_recaudadora_id:
            ctx.update({'default_journal_id':inv.caja_recaudadora_id.journal_id.id,'caja_recaudadora': True})
            return {
                'name': _("Pay Invoice"),
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'account.voucher',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                'context': ctx
            }
        else:
            return super(GrpAccountInvoice, self).invoice_pay_customer(cr, uid, ids, context=context)

    @api.depends('doc_type', 'type')
    def _compute_doc_type(self):
        voucher_obj = self.env['account.voucher']
        for rec in self:
            if rec.doc_type != 'invoice':
                dict_types = dict(self.fields_get(allfields=['doc_type'])['doc_type']['selection'])
                if rec.doc_type == 'adelanto_viatico':
                    voucher_id = voucher_obj.search([('invoice_id', '=', rec.id)], limit=1)
                    if voucher_id.rendicion_viaticos_id:
                        rec.doc_type_computed = u'Rendición de viáticos'
                    elif voucher_id.solicitud_viatico_id:
                        rec.doc_type_computed = u'Solicitud de viáticos'
                    else:
                        rec.doc_type_computed = u'Adelanto de viáticos'
                elif rec.doc_type == 'vales_caja':
                    voucher_id = voucher_obj.search([('invoice_id', '=', rec.id)], limit=1)
                    if voucher_id.rendicion_anticipos_id:
                        rec.doc_type_computed = u'Rendición de anticipos'
                    elif voucher_id.solicitud_anticipos_id:
                        rec.doc_type_computed = u'Solicitud de anticipos'
                    else:
                        rec.doc_type_computed = u'Vales de caja'
                else:
                    rec.doc_type_computed = dict_types.get(rec.doc_type, rec.doc_type)
            else:
                if rec.type == 'out_refund':
                    rec.doc_type_computed = "Nota de crédito de cliente"
                elif rec.type == 'in_refund':
                    rec.doc_type_computed = "Nota de crédito de proveedor"
                elif rec.type == 'out_invoice':
                    rec.doc_type_computed = "Factura de cliente"
                elif rec.type == 'in_invoice':
                    rec.doc_type_computed = "Factura de proveedor"

