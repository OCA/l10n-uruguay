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
import openerp.addons.decimal_precision as dp
import logging
from openerp import netsvc
from openerp.tools import float_compare
import openerp
import time
from datetime import datetime

_logger = logging.getLogger(__name__)


# TODO: C SPRING 12 GAP 301


class GrpValeCaja(models.Model):
    _inherit = 'account.voucher'
    _name = 'grp.vale.caja'
    _description = 'Vale de caja'

    # RAGU redefiniendo comportamiento del journal, sacando Desconocido
    @api.model
    def _default_journal_id(self):
        return self.env['account.journal'].search([('type','=','purchase'),'|',('currency','=',self.env.user.company_id.currency_id.id),('currency','=',False)], limit=1).id or self.env['account.journal']

    # TODO L VARIANZA GRP
    @api.model
    def default_get(self, fields):
        res = super(GrpValeCaja, self).default_get(fields)
        res['partner_id'] = self.env.user.partner_id.id
        return res

    journal_id = fields.Many2one('account.journal', string=u'Diario', required=True, default=lambda self: self._default_journal_id())

    fecha_inicio_pago = fields.Date(string=u'Fecha inicio pago', required=False)
    solicitud_viatico_id = fields.Many2one('grp.solicitud.viaticos', string=u'Solicitud de viajes',
                                           domain=[('lleva_adelanto', '=', True), ('state', '=', 'autorizado')],
                                           ondelete='restrict', required=False, readonly=True,
                                           states={'draft': [('readonly', False)]})
    fecha_aprobacion_pago = fields.Date(string=u'Fecha de aprobación de pago',
                                        related='aprobacion_pago_id.fecha_aprobacion', store=True, readonly=True)
    state = fields.Selection([('draft', 'Borrador'),
                              ('posted', 'Contabilizado'),
                              ('cancel', 'Cancelado'),
                              ('pagado', 'Pagado')], string="Estado", track_visibility='onchange', copy=False)
    aprobacion_pago_id = fields.Many2one('account.invoice', u"Aprobación de pago")
    account_voucher_id = fields.Many2one('account.voucher', u"Formulario de pago",
                                         related='aprobacion_pago_id.account_voucher_id', readonly=True)
    cuenta_bancaria_id = fields.Many2one('account.journal', 'Cuenta bancaria',
                                         related='aprobacion_pago_id.cuenta_bancaria_id', readonly=True)
    payment_ids = fields.Many2many('account.move.line', u"Pagos", related='aprobacion_pago_id.payment_ids', readonly=True)
    payment_ret_ids = fields.Many2many('account.move.line', string='Retenciones',
                                       related='aprobacion_pago_id.payment_ret_ids', readonly=True)
    invoice_ret_lines = fields.Boolean(string='Retenciones', related='aprobacion_pago_id.invoice_ret_lines', readonly=True)
    line_ids = fields.One2many('grp.vale.caja.line', 'vale_id', 'Vale lineas',
                               readonly=True, copy=True,
                               states={'draft': [('readonly', False)]})

    line_cr_ids = fields.One2many('grp.vale.caja.line', 'vale_id', 'Credits',
                                  domain=[('type', '=', 'cr')], context={'default_type': 'cr'}, readonly=True,
                                  states={'draft': [('readonly', False)]})

    line_dr_ids = fields.One2many('grp.vale.caja.line', 'vale_id', 'Debits',
                                  domain=[('type', '=', 'dr')], context={'default_type': 'dr'}, readonly=True,
                                  states={'draft': [('readonly', False)]})

    @api.multi
    def cancel_voucher(self):
        for rec in self:
            if rec.fecha_aprobacion_pago:
                raise exceptions.ValidationError(_("Este documento ya fue aprobado para su pago. Cancele "
                                                   "la aprobación del pago si desea cancelar la factura."))
        return self.write({'state': 'cancel'})

    @api.multi
    def proforma_vale(self):
        self.generate_aprobacion_pago()
        return self.write({'state': 'posted'})

    @api.multi
    def generate_aprobacion_pago(self):
        tipo_ejecucion = self.env['tipo.ejecucion.siif'].search([('codigo', '=', 'P')])
        for rec in self:
            invoice = self.env['account.invoice'].create({
                'partner_id': rec.partner_id.id,
                'date_invoice': rec.date,
                'number': rec.number,
                'currency_id': rec.currency_id.id,
                'amount_total': rec.amount,
                'siif_tipo_ejecucion': tipo_ejecucion and tipo_ejecucion.id or False,
                'type': 'in_invoice',
                'journal_id': rec.journal_id.id,
                'account_id': rec.account_id.id,
                'operating_unit_id': rec.operating_unit_id.id or False,
                'internal_number': rec.number,
                'doc_type': 'vales_caja',
                'invoice_line': [
                    (0, 0, {'name': line.name or '', 'account_id': line.account_id.id, 'price_unit': line.amount}) for
                    line in
                    rec.line_dr_ids]

            })
            # TODO: Revisar, esta creando 2 veces el asiento: al crear la factura y al aprobar el pago
            wf_service = netsvc.LocalService('workflow')
            wf_service.trg_validate(rec._uid, 'account.invoice', invoice.id, 'invoice_open', rec._cr)
            #MVARELA: al vale se le asocia el asiento de la factura y no se crea uno nuevo
            # rec.write({'aprobacion_pago_id': invoice.id})
            rec.write({'aprobacion_pago_id': invoice.id, 'move_id':invoice.move_id.id})


    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
        if not journal_id:
            return {}
        if context is None:
            context = {}
        # TODO: comment me and use me directly in the sales/purchases views
        res = self.basic_onchange_partner(cr, uid, ids, partner_id, journal_id, ttype, context=context)
        if ttype in ['sale', 'purchase']:
            return res
        ctx = context.copy()
        # not passing the payment_rate currency and the payment_rate in the context but it's ok because they are reset in recompute_payment_rate
        ctx.update({'date': date})
        return res

    def _get_company_currency(self, cr, uid, voucher_id, context=None):
        return self.pool.get('grp.vale.caja').browse(cr, uid, voucher_id, context).journal_id.company_id.currency_id.id

    def _sel_context(self, cr, uid, voucher_id, context=None):
        company_currency = self._get_company_currency(cr, uid, voucher_id, context)
        current_currency = self._get_current_currency(cr, uid, voucher_id, context)
        if current_currency != company_currency:
            context_multi_currency = context.copy()
            voucher = self.pool.get('grp.vale.caja').browse(cr, uid, voucher_id, context)
            context_multi_currency.update({'date': voucher.date})
            return context_multi_currency
        return context

    def account_move_get(self, cr, uid, voucher_id, context=None):
        seq_obj = self.pool.get('ir.sequence')
        voucher = self.pool.get('grp.vale.caja').browse(cr,uid,voucher_id,context)
        if voucher.number:
            name = voucher.number
        elif voucher.journal_id.sequence_id:
            if not voucher.journal_id.sequence_id.active:
                raise exceptions.ValidationError(_('Please activate the sequence of selected journal !'))
            c = dict(context)
            c.update({'fiscalyear_id': voucher.period_id.fiscalyear_id.id})
            name = seq_obj.next_by_id(cr, uid, voucher.journal_id.sequence_id.id, context=c)
        else:
            raise exceptions.ValidationError(_('Please define a sequence on the journal.!'))
        if not voucher.reference:
            ref = name.replace('/','')
        else:
            ref = voucher.reference

        move = {
            'name': name,
            'journal_id': voucher.journal_id.id,
            'narration': voucher.narration,
            'date': voucher.date,
            'ref': ref,
            'period_id': voucher.period_id.id,
            'operating_unit_id': voucher.operating_unit_id and voucher.operating_unit_id.id or False,
        }
        return move

    def first_move_line_get(self, cr, uid, voucher_id, move_id, company_currency, current_currency, context=None):
        voucher = self.pool.get('grp.vale.caja').browse(cr,uid,voucher_id,context)
        debit = credit = 0.0
        # TODO: is there any other alternative then the voucher type ??
        # ANSWER: We can have payment and receipt "In Advance".
        # TODO: Make this logic available.
        # -for sale, purchase we have but for the payment and receipt we do not have as based on the bank/cash journal we can not know its payment or receipt
        if voucher.type in ('purchase', 'payment'):
            credit = voucher.paid_amount_in_company_currency
        elif voucher.type in ('sale', 'receipt'):
            debit = voucher.paid_amount_in_company_currency
        if debit < 0: credit = -debit; debit = 0.0
        if credit < 0: debit = -credit; credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        #set the first line of the voucher
        move_line = {
                'name': voucher.name or '/',
                'debit': debit,
                'credit': credit,
                'account_id': voucher.account_id.id,
                'move_id': move_id,
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'partner_id': voucher.partner_id.id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': (sign * abs(voucher.amount) # amount < 0 for refunds
                    if company_currency != current_currency else 0.0),
                'date': voucher.date,
                'date_maturity': voucher.date_due
            }
        return move_line

    def _convert_amount(self, cr, uid, amount, voucher_id, context=None):
        if context is None:
            context = {}
        currency_obj = self.pool.get('res.currency')
        voucher = self.browse(cr, uid, voucher_id, context=context)
        return currency_obj.compute(cr, uid, voucher.currency_id.id, voucher.company_id.currency_id.id, amount, context=context)

    def _get_exchange_lines(self, cr, uid, line, move_id, amount_residual, company_currency, current_currency, context=None):
        if amount_residual > 0:
            account_id = line.voucher_id.company_id.expense_currency_exchange_account_id
            if not account_id:
                model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'account', 'action_account_form')
                msg = _("You should configure the 'Loss Exchange Rate Account' to manage automatically the booking of accounting entries related to differences between exchange rates.")
                raise openerp.exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
        else:
            account_id = line.voucher_id.company_id.income_currency_exchange_account_id
            if not account_id:
                model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'account', 'action_account_form')
                msg = _("You should configure the 'Gain Exchange Rate Account' to manage automatically the booking of accounting entries related to differences between exchange rates.")
                raise openerp.exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
        # Even if the amount_currency is never filled, we need to pass the foreign currency because otherwise
        # the receivable/payable account may have a secondary currency, which render this field mandatory
        if line.account_id.currency_id:
            account_currency_id = line.account_id.currency_id.id
        else:
            account_currency_id = company_currency != current_currency and current_currency or False
        move_line = {
            'journal_id': line.voucher_id.journal_id.id,
            'period_id': line.voucher_id.period_id.id,
            'name': _('change')+': '+(line.name or '/'),
            'account_id': line.account_id.id,
            'move_id': move_id,
            'partner_id': line.voucher_id.partner_id.id,
            'currency_id': account_currency_id,
            'amount_currency': 0.0,
            'quantity': 1,
            'credit': amount_residual > 0 and amount_residual or 0.0,
            'debit': amount_residual < 0 and -amount_residual or 0.0,
            'date': line.voucher_id.date,
        }
        move_line_counterpart = {
            'journal_id': line.voucher_id.journal_id.id,
            'period_id': line.voucher_id.period_id.id,
            'name': _('change')+': '+(line.name or '/'),
            'account_id': account_id.id,
            'move_id': move_id,
            'amount_currency': 0.0,
            'partner_id': line.voucher_id.partner_id.id,
            'currency_id': account_currency_id,
            'quantity': 1,
            'debit': amount_residual > 0 and amount_residual or 0.0,
            'credit': amount_residual < 0 and -amount_residual or 0.0,
            'date': line.voucher_id.date,
        }
        return (move_line, move_line_counterpart)

    def voucher_move_line_create(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency, context=None):
        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        tot_line = line_total
        rec_lst_ids = []

        date = self.read(cr, uid, [voucher_id], ['date'], context=context)[0]['date']
        ctx = context.copy()
        ctx.update({'date': date})
        voucher = self.pool.get('grp.vale.caja').browse(cr, uid, voucher_id, context=ctx)
        voucher_currency = voucher.journal_id.currency or voucher.company_id.currency_id
        ctx.update({
            'voucher_special_currency_rate': voucher_currency.rate * voucher.payment_rate ,
            'voucher_special_currency': voucher.payment_rate_currency_id and voucher.payment_rate_currency_id.id or False,})
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        for line in voucher.line_ids:
            #create one move line per voucher line where amount is not 0.0
            # AND (second part of the clause) only if the original move line was not having debit = credit = 0 (which is a legal value)
            if not line.amount and not (line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit, precision_digits=prec) and not float_compare(line.move_line_id.debit, 0.0, precision_digits=prec)):
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_curreny.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            amount = self._convert_amount(cr, uid, line.untax_amount or line.amount, voucher.id, context=ctx)
            # if the amount encoded in voucher is equal to the amount unreconciled, we need to compute the
            # currency rate difference
            if line.amount == line.amount_unreconciled:
                if not line.move_line_id:
                    raise exceptions.ValidationError(_('The invoice you are willing to pay is not valid anymore.'))
                sign = line.type == 'dr' and -1 or 1
                currency_rate_difference = sign * (line.move_line_id.amount_residual - amount)
            else:
                currency_rate_difference = 0.0
            move_line = {
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'currency_id': line.move_line_id and (company_currency != line.move_line_id.currency_id.id and line.move_line_id.currency_id.id) or False,
                'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': voucher.date
            }
            if amount < 0:
                amount = -amount
                if line.type == 'dr':
                    line.type = 'cr'
                else:
                    line.type = 'dr'

            if (line.type=='dr'):
                tot_line += amount
                move_line['debit'] = amount
            else:
                tot_line -= amount
                move_line['credit'] = amount

            if voucher.tax_id and voucher.type in ('sale', 'purchase'):
                move_line.update({
                    'account_tax_id': voucher.tax_id.id,
                })

            # compute the amount in foreign currency
            foreign_currency_diff = 0.0
            amount_currency = False
            if line.move_line_id:
                # We want to set it on the account move line as soon as the original line had a foreign currency
                if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency:
                    # we compute the amount in that foreign currency.
                    if line.move_line_id.currency_id.id == current_currency:
                        # if the voucher and the voucher line share the same currency, there is no computation to do
                        sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                        amount_currency = sign * (line.amount)
                    else:
                        # if the rate is specified on the voucher, it will be used thanks to the special keys in the context
                        # otherwise we use the rates of the system
                        amount_currency = currency_obj.compute(cr, uid, company_currency, line.move_line_id.currency_id.id, move_line['debit']-move_line['credit'], context=ctx)
                if line.amount == line.amount_unreconciled:
                    foreign_currency_diff = line.move_line_id.amount_residual_currency - abs(amount_currency)

            move_line['amount_currency'] = amount_currency
            voucher_line = move_line_obj.create(cr, uid, move_line)
            rec_ids = [voucher_line, line.move_line_id.id]

            if not currency_obj.is_zero(cr, uid, voucher.company_id.currency_id, currency_rate_difference):
                # Change difference entry in company currency
                exch_lines = self._get_exchange_lines(cr, uid, line, move_id, currency_rate_difference, company_currency, current_currency, context=context)
                new_id = move_line_obj.create(cr, uid, exch_lines[0],context)
                move_line_obj.create(cr, uid, exch_lines[1], context)
                rec_ids.append(new_id)

            if line.move_line_id and line.move_line_id.currency_id and not currency_obj.is_zero(cr, uid, line.move_line_id.currency_id, foreign_currency_diff):
                # Change difference entry in voucher currency
                move_line_foreign_currency = {
                    'journal_id': line.voucher_id.journal_id.id,
                    'period_id': line.voucher_id.period_id.id,
                    'name': _('change')+': '+(line.name or '/'),
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': line.voucher_id.partner_id.id,
                    'currency_id': line.move_line_id.currency_id.id,
                    'amount_currency': (-1 if line.type == 'cr' else 1) * foreign_currency_diff,
                    'quantity': 1,
                    'credit': 0.0,
                    'debit': 0.0,
                    'date': line.voucher_id.date,
                }
                new_id = move_line_obj.create(cr, uid, move_line_foreign_currency, context=context)
                rec_ids.append(new_id)
            if line.move_line_id.id:
                rec_lst_ids.append(rec_ids)
        return (tot_line, rec_lst_ids)

    def action_move_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        for voucher in self.browse(cr, uid, ids, context=context):
            context = dict(context, voucher=voucher)
            local_context = dict(context, force_company=voucher.journal_id.company_id.id)
            if voucher.move_id:
                continue
            company_currency = self._get_company_currency(cr, uid, voucher.id, context)
            current_currency = self._get_current_currency(cr, uid, voucher.id, context)
            # we select the context to use accordingly if it's a multicurrency case or not
            context = self._sel_context(cr, uid, voucher.id, context)
            # But for the operations made by _convert_amount, we always need to give the date in the context
            ctx = context.copy()
            ctx.update({'date': voucher.date})
            # Create the account move record.
            move_id = move_pool.create(cr, uid, self.account_move_get(cr, uid, voucher.id, context=context),
                                       context=context)
            # Get the name of the account_move just created
            name = move_pool.browse(cr, uid, move_id, context=context).name
            # Create the first line of the voucher
            move_line_id = move_line_pool.create(cr, uid,
                                                 self.first_move_line_get(cr, uid, voucher.id, move_id,
                                                                          company_currency,
                                                                          current_currency, local_context),
                                                 local_context)
            move_line_brw = move_line_pool.browse(cr, uid, move_line_id, context=context)
            line_total = move_line_brw.debit - move_line_brw.credit
            rec_list_ids = []
            if voucher.type == 'sale':
                line_total = line_total - self._convert_amount(cr, uid, voucher.tax_amount, voucher.id, context=ctx)
            elif voucher.type == 'purchase':
                line_total = line_total + self._convert_amount(cr, uid, voucher.tax_amount, voucher.id, context=ctx)
            # Create one move line per voucher line where amount is not 0.0
            line_total, rec_list_ids = self.voucher_move_line_create(cr, uid, voucher.id, line_total, move_id,
                                                                     company_currency, current_currency, context)

            # Create the writeoff line if needed
            ml_writeoff = self.writeoff_move_line_get(cr, uid, voucher.id, line_total, move_id, name, company_currency,
                                                      current_currency, local_context)
            if ml_writeoff:
                move_line_pool.create(cr, uid, ml_writeoff, local_context)
            # We post the voucher.
            self.write(cr, uid, [voucher.id], {
                'move_id': move_id,
                'state': 'posted',
                'number': name,
            })
            if voucher.journal_id.entry_posted:
                move_pool.post(cr, uid, [move_id], context={})
            # We automatically reconcile the account move lines.
            reconcile = False
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    reconcile = move_line_pool.reconcile_partial(cr, uid, rec_ids,
                                                                 context=context,
                                                                 writeoff_acc_id=voucher.writeoff_acc_id.id,
                                                                 writeoff_period_id=voucher.period_id.id,
                                                                 writeoff_journal_id=voucher.journal_id.id)
        return True

    def writeoff_move_line_get(self, cr, uid, voucher_id, line_total, move_id, name, company_currency, current_currency,
                               context=None):
        currency_obj = self.pool.get('res.currency')
        move_line = {}

        voucher = self.pool.get('grp.vale.caja').browse(cr, uid, voucher_id, context)
        current_currency_obj = voucher.currency_id or voucher.journal_id.company_id.currency_id

        if not currency_obj.is_zero(cr, uid, current_currency_obj, line_total):
            diff = line_total
            account_id = False
            write_off_name = ''
            if voucher.payment_option == 'with_writeoff':
                account_id = voucher.writeoff_acc_id.id
                write_off_name = voucher.comment
            elif voucher.partner_id:
                if voucher.type in ('sale', 'receipt'):
                    account_id = voucher.partner_id.property_account_receivable.id
                else:
                    account_id = voucher.partner_id.property_account_payable.id
            else:
                # fallback on account of voucher
                account_id = voucher.account_id.id
            sign = voucher.type == 'payment' and -1 or 1
            move_line = {
                'name': write_off_name or name,
                'account_id': account_id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'date': voucher.date,
                'credit': diff > 0 and diff or 0.0,
                'debit': diff < 0 and -diff or 0.0,
                'amount_currency': company_currency != current_currency and (sign * -1 * voucher.writeoff_amount) or 0.0,
                'currency_id': company_currency != current_currency and current_currency or False,
                'analytic_account_id': voucher.analytic_id and voucher.analytic_id.id or False,
            }

        return move_line

    #TODO: Revisar, esta creando 2 veces el asiento
    def proforma_voucher(self, cr, uid, ids, context=None):
        self.action_move_line_create(cr, uid, ids, context=context)
        return True

    def get_topay_amount(self):
        self.ensure_one()
        debit = credit = 0
        for line in self.line_dr_ids:
            debit += line.amount
        for line in self.line_cr_ids:
            credit += line.amount
        currency_id = self.currency_id or self.company_id.currency_id
        return currency_id.round(debit - credit)

    def action_topay_amount(self, cr, uid, ids, context=None):
        for rec in self.browse(cr,uid,ids,context):
            rec.amount = rec.get_topay_amount()


class GrpValeCajaLine(models.Model):
    _name = 'grp.vale.caja.line'

    account_id = fields.Many2one('account.account', 'Cuenta')
    dimension_id = fields.Many2one('account.analytic.plan.instance', "Dimensiones")
    vale_id = fields.Many2one('grp.vale.caja', "Vale de caja")
    name = fields.Char('Descripción')
    partner_id = fields.Many2one('res.partner', string='Partner', related='vale_id.partner_id', readonly=True)
    untax_amount = fields.Float('Untax Amount')
    amount = fields.Float('Monto', digits_compute=dp.get_precision('Account'))
    reconcile = fields.Boolean('Full Reconcile')
    type = fields.Selection([('dr', 'Debit'), ('cr', 'Credit')], 'Dr/Cr')
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    move_line_id = fields.Many2one('account.move.line', 'Journal Item', copy=False)
    date_original = fields.Date(string='Date', readonly=1, related='move_line_id.date')
    date_due = fields.Date(string='Due Date', readonly=1, related='move_line_id.date_maturity')
    amount_original = fields.Float(compute='_compute_balance', multi='dc', type='float', string='Original Amount',
                                   store=True,
                                   digits_compute=dp.get_precision('Account'))
    amount_unreconciled = fields.Float(compute='_compute_balance', multi='dc', type='float', string='Open Balance',
                                       store=True, digits_compute=dp.get_precision('Account'))
    company_id = fields.Many2one('res.company', related='vale_id.company_id', string='Company', store=True,
                                 readonly=True)
    currency_id = fields.Many2one('res.currency', compute='_currency_id', string='Currency')
    state = fields.Selection([('draft', 'Borrador'),
                              ('posted', 'Contabilizado'),
                              ('cancel', 'Cancelado'),
                              ('pagado', 'Pagado')], string='State', readonly=True, related='vale_id.state')

    # RAGU concepto en las lineas
    concept_id = fields.Many2one('grp_concepto_gasto_cc_viaticos', u'Concepto',
                                 domain="[('viaticos','=', True)]")

    @api.onchange('concept_id')
    def _onchange_concept_id(self):
        if self.concept_id and self.concept_id.cuenta_id:
            _account_id = self.concept_id.cuenta_id.id
        else:
            context_journal = self.env.context.get('journal_id')
            if context_journal:
                _account_id = self.env['account.journal'].search([('id','=',context_journal)]).default_debit_account_id.id
            else:
                _account_id = False
        self.account_id = _account_id

    @api.multi
    def _compute_balance(self):
        currency_pool = self.pool.get('res.currency')
        for rec in self:
            ctx = self._context.copy()
            ctx.update({'date': rec.vale_id.date})
            voucher_rate = self.env['res.currency'].read(rec.vale_id.currency_id.id, ['rate'], context=ctx)['rate']
            ctx.update({
                'voucher_special_currency': rec.vale_id.payment_rate_currency_id and rec.vale_id.payment_rate_currency_id.id or False,
                'voucher_special_currency_rate': rec.vale_id.payment_rate * voucher_rate})
            res = {}
            company_currency = rec.vale_id.journal_id.company_id.currency_id.id
            voucher_currency = rec.vale_id.currency_id and rec.vale_id.currency_id.id or company_currency
            move_line = rec.move_line_id or False
            if not move_line:
                rec.amount_original = 0.0
                rec.amount_unreconciled = 0.0
            elif move_line.currency_id and voucher_currency == move_line.currency_id.id:
                rec.amount_original = abs(move_line.amount_currency)
                rec.amount_unreconciled = abs(move_line.amount_residual_currency)
            else:
                # always use the amount booked in the company currency as the basis of the conversion into the voucher currency
                rec.amount_original = currency_pool.compute(company_currency, voucher_currency,
                                                            move_line.credit or move_line.debit or 0.0, context=ctx)
                rec.amount_unreconciled = currency_pool.compute(company_currency, voucher_currency,
                                                                abs(move_line.amount_residual), context=ctx)

    @api.multi
    def _currency_id(self):
        for rec in self:
            move_line = rec.move_line_id
            if move_line:
                rec.currency_id = move_line.currency_id and move_line.currency_id.id or move_line.company_id.currency_id.id
            else:
                rec.currency_id = rec.vale_id.currency_id and rec.vale_id.currency_id.id or rec.vale_id.company_id.currency_id.id

    @api.model
    def default_get(self, fields):
        if self._context is None:
            context = {}
        journal_id = self._context.get('journal_id', False)
        partner_id = self._context.get('partner_id', False)
        journal_pool = self.env['account.journal']
        partner_pool = self.env['res.partner']
        res = super(GrpValeCajaLine, self).default_get(fields)
        if (not journal_id) or ('account_id' not in fields):
            return res
        journal = journal_pool.browse(journal_id)
        account_id = False
        ttype = 'cr'
        if journal.type in ('sale', 'sale_refund'):
            account_id = journal.default_credit_account_id and journal.default_credit_account_id.id or False
            ttype = 'cr'
        elif journal.type in ('purchase', 'expense', 'purchase_refund'):
            account_id = journal.default_debit_account_id and journal.default_debit_account_id.id or False
            ttype = 'dr'
        elif partner_id:
            partner = partner_pool.browse(partner_id)
            if self._context.get('type') == 'payment':
                ttype = 'dr'
                account_id = partner.property_account_payable.id
            elif self._context.get('type') == 'receipt':
                account_id = partner.property_account_receivable.id

        res['account_id'] = account_id
        res['type'] = ttype
        return res


# TODO: C SPRING 12 GAP 301
class aprobar_pago(models.TransientModel):
    _inherit = "aprobar.pago.guardar"

    # @api.multi
    # def pago_guardar(self, vals):
    #     for invoice in self.env['account.invoice'].browse(vals['active_ids']):
    #         if not invoice.pago_aprobado:
    #             vale = self.env['grp.vale.caja'].search([('aprobacion_pago_id', '=', invoice.id)])
    #             if vale:
    #                 vale.proforma_voucher()
    #     return super(aprobar_pago, self).pago_guardar(vals)
