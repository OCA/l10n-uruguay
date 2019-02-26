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

from openerp import models, fields, api, exceptions
from openerp.tools.translate import _
from openerp.tools import float_compare, float_round
from openerp.exceptions import ValidationError
from datetime import *
import time
from lxml import etree


class GrpCajaRecaudadoraTesoreria(models.Model):
    _name = 'grp.caja.recaudadora.tesoreria'
    _inherit = ['mail.thread']
    _order = 'closing_date desc'
    _description = u"Caja recaudadora tesorería"

    name = fields.Char(u'Nombre', default='/')
    box_id = fields.Many2one('grp.caja', string='Caja', readonly=True,
                             states={'draft': [('readonly', False)]})  # domain="[('caja_recaudadora','=', True)]",
    control_efectivo = fields.Boolean(u'Control de efectivo', related='box_id.control_efectivo', readonly=True)
    caja_principal = fields.Boolean(u'Caja principal', related='box_id.caja_principal', store=True, readonly=True)
    operating_unit_id = fields.Many2one('operating.unit', string='Unidad ejecutora',
                                        related='box_id.journal_id.operating_unit_id', readonly=True)
    journal_id = fields.Many2one('account.journal', string=u'Diario', related='box_id.journal_id', store=True,
                                 readonly=True)
    currency_id = fields.Many2one('res.currency', u'Divisa', related='box_id.currency_id', readonly=True)
    user_uid = fields.Many2one('res.users', 'Responsable', readonly=True, default=lambda self: self._uid)
    open_date = fields.Datetime(u'Fecha de apertura', readonly=True,
                                default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    closing_date = fields.Datetime(u'Cerrado en', readonly=True)
    state = fields.Selection(
        [('draft', u'Borrador'),
         ('open', u'Abierto'),
         ('collection_send', u'Recaudación enviada'),
         ('close', u'Cerrado'),
         ('checked', u'Revisado')], u'Estado', default='draft')

    opening_details_ids = fields.One2many('account.cashbox.line', 'caja_recaudadora_id', 'Control de efectivo')
    details_ids = fields.One2many('account.cashbox.line', 'caja_recaudadora_id', 'Control de efectivo')
    closing_details_ids = fields.One2many('account.cashbox.line', 'caja_recaudadora_id',
                                          string='Control de cierre efectivo')

    cash_subtotal = fields.Float(compute='_compute_cash_subtotal', string=u'Subtotal de apertura en efectivo')
    cash_initial_balance = fields.Float(string=u'Saldo inicial efectivo')
    cash_total_entry_encoding = fields.Float(compute='_compute_cash_total_entry_encoding',
                                             string=u'Transacciones efectivo', store=True, multi='cash')
    # cash_in_amount = fields.Float(string="Total de ingresos", compute='_compute_cash_total_entry_encoding', multi='cash', store=True)
    # cash_out_amount = fields.Float(string="Total de egresos", compute='_compute_cash_total_entry_encoding', multi='cash', store=True)
    cash_close_balance = fields.Float(compute='_compute_cash_total_entry_encoding',
                                      string=u'Saldo teórico de cierre efectivo', store=True, multi='cash')
    cash_closing_balance = fields.Float(compute='_compute_cash_closing_balance',
                                        string=u'Saldo de cierre real efectivo')
    cash_close_difference = fields.Float(compute='_compute_cash_close_difference', string=u'Diferencia efectivo')

    check_details_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line', 'caja_recaudadora_id',
                                        u'Control de cheques', domain=[('type', '=', 'opening_check')])
    opening_quantity_check = fields.Integer(compute='_compute_opening_check', string=u'Cantidad de cheques',
                                            multi='openig_check')
    total_amount_check = fields.Float(compute='_compute_opening_check', string=u'Total Importe cheque',
                                      multi='openig_check')
    check_initial_balance = fields.Float(string=u'Saldo inicial cheque')
    check_total_entry_encoding = fields.Float(compute='_compute_check_total_entry_encoding',
                                              string=u'Transacciones cheque', store=True, multi='check')
    # check_in_amount = fields.Float(string="Total de ingresos", compute='_compute_check_total_entry_encoding',
    #                               multi='check', store=True)
    # check_out_amount = fields.Float(string="Total de egresos", compute='_compute_check_total_entry_encoding',
    #                                multi='check', store=True)
    check_close_balance = fields.Float(compute='_compute_check_total_entry_encoding',
                                       string=u'Saldo teórico de cierre cheque',
                                       store=True, multi='check')

    closing_check_details_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line', 'caja_recaudadora_id',
                                                u'Control de cierre cheques',
                                                domain=[('type', '=', 'check'), ('voucher_selected', '=', False),('remove_transaction', '=', False),('entregado', '=', False),('cancel_transaction', '=', False)])
    closing_quantity_check = fields.Integer(compute='_compute_closing_check',
                                            string=u'Cantidad de cheques en cierre', multi='closing_check')
    closing_total_amount_check = fields.Float(compute='_compute_closing_check',
                                              string=u'Total Importe cheque en cierre', multi='closing_check')
    check_closing_balance = fields.Float(compute='_compute_check_closing_balance',
                                         string=u'Saldo de cierre real cheque')  # ,store=True
    check_close_difference = fields.Float(compute='_compute_check_close_difference',
                                          string=u'Diferencia cheque')  # ,store=True
    voucher_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line', 'caja_recaudadora_id', 'Recibos',
                                  states={'checked': [('readonly', True)]},
                                  domain=[('type', '=', 'voucher')])

    voucher_details_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line', 'caja_recaudadora_id', 'Detalles',
                                          states={'checked': [('readonly', True)],'close': [('readonly', True)]},
                                          domain=[('type', '=', 'details'), ('cancel_transaction', '=', False),
                                                  ('remove_transaction', '=', False)])

    check_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line', 'caja_recaudadora_id', 'Cheques',
                                domain=[('type', '=', 'check'), ('cancel_transaction', '=', False),
                                        ('remove_transaction', '=', False)], states={'checked': [('readonly', True)],'close': [('readonly', True)]})

    valores_custodia_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line.valor.custodia', 'caja_recaudadora_id',
                                           'Valores Custodia', states={'checked': [('readonly', True)],'close': [('readonly', True)]})

    cash_shipment_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line.remesa', 'caja_recaudadora_id',
                                        'Remesas efectivo', states={'checked': [('readonly', True)],'close': [('readonly', True)]},
                                        domain=[('type', '=', 'cash')])
    check_shipment_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line.remesa', 'caja_recaudadora_id',
                                         'Remesas cheque', states={'checked': [('readonly', True)],'close': [('readonly', True)]},
                                         domain=[('type', '=', 'check')])
    selected_check_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line', 'caja_recaudadora_id', 'Cheques',
                                         states={'checked': [('readonly', True)],'close': [('readonly', True)]},
                                         domain=[('type', '=', 'check'), ('cancel_transaction', '=', False),
                                                 ('remove_transaction', '=', False), ('voucher_selected', '=', True)])
    total_shipment_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line.remesa', 'caja_recaudadora_id',
                                         'Remesas Total', states={'checked': [('readonly', True)],'close': [('readonly', True)]},
                                         domain=[('type', '=', 'total')])
    transaction_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line.transaccion', 'caja_recaudadora_id',
                                      u'Transacciones',states={'checked': [('readonly', True)],'close': [('readonly', True)]})
    move_line_ids = fields.One2many('account.move.line', 'caja_recaudadora_id', u'Asientos contables',states={'checked': [('readonly', True)]})

    cash_total_shipment = fields.Float(compute='_compute_cash_total_shipment', string=u'Total de efectivo remesa',
                                       multi='efectivo_remesa', store=True)
    cash_total_shipment_no_siif = fields.Float(compute='_compute_cash_total_shipment',
                                               string=u'Total de efectivo remesa no siif',
                                               multi='efectivo_remesa')
    cash_shipment_siff_ticket = fields.Char(u'Boleto SIIF', size=60)
    cash_shipment_bar_code = fields.Char(u'Código de barra')

    check_total_shipment = fields.Float(compute='_compute_check_total_shipment', string=u'Total de cheque remesa',
                                        multi='cheque_remesa', store=True)
    check_total_shipment_no_siif = fields.Float(compute='_compute_check_total_shipment',
                                                string=u'Total de cheque remesa no siif',
                                                multi='cheque_remesa')
    total_shipment = fields.Float(compute='_compute_total_shipment', string=u'Total remesa', store=True)
    check_shipment_siff_ticket = fields.Char(u'Boleto SIIF', size=60)
    total_shipment_siff_ticket = fields.Char(u'Boleto SIIF', size=60)
    show_adv = fields.Boolean(string="Mostrar confirm", compute='_compute_show_adv', default=False)
    show_btn = fields.Boolean(string="Mostrar boton", compute='_compute_show_btn', default=False)

    line_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line', 'caja_recaudadora_id', 'Lineas')

    # RAGU: remesa
    remittance_date = fields.Date('Fecha de remesa')
    r_move_id = fields.Many2one('account.move', 'Asiento contable remesa')
    preparar_remesa = fields.Boolean(compute='_get_preparar_remesa', string=u'En preparar remesa', store=True)

    total_close_balance = fields.Float(compute='_compute_total_close_balance', string=u'Saldo final total', store=True)

    total_in_amount = fields.Float(compute='_compute_total_in_amount',
                                             string=u'Importe cobrado')

    @api.depends('voucher_details_ids.preparar_remesa')
    def _get_preparar_remesa(self):
        for rec in self:
            resultado = True
            for line in rec.voucher_details_ids:
                if line.entrega_tesoreria is True and line.siff_ticket is False:
                    resultado = resultado and line.preparar_remesa
            rec.preparar_remesa = resultado

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(GrpCajaRecaudadoraTesoreria, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                                       context=context,
                                                                       toolbar=toolbar, submenu=submenu)
        user = self._uid
        box_ids = []
        doc = etree.XML(res['arch'])
        if view_type == 'form':
            box = self.env['grp.caja'].search([('caja_recaudadora', '=', True), ('users', '=', user)])
            if box:
                box_ids.extend(box.ids)
            for field in res['fields']:
                if field == 'box_id':
                    res['fields'][field]['domain'] = [('id', 'in', box_ids)]
            res['arch'] = etree.tostring(doc)
        return res

    @api.one
    @api.constrains('state')
    def _check_state(self):
        if self._model._name == 'grp.caja.recaudadora.tesoreria' and self.search_count([('box_id','=',self.box_id.id),('state','not in',['close','checked'])]) > 1:
            raise ValidationError(_(u"Existe otra caja que no se encuentra en estado cerrado o revisado"))
        return True

    @api.one
    @api.constrains('voucher_ids')
    def _check_voucher_lines_fromcheck(self):
        checks = []
        for line in self.voucher_ids.filtered(lambda x: x.payment_method == 'check'):
            line_exist = False
            for check in checks:
                if line.receipt_check == check['receipt_check'] and line.voucher_id.id == check['voucher_id'] and (line.remove_transaction != check['remove_transaction'] or line.cancel_transaction != check['cancel_transaction']):
                    raise ValidationError(_("No se han marcado para Cancelar o Quitar transacción todas las líneas asociadas al cheque %s en la pestaña Recibos!") % (line.receipt_check))
                elif line.receipt_check == check['receipt_check'] and line.voucher_id.id == check['voucher_id']:
                    line_exist = True
            if not line_exist:
                checks.append({'receipt_check':line.receipt_check,'voucher_id':line.voucher_id.id, 'remove_transaction': line.remove_transaction,'cancel_transaction':line.cancel_transaction})
        return True

    @api.one
    @api.constrains('valores_custodia_ids')
    def _check_vc_lines_fromcheck(self):
        checks = {}
        for line in self.valores_custodia_ids.filtered(lambda x: x.payment_method == 'check'):
            if checks.get(line.check_number, False):
                if (line.shipment != checks[line.receipt_check][0] or line.cancel_transaction !=
                    checks[line.check_number][1] or line.entrega_tesoreria != checks[line.check_number][2]):
                    raise ValidationError(_(
                        "No se han marcado para Cancelar o Quitar transacción todas las líneas asociadas al cheque %s en la pestaña Valores en custodia!") % (
                                          line.receipt_check))
            else:
                checks.update({line.check_number: [line.shipment, line.remove_transaction, line.entrega_tesoreria]})
        return True

    @api.one
    @api.constrains('voucher_details_ids')
    def _check_details_lines_fromcheck(self):
        checks = {}
        for line in self.voucher_details_ids.filtered(lambda x: x.payment_method == 'check'):
            if checks.get(line.receipt_check, False):
                if (line.shipment != checks[line.receipt_check][0]):
                    raise ValidationError(_(
                        "No se han marcado para Preparar remesa todas las líneas asociadas al cheque %s en la pestaña Detalles") % (
                                              line.receipt_check))
            else:
                checks.update({line.receipt_check: [line.shipment]})
        return True

    def _check_partials_invoices(self):
        for rec in self:
            if rec.voucher_ids.filtered(lambda x: x.invoice_id and x.invoice_id.state != 'paid' and not x.remove_transaction):
                raise ValidationError(_(u"Existe una factura cobrada parcialmente, debe registrar el pago total antes de continuar!"))
        return True

    @api.multi
    @api.depends('voucher_ids')
    def _compute_show_btn(self):
        for rec in self:
            rec.show_btn = rec.voucher_ids.filtered(lambda x: x.remove_transaction and not x.removed_transaction)

    @api.multi
    @api.depends('cash_close_difference')
    def _compute_show_adv(self):
        for rec in self:
            rec.show_adv = rec.control_efectivo and rec.cash_close_difference != 0

    @api.multi
    @api.depends('total_shipment_ids')
    def _compute_total_shipment(self):
        for rec in self:
            rec.total_shipment = sum(map(lambda x: x.amount, rec.total_shipment_ids))

    @api.multi
    @api.depends('check_shipment_ids')
    def _compute_check_total_shipment(self):
        for rec in self:
            rec.check_total_shipment = sum(map(lambda x: x.amount, rec.check_shipment_ids.filtered(
                lambda x: rec._get_mapeo_cuenta_deposito(x.product_id, True))))
            rec.check_total_shipment_no_siif = sum(map(lambda x: x.amount, rec.check_shipment_ids.filtered(
                lambda x: rec._get_mapeo_cuenta_deposito(x.product_id, False))))

    @api.multi
    @api.depends('cash_shipment_ids')
    def _compute_cash_total_shipment(self):
        for rec in self:
            rec.cash_total_shipment = sum(map(lambda x: x.amount, rec.cash_shipment_ids.filtered(
                lambda x: rec._get_mapeo_cuenta_deposito(x.product_id, True))))
            rec.cash_total_shipment_no_siif = sum(map(lambda x: x.amount, rec.cash_shipment_ids.filtered(
                lambda x: rec._get_mapeo_cuenta_deposito(x.product_id, False))))

    @api.multi
    @api.depends('opening_details_ids')
    def _compute_cash_subtotal(self):
        for rec in self:
            rec.cash_subtotal = sum(map(lambda x: x.subtotal_opening, rec.opening_details_ids))

    @api.multi
    @api.depends('box_id')
    def _compute_cash_initial_balance(self):
        for rec in self:
            rec.cash_initial_balance = 0.0
            if rec.box_id:
                previous_box = rec._get_previous_box(rec.box_id.id, rec.open_date)
                if previous_box:
                    rec.cash_initial_balance = previous_box.cash_close_balance

    @api.depends('cash_initial_balance', 'voucher_ids', 'transaction_ids', 'valores_custodia_ids', 'cash_shipment_ids')
    def _compute_cash_total_entry_encoding(self):
        for rec in self:
            voucher_details = rec.suspend_security().voucher_details_ids.filtered(lambda x: x.payment_method == 'cash' and not x.apertura_recibo and not x.entrega_caja and not x.entrega_tesoreria).ids
            if voucher_details:
                self.suspend_security().env.cr.execute('SELECT weight_amount FROM grp_caja_recaudadora_tesoreria_line WHERE id IN %s',(tuple(voucher_details),))
                sum_total_enty_encoding = sum(map(lambda x:x['weight_amount'] if x['weight_amount'] else float(0),self.env.cr.dictfetchall()),float(0))
            else:
                sum_total_enty_encoding = float(0)
            voucher_details = rec.suspend_security().voucher_details_ids.filtered(lambda x: x.payment_method == 'cash' and x.apertura_recibo and (x.entrega_caja or x.entrega_tesoreria)).ids
            if voucher_details:
                self.suspend_security().env.cr.execute('SELECT weight_amount FROM grp_caja_recaudadora_tesoreria_line WHERE id IN %s', (tuple(voucher_details),))
                rest_total_enty_encoding = sum(map(lambda x:x['weight_amount'] if x['weight_amount'] else float(0),self.env.cr.dictfetchall()),float(0))
            else:
                rest_total_enty_encoding = float(0)

            cash_total_entry_encoding = float_round(sum_total_enty_encoding - rest_total_enty_encoding,2)
            if rec.suspend_security().valores_custodia_ids:
                cash_total_entry_encoding = float_round(cash_total_entry_encoding,2) + float_round(sum(map(lambda x: x.amount, rec.suspend_security().valores_custodia_ids.filtered(
                    lambda x: not x.remove_transaction and x.payment_method == 'cash' and not x.apertura_recibo))),2)
            if rec.suspend_security().transaction_ids:
                cash_total_entry_encoding = float_round(cash_total_entry_encoding,2) + float_round(sum(map(lambda x: x.amount, rec.suspend_security().transaction_ids)),2)
            if rec.suspend_security().cash_shipment_ids:
                cash_total_entry_encoding = float_round(cash_total_entry_encoding,2) + float_round(sum(map(lambda x: x.amount, rec.suspend_security().cash_shipment_ids)),2)
            rec.cash_total_entry_encoding = cash_total_entry_encoding
            rec.cash_close_balance = rec.cash_initial_balance + cash_total_entry_encoding

    @api.depends('cash_initial_balance', 'cash_total_entry_encoding')
    def _compute_cash_close_balance(self):
        for rec in self:
            rec.cash_close_balance = rec.cash_initial_balance + rec.cash_total_entry_encoding

    @api.depends('check_details_ids')
    def _compute_opening_check(self):
        for rec in self:
            rec.opening_quantity_check = 0
            rec.total_amount_check = 0.0
            if rec.check_details_ids:
                rec.opening_quantity_check = len(rec.check_details_ids.ids)
                rec.total_amount_check = sum(map(lambda x: x.check_amount, rec.check_details_ids))

    @api.depends('closing_check_details_ids')
    def _compute_closing_check(self):
        for rec in self:
            rec.closing_quantity_check = 0
            rec.closing_total_amount_check = 0.0
            if rec.closing_check_details_ids:
                rec.closing_quantity_check = len(rec.closing_check_details_ids.ids)
                rec.closing_total_amount_check = sum(map(lambda x: x.check_amount, rec.closing_check_details_ids))

    @api.depends('box_id')
    def _compute_check_initial_balance(self):
        for rec in self:
            rec.check_initial_balance = 0.0
            if rec.box_id:
                previous_box = rec._get_previous_box(rec.box_id.id, rec.open_date)
                if previous_box:
                    rec.check_initial_balance = previous_box.check_close_balance

    @api.depends('check_initial_balance', 'check_ids.voucher_selected', 'check_ids.cancel_transaction','check_ids.remove_transaction',
                 'check_ids.entregado','check_ids.apertura_recibo','check_ids')
    def _compute_check_total_entry_encoding(self):
        for rec in self:
            sum_check_total_entry_encoding = sum(map(lambda x: x.check_amount, rec.suspend_security().check_ids.filtered(
                lambda x: not x.apertura_recibo and not x.entregado and not x.voucher_selected and not x.remove_transaction)))
            rest_check_total_entry_encoding = sum(map(lambda x: x.check_amount, rec.suspend_security().check_ids.filtered(
                lambda x: x.apertura_recibo and (x.entregado or x.voucher_selected))))
            _check_total_entry_encoding = sum_check_total_entry_encoding - rest_check_total_entry_encoding
            # rec.check_in_amount = sum_check_total_entry_encoding
            # rec.check_out_amount = rest_check_total_entry_encoding
            rec.check_total_entry_encoding = _check_total_entry_encoding
            rec.check_close_balance = rec.check_initial_balance + _check_total_entry_encoding

    @api.depends('check_initial_balance', 'check_total_entry_encoding')
    def _compute_check_close_balance(self):
        for rec in self:
            rec.cash_close_balance = rec.check_initial_balance + rec.check_total_entry_encoding

    @api.depends('closing_details_ids')
    def _compute_cash_closing_balance(self):
        for rec in self:
            rec.cash_closing_balance = sum(map(lambda x: x.subtotal_closing, rec.closing_details_ids))

    @api.depends('cash_closing_balance', 'cash_close_balance', 'closing_details_ids')
    def _compute_cash_close_difference(self):
        for rec in self:
            rec.cash_close_difference = rec.cash_closing_balance - rec.cash_close_balance

    @api.depends('closing_check_details_ids')
    def _compute_check_closing_balance(self):
        for rec in self:
            rec.check_closing_balance = sum(map(lambda x: x.check_amount, rec.closing_check_details_ids))

    @api.depends('check_closing_balance', 'check_close_balance', 'closing_check_details_ids')
    def _compute_check_close_difference(self):
        for rec in self:
            rec.check_close_difference = rec.check_closing_balance - rec.check_close_balance

    @api.multi
    @api.depends('cash_close_balance','check_close_balance')
    def _compute_total_close_balance(self):
        for rec in self:
            rec.total_close_balance = rec.cash_close_balance + rec.check_close_balance

    @api.multi
    @api.depends('voucher_ids.amount','voucher_ids')
    def _compute_total_in_amount(self):
        line_obj = self.env['grp.caja.recaudadora.tesoreria.line']
        for rec in self:
            _total_in_amount = 0
            for voucher_id in rec.voucher_ids.filtered(lambda x:not x.remove_transaction):
                line_id = line_obj.search([('caja_recaudadora_id.name', '=', voucher_id.caja_recaudadora_id.name),
                                       ('type', '=', 'details'), ('voucher_id', '=', voucher_id.voucher_id.id),
                                       ('invoice_id', '=', voucher_id.invoice_id.id)], limit=1)
                if line_id and not line_id.apertura_recibo:
                    _total_in_amount += voucher_id.amount
            rec.total_in_amount = _total_in_amount

    @api.model
    def create(self, vals):
        rec = super(GrpCajaRecaudadoraTesoreria, self).create(vals)
        opening_details = rec._get_opening_details()
        details_ids = opening_details['opening_details_ids']
        check_details_ids = opening_details['check_details_ids']
        cash_initial_balace = rec._get_cash_initial_balance()
        check_initial_balace = rec._get_check_initial_balance()
        rec.write({'opening_details_ids': details_ids, 'check_details_ids': check_details_ids,
                   'cash_initial_balance': cash_initial_balace, 'check_initial_balance': check_initial_balace})
        return rec

    @api.multi
    def write(self, values):
        res = super(GrpCajaRecaudadoraTesoreria, self).write(values)
        if 'voucher_details_ids' in values or 'valores_custodia_ids' in values:
            data = self._update_remesa()
            res = super(GrpCajaRecaudadoraTesoreria, self).write(data)
        return res

    def _update_remesa(self):
        for rec in self:
            cash_shipment_ids = []
            check_shipment_ids = []
            total_shipment_ids = []
            details = rec.voucher_details_ids.filtered(lambda x: x.shipment)
            valores_custodia = rec.valores_custodia_ids.filtered(lambda x: x.shipment)
            products = []
            if details or valores_custodia:
                products = list(set(details.mapped('product_id')) | set(valores_custodia.mapped('product_id')))
            rec.cash_shipment_ids.unlink()
            rec.check_shipment_ids.unlink()
            rec.total_shipment_ids.unlink()
            cash_expensive_line = False
            check_expensive_line = False
            total_expensive_line = False
            cash_residuals_amount = 0
            check_residuals_amount = 0
            total_residuals_amount = 0
            for product in products:
                if not self.env['grp.producto.cuenta.deposito'].search([('product_id', '=', product.id)]):
                    raise ValidationError(_(
                        u'Todos los productos marcados como "Preparar remesa" deben tener una cuenta de depósito asignada!'))

                total_cash = sum(map(lambda v: v.weight_amount, details.filtered(
                    lambda x: x.payment_method == 'cash' and x.product_id.id == product.id))) * (-1)

                total_cash += sum(map(lambda v: v.monto, valores_custodia.filtered(
                    lambda x: x.payment_method == 'cash' and x.product_id.id == product.id))) * (-1)
                if total_cash:
                    round_total = round(total_cash,0)
                    new_line = (0, 0, {'product_id': product.id, 'amount': total_cash, 'amount_siif': round_total, 'type': 'cash'})
                    cash_shipment_ids.append(new_line)
                    cash_residuals_amount += total_cash - round_total

                    if not cash_expensive_line or cash_expensive_line[2]['amount_siif'] < round_total:
                        cash_expensive_line = new_line

                total_check = sum(map(lambda v: v.weight_amount, details.filtered(
                    lambda x: x.payment_method == 'check' and x.product_id.id == product.id))) * (-1)

                total_check += sum(map(lambda v: v.monto, valores_custodia.filtered(
                    lambda x: x.payment_method == 'check' and x.product_id.id == product.id))) * (-1)
                if total_check:
                    round_total = round(total_check, 0)
                    new_line = (0, 0, {'product_id': product.id, 'amount': total_check, 'amount_siif': round_total, 'type': 'check'})
                    check_shipment_ids.append(new_line)
                    check_residuals_amount += total_check - round_total

                    if not check_expensive_line or check_expensive_line[2]['amount_siif'] < round_total:
                        check_expensive_line = new_line

                total = sum(map(lambda v: v.weight_amount, details.filtered(
                    lambda x: x.product_id.id == product.id))) * (-1)

                total += sum(map(lambda v: v.monto, valores_custodia.filtered(
                    lambda x: x.product_id.id == product.id))) * (-1)
                if total:
                    round_total = round(total, 0)
                    new_line = (0, 0, {'product_id': product.id, 'amount': total, 'amount_siif': round_total, 'type': 'total'})
                    total_shipment_ids.append(new_line)
                    total_residuals_amount += total - round_total
                    if not total_expensive_line or total_expensive_line[2]['amount_siif'] < round_total:
                        total_expensive_line = new_line

            if cash_expensive_line:
                cash_expensive_line[2]['amount_siif'] += round(cash_residuals_amount,0)
            if check_expensive_line:
                check_expensive_line[2]['amount_siif'] += round(check_residuals_amount,0)
            if total_expensive_line:
                total_expensive_line[2]['amount_siif'] += round(total_residuals_amount,0)
            data = {
                'cash_shipment_ids': cash_shipment_ids,
                'check_shipment_ids': check_shipment_ids,
                'total_shipment_ids': total_shipment_ids
            }

            return data

    def _get_opening_details(self):
        vals = {}
        details_ids = []
        check_details_ids = []
        for rec in self:
            previous_box = self._get_previous_box(rec.box_id.id, rec.open_date)
            if previous_box:
                for value in previous_box.details_ids:
                    nested_values = {
                        'number_closing': 0,
                        'number_opening': value.number_closing,
                        'pieces': value.pieces
                    }
                    details_ids.append([0, False, nested_values])
            else:
                for value in rec.box_id.cashbox_line_ids:
                    nested_values = {
                        'number_closing': 0,
                        'number_opening': 0,
                        'pieces': value.pieces
                    }
                    details_ids.append([0, False, nested_values])
            vals['opening_details_ids'] = details_ids

            for check in previous_box.check_ids.filtered(lambda x: not x.voucher_selected
            and not x.entregado
            and not x.cancel_transaction):
                check_values = {
                    'voucher_id': check.voucher_id.id,
                    'invoice_id': check.invoice_id.id,
                    'valor_custodia_id': check.valor_custodia_id.id,
                    'type': 'opening_check',
                    'check_amount': check.check_amount
                }
                check_details_ids.append([0, False, check_values])
            vals['check_details_ids'] = check_details_ids

            return vals

    def _get_cash_initial_balance(self):
        caja_pagadora_id = self._get_previous_box(self.box_id.id, self.open_date)
        return caja_pagadora_id.cash_close_balance if caja_pagadora_id else 0

    def _get_check_initial_balance(self):
        caja_pagadora_id = self._get_previous_box(self.box_id.id, self.open_date)
        return caja_pagadora_id.check_close_balance if caja_pagadora_id else 0

    def _validate_open(self):
        if sum(self.voucher_details_ids.filtered(lambda f:f.apertura_recibo and f.payment_method == 'cash').mapped(lambda x: x.weight_amount)) != self.cash_initial_balance:
            raise ValidationError(_("El total de líneas de Saldo apertura debe ser igual al Saldo inicial de caja para el método de pago 'Efectivo'"))
        if sum(self.voucher_details_ids.filtered(lambda f:f.apertura_recibo and f.payment_method != 'cash').mapped(lambda x: x.weight_amount)) != self.check_initial_balance:
            raise ValidationError(_("El total de líneas de Saldo apertura debe ser igual al Saldo inicial de caja para el método de pago 'Cheque'"))
        return True

    @api.multi
    def btn_open(self):
        for rec in self:
            rec._validate()
            vals = rec.update_fields()
            rec.write(vals)
            # rec._validate_open()

            rec.message_post(body=u"Caja recaudadora %s abierta." % (rec.name,))
        return True

    @api.multi
    def btn_reopen(self):
        for rec in self:
            rec._validate()
            rec.write({'state': 'open'})
            rec.message_post(body=u"Caja recaudadora %s abierta nuevamente." % (rec.name,))
        return True

    @api.multi
    def btn_close(self):
        self._check_partials_invoices()
        for rec in self:
            if rec.state == 'open' and rec.voucher_details_ids.filtered(lambda x: x.shipment):
                # TODO: M INCIDENCIA
                raise ValidationError(_(
                    u'Tiene lineas seleccionadas para remesa, debe confirmar la recaudación antes de cerrar la caja.'))
            if rec.cash_close_balance < 0:
                raise ValidationError(_(
                    u'No puede cerrar una caja con "Saldo teórico de cierre" negativo.'))
            if rec.check_close_difference != 0.0:
                raise ValidationError(_(
                    u'Existen diferencias en el saldo de cheques. Revisar la caja.'))
            if rec.cash_close_difference != 0.0:
                if rec.cash_close_difference < 0.0:
                    account = rec.journal_id.loss_account_id
                    name = _('Perdida')
                    concept_id = self.env['grp_concepto_gasto_cc_viaticos'].search([('perdida_diferencia', '=', True)])
                else:
                    account = rec.journal_id.profit_account_id
                    name = _('Ganancias')
                    concept_id = self.env['grp_concepto_gasto_cc_viaticos'].search([('ganancia_diferencia', '=', True)])

                if not account:
                    raise ValidationError(_(
                        u'Debe configurar las cuentas de ganancia y perdida del diario seleccionado!'))

                if concept_id:
                    values = {
                        'caja_recaudadora_id': rec.id,
                        'concept_id': concept_id.id,
                        'name': name,
                        'date': fields.Date.today(),
                        'amount': rec.cash_close_difference,
                        'ajuste': True,
                    }
                    ctx = self._context.copy()
                    ctx.update({'diference': rec.cash_close_difference})
                    self.env['grp.caja.recaudadora.tesoreria.line.transaccion'].with_context(ctx).create(values)

            rec.write({
                'state': 'close',
                'closing_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            })
            rec.message_post(body=u"Caja recaudadora %s cerrada." % (rec.name,))
        return True

    @api.multi
    def btn_check(self):
        for rec in self:
            # TODO: M INCIDENCIA
            if not rec.journal_id.default_debit_account_id:
                raise ValidationError(_(
                    u'Debe configurar la cuenta deudora por defecto del diario %s') % (rec.journal_id.name,))
            vals = {'state': 'checked'}
            if rec.total_shipment_ids:
                if rec.caja_principal:
                    move_vals = rec._prepare_move()
                    move = self.env['account.move'].create(move_vals)
                    vals.update({'r_move_id': move.id})
                else:
                    journal = self.env['account.journal'].search([('recaudacion_cta', '=', True)])
                    if journal:
                        if rec.journal_id.operating_unit_id.id == journal.operating_unit_id.id:
                            if not journal.default_credit_account_id:
                                raise ValidationError(_(
                                    u'Debe configurar la cuenta acreedora por defecto del diario %s') % (journal.name,))
                            move_vals = rec._prepare_move2(journal)
                            move = self.env['account.move'].create(move_vals)
                        else:
                            move = rec._create_move3(journal)
                        vals.update({'r_move_id': move.id})

            # RAGU CANCELANDO PAGOS, EXTORNO DE PAGOS.
            cancel_vouchers = rec.voucher_ids.filtered(lambda x: x.cancel_transaction)
            if cancel_vouchers:
                rec._cancel_transaccion(cancel_vouchers)

            if rec.transaction_ids:
                rec._create_move_transaction(rec.transaction_ids.filtered(lambda x: not x.concept_id.ajuste_caja))
            if rec.valores_custodia_ids:
                for valores_custodia in rec.valores_custodia_ids.filtered(lambda x: not x.remove_transaction
                and x.product_id and not x.apertura_recibo):
                    rec._create_move_valores_custodia(valores_custodia)
            if rec.voucher_details_ids:
                for detail in rec.voucher_details_ids.filtered(lambda x: x.entrega_caja and not x.remove_transaction):
                    rec._create_move_details(detail)
            rec.write(vals)
            rec.message_post(body=u"Caja recaudadora %s revisada." % (rec.name))
        return True

    @api.multi
    def action_remove_transaction(self):
        # caja_recaudadora_line = self.env['grp.caja.recaudadora.tesoreria.line']
        for rec in self:
            vouchers = rec.voucher_ids.filtered(lambda x: x.remove_transaction)
            self._cancel_transaccion(vouchers)
            vouchers.write({'removed_transaction': True})
            # for voucher in vouchers:
            #     details_voucher = caja_recaudadora_line.search([('caja_recaudadora_id', '=', rec.id),
            #                                                     ('voucher_id', '=', voucher.voucher_id.id),
            #                                                     ('type', '=', 'details'),
            #                                                     ('invoice_id', '=', voucher.invoice_id.id)])
            #     if details_voucher:
            #         details_voucher.unlink()
            #     check_voucher = caja_recaudadora_line.search([('caja_recaudadora_id', '=', rec.id),
            #                                                   ('voucher_id', '=', voucher.voucher_id.id),
            #                                                   ('type', '=', 'check'),
            #                                                   ('invoice_id', '=', voucher.invoice_id.id)])
            #     if check_voucher:
            #         check_voucher.unlink()
            # vouchers.unlink()

    @api.multi
    def btn_collection_send(self):
        self._check_partials_invoices()
        for rec in self:
            if not rec.remittance_date:
                raise ValidationError(
                    _("No se puede 'Confirmar remesa' sin antes haber definido una 'Fecha de remesa'!"))
            # TODO: M INCIDENCIA 19-09-17
            if not rec.voucher_details_ids.filtered(lambda x: x.shipment) and not \
                    rec.valores_custodia_ids.filtered(lambda x: x.shipment):
                raise ValidationError(_(
                    u'Debe tener al menos una linea seleccionada con preparar remesa.'))
            if rec.caja_principal and not rec.cash_shipment_siff_ticket and not rec.check_shipment_siff_ticket \
                    and not rec.total_shipment_siff_ticket:
                raise ValidationError(_(
                    u'Debe ingresar alguno de los Boletos SIIF.'))

        self.write({'state': 'collection_send'})

    @api.multi
    def _check_cancel_action(self):
        for rec in self:
            next_box = rec._get_next_box(rec.journal_id.id, rec.open_date)
            if next_box:
                raise ValidationError(_(
                    u'No es posible cancelar la caja; existe una caja posterior.'))
            for line_id in rec.line_ids:
                if line_id.boleto_siif_id.id != False or line_id.siff_ticket:
                    raise ValidationError(_('No es posible cancelar esta caja. Ya generó el Boleto SIIF. Debe cancelar el Boleto SIIF para luego cancelar la caja'))

    @api.multi
    def btn_cancel(self):
        self._check_cancel_action()
        for rec in self:
            moves = self.env['account.move'].browse()
            vals = {'state': 'open'}
            if rec.r_move_id:
                moves |= rec.r_move_id
                vals.update({'r_move_id': False})
            if rec.transaction_ids:
                moves |= rec.transaction_ids.mapped('move_id')
                rec.transaction_ids.write({'move_id': False})
            vc2upd = self.env['grp.valores_custodia'].browse()
            for vc in rec.valores_custodia_ids:
                if vc.valor_custodia_id.asiento_alta:
                    moves |= vc.valor_custodia_id.asiento_alta
                    vc2upd |= vc.valor_custodia_id
            if vc2upd:
                vc2upd.write({'asiento_alta': False, 'diario_alta': False, 'fecha_alta': False })
            if rec.voucher_details_ids:
                moves |= rec.voucher_details_ids.mapped('move_id')
                rec.voucher_details_ids.write({'move_id': False})
            if moves:
                rec.crear_extorno(moves)
            rec.write(vals)
            rec.message_post(body=u"Caja recaudadora %s abierta." % (rec.name,))
        return True

    def crear_extorno(self, moves):
        for move in moves:
            period_id = self.env['account.period'].find(fields.Date.today()).id
            move.create_reversals(
                fields.Date.today(),
                reversal_period_id=period_id,
            )
        return True

    def update_fields(self):
        voucher_ids = []
        voucher_details = []
        checks = []
        valores_custodia_ids = []
        vals = {
            'state': 'open',
            'open_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        if self.journal_id.sequence_id:
            fiscalyear_id = self._get_fiscalyear()
            if fiscalyear_id:
                name = self.env['ir.sequence'].with_context(fiscalyear_id=fiscalyear_id[0].id).next_by_id(
                    self.journal_id.sequence_id.id)
                vals['name'] = name

        previous_box = self._get_previous_box(self.box_id.id, vals['open_date'])
        if previous_box:
            previous_voucher_details = []
            for voucher in previous_box.voucher_ids.filtered(lambda x: not x.voucher_selected
            and not x.entregado
            and not x.cancel_transaction
            and not x.remove_transaction):
                voucher_ids.append([0, 0, {'voucher_id': voucher.voucher_id.id,
                                           'vline_id': voucher.vline_id.id,
                                           'invoice_id': voucher.invoice_id.id,
                                           'origin_voucher_id': voucher.origin_voucher_id.id,
                                           'type': 'voucher',
                                           'no_recibo': voucher.no_recibo,
                                           'amount': voucher.amount}])
                for details_line in previous_box.voucher_details_ids.filtered(
                        lambda x: x.voucher_id.id == voucher.voucher_id.id):
                    if details_line.id not in previous_voucher_details and details_line_id.caja_recaudadora_line_id.boleto_siif_id.state != u'collection_send':
                        voucher_details.append([0, 0, {'voucher_id': details_line.voucher_id.id,
                                                       'vline_id': details_line.vline_id.id,
                                                       'origin_voucher_id': voucher.origin_voucher_id.id,
                                                       'invoice_id': details_line.invoice_id.id,
                                                       'type': 'details',
                                                       'product_id': details_line.product_id.id,
                                                       'price_subtotal': details_line.price_subtotal,
                                                       'plus_amount': details_line.plus_amount,
                                                       'apertura_recibo': True,
                                                       'amount': details_line.amount}])
                    previous_voucher_details.append(details_line.id)

            for valores_custodia in previous_box.valores_custodia_ids.filtered(lambda x: not x.shipment
            and not x.remove_transaction and not x.entrega_tesoreria):
                valores_custodia_ids.append([0, 0, {'valor_custodia_id': valores_custodia.valor_custodia_id.id,
                                                    'product_id': valores_custodia.product_id.id,
                                                    'payment_method': valores_custodia.payment_method,
                                                    'apertura_recibo': True}])

            for check_id in previous_box.check_ids.filtered(lambda x: not x.voucher_selected
            and not x.entregado
            and not x.cancel_transaction
            and not x.remove_transaction):
                checks.append([0, 0, {'voucher_id': check_id.voucher_id.id,
                                      'vline_id': check_id.vline_id.id,
                                      'origin_voucher_id': check_id.origin_voucher_id.id,
                                      'invoice_id': check_id.invoice_id.id,
                                      'valor_custodia_id':check_id.valor_custodia_id.id,
                                      'type': 'check',
                                      'apertura_recibo':True,
                                      'check_amount': check_id.check_amount}])
        vals['voucher_ids'] = voucher_ids
        vals['voucher_details_ids'] = voucher_details
        vals['check_ids'] = checks
        vals['valores_custodia_ids'] = valores_custodia_ids
        return vals

    def _get_previous_box(self, box_id, open_date):
        previous_box = self.search(
            [('state', 'in', ['checked', 'close']), ('box_id', '=', box_id), ('id', '!=', self.id),
             ('closing_date', '<=', open_date)], order='closing_date desc', limit=1)
        return previous_box

    def _get_next_box(self, journal_id, open_date):
        next_box = self.search([('state', '!=', 'draft'), ('journal_id', '=', journal_id),
                                ('open_date', '>=', open_date), ('id', '!=', self.id)], order='open_date asc', limit=1)
        return next_box

    def _get_fiscalyear(self):
        fecha_hoy = time.strftime('%Y-%m-%d')
        uid_company_id = self.env['res.users'].browse(self._uid).company_id.id
        fiscalyear_id = self.env['account.fiscalyear'].search(
            [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
             ('company_id', '=', uid_company_id)])
        return fiscalyear_id

    def _get_shipment(self, product, type=None):
        total = 0
        if type is None:
            vouchers = self.voucher_details_ids.filtered(
                lambda x: x.shipment is True and x.product_id.id == product.id)
            if vouchers:
                total = sum(map(lambda v: v.weight_amount, vouchers)) * (-1)
        else:
            vouchers = self.voucher_details_ids.filtered(
                lambda x: x.shipment is True and x.payment_method == type and x.product_id.id == product.id)
            if vouchers:
                total = sum(map(lambda v: v.weight_amount, vouchers)) * (-1)
        return total

    def _validate(self):
        # if self.search([('state', '=', 'open'), ('box_id', '=', self.box_id.id), ('id', '!=', self.id)]):
        #     raise exceptions.ValidationError(
        #         _(u'Existe para esta caja otra en estado Abierto. No es posible abrir una nueva caja'))
        if self.state == 'open':
            raise exceptions.ValidationError(_(u'Error al abrir la caja, ya se encuentra en estado Abierto.'))
        if self.cash_subtotal <> self.cash_initial_balance or self.total_amount_check <> self.check_initial_balance:
            raise exceptions.ValidationError(
                _(u'El total de la composición de la caja debe ser igual al total del saldo inicial.'))

    def _prepare_move(self):
        period_id = self.env['account.period'].find(fields.Date.today()).id
        lines = []
        product_cuenta_dep_id = self.env['grp.producto.cuenta.deposito']
        credit_amount = self.total_shipment < 0 and -self.total_shipment or self.total_shipment
        company_currency = self.journal_id.company_id.currency_id.id
        current_currency = self.currency_id.id
        diff_currency = current_currency != company_currency and current_currency
        product_cuenta_dep = product_cuenta_dep_id.search([])
        if product_cuenta_dep:
            cuenta_deposito = product_cuenta_dep.mapped('account_id')
            for cuenta in cuenta_deposito:
                products = product_cuenta_dep.search([('account_id', '=', cuenta.id)]).mapped('product_id')
                shipment_products = self.total_shipment_ids.filtered(lambda x: x.product_id.id in products.ids)
                if shipment_products:
                    amount = sum(map(lambda x: x.amount, shipment_products))
                    debit_amount = amount < 0 and -amount or amount
                    lines.append((0, 0, {
                        'name': "/",
                        'account_id': cuenta.id,
                        'debit': diff_currency and self.currency_id.rate * debit_amount or debit_amount,
                        'credit': 0.0,
                        'currency_id': diff_currency and current_currency or False,
                        'amount_currency': diff_currency and debit_amount or 0.0,
                        'caja_recaudadora_id': self.id,
                    }))

            if not len(lines):
                # TODO: M INCIDENCIA
                raise ValidationError(_(
                    u'Debe configurar el "Mapeo producto cuenta de depósito" para los productos implicados.'))
            lines.append((0, 0, {
                'name': "/",
                'account_id': self.journal_id.default_debit_account_id.id,
                'debit': 0.0,
                'credit': diff_currency and self.currency_id.rate * credit_amount or credit_amount,
                'currency_id': diff_currency and current_currency or False,
                'amount_currency': diff_currency and - credit_amount or 0.0,
                'caja_recaudadora_id': self.id,
            }))

        return {
            'journal_id': self.journal_id.id,
            'period_id': period_id,
            'operating_unit_id': self.operating_unit_id.id,
            'date': fields.Date.today(),
            'name': self.name,
            'ref': self.name or "/",
            'line_id': lines
        }

    def _prepare_move2(self, journal):
        period_id = self.env['account.period'].find(fields.Date.today()).id
        company_currency = self.journal_id.company_id.currency_id.id
        current_currency = self.currency_id.id
        diff_currency = current_currency != company_currency and current_currency
        amount = self.total_shipment < 0 and -self.total_shipment or self.total_shipment
        move_line_vals_debit = {
            'name': "/",
            'account_id': journal.default_credit_account_id.id,
            'debit': diff_currency and self.currency_id.rate * amount or amount,
            'credit': 0.0,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': diff_currency and amount or 0.0,
            'caja_recaudadora_id': self.id,
        }
        move_line_vals_credit = {
            'name': "/",
            'account_id': self.journal_id.default_debit_account_id.id,
            'debit': 0.0,
            'credit': diff_currency and self.currency_id.rate * amount or amount,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': diff_currency and - amount or 0.0,
            'caja_recaudadora_id': self.id,
        }

        return {
            'journal_id': self.journal_id.id,
            'period_id': period_id,
            'operating_unit_id': self.operating_unit_id.id,
            'date': fields.Date.today(),
            'name': self.name,
            'ref': self.name or "/",
            'line_id': [(0, 0, move_line_vals_debit), (0, 0, move_line_vals_credit)]
        }

    def _create_move3(self, journal):
        period_id = self.env['account.period'].find(fields.Date.today()).id
        company_id = self.env['res.users'].browse(self._uid).company_id
        company_currency = company_id.currency_id.id
        current_currency = self.currency_id.id
        diff_currency = current_currency != company_currency and current_currency
        if not company_id.transfer_account_id:
            raise ValidationError(_(u'Debe configurar la cuenta de trasferencia para la compañia'))

        amount = self.total_shipment < 0 and -self.total_shipment or self.total_shipment
        move_line_vals_debit = {
            'name': "/",
            'account_id': company_id.transfer_account_id.id,
            'debit': diff_currency and self.currency_id.rate * amount or amount,
            'credit': 0.0,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': diff_currency and amount or 0.0,
            'caja_recaudadora_id': self.id,
        }
        move_line_vals_credit = {
            'name': "/",
            'account_id': self.journal_id.default_debit_account_id.id,
            'debit': 0.0,
            'credit': diff_currency and self.currency_id.rate * amount or amount,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': diff_currency and - amount or 0.0,
            'caja_recaudadora_id': self.id,
        }
        move_vals = {
            'journal_id': self.journal_id.id,
            'period_id': period_id,
            'operating_unit_id': self.operating_unit_id.id,
            'date': fields.Date.today(),
            'name': self.name,
            'ref': self.name or "/",
            'line_id': [(0, 0, move_line_vals_debit), (0, 0, move_line_vals_credit)]
        }
        self.env['account.move'].create(move_vals)

        move_line_vals_debit2 = {
            'name': "/",
            'account_id': journal.default_credit_account_id.id,
            'debit': diff_currency and self.currency_id.rate * amount or amount,
            'credit': 0.0,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': diff_currency and amount or 0.0,
            'caja_recaudadora_id': self.id,
        }
        move_line_vals_credit2 = {
            'name': "/",
            'account_id': company_id.transfer_account_id.id,
            'debit': 0.0,
            'credit': diff_currency and self.currency_id.rate * amount or amount,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': diff_currency and - amount or 0.0,
            'caja_recaudadora_id': self.id,
        }
        move_vals2 = {
            'journal_id': journal.id,
            'operating_unit_id': journal.operating_unit_id.id,
            'period_id': period_id,
            'date': fields.Date.today(),
            'name': self.name,
            'ref': self.name or "/",
            'line_id': [(0, 0, move_line_vals_debit2), (0, 0, move_line_vals_credit2)]
        }
        move2 = self.env['account.move'].create(move_vals2)
        return move2

    def _create_move_transaction(self, transactions):
        period_id = self.env['account.period'].find(fields.Date.today()).id
        company_currency = self.journal_id.company_id.currency_id.id
        current_currency = self.currency_id.id
        diff_currency = current_currency != company_currency and current_currency
        for transaction in transactions:
            # TODO: M INCIDENCIA
            if not transaction.concept_id.cuenta_id:
                raise ValidationError(_(
                    u'Debe configurar la cuenta del concepto %s') % (transaction.concept_id.name,))
            if transaction.amount < 0.0:
                account_debit = transaction.concept_id.cuenta_id.id
                account_credit = self.journal_id.default_debit_account_id.id
                amount = -transaction.amount
            else:
                account_debit = self.journal_id.default_debit_account_id.id
                account_credit = transaction.concept_id.cuenta_id.id
                amount = transaction.amount
            move_line_vals_debit = {
                'name': self.name,
                'ref': self.name or "/",
                'account_id': account_debit,
                'debit': diff_currency and self.currency_id.rate * amount or amount,
                'credit': 0.0,
                'currency_id': diff_currency and current_currency or False,
                'amount_currency': diff_currency and amount or 0.0,
                'caja_recaudadora_id': self.id,
                # 'transaccion_id': transaction.id,
            }
            move_line_vals_credit = {
                'name': self.name,
                'ref': self.name or "/",
                'account_id': account_credit,
                'debit': 0.0,
                'credit': diff_currency and self.currency_id.rate * amount or amount,
                'currency_id': diff_currency and current_currency or False,
                'amount_currency': diff_currency and - amount or 0.0,
                'caja_recaudadora_id': self.id,
                # 'transaccion_id': transaction.id,
            }
            move_vals = {
                'journal_id': self.journal_id.id,
                'period_id': period_id,
                'operating_unit_id': self.operating_unit_id.id,
                'date': fields.Date.today(),
                'name': self.name,
                'ref': self.name or "/",
                'line_id': [(0, 0, move_line_vals_debit), (0, 0, move_line_vals_credit)]
            }

            move = self.env['account.move'].create(move_vals)
            transaction.write({'move_id': move.id})
        return True

    def _create_move_valores_custodia(self, valor_custodia):
        # TODO: M INCIDENCIA
        if not valor_custodia.product_id.property_account_expense:
            raise ValidationError(_(
                u'Debe configurar la cuenta de gasto del producto %s') % (valor_custodia.product_id.name,))
        company_currency = self.journal_id.company_id.currency_id.id
        current_currency = self.currency_id.id
        diff_currency = current_currency != company_currency and current_currency
        period_id = self.env['account.period'].find(valor_custodia.fecha_recepcion).id
        amount = valor_custodia.monto < 0 and -valor_custodia.monto or valor_custodia.monto
        move_line_vals_debit = {
            'name': "/",
            'account_id': self.journal_id.default_debit_account_id.id,
            'debit': diff_currency and self.currency_id.rate * amount or amount,
            'credit': 0.0,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': diff_currency and amount or 0.0,
            'caja_recaudadora_id': self.id,
        }
        move_line_vals_credit = {
            'name': "/",
            'account_id': valor_custodia.product_id.property_account_expense.id,
            'debit': 0.0,
            'credit': diff_currency and self.currency_id.rate * amount or amount,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': diff_currency and - amount or 0.0,
            'caja_recaudadora_id': self.id,
        }

        move_vals = {
            'journal_id': self.journal_id.id,
            'period_id': period_id,
            # 'operating_unit_id': valor_custodia.operating_unit_id.id,
            'date': valor_custodia.fecha_recepcion,
            'name': valor_custodia.name,
            'ref': valor_custodia.name or "/",
            'line_id': [(0, 0, move_line_vals_debit), (0, 0, move_line_vals_credit)]
        }

        move = self.env['account.move'].create(move_vals)
        valor_custodia.valor_custodia_id.write(
            {'asiento_alta': move.id, 'diario_alta': move.journal_id.id, 'fecha_alta': move.date})
        return True

    def _create_move_details(self, detail):
        period_id = self.env['account.period'].find(detail.fecha_entrega).id
        company_currency = self.journal_id.company_id.currency_id.id
        current_currency = self.currency_id.id
        diff_currency = current_currency != company_currency and current_currency
        amount = detail.amount < 0 and -detail.amount or detail.amount
        # TODO: M INCIDENCIA
        if not detail.product_id.property_account_expense:
            raise ValidationError(_(
                u'Debe configurar la cuenta de gasto del producto %s') % (detail.product_id.name,))

        move_line_vals_debit = {
            'name': "/",
            'account_id': detail.product_id.property_account_expense.id,
            'debit': diff_currency and self.currency_id.rate * amount or amount,
            'credit': 0.0,
            'partner_id': detail.partner_id.id,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': diff_currency and amount or 0.0,
            'caja_recaudadora_id': self.id,
        }
        move_line_vals_credit = {
            'name': "/",
            'account_id': self.journal_id.default_debit_account_id.id,
            'debit': 0.0,
            'credit': diff_currency and self.currency_id.rate * amount or amount,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': diff_currency and - amount or 0.0,
            'caja_recaudadora_id': self.id,
        }

        move_vals = {
            'journal_id': self.journal_id.id,
            'period_id': period_id,
            'date': detail.fecha_entrega,
            'operating_unit_id': detail.operating_unit_id.id,
            'line_id': [(0, 0, move_line_vals_debit), (0, 0, move_line_vals_credit)]
        }
        move = self.env['account.move'].create(move_vals)
        detail.write({ 'move_id': move.id })
        return True

    def _cancel_transaccion(self, vouchers):
        invoices = self.env['account.invoice']
        for voucher in vouchers:
            voucher.voucher_id.cancel_voucher()
            invoices += voucher.invoice_id
            # voucher.invoice_id.write({'caja_recaudadora_id': False, 'state': 'open'})
            #RAGU: DEVOLUCION DE VIATICOS
            for line in voucher.voucher_id.line_cr_ids:
                if line.origin_voucher_id:
                    line.origin_voucher_id.write({'state': 'posted', 'in_cashbox': False})
                    if line.origin_voucher_id.rendicion_viaticos_id:
                        line.origin_voucher_id.rendicion_viaticos_id.write({'state':'autorizado'})
        invoices.signal_workflow('invoice_cancel_paid')
        invoices.signal_workflow('invoice_cancel')
        invoices.write({'caja_recaudadora_id':False})
        return True

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise exceptions.ValidationError(u'No es posible eliminar una caja en estado diferente a Borrador.')
        return super(GrpCajaRecaudadoraTesoreria, self).unlink()

    @api.multi
    def open_invoice(self):
        self.ensure_one()
        mod_obj = self.env['ir.model.data']
        res = mod_obj.get_object_reference('account', 'invoice_form')
        res_id = res and res[1] or False
        ctx = dict(self._context)
        ctx.update({'default_type': 'out_invoice', 'type': 'out_invoice', 'journal_type': 'sale',
                    # 'default_journal_id':self.journal_id.id,
                    'default_caja_recaudadora_id': self.id, 'default_operating_unit_id': self.operating_unit_id.id})
        return {
            'name': _('Facturas de cliente'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'domain': "[('type','=','out_invoice')]",
            'context': ctx,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
        }

    @api.multi
    def open_valor_custodia(self):
        self.ensure_one()
        mod_obj = self.env['ir.model.data']
        res = mod_obj.get_object_reference('grp_tesoreria', 'view_grp_valores_custodia_form')
        res_id = res and res[1] or False
        ctx = dict(self._context)
        ctx.update({'search_default_group_estado': 1, 'default_caja_recaudadora_id': self.id, 'default_operating_unit_id': self.operating_unit_id.id})
        return {
            'name': _('Valores en Custodia'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'grp.valores_custodia',
            'context': ctx,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
        }

    def _get_mapeo_cuenta_deposito(self, product_id, condicion):
        mapeo = self.env['grp.producto.cuenta.deposito'].search([('product_id', '=', product_id.id)], limit=1)
        if mapeo and mapeo.no_siif == condicion:
            return False
        else:
            return True

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
                                        context=None, count=False):
        lista_ids = []
        if context == None:
            context = {}
        if context.get('remesa') or context.get('boleto_siif'):
            _limit = None
            _offset = 0
            _count = False
        else:
            _limit = limit
            _offset = offset
            _count = count
        ids = super(GrpCajaRecaudadoraTesoreria, self).search(cr, uid, args, offset=_offset, limit=_limit, order=order, context=context,
                                          count=_count)
        if context.get('remesa', False):
            for box_id in self.browse(cr, uid, ids, context=context):
                resultado = True
                for line in box_id.voucher_details_ids:
                    if line.entrega_tesoreria is True and line.siff_ticket is False:
                        resultado = resultado and line.preparar_remesa
                if not resultado and box_id.state in ['checked'] and box_id.caja_principal:
                    lista_ids.append(box_id.id)
        elif context.get('boleto_siif', False):
            for box_id in self.browse(cr, uid, ids, context=context):
                voucher_details = box_id.voucher_details_ids.filtered(lambda x: x.shipment is True and
                                                                             x.siff_ticket is False)
                if len(voucher_details) and box_id.state in ['checked'] and not box_id.caja_principal:
                    lista_ids.append(box_id.id)
        return lista_ids or ids



class GrpCajaRecaudadoraTesoreriaLine(models.Model):
    _name = 'grp.caja.recaudadora.tesoreria.line'

    active = fields.Boolean(u'Activo', default=True)
    caja_recaudadora_id = fields.Many2one('grp.caja.recaudadora.tesoreria', u'Caja recaudadora')
    siif_reference_id = fields.Many2one('grp.caja.recaudadora.tesoreria.line', u'Boleto SIIF referencia')
    boleto_siif_id = fields.Many2one('grp.caja.recaudadora.tesoreria.boleto.siif', u'Boleto SIIF', ondelete='cascade')
    voucher_id = fields.Many2one('account.voucher', u'Pago a proveedor')
    # voucher_line_id = fields.Many2one('account.voucher.line', u'Linea de Pago a proveedor')
    vline_id = fields.Many2one('account.voucher.line', u'Linea de Pago a proveedor')
    origin_voucher_id = fields.Many2one('account.voucher', u'Pago origen')
    valor_custodia_id = fields.Many2one('grp.valores_custodia', u'Valor en custodia')
    receipt_serial = fields.Char(string=u'Serie', size=10, compute='_compute_origin_fields', multi='origin_fields', compute_sudo=True)
    # receipt_check = fields.Integer(string=u'Nº cheque', compute='_compute_origin_fields', multi='origin_fields')
    receipt_check = fields.Char(string=u'Nº cheque', compute='_compute_origin_fields', multi='origin_fields', compute_sudo=True)
    bank_id = fields.Many2one('res.bank', string=u'Banco', compute='_compute_origin_fields', multi='origin_fields', compute_sudo=True)
    check_amount = fields.Float(string=u'Importe', compute='_compute_origin_fields', multi='origin_fields', compute_sudo=True)
    # no_bank_account = fields.Integer(string=u'Nº cuenta bancaria', compute='_compute_origin_fields',
    #                                  multi='origin_fields')
    no_bank_account = fields.Char(string=u'Nº cuenta bancaria', compute='_compute_origin_fields',
                                     multi='origin_fields', compute_sudo=True)
    voucher_currency_id = fields.Many2one('res.currency', u'Divisa', compute='_compute_origin_fields',
                                          multi='origin_fields', compute_sudo=True)

    invoice_id = fields.Many2one('account.invoice', 'Factura')
    # NOTA: invoice_id DEBERIA PASAR A SER RELATED, NO SE PUEDE PORQUE SE PERDERIA INFORMACION EXISTENTE:
    # MOTIVO: invoice_line_id ES UN CAMPO NUEVO. SE CREA POR LA POSIBILIDAD DE VARIAS LINEAS DE FACTURA CON PRODUCTOS IGUALES
    invoice_line_id = fields.Many2one('account.invoice.line', 'Línea de factura')
    nro_factura_grp = fields.Char(u'Nro. Factura GRP', readonly=True, related='invoice_id.number')
    partner_id = fields.Many2one('res.partner', string=u'Cliente', compute='_compute_origin_fields', multi='origin_fields', compute_sudo=True)
    number = fields.Char(string=u'N° cobro GRP', compute='_compute_origin_fields', multi='origin_fields', compute_sudo=True)
    operating_unit_id = fields.Many2one('operating.unit', u'Unidad ejecutora', compute='_compute_operating_unit_id', store=True, compute_sudo=True)
    currency_id = fields.Many2one('res.currency', u'Divisa', compute='_compute_origin_fields', multi='origin_fields', compute_sudo=True)
    date = fields.Date(u'Fecha de cobro', compute='_compute_origin_fields', multi='origin_fields', compute_sudo=True)
    payment_method = fields.Selection([('check', 'Cheque'),
                                       ('cash', 'Efectivo'),
                                       ('transfer', 'Transferencia')],
                                      string='Medio de pago', compute='_compute_origin_fields', multi='origin_fields', compute_sudo=True)
    amount = fields.Float(string=u'Importe cobrado')
    remove_transaction = fields.Boolean(u'Quitar transacción', default=False)
    removed_transaction = fields.Boolean(u'Transacción removida', default=False)
    cancel_transaction = fields.Boolean(u'Cancelar transacción', default=False)

    type = fields.Selection([('opening_check', 'Apertura Cheque'),
                             ('voucher', 'Recibo'),
                             ('check', 'Cheque'),
                             ('details', 'Detalles'),
                             ('box_details', 'Detalles de caja')], string='Tipo', store=True)
    product_id = fields.Many2one('product.product', u'Producto')
    price_subtotal = fields.Float(string=u'Importe')
    plus_amount = fields.Float(string=u'Redondeo')
    weight_amount = fields.Float(compute='_compute_weight_amount', string=u'Importe moneda caja',
                                 store=True)
    companycurrency_amount = fields.Float(compute='_compute_companycurrency_amount', string=u'Importe moneda compañía', store=True)

    shipment = fields.Boolean(u'Preparar remesa', default=False)
    siff_ticket = fields.Boolean(u'Boleto SIIF', default=False)
    voucher_selected = fields.Boolean(u'Recibo seleccionado', compute='_compute_voucher_selected', store=True)

    edit_remove_transaction = fields.Boolean(string="Editar Quitar transacción",
                                             compute='_compute_shipment',multi='shipment', default=True)
    edit_cancel_transaction = fields.Boolean(string="Editar Cancelar transacción",
                                             compute='_compute_shipment',multi='shipment', default=True)
    # update_remove_transaction = fields.Boolean(string="Actualizar Quitar transacción",
    #                                          compute='_compute_update_remove_transaction', default=True)

    edit_shipment = fields.Boolean(string="Editar remesa", default=True)

    no_recibo = fields.Char(string=u'No recibo')
    entrega_caja = fields.Boolean(u'Entrega en caja', default=False)
    fecha_entrega = fields.Date(u'Fecha entrega')
    edit_entrega = fields.Boolean(string="Editar Enttrega caja", compute='_compute_edit_entrega',
                                  default=False)
    entregado = fields.Boolean(u'Entregado', default=False, compute='_compute_entregado', store=True, compute_sudo=True)
    check_shipment_bar_code = fields.Char(u'Código de barra')
    apertura_recibo = fields.Boolean(u'Saldo apertura', default=False)
    caja_state = fields.Selection([('draft', u'Borrador'),
                                   ('open', u'Abierto'),
                                   ('collection_send', u'Recaudación enviada'),
                                   ('close', u'Cerrado'),
                                   ('checked', u'Revisado')], string=u'Estado',
                                  related='caja_recaudadora_id.state', readonly=True)
    move_id = fields.Many2one('account.move', 'Asiento contable')

    # RAGU entrega tesoreria
    entrega_tesoreria = fields.Boolean(u'Entrega en tesorería', default=False)
    preparar_remesa = fields.Boolean(string=u'En preparar remesa', default=False)

    @api.onchange('entrega_caja')
    def _onchange_entrega_caja(self):
        if not self.entrega_caja:
            self.fecha_entrega = False
        else:
            self.entrega_tesoreria = False
            self.shipment = False

    @api.onchange('entrega_tesoreria')
    def _onchange_entrega_tesoreria(self):
        if self.entrega_tesoreria:
            self.entrega_caja = False
            self.shipment = False

    @api.onchange('shipment')
    def _onchange_shipment(self):
        if self.shipment:
            self.entrega_caja = False
            self.entrega_tesoreria = False

    @api.multi
    @api.depends('valor_custodia_id', 'voucher_id', 'invoice_id')
    def _compute_origin_fields(self):
        for rec in self:
            if rec.voucher_id:
                rec.receipt_serial = rec.voucher_id.receipt_serial
                rec.receipt_check = rec.voucher_id.receipt_check
                rec.bank_id = rec.voucher_id.bank_id.id
                rec.check_amount = rec.voucher_id.check_amount
                rec.no_bank_account = rec.voucher_id.no_bank_account
                rec.voucher_currency_id = rec.voucher_id.currency_id.id
                rec.date = rec.voucher_id.date
                rec.payment_method = rec.voucher_id.payment_method
                if rec.invoice_id:
                    rec.partner_id = rec.invoice_id.partner_id.id
                    rec.currency_id = rec.voucher_id.currency_id.id
                    rec.number = rec.voucher_id.number
                else:
                    rec.partner_id = rec.origin_voucher_id.partner_id.id
                    rec.currency_id = rec.origin_voucher_id.currency_id.id
                    if rec.origin_voucher_id.exists():
                        if rec.origin_voucher_id.rendicion_viaticos_id:
                            # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
                            # rec.number = rec.origin_voucher_id.rendicion_viaticos_id.sequence
                            rec.number = rec.origin_voucher_id.rendicion_viaticos_id.x_sequence
                            #
                        elif rec.origin_voucher_id.rendicion_anticipos_id:
                            # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
                            # rec.number = rec.origin_voucher_id.rendicion_anticipos_id.sequence
                            rec.number = rec.origin_voucher_id.rendicion_anticipos_id.x_sequence
                            #
                        elif rec.origin_voucher_id.solicitud_viatico_id:
                            rec.number = rec.origin_voucher_id.solicitud_viatico_id.name
                        elif rec.origin_voucher_id.solicitud_anticipos_id:
                            rec.number = rec.origin_voucher_id.solicitud_anticipos_id.name
                        else:
                            rec.number = rec.origin_voucher_id.number
            else:
                rec.receipt_serial = rec.valor_custodia_id.serie
                rec.receipt_check = rec.valor_custodia_id.check_number
                rec.bank_id = rec.valor_custodia_id.bank_id
                rec.check_amount = rec.valor_custodia_id.monto
                rec.no_bank_account = rec.valor_custodia_id.number_bank_account
                rec.voucher_currency_id = rec.valor_custodia_id.currency_id.id
                rec.date = rec.valor_custodia_id.fecha_recepcion
                rec.payment_method = rec.valor_custodia_id.payment_method
                rec.partner_id = rec.valor_custodia_id.partner_id.id
                rec.number = rec.valor_custodia_id.name
                rec.currency_id = rec.valor_custodia_id.currency_id.id

    @api.multi
    @api.depends('valor_custodia_id', 'voucher_id', 'invoice_id', 'origin_voucher_id')
    def _compute_operating_unit_id(self):
        for rec in self:
            if rec.vline_id:
                rec.operating_unit_id = rec.vline_id.operating_unit_id.id
            elif rec.invoice_id:
                rec.operating_unit_id = rec.invoice_id.operating_unit_id.id
            elif rec.voucher_id:
                rec.operating_unit_id = rec.origin_voucher_id.operating_unit_id.id
            elif rec.valor_custodia_id:
                rec.operating_unit_id = rec.valor_custodia_id.operating_unit_id.id
            else:
                rec.operating_unit_id = False

    @api.multi
    @api.depends('product_id', 'type')
    def _compute_edit_entrega(self):
        mapeo = self.env['grp.producto.cuenta.deposito']
        for rec in self:
            rec.edit_entrega = rec.product_id and rec.type == 'details' and mapeo.search([('product_id', '=', rec.product_id.id), ('no_siif', '=', True)])
        return True

    @api.multi
    @api.depends('caja_recaudadora_id.voucher_details_ids.entrega_caja',
                 'caja_recaudadora_id.voucher_details_ids.entrega_tesoreria',
                 'caja_recaudadora_id.valores_custodia_ids.entrega_tesoreria')
    def _compute_entregado(self):
        vc_obj = self.env['grp.caja.recaudadora.tesoreria.line.valor.custodia']
        # for rec in self.filtered(lambda x: x.type in ['voucher', 'check']):
        for rec in self:
            _entregado = False
            if self.search([('caja_recaudadora_id.name', '=', rec.caja_recaudadora_id.name),
                           ('voucher_id', '=', rec.voucher_id.id), ('type', '=', 'details'),'|',('entrega_caja', '=', True),('entrega_tesoreria', '=', True)]):
                _entregado = True
            if vc_obj.search([('caja_recaudadora_id.name', '=', rec.caja_recaudadora_id.name),
                           ('valor_custodia_id', '=', rec.valor_custodia_id.id), ('entrega_tesoreria', '=', True)]):
                _entregado = True
            rec.entregado = _entregado

    @api.multi
    @api.depends('caja_recaudadora_id.voucher_details_ids.shipment',
                 'caja_recaudadora_id.voucher_details_ids.entrega_caja',
                 'caja_recaudadora_id.voucher_details_ids.entrega_tesoreria',
                 'caja_recaudadora_id.valores_custodia_ids.shipment')
    def _compute_shipment(self):
        for rec in self.filtered(lambda x: x.type in ['voucher', 'check']):
            if rec.removed_transaction:
                _edit_remove_transaction = False
                _edit_cancel_transaction = False
            else:
                _edit_remove_transaction = True
                _edit_cancel_transaction = True
                line_id = self.search([('caja_recaudadora_id.name','=',rec.caja_recaudadora_id.name),
                                      ('type','=','details'),('voucher_id','=',rec.voucher_id.id),
                                      ('invoice_id','=',rec.invoice_id.id)], limit=1)
                if line_id:
                    _edit_cancel_transaction = False if line_id.apertura_recibo else True
                    _edit_remove_transaction = False if line_id.apertura_recibo or line_id.shipment or line_id.entrega_caja or line_id.entrega_tesoreria else True

                if _edit_remove_transaction:
                    for valor_custodia in rec.caja_recaudadora_id.valores_custodia_ids: #PARCHE
                        if (valor_custodia.shipment) and valor_custodia.valor_custodia_id.id == rec.valor_custodia_id.id:
                            _edit_remove_transaction = False
                            break

                    for detalle_id in rec.caja_recaudadora_id.voucher_details_ids: #PARCHE
                        if (detalle_id.shipment) and (detalle_id.number == rec.number or (detalle_id.vline_id and detalle_id.vline_id.id == rec.vline_id.id)):
                            _edit_remove_transaction = False
                            break

            rec.edit_remove_transaction = _edit_remove_transaction
            rec.edit_cancel_transaction = _edit_cancel_transaction


    @api.multi
    @api.depends('caja_recaudadora_id.voucher_details_ids.shipment',
                 'caja_recaudadora_id.valores_custodia_ids.shipment')
    def _compute_voucher_selected(self):
        for rec in self:
        # for rec in self.filtered(lambda x: x.type in ['voucher', 'check']):
            _voucher_selected = False

            for valor_custodia in rec.suspend_security().caja_recaudadora_id.valores_custodia_ids:  # PARCHE
                if (valor_custodia.shipment) and valor_custodia.valor_custodia_id.id == rec.suspend_security().valor_custodia_id.id:
                    _voucher_selected = True
                    break

            for detalle_id in rec.suspend_security().caja_recaudadora_id.voucher_details_ids:  # PARCHE
                if (detalle_id.shipment) and (detalle_id.number == rec.number or (
                    detalle_id.vline_id and detalle_id.vline_id.id == rec.suspend_security().vline_id.id)):
                    _voucher_selected = True
                    break

            rec.voucher_selected = _voucher_selected

    @api.multi
    @api.depends('product_id','currency_id','invoice_id','voucher_id','price_subtotal','plus_amount')
    def _compute_weight_amount(self):
        for rec in self:
            if rec.invoice_id:
                source_currency_id = rec.invoice_id.currency_id
                lang = rec.invoice_id.partner_id.lang
            else:
                source_currency_id = rec.voucher_id.currency_id
                lang = rec.voucher_id.partner_id.lang
            if rec.currency_id and source_currency_id and rec.currency_id.id != source_currency_id.id:
                ctx = dict(self._context, lang=lang)
                ctx.update({'date': rec.date or time.strftime('%Y-%m-%d')})
                _weight_amount = source_currency_id.with_context(ctx).compute(rec.price_subtotal, rec.currency_id)
            else:
                _weight_amount = rec.price_subtotal
            rec.weight_amount = _weight_amount + rec.plus_amount

    @api.multi
    @api.depends('weight_amount')
    def _compute_companycurrency_amount(self):
        for rec in self:
            company_currency_id = rec.caja_recaudadora_id.journal_id.company_id.currency_id
            if rec.currency_id and company_currency_id and rec.currency_id.id != company_currency_id.id:
                ctx = dict(self._context)
                ctx.update({'date': rec.date or time.strftime('%Y-%m-%d')})
                _companycurrency_amount = rec.currency_id.with_context(ctx).compute(rec.weight_amount, company_currency_id)
            else:
                _companycurrency_amount = rec.weight_amount
            rec.companycurrency_amount = _companycurrency_amount + rec.plus_amount


    @api.onchange('cancel_transaction')
    def onchange_cancel_transaction(self):
        voucher_details = self.search([('voucher_id', '=', self.voucher_id.id), ('type', '=', 'details'),
                                       ('caja_recaudadora_id', '=', self.caja_recaudadora_id.id)])
        voucher_details.write({'cancel_transaction': True})
        check = self.search([('voucher_id', '=', self.voucher_id.id), ('type', '=', 'check'),
                             ('caja_recaudadora_id', '=', self.caja_recaudadora_id.id)])
        if self.cancel_transaction:
            voucher_details.write({'cancel_transaction': True})
            check.write({'cancel_transaction': True})
        else:
            voucher_details.write({'cancel_transaction': False})
            check.write({'cancel_transaction': False})

    @api.multi
    def btn_imprimir_recibo(self):
        self.ensure_one()
        invoices = self.env['account.invoice'].browse(self.invoice_id.ids)
        datas = {
            'ids': invoices.ids,
            'model': 'account.invoice',
        }
        return self.env['report'].get_action(invoices, 'grp_tesoreria.report_recibos_document', data=datas)

    @api.multi
    def write(self, values):
        for rec in self:
            if 'remove_transaction' in values and rec.type == 'voucher':
                details = rec.search([('caja_recaudadora_id', '=', rec.caja_recaudadora_id.id),
                                      ('voucher_id', '=', rec.voucher_id.id), ('type', '=', 'details'),
                                      ('invoice_id', '=', rec.invoice_id.id)])
                if details:
                    details.write({'remove_transaction': values['remove_transaction']})

                check = rec.search([('caja_recaudadora_id', '=', rec.caja_recaudadora_id.id),
                                    ('voucher_id', '=', rec.voucher_id.id), ('type', '=', 'check'),
                                    ('invoice_id', '=', rec.invoice_id.id)])
                if check:
                    check.write({'remove_transaction': values['remove_transaction']})
            if 'shipment' in values and rec.type == 'details' and 'shipment' not in self._context:
                details = rec.search([('caja_recaudadora_id', '=', rec.caja_recaudadora_id.id),
                                      ('voucher_id', '=', rec.voucher_id.id), ('type', '=', 'details'),
                                      ('invoice_id', '=', rec.invoice_id.id), ('id', '!=', self.id)])
                if details:
                    ctx = self._context.copy()
                    ctx.update({'shipment': True})
                    details.with_context(ctx).write({'shipment': values['shipment']})
        return super(GrpCajaRecaudadoraTesoreriaLine, self).write(values)

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.origin_line_id:
                rec.origin_line_id.write({'preparar_remesa': False})
            # if rec.payment_method in ['check']:
            #
            if rec.type == 'voucher':
                if rec.caja_recaudadora_id.state == 'checked':
                    raise exceptions.ValidationError(
                        _(u'No se puede eliminar el recibo ya que la caja se encuentra en estado "Revisado".'))
                # RAGU limpiando enlace de factura con Boleto SIIF
                if rec.boleto_siif_id and rec.invoice_id:
                    rec.invoice_id.write({'boleto_siif_id': False})

                lineas = rec.search([('caja_recaudadora_id', '=', rec.caja_recaudadora_id.id),
                                     ('voucher_id', '=', rec.voucher_id.id), ('type', 'in', ['details', 'check']),
                                     ('invoice_id', '=', rec.invoice_id.id)])
                lineas.unlink()
                rec.invoice_id.write({'caja_recaudadora_id': False})
            #RAGU limpiando referencia siif
            if rec.siif_reference_id:
                rec.siif_reference_id.write({'siff_ticket':False})

        return super(GrpCajaRecaudadoraTesoreriaLine, self).unlink()

class ReciboPagoReporte(models.AbstractModel):
    _name = 'report.grp_tesoreria.report_recibos_document'

    def render_html(self, cr, uid, ids, data=None, context=None):
        report_obj = self.pool['report']
        invoices_obj = self.pool['account.invoice']
        report = report_obj._get_report_from_name(cr, uid, 'grp_tesoreria.report_recibos_document')
        ids = ids
        if data is not None and 'ids' in data:
            ids = data['ids']
        invoices = invoices_obj.browse(cr, uid, ids, context=context)
        ids_to_print = [invoice.id for invoice in invoices]

        docargs = {
            'doc_ids': ids_to_print,
            'doc_model': report.model,
            'docs': invoices,
        }
        return report_obj.render(cr, uid, ids, 'grp_tesoreria.report_recibos_document', docargs, context=context)


class GrpCajaRecaudadoraTesoreriaLineRemesa(models.Model):
    _name = 'grp.caja.recaudadora.tesoreria.line.remesa'

    caja_recaudadora_id = fields.Many2one('grp.caja.recaudadora.tesoreria', 'Caja recaudadora')
    boleto_siif_id = fields.Many2one('grp.caja.recaudadora.tesoreria.boleto.siif', u'Boleto SIIF')
    type = fields.Selection([('cash', 'Remesa efectivo'),
                             ('check', 'Remesa cheque'),
                             ('product_ue', 'Remesa producto y ue'),
                             ('total', 'Remesa Total')], string='Tipo', store=True)
    product_id = fields.Many2one('product.product', u'Producto')
    operating_unit_id = fields.Many2one('operating.unit', string='Unidad ejecutora')
    amount = fields.Float(string=u'Importe')
    amount_siif = fields.Float(string=u'Importe SIIF')


class GrpCajaRecaudadoraTesoreriaLineTransaccion(models.Model):
    _name = 'grp.caja.recaudadora.tesoreria.line.transaccion'

    name = fields.Char(u'Nombre', default='/')
    caja_recaudadora_id = fields.Many2one('grp.caja.recaudadora.tesoreria', 'Caja recaudadora')
    date = fields.Date(u'Fecha', required=True)
    concept_id = fields.Many2one('grp_concepto_gasto_cc_viaticos', u'Concepto', required=True,
                                 domain="[('caja_recaudadora','=', True)]")
    amount = fields.Float(string=u'Importe', required=True)
    ajuste = fields.Boolean(u'Ajuste en el cierre de caja', default=False)
    move_id = fields.Many2one('account.move', 'Asiento contable')

    @api.model
    def create(self, vals):
        if vals.get('concept_id', False):
            concepto = self.env['grp_concepto_gasto_cc_viaticos'].browse(vals['concept_id'])
            if vals.get('amount', False):
                amount = vals['amount']
                if not concepto.otros:
                    if concepto.signo in ['pos']:
                        vals.update({'amount': abs(amount)})
                    else:
                        vals.update({'amount': -abs(amount)})
                        # TODO: M INCIDENCIA
        return super(GrpCajaRecaudadoraTesoreriaLineTransaccion, self).create(vals)

    # RAGU verificando signo si cambia concepto o monto
    @api.multi
    def write(self, vals):
        if vals.get('concept_id') or vals.get('amount'):
            concept_id = self.env['grp_concepto_gasto_cc_viaticos'].browse(vals['concept_id']) if vals.get(
                'concept_id') else self.concept_id
            if not concept_id.otros:
                amount = vals['amount'] if vals.get('amount') else self.amount
                vals.update({'amount': abs(amount) if concept_id.signo in ['pos'] else -abs(amount)})
        return super(GrpCajaRecaudadoraTesoreriaLineTransaccion, self).write(vals)

    def _prepare_move(self):
        period_id = self.env['account.period'].find(self.date).id
        if self._context.get('diference', False) and self._context['diference'] < 0.0:
            account_debit = self.caja_recaudadora_id.journal_id.loss_account_id.id
            account_credit = self.caja_recaudadora_id.journal_id.default_debit_account_id.id
        if self._context.get('diference', False) and self._context['diference'] > 0.0:
            account_debit = self.caja_recaudadora_id.journal_id.profit_account_id.id
            account_credit = self.caja_recaudadora_id.journal_id.default_credit_account_id.id
        move_line_vals_debit = {
            'name': self.name,
            'ref': self.caja_recaudadora_id.name or "/",
            'account_id': account_debit,
            'debit': self.amount,
            'credit': 0.0,
            'currency_id': False,
            'amount_currency': 0.0,
        }
        move_line_vals_credit = {
            'name': self.name,
            'ref': self.caja_recaudadora_id.name or "/",
            'account_id': account_credit,
            'debit': 0.0,
            'credit': self.amount,
            'currency_id': False,
            'amount_currency': 0.0,
        }

        return {
            'journal_id': self.caja_recaudadora_id.journal_id.id,
            'period_id': period_id,
            'date': self.date,
            'name': self.name,
            'ref': self.caja_recaudadora_id.name or "/",
            'line_id': [(0, 0, move_line_vals_debit), (0, 0, move_line_vals_credit)]
        }


class GrpCajaRecaudadoraTesoreriaLineValorCustodia(models.Model):
    _name = 'grp.caja.recaudadora.tesoreria.line.valor.custodia'

    caja_recaudadora_id = fields.Many2one('grp.caja.recaudadora.tesoreria', 'Caja recaudadora')
    boleto_siif_id = fields.Many2one('grp.caja.recaudadora.tesoreria.boleto.siif', u'Boleto SIIF')
    valor_custodia_id = fields.Many2one('grp.valores_custodia', 'VC', help='Valor en custodia')
    operating_unit_id = fields.Many2one('operating.unit', string='Unidad ejecutora',
                                        related='valor_custodia_id.operating_unit_id', readonly=True, store=True)
    partner_id = fields.Many2one('res.partner', string=u'Cliente', related='valor_custodia_id.partner_id', readonly=True)
    fecha_recepcion = fields.Date(u'Fecha de cobro', related='valor_custodia_id.fecha_recepcion', readonly=True)
    name = fields.Char(u'N°', related='valor_custodia_id.name', readonly=True)
    monto = fields.Float(string=u'Importe cobrado', related='valor_custodia_id.monto', store=True, readonly=True)
    payment_method = fields.Selection([('check', 'Cheque'),
                                       ('cash', 'Efectivo')], string='Medio de pago',
                                      related='valor_custodia_id.payment_method', readonly=True)
    serie = fields.Char(u'Serie', related='valor_custodia_id.serie', readonly=True)
    # check_number = fields.Integer(string=u'Nº cheque', related='valor_custodia_id.check_number')
    check_number = fields.Char(string=u'Nº cheque', related='valor_custodia_id.check_number', readonly=True)
    check_date = fields.Date(u'Fecha cheque', related='valor_custodia_id.check_date', readonly=True)
    number_bank_account = fields.Char(string=u'Nº cuenta bancaria', related='valor_custodia_id.number_bank_account', readonly=True)
    currency_id = fields.Many2one('res.currency', u'Divisa', related='valor_custodia_id.currency_id', readonly=True)
    product_id = fields.Many2one('product.product', u'Producto')
    amount = fields.Float(string=u'Importe', related='valor_custodia_id.monto', store=True, readonly=True)
    shipment = fields.Boolean(u'Preparar remesa', default=False)
    remove_transaction = fields.Boolean(u'Quitar transacción', default=False)
    siff_ticket = fields.Boolean(u'Boleto SIIF', default=False)
    entregado = fields.Boolean(u'Entregado', default=False)
    apertura_recibo = fields.Boolean(u'Saldo apertura', default=False)
    caja_state = fields.Selection([('draft', u'Borrador'),
                                   ('open', u'Abierto'),
                                   ('collection_send', u'Recaudación enviada'),
                                   ('close', u'Cerrado'),
                                   ('checked', u'Revisado')], string=u'Estado',
                                  related='caja_recaudadora_id.state', readonly=True)

    # RAGU entrega tesoreria
    entrega_tesoreria = fields.Boolean(u'Entrega en tesorería', default=False)

    @api.onchange('remove_transaction')
    def _onchange_remove_transaction(self):
        if self.remove_transaction:
            self.entrega_tesoreria = False
            self.shipment = False

    @api.onchange('shipment')
    def _onchange_shipment(self):
        if self.shipment:
            self.remove_transaction = False
            self.entrega_tesoreria = False

    @api.onchange('entrega_tesoreria')
    def _onchange_entrega_tesoreria(self):
        if self.entrega_tesoreria:
            self.shipment = False
            self.remove_transaction = False

    @api.multi
    def write(self, values):
        for rec in self:
            line_id = self.env['grp.caja.recaudadora.tesoreria.line'].search([
                ('caja_recaudadora_id', '=', rec.caja_recaudadora_id.id),
                ('valor_custodia_id', '=', rec.valor_custodia_id.id)])
            voucher_selected = True if values.get('shipment') and values['shipment'] else False
            remove_transaction = True if values.get('remove_transaction') and values['remove_transaction'] else False
            if line_id:
                line_id.write({'voucher_selected':voucher_selected,'remove_transaction':remove_transaction})

        return super(GrpCajaRecaudadoraTesoreriaLineValorCustodia, self).write(values)

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.valor_custodia_id:
                rec.valor_custodia_id.write({'boleto_siif': False})
        return super(GrpCajaRecaudadoraTesoreriaLineValorCustodia, self).unlink()


class GrpAccountCashboxLine(models.Model):
    _inherit = 'account.cashbox.line'

    caja_recaudadora_id = fields.Many2one('grp.caja.recaudadora.tesoreria', 'Caja recaudadora')


class GrpAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    caja_recaudadora_id = fields.Many2one('grp.caja.recaudadora.tesoreria', 'Caja recaudadora')


class GrpCajaRecaudadoraTesoreriaBoletoSiif(models.Model):
    _inherit = 'grp.caja.recaudadora.tesoreria'
    _name = 'grp.caja.recaudadora.tesoreria.boleto.siif'
    _description = u"Caja recaudadora tesorería boleto SIIF"

    date = fields.Date(u'Fecha')
    state = fields.Selection(
        [('draft', u'Nuevo'),
         ('send', u'Enviado a Tesorería'),
         ('collection_send', u'Recaudación enviada')],
        u'Estado', default='draft', track_visibility='onchange')

    box_details_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line', 'boleto_siif_id', 'Detalles de caja',
                                      domain=[('type', '=', 'box_details')])
    voucher_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line', 'boleto_siif_id', 'Recibos',
                                  domain=[('type', '=', 'voucher')])
    voucher_details_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line', 'boleto_siif_id', 'Detalles',
                                          domain=[('type', '=', 'details')])
    valores_custodia_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line.valor.custodia', 'boleto_siif_id',
                                           'Valores Custodia')
    product_ue_shipment_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line.remesa', 'boleto_siif_id',
                                              'Remesas Producto y UE',
                                              domain=[('type', '=', 'product_ue')])
    total_shipment_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line.remesa', 'boleto_siif_id',
                                         'Remesas',
                                         domain=[('type', '=', 'total')])
    cash_shipment_siff_ticket = fields.Char(u'Boleto SIIF', size=60)
    cash_shipment_bar_code = fields.Char(u'Código de barra')

    def _get_shipment_siif(self, product):
        total = 0
        vouchers_details = self.voucher_details_ids.filtered(
            lambda x: x.shipment is True and x.product_id.id == product.id)
        if vouchers_details:
            total += sum(map(lambda v: v.weight_amount, vouchers_details)) * (-1)

            box_details = self.box_details_ids.filtered(
                lambda x: x.shipment is True and x.product_id.id == product.id)
            if box_details:
                total += sum(map(lambda v: v.weight_amount, box_details)) * (-1)
        return total

    @api.multi
    def btn_send(self):
        self.write({'state': 'send'})

    @api.multi
    def btn_collection_send(self):
        data = self._update_remesa()
        res = super(GrpCajaRecaudadoraTesoreriaBoletoSiif, self).write(data)
        for rec in self:
            if not rec.cash_shipment_siff_ticket:
                raise exceptions.ValidationError(
                    _(u'Debe ingresar un valor para el campo Boleto SIIF.'))
            rec.write({'state': 'collection_send'})

    @api.multi
    def btn_cancel(self):
        self.write({'state': 'draft'})

    @api.multi
    def write(self, values):
        res = super(GrpCajaRecaudadoraTesoreriaBoletoSiif, self).write(values)
        if 'box_details_ids' in values or 'valores_custodia_ids' in values or 'voucher_details_ids' in values:
            data = self._update_remesa()
            res = super(GrpCajaRecaudadoraTesoreriaBoletoSiif, self).write(data)
        return res

    def _update_remesa(self):
        data = super(GrpCajaRecaudadoraTesoreriaBoletoSiif, self)._update_remesa()
        for rec in self:
            total_shipment_ids = []
            _product_ue_shipment_ids = []
            box_details = rec.box_details_ids.filtered(lambda x: x.shipment)
            voucher_details = rec.voucher_details_ids
            valores_custodia = rec.valores_custodia_ids.filtered(lambda x: x.product_id)
            products = []
            if box_details or valores_custodia or voucher_details:
                products = list(
                    set(box_details.mapped('product_id')) | set(valores_custodia.mapped('product_id')) | set(
                        voucher_details.mapped('product_id')))

            rec.total_shipment_ids.unlink()
            rec.product_ue_shipment_ids.unlink()

            # RAGU remesas por producto y UE
            sql = """SELECT product_id, operating_unit_id, SUM(amount) AS amount FROM
(SELECT product_id, operating_unit_id, weight_amount AS amount FROM grp_caja_recaudadora_tesoreria_line WHERE type IN ('box_details', 'details') AND boleto_siif_id = %s
UNION ALL
SELECT product_id, operating_unit_id, SUM(amount) AS amount FROM grp_caja_recaudadora_tesoreria_line_valor_custodia WHERE boleto_siif_id = %s GROUP BY product_id,operating_unit_id) AS subquery_1
GROUP BY product_id, operating_unit_id""" % (str(rec.id),str(rec.id))
            self.env.cr.execute(sql)

            expensive_product_ue_line = False
            product_ue_residuals_amount = 0
            for line in self.env.cr.dictfetchall():
                round_total = round(line['amount'], 0)
                new_line = (0, 0, {'product_id': line['product_id'],
                                                        'operating_unit_id': line['operating_unit_id'],
                                                        'amount': line['amount'],
                                                        'amount_siif': round_total,
                                                        'type': 'product_ue'})
                _product_ue_shipment_ids.append(new_line)
                product_ue_residuals_amount += line['amount'] - round_total
                if not expensive_product_ue_line or expensive_product_ue_line[2]['amount_siif'] < round_total:
                    expensive_product_ue_line = new_line

            expensive_total_line = False
            total_residuals_amount = 0
            for product in products:
                total = sum(map(lambda v: v.weight_amount, box_details.filtered(
                    lambda x: x.product_id.id == product.id))) * (-1)

                total += sum(map(lambda v: v.amount, valores_custodia.filtered(
                    lambda x: x.product_id.id == product.id))) * (-1)

                total += sum(map(lambda v: v.weight_amount, voucher_details.filtered(
                    lambda x: x.product_id.id == product.id))) * (-1)
                if total:
                    round_total = round(total, 0)
                    new_line = (0, 0, {'product_id': product.id, 'amount': total,'amount_siif': round_total, 'type': 'total'})
                    total_shipment_ids.append(new_line)
                    total_residuals_amount += total - round_total
                    if not expensive_total_line or expensive_total_line[2]['amount_siif'] < round_total:
                        expensive_total_line = new_line

            if expensive_total_line:
                expensive_total_line[2]['amount_siif'] += round(total_residuals_amount,0)
            if expensive_product_ue_line:
                expensive_product_ue_line[2]['amount_siif'] += round(product_ue_residuals_amount,0)
            data.update({
                'total_shipment_ids': total_shipment_ids,
                'product_ue_shipment_ids': _product_ue_shipment_ids
            })

            return data

    @api.multi
    def unlink(self):
        for rec in self:
            rec.box_details_ids.unlink()
            rec.voucher_ids.unlink()
            rec.voucher_details_ids.unlink()
            rec.valores_custodia_ids.unlink()
            rec.product_ue_shipment_ids.unlink()
            rec.total_shipment_ids.unlink()
        return super(GrpCajaRecaudadoraTesoreriaBoletoSiif, self).unlink()
