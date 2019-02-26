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

import itertools
import time

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
from openerp.tools import float_compare, float_round

# TODO: SPRING 10 GAP 474 C

VOUCHER_STATE = [('draft', 'Borrador'),
                 ('confirm', 'Confirmado'),
                 ('issue', 'Emitido'),
                 ('cancel', 'Cancelado'),
                 ('proforma', 'Pro-forma'),
                 ('posted', 'Pago')
                 ]
CUSTODY_STATE = [('borrador', 'Borrador'),
                 ('entregado', u'Entregar a Tesorería'),
                 ('recibido', u'Recibido Tesorería'), ('vencido', u'Vencido en Tesorería'),
                 ('entrega_autorizada', u'Entrega Autorizada'),
                 ('entrega_tesoreria', u'Entregado por Tesorería'),
                 ('baja', 'Baja')
                 ]


def _get_state(states, current):
    state = filter(lambda x: x[0] == current, states)
    return state[0][1] if len(state) else ''

# TODO: M INCIDENCIA
class GrpCajaChicaTesoreria(models.Model):
    _name = 'grp.caja.chica.tesoreria'
    _description = "Caja efectivo"
    _inherit = 'account.bank.statement'

    journal_id = fields.Many2one('account.journal', string=u'Diario', readonly=True, store=True,required=False,
                                 related='box_id.journal_id')
    operating_unit_id = fields.Many2one('operating.unit', string="Unidad Ejecutora",
                                        related='journal_id.operating_unit_id', readonly=True)
    user_id = fields.Many2one('res.users', 'Responsable')
    date = fields.Datetime(string=u'Fecha de apertura', required=True)
    state = fields.Selection([('draft', 'Borrador'),
                              ('open', u'Abierto/a'),
                              ('end', 'Cerrado'),
                              ('check', 'Revisado'),
                              ], u'Estado', default='draft')
    box_id = fields.Many2one('grp.caja', string='Caja', states={'draft': [('readonly', False)]}, readonly=True,
                             domain="[('caja_pagadora','=', True),('journal_id.caja_chica_t','=', True),('users','=',uid)]")
    line_ids = fields.One2many('grp.caja.chica.tesoreria.line', 'caja_chica_id', 'Transacciones',
                                      states={'check': [('readonly', True)]}, readonly=False)
    transaction_ids = fields.One2many('grp.caja.chica.tesoreria.line', 'caja_chica_id', 'Transacciones',
                                      states={'check': [('readonly', True)]}, readonly=False)
    move_line_ids = fields.One2many('account.move.line', 'caja_chica_id', u'Líneas de asiento',
                                    states={'check': [('readonly', True)]}, readonly=False)
    opening_details_ids = fields.One2many('account.cashbox.line', 'caja_chica_id', 'Control de efectivo',
                                          states={'check': [('readonly', True)]})
    details_ids = fields.One2many('account.cashbox.line', 'caja_chica_id', 'Control de efectivo',
                                  states={'check': [('readonly', True)]})
    closing_details_ids = fields.One2many('account.cashbox.line', 'caja_chica_id', 'Control de efectivo',
                                          states={'check': [('readonly', True)]})
    show_adv = fields.Boolean(string="Mostrar confirm", compute='_compute_show_adv', default=False)
    total_entry_encoding = fields.Float(string="Transacciones", compute='_compute_total_entry_encoding', multi='transactions', store=False)
    in_amount = fields.Float(string="Total de ingresos", compute='_compute_total_entry_encoding', multi='transactions')
    out_amount = fields.Float(string="Total de egresos", compute='_compute_total_entry_encoding', multi='transactions')
    balance_end = fields.Float(string="Transacciones", compute='_compute_balance_end', store=False)
    linea_llp_ids = fields.One2many('grp_llave_presupuestal_registro_caja', 'caja_chica_id', u'Líneas de llave presupuestal')

    sequence_complement = fields.Integer(u'Complemento para secuencial de cada caja', default=1)

    @api.onchange('box_id')
    def _onchange_box_id(self):
        _journal_id = False
        if self.box_id:
            if self.box_id.journal_id.type == 'cash' and self.box_id.journal_id.caja_chica_t:
                _journal_id = self.box_id.journal_id.id
        self.opening_details_ids = self._get_opening_details_ids()
        self.journal_id =_journal_id

    @api.multi
    @api.constrains('box_id', 'state')
    def _check_account_bank_statement_journal(self):
        for rec in self:
            if rec.state in ['open','draft'] and self.search_count(
                    [('box_id', '=', rec.box_id.id), ('state', '=', rec.state), ('id', '!=', rec.id)]):
                raise ValidationError(_(u"Solo debe existir un registro por Caja en estado 'Abierto' o 'Borrador'!"))
        return True

    @api.multi
    @api.depends('difference')
    def _compute_show_adv(self):
        for rec in self:
            rec.show_adv = rec.difference != 0
        return True

    @api.one
    @api.constrains('state')
    def _check_amounts(self):
        if self.state == 'open' and self.box_id.control_efectivo and self.balance_start != sum(self.details_ids.mapped('subtotal_opening')):
            raise ValidationError(u'El total de la composición de la caja debe ser igual al total del saldo inicial!')
        # TODO: C INCIDENCIA
        if self.state == 'end' and self.balance_end < 0:
            raise ValidationError(u'El saldo téorico del cierre no puede ser negativo!')

    @api.model
    def create(self, vals):
        rec = super(models.Model, self).create(vals)
        data = rec._update_balances2()
        rec.write(data)
        return rec

    @api.multi
    def write(self, vals):
        res = super(models.Model, self).write(vals)
        if 'balance_start' not in vals or 'balance_end_real' not in vals:
            data = self._update_balances2()
            res = super(models.Model, self).write(data)
        return res

    @api.multi
    def button_open(self):
        fiscalyear_id = self._get_fiscalyear()
        if fiscalyear_id:
            name = self.env['ir.sequence'].with_context(fiscalyear_id=fiscalyear_id[0].id).next_by_id(
                self.journal_id.sequence_id.id)
        else:
            raise ValidationError(_('No se ha identificado ejercicio fiscal para la fecha actual!'))
        self.write({'state': 'open', 'user_id': self.env.uid, 'name': name})
        for rec in self:
            rec.message_post(body=u"Caja chica %s abierta." % (self.name,))
        return True

    # RAGU
    def check_balance_end_atclose(self):
        self.ensure_one()
        if self.transaction_ids.filtered(lambda x: x.is_custody and x.amount > 0):
            raise ValidationError(_(u"No se puede cerrar una caja con valores en custodia sin entregar!"))
        if self.balance_end < 0:
            raise ValidationError(
                u'No se puede cerrar si el Saldo teórico de cierre tiene valor negativo!')


    @api.multi
    def button_close(self):
        for rec in self:
            rec.check_balance_end_atclose()
        # TODO: C INCIDENCIA
            if rec.difference != 0.0 and rec.balance_end >= 0:
                Concept = self.env['grp_concepto_gasto_cc_viaticos']
                concept = False
                values = {
                    'date': fields.Date.today(),
                    'journal_id': rec.journal_id.id,
                    'amount': rec.difference}
                if rec.difference < 0:
                    concept = Concept.search([('perdida_diferencia', '=', True)], limit=1)
                    values.update({'ref': u'Pérdida por diferencia'})
                if rec.difference > 0:
                    concept = Concept.search([('ganancia_diferencia', '=', True)], limit=1)
                    values.update({'ref': u'Ganancia por diferencia'})
                if not concept:
                    raise ValidationError(
                        u'Debe configurar un concepto pérdida por diferencia y ganancia por diferencia!')
                if not concept.cuenta_id:
                    raise ValidationError(
                        u'Debe configurar la cuenta del concepto de caja chica y viaticos utilizado!')
                values.update({'concept_cc_id': concept.id})
                rec.write({'transaction_ids': [(0, 0, values)]})
            # else:
            #     rec.transaction_ids.write({'concept_cc_id': False})
            rec.write({'state': 'end', 'closing_date': time.strftime('%Y-%m-%d %H:%M:%S')})
            rec.message_post(body=u"Caja chica %s cerrada." % (self.name,))
        return True

    @api.onchange('transaction_ids')
    def onchange_transactions(self):
        if self._context.get('remove_transaction_ids'):
            remove_transaction_ids = self._context.get('remove_transaction_ids')
            remove_transaction = self.env['grp.caja.chica.tesoreria.line'].browse(remove_transaction_ids)
            if self.transaction_ids:
                self.transaction_ids -= remove_transaction

    @api.multi
    @api.depends('transaction_ids', 'move_line_ids', 'transaction_ids.amount')
    def _compute_total_entry_encoding(self):
        for rec in self:
            _in_amount = sum(rec.transaction_ids.filtered(lambda x:x.rounded_amount >= 0).mapped('rounded_amount'),0.0)
            _out_amount = sum(rec.transaction_ids.filtered(lambda x:x.rounded_amount < 0).mapped('rounded_amount'),0.0)
            rec.in_amount = abs(_in_amount)
            rec.out_amount = abs(_out_amount)
            rec.total_entry_encoding = float_round(_in_amount + _out_amount, 0)

    @api.multi
    @api.depends('transaction_ids', 'move_line_ids', 'balance_start', 'transaction_ids.amount')
    def _compute_balance_end(self):
        for rec in self:
            rec.balance_end = rec.balance_start + rec.total_entry_encoding

    def _cancel_moves(self):
        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line']
        period_id = self.env['account.period'].find(fields.Date.today()).id
        journal_accounts = [self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id]

        move_ids = self.env['account.move']
        for move_line_id in self.move_line_ids:
            if move_line_id.move_id.id not in move_ids.ids:
                move_ids += move_line_id.move_id

        lines2rec = AccountMoveLine.browse()
        for move_id in move_ids:
            reversal_move_ids = AccountMove.browse(move_id.create_reversals(fields.Date.today(), reversal_period_id=period_id))
            for move_line_id in move_id.line_id:
                if move_line_id.account_id.id not in journal_accounts:
                    lines2rec += move_line_id
                    lines2rec += reversal_move_ids.line_id.filtered(
                        lambda x: x.account_id.id == move_line_id.account_id.id)
                if move_line_id.reconcile_id:
                    move_line_id.reconcile_id.unlink()
            if lines2rec:
                lines2rec.reconcile('manual')

    @api.multi
    def button_cancel(self):
        for rec in self:
            if rec.state == 'open':
                rec.write({'state':'draft'})
            else:
                caja_chica_line_obj = self.env['grp.caja.chica.tesoreria.line']
                caja_chica_line_ids = caja_chica_line_obj.search([('caja_chica_id', '=', rec.id),
                                                                  ('fondo_rotario', '=', True)])
                if len(caja_chica_line_ids) > 0:
                    raise ValidationError(u'No puede cancelar una Caja Chica de Tesorería incluida en un 3 en 1.')
                previous_box = self._get_next_box(rec.box_id.id, rec.date)
                if previous_box:
                    raise ValidationError(u'No es posible cancelar la caja; existe una caja posterior, cambie el estado de la caja posterior a borrador para poder cancelar!')
                rec.transaction_ids.filtered(lambda
                                                 x: x.is_catch_mov or x.concept_cc_id.ganancia_diferencia or x.concept_cc_id.perdida_diferencia).reverse_move()
                rec._cancel_moves()
                rec.move_line_ids.write({'caja_chica_id': False})
                rec.linea_llp_ids.unlink()
                rec.write({'state': 'open'})
            rec.message_post(body=u"Caja chica %s cancelada." % (rec.name,))
        return True

    @api.multi
    def button_check(self):
        cr = self.env.cr
        for rec in self:
            cr.execute(""" SELECT cctl.amount as importe,
                                  cg.id as concepto_id
                           FROM grp_caja_chica_tesoreria_line cctl
                                inner join grp_caja_chica_tesoreria cct ON (cctl.caja_chica_id=cct.id)
                                inner join grp_concepto_gasto_cc_viaticos cg ON (cctl.concept_cc_id=cg.id)
                           WHERE cg.a_rendir=True and cct.id=%s """, (rec.id,))
            for vals in cr.dictfetchall():
                vals.update({ 'caja_chica_id': rec.id})
                self.env['grp_llave_presupuestal_registro_caja'].create(vals)
            rec.transaction_ids.generate_account_move()
            difference = sum(rec.transaction_ids.mapped('rounded_amount')) - sum(rec.transaction_ids.mapped('amount'))
            if difference != 0:
                mov = self.env['account.move'].create(self._prepare_adjust_account_move_data()[0])
                mov.line_id.write({'caja_chica_id': rec.id})
            rec.write({'state': 'check'})
            rec.message_post(body=u"Caja chica %s revisada." % (rec.name,))
        return True

    @api.one
    def _prepare_adjust_account_move_data(self):
        company = self.env.user.company_id
        period_id = self.env['account.period'].find(self.closing_date).id
        company_currency = self.journal_id.company_id.currency_id.id
        current_currency = self.currency.id
        diff_currency = current_currency and current_currency != company_currency

        difference = sum(self.transaction_ids.mapped('rounded_amount')) - sum(self.transaction_ids.mapped('amount'))

        if difference < 0:
            debit_account_id = self.journal_id.default_debit_account_id.id
            credit_account_id = company.income_rounding_adjust_account_id.id
        elif difference > 0:
            credit_account_id = self.journal_id.default_debit_account_id.id
            debit_account_id = company.expense_rounding_adjust_account_id

        amount_currency = diff_currency and self.currency.rate * abs(difference) or 0.0

        move_line_vals_debit = {
            'name': 'Ajuste por redondeo',
            'ref': '%s/%s' % (self.name, self.sequence_complement),
            'operating_unit_id': self.operating_unit_id.id,
            'account_id': debit_account_id,
            'debit': abs(diff_currency and self.caja_chica_id.currency.rate * difference or difference),
            # 'debit': abs(difference),
            'credit': 0.0,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': amount_currency,
            # 'partner_id': partner_id
        }
        move_line_vals_credit = {
            'operating_unit_id': self.operating_unit_id.id,
            'name': 'Ajuste por redondeo',
            'ref': '%s/%s' % (self.name, self.sequence_complement),
            'account_id': credit_account_id,
            'debit': 0.0,
            'credit': abs(diff_currency and self.caja_chica_id.currency.rate * difference or difference),
            # 'credit': abs(difference),
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': amount_currency,
            # 'partner_id': partner_id
        }
        move_vals = {
            'name': '%s/%s' % (self.name, self.sequence_complement),
            'journal_id': self.journal_id.id,
            'date': self.closing_date,
            'ref': '%s/%s' % (self.name, self.sequence_complement),
            'period_id': period_id,
            'line_id': [(0, 0, move_line_vals_debit), (0, 0, move_line_vals_credit)],
            # 'partner_id': partner_id
        }
        return move_vals

    # RAGU actualizar saldo inicial
    def _get_balance_start(self):
        previous_box = self._get_previous_box(self.box_id.id, self.date, rec_id=self.id)
        start = previous_box.balance_end if previous_box else sum(self.details_ids.mapped('subtotal_opening'))
        return start

    @api.multi
    def action_update_balance_start(self):
        for rec in self:
            rec.balance_start = rec._get_balance_start()

    def _get_opening_details_ids(self):
        details_ids = [(5,)]
        date = time.strftime('%Y-%m-%d %H:%M:%S')
        previous_box = self._get_previous_box(self.box_id.id, date)

        if previous_box:
            for value in previous_box.details_ids:
                nested_values = {
                    'number_closing': 0,
                    'number_opening': value.number_closing,
                    'pieces': value.pieces
                }
                details_ids.append([0, False, nested_values])
        else:
            box_id = self.env['grp.caja'].search([('id','=',self.box_id.id)])
            for value in box_id.cashbox_line_ids:
                nested_values = {
                    'number_closing': 0,
                    'number_opening': 0,
                    'pieces': value.pieces
                }
                details_ids.append([0, False, nested_values])
        return details_ids

    @api.multi
    def _update_balances2(self):
        data = {}
        for rec in self:
            if not rec.box_id.control_efectivo:
                prec = self.env['decimal.precision'].precision_get('Account')
                if float_compare(rec.balance_end_real, rec.balance_end, precision_digits=prec):
                    rec.write({'balance_end_real': rec.balance_end})
            previous_box = self._get_previous_box(rec.box_id.id, rec.date, rec_id=rec.id)
            start = previous_box and previous_box.balance_end or sum(rec.details_ids.mapped('subtotal_opening'))
            end = sum(rec.details_ids.mapped('subtotal_closing'))
            data.update({
                'balance_start': start,
                'balance_end_real': end,
            })
        return data

    @api.multi
    def _update_balances(self):
        return True

    def _get_previous_box(self, box_id, date, state=['check','end'], op='in', rec_id=False):
        return self.search([('id', '!=', rec_id), ('state', op, state), ('box_id', '=', box_id),
                                    ('date', '<', date)], order='date desc', limit=1)

    def _get_next_box(self, box_id, date, state='draft'):
        return self.search([('state', '!=', state), ('box_id', '=', box_id),
                                    ('date', '>', date)], order='date asc', limit=1)

    def _get_fiscalyear(self):
        fecha_hoy = time.strftime('%Y-%m-%d')
        uid_company_id = self.env['res.users'].browse(self._uid).company_id.id
        fiscalyear_id = self.env['account.fiscalyear'].search(
            [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
             ('company_id', '=', uid_company_id)])
        return fiscalyear_id


class GrpCajaChicaTesoreriaLine(models.Model):
    _name = 'grp.caja.chica.tesoreria.line'

    caja_chica_id = fields.Many2one('grp.caja.chica.tesoreria', 'Caja chica', ondelete='cascade')
    account_move_id = fields.Many2one('account.move', "Asiento contable")
    journal_id = fields.Many2one('account.journal', "Diario")

    voucher_id = fields.Many2one('account.voucher', "Comprobante de pago")
    custody_id = fields.Many2one('grp.valores_custodia', "Valor en custodia")
    catch_mov_id = fields.Many2one('grp.caja.chica.movimiento.efectivo', "Movimiento en efectivo")
    concept_cc_id = fields.Many2one('grp_concepto_gasto_cc_viaticos', "Concepto")

    is_difference = fields.Boolean('Transaccion con la diferencia?', compute='_compute_origin', multi='origin')
    is_voucher = fields.Boolean('Es comprobante de pago?', compute='_compute_origin', multi='origin')
    is_catch_mov = fields.Boolean('Es movimiento en efectivo?', compute='_compute_origin', multi='origin')
    is_custody = fields.Boolean('Es valor en custodia?', compute='_compute_origin', multi='origin')
    show_cancel = fields.Boolean('Mostrar cancelar?', compute='_compute_show_cancel')
    line_served = fields.Boolean('Entregada')
    state_caja = fields.Selection([('draft', 'Nuevo'),
                                   ('open', u'Abierto/a'),
                                   ('end', 'Cerrado'),
                                   ('check', 'Revisado'),
                                   ], u'Estado', related='caja_chica_id.state', readonly=True)

    ref = fields.Char('Concepto')
    date = fields.Date(string='Fecha de pago')
    entry_date = fields.Date(string='Fecha de asiento')
    partner_id = fields.Many2one('res.partner', string=u'Empresa')
    amount = fields.Float(string='Importe')
    rounded_amount = fields.Float(string='Importe redondeado', compute='_compute_rounded_amount', store=True)
    state = fields.Char(string='Estado', compute='_compute_fields')

    @api.multi
    @api.depends('voucher_id', 'custody_id', 'catch_mov_id', 'concept_cc_id')
    def _compute_origin(self):
        for rec in self:
            rec.is_voucher = rec.voucher_id.id is not False
            rec.is_catch_mov = rec.catch_mov_id.id is not False
            rec.is_custody = rec.custody_id.id is not False
            rec.is_difference = rec.concept_cc_id.id is not False

    @api.multi
    @api.depends('account_move_id','caja_chica_id.state')
    def _compute_show_cancel(self):
        for rec in self:
            rec.show_cancel = rec.account_move_id and not rec.account_move_id.reversal_id and rec.caja_chica_id.state == 'end' and not rec.catch_mov_id

    @api.multi
    @api.depends('voucher_id', 'custody_id', 'voucher_id.state', 'custody_id.state')
    def _compute_fields(self):
        for rec in self:
            if rec.is_custody:
                rec.state = _get_state(CUSTODY_STATE, rec.custody_id.state)
            elif rec.is_voucher:
                rec.state = _get_state(VOUCHER_STATE, rec.voucher_id.state)
            else:
                rec.state = ''

    @api.multi
    @api.depends('voucher_id', 'amount')
    def _compute_rounded_amount(self):
        for rec in self:
            rec.rounded_amount = float_round(rec.amount, 0)

    @api.multi
    def edit_transaction(self):
        mod_obj = self.env['ir.model.data']
        for rec in self:
            if rec.is_catch_mov:
                res = mod_obj.get_object_reference('grp_tesoreria', 'view_grp_caja_chica_mov_efectivo_form')
                return {
                    'name': 'Movimiento en efectivo',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_id': [res and res[1] or False],
                    'view_mode': 'form',
                    'res_model': 'grp.caja.chica.movimiento.efectivo',
                    'res_id': rec.catch_mov_id.id,
                    'target': 'new',
                    'nodestroy': True,
                    'context': "{}",
                }
            mod_obj.get_object_reference('grp_tesoreria', 'view_grp_caja_chica_line_form')
            return {
                'name': 'Valor en custodia',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_id': False,
                'view_mode': 'form',
                'res_model': 'grp.caja.chica.tesoreria.line',
                'res_id': rec.id,
                'target': 'new',
                'nodestroy': True,
                'context': "{'custody': True}",
            }

    @api.multi
    def edit_line(self):
        for rec in self:
            if rec.is_custody:
                mov_values = rec._prepare_account_move_data()
                mov = self.env['account.move'].create(mov_values[0])
                rec.write({'account_move_id': mov.id, 'amount': - abs(rec.amount), 'line_served': True})
                rec.caja_chica_id.write({'sequence_complement': rec.caja_chica_id.sequence_complement + 1})
                rec.custody_id.write({'state': 'entrega_tesoreria', 'asiento_baja': mov.id,
                                      'diario_baja': rec.journal_id.id, 'fecha_baja': rec.date})
        return True

    @api.multi
    def btn_cancel(self):
        self.reverse_move()
        for rec in self:
            if rec.is_custody:
                rec.write({'amount': rec.amount * -1})
        return

    @api.multi
    def reverse_move(self):
        for rec in self:
            move = rec.account_move_id
            if move:
                period = self.env['account.period'].find(fields.Date.today())
                if rec.is_voucher:
                    if rec.voucher_id.rendicion_viaticos_id:
                        rec.voucher_id.write({'in_cashbox':False,'state':'posted'})
                        rec.voucher_id.rendicion_viaticos_id.write({'state':'autorizado'})
                    else:
                        rec.voucher_id.cancel_voucher()
                        rec.voucher_id.proforma_voucher()
                        for line in rec.voucher_id.line_dr_ids:
                            if line.origin_voucher_id:
                                line.origin_voucher_id.write({'state': 'posted', 'in_cashbox': False})
                                line.origin_voucher_id.solicitud_viatico_id.write({'adelanto_pagado': False})
                        rec.voucher_id.write({'state': 'posted','in_cashbox':False})
                        if rec.voucher_id.rendicion_anticipos_id:
                            rec.voucher_id.rendicion_anticipos_id.write({'state': 'autorizado'})
                else:
                    move.create_reversals(fields.Date.today(), reversal_period_id=period.id if period else False)
                    move.line_id.write({'caja_chica_id': False})
                    if rec.is_custody:
                        rec.custody_id.write({'fecha_baja': False, 'diario_baja': False, 'asiento_baja': False,
                                              'state': 'entrega_autorizada'})
        self.write({'account_move_id': False})

    @api.multi
    def generate_account_move(self):
        for rec in self:
            if rec.is_custody and (not rec.date or not rec.journal_id):
                raise ValidationError(
                    u'Existes transacciones de tipo valor en custodia sin configurar la fecha y el diario!')
            mov = rec.account_move_id
            if (not rec.is_voucher and not rec.is_custody) or rec.voucher_id.rendicion_viaticos_id or rec.voucher_id.rendicion_anticipos_id:
                mov_values = rec._prepare_account_move_data()
                mov = self.env['account.move'].create(mov_values[0])
                rec.write({'account_move_id': mov.id})
                rec.caja_chica_id.write({'sequence_complement': rec.caja_chica_id.sequence_complement + 1})
                try:
                    _writeoff_acc_id = mov_values[0]['line_id'][0][2]['account_id'] or False
                except ImportError:
                    _writeoff_acc_id = False
                    pass
                if rec.voucher_id.rendicion_viaticos_id or rec.voucher_id.rendicion_anticipos_id:
                    lines2rec = rec.voucher_id.move_ids.filtered(lambda x:x.account_id == rec.voucher_id.account_id) + mov.line_id.filtered(lambda x:x.account_id == rec.voucher_id.account_id)
                    # lines2rec.reconcile('manual')
                    lines2rec.reconcile('manual',
                                        writeoff_acc_id=_writeoff_acc_id,
                                        writeoff_journal_id=rec.caja_chica_id.journal_id.id,
                                        writeoff_period_id=self.env['account.period'].find(fields.Date.today()).id)

            if mov:
                mov.line_id.write({'caja_chica_id': rec.caja_chica_id.id})

    @api.one
    def _prepare_account_move_data(self):
        period_id = self.env['account.period'].find(self.date).id
        company_currency = self.caja_chica_id.journal_id.company_id.currency_id.id
        current_currency = self.caja_chica_id.currency.id
        diff_currency = current_currency != company_currency and current_currency

        if self.is_custody:
            debit_account_id = self.journal_id.default_debit_account_id.id
            credit_account_id = self.caja_chica_id.journal_id.default_credit_account_id.id
            partner_id = False
        elif self.voucher_id.rendicion_viaticos_id or self.voucher_id.rendicion_anticipos_id:
            debit_account_id = self.caja_chica_id.journal_id.default_debit_account_id.id
            credit_account_id = self.voucher_id.account_id.id
            partner_id = self.voucher_id.partner_id.id
        else:
            partner_id = False
            if self.amount > 0:
                debit_account_id = self.caja_chica_id.journal_id.default_debit_account_id.id
                credit_account_id = self.concept_cc_id.cuenta_id.id
            else:
                credit_account_id = self.caja_chica_id.journal_id.default_debit_account_id.id
                debit_account_id = self.concept_cc_id.cuenta_id.id

        if not credit_account_id or not debit_account_id:
            raise ValidationError(u'No se han podido identificar las cuentas para la información contable!')

        sequence = self.caja_chica_id.sequence_complement

        amount = abs(self.rounded_amount)
        move_line_vals_debit = {
            'name': self.ref,
            'ref': '%s/%s' % (self.caja_chica_id.name, sequence),
            'operating_unit_id': self.caja_chica_id.operating_unit_id.id,
            'account_id': debit_account_id,
            'debit': diff_currency and amount or self.caja_chica_id.currency.rate * amount,
            'credit': 0.0,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': diff_currency and amount or 0.0,
            'partner_id': partner_id
        }
        move_line_vals_credit = {
            'operating_unit_id': self.caja_chica_id.operating_unit_id.id,
            'name': self.ref,
            'ref': '%s/%s' % (self.caja_chica_id.name, sequence),
            'account_id': credit_account_id,
            'debit': 0.0,
            'credit': diff_currency and amount or self.caja_chica_id.currency.rate * amount,
            'currency_id': diff_currency and current_currency or False,
            'amount_currency': diff_currency and - amount or 0.0,
            'partner_id': partner_id
        }
        move_vals = {
            'name': '%s/%s' % (self.caja_chica_id.name, sequence),
            'journal_id': self.caja_chica_id.journal_id.id,
            'date': self.entry_date or self.date,
            'ref': '%s/%s' % (self.caja_chica_id.name, sequence),
            'period_id': period_id,
            'line_id': [(0, 0, move_line_vals_debit), (0, 0, move_line_vals_credit)],
            'partner_id': partner_id
        }
        return move_vals

    @api.multi
    def unlink(self):
        self.reverse_move()  #RAGU removiendo transacciones al eliminar linea
        return super(GrpCajaChicaTesoreriaLine, self).unlink()


class GrpAccountCashboxLine(models.Model):
    _inherit = 'account.cashbox.line'

    caja_chica_id = fields.Many2one('grp.caja.chica.tesoreria', 'Caja chica', copy=False)


class GrpAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    caja_chica_id = fields.Many2one('grp.caja.chica.tesoreria', 'Caja chica', copy=False)
