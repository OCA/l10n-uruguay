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

from openerp import models, fields, api, osv
from openerp.tools.translate import _
from openerp.exceptions import ValidationError
from openerp.tools import float_compare

# TODO: SPRING 10 GAP 474 M


class GrpInternalPayOrder(models.Model):
    _inherit = 'account.voucher'

    def _compute_payments(self):
        partial_lines = lines = self.env['account.move.line']
        for line in self.move_id.line_id:
            if line.account_id != self.account_id:
                continue
            if line.reconcile_id:
                lines |= line.reconcile_id.line_id
            elif line.reconcile_partial_id:
                lines |= line.reconcile_partial_id.line_partial_ids
            partial_lines += line
        self.payment_ids = (lines - partial_lines).sorted()

    entry_date = fields.Date('Fecha de asiento')
    # RAGU: OPI
    opi = fields.Boolean('OPI')
    caja_chica_id = fields.Many2one('account.journal', u'Caja chica', domain="[('type','=','cash')])")
    bank_statement_id = fields.Many2one('account.bank.statement', u'Registro de caja',
                                        domain="[('journal_id','=',caja_chica_id)]")
    payment_ids = fields.Many2many('account.move.line', string='Payments',
                                   compute='_compute_payments')

    @api.multi
    def cancel_voucher(self):
        voucher_line_obj = self.env['account.voucher.line']
        for rec in self:
            # RAGU: señal de cancelación de OPI
            if rec.state == 'posted' and rec._context.get('default_opi'):
                for move_line in rec.move_ids:
                    if voucher_line_obj.search_count([('move_line_id','=',move_line.id),('amount','!=',0),('voucher_id.state','!=','cancel')]):
                        raise ValidationError(_(u'La OPI está incluida en un pago, no puede ser cancelada!'))
            # rec.line_ids.filtered(lambda x: x.origin_voucher_id.opi and x.origin_voucher_id.state == 'pagado').mapped('origin_voucher_id').cancel_voucher()
            rec.line_ids.filtered(lambda x: x.origin_voucher_id.opi and x.origin_voucher_id.state == 'pagado').mapped('origin_voucher_id').write({'state':'posted'})


        return super(GrpInternalPayOrder, self).cancel_voucher()


    @api.multi
    def proforma_voucher(self):
        res = super(GrpInternalPayOrder, self).proforma_voucher()
        for rec in self:
            for line in rec.mapped(lambda x: x.line_dr_ids).filtered(lambda x: x.amount > 0 and x.amount == x.amount_unreconciled):
                if line.move_line_id.internal_pay_order:
                    line.move_line_id.internal_pay_order.write({'state': 'pagado'})
        return res

    def voucher_move_line_create(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency,
                                 context=None):
        '''
        Create one account move line, on the given account move, per voucher line where amount is not 0.0.
        It returns Tuple with tot_line what is total of difference between debit and credit and
        a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).

        :param voucher_id: Voucher id what we are working with
        :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
        :param move_id: Account move wher those lines will be joined.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
        :rtype: tuple(float, list of int)
        '''
        if voucher_id and self.browse(cr, uid, voucher_id).opi:
            if context is None:
                context = {}
            move_line_obj = self.pool.get('account.move.line')
            currency_obj = self.pool.get('res.currency')
            tax_obj = self.pool.get('account.tax')
            tot_line = line_total
            rec_lst_ids = []

            date = self.read(cr, uid, voucher_id, ['date'], context=context)['date']
            ctx = context.copy()
            ctx.update({'date': date})
            voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=ctx)
            voucher_currency = voucher.journal_id.currency or voucher.company_id.currency_id
            ctx.update({
                'voucher_special_currency_rate': voucher_currency.rate * voucher.payment_rate,
                'voucher_special_currency': voucher.payment_rate_currency_id and voucher.payment_rate_currency_id.id or False, })
            prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
            for line in voucher.line_ids:
                context_line = context.copy()
                context_line.update({'line_amount':line.amount})
                # create one move line per voucher line where amount is not 0.0
                # AND (second part of the clause) only if the original move line was not having debit = credit = 0 (which is a legal value)
                if not line.amount and not (
                        line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit,
                                                                precision_digits=prec) and not float_compare(
                        line.move_line_id.debit, 0.0, precision_digits=prec)):
                    continue
                # convert the amount set on the voucher line into the currency of the voucher's company
                # this calls res_curreny.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
                amount = self._convert_amount(cr, uid, line.untax_amount or line.amount, voucher.id, context=ctx)
                # if the amount encoded in voucher is equal to the amount unreconciled, we need to compute the
                # currency rate difference
                if line.amount == line.amount_unreconciled:
                    if not line.move_line_id:
                        raise osv.except_osv(_('Wrong voucher line'),
                                             _("The invoice you are willing to pay is not valid anymore."))
                    sign = voucher.type in ('payment', 'purchase') and -1 or 1
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
                    'currency_id': line.move_line_id and (
                    company_currency <> line.move_line_id.currency_id.id and line.move_line_id.currency_id.id) or False,
                    'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                    'quantity': 1,
                    'credit': 0.0,
                    'debit': 0.0,
                    'date': voucher.date,
                }
                if amount < 0:
                    amount = -amount
                    if line.type == 'dr':
                        line.type = 'cr'
                    else:
                        line.type = 'dr'

                if (line.type == 'dr'):
                    tot_line += amount
                    move_line['debit'] = amount
                else:
                    tot_line -= amount
                    move_line['credit'] = amount

                if voucher.tax_id and voucher.type in ('sale', 'purchase'):
                    move_line.update({
                        'account_tax_id': voucher.tax_id.id,
                    })

                if move_line.get('account_tax_id', False):
                    tax_data = tax_obj.browse(cr, uid, [move_line['account_tax_id']], context=context)[0]
                    if not (tax_data.base_code_id and tax_data.tax_code_id):
                        raise osv.except_osv(_('No Account Base Code and Account Tax Code!'), _(
                            "You have to configure account base code and account tax code on the '%s' tax!") % (
                                             tax_data.name))

                # compute the amount in foreign currency
                foreign_currency_diff = 0.0
                amount_currency = False
                corregido = False
                ajuste_negativo = False
                if line.move_line_id:
                    # We want to set it on the account move line as soon as the original line had a foreign currency
                    if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency:
                        # we compute the amount in that foreign currency.
                        if line.move_line_id.currency_id.id == current_currency:
                            # if the voucher and the voucher line share the same currency, there is no computation to do
                            # PCARBALLO modificacion del signo del monto.
                            # si tiene monto en debito o en credito, entonces es el caso comun,
                            # y no se modifica el calculo del signo con respecto al estandar.
                            # de lo contrario, chequea si el voucher tiene lineas de credito
                            # o lineas de debito, para modificar el signo en base a ese criterio.
                            # Se declara ademas una variable booleana "corregido", que sirve
                            # para verificar si el codigo ingreso o no a estos casos particulares.
                            # Se utiliza mas adelante para el calculo de la diferencia de cambio.
                            # ECHAVIANO 26/10 ACA ESTA EL PROBLEMA EN EL PAGO DEL AJUSTE > 0
                            if move_line['debit'] or move_line['credit']:
                                sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                                amount_currency = sign * (line.amount)
                            elif voucher.line_dr_ids or voucher.line_cr_ids and line.amount != 0:
                                if voucher.invoice_id and line.amount != 0:
                                    if voucher.invoice_id.type in ('in_invoice','out_refund'):  # fact de proveedor o rectificativa de cliente
                                        sign = 1
                                    elif voucher.invoice_id.type in ('in_refund'): # rect de proveedor
                                        corregido = True
                                        sign = (line.amount > 0) and -1 or 1
                                        ajuste_negativo = voucher.invoice_id.amount_total < 0 and True or False
                                        # if voucher.invoice_id.residual < 0:
                                        #     sign = (line.amount > 0) and -1 or 1
                                        # else:
                                        #     sign = (line.amount > 0) and 1 or -1
                                    elif voucher.invoice_id.type in ('out_invoice'): # de cliente, dividido en un else por si es un caso diferente, puede agregarse en la condicion de arriba
                                        sign = (line.amount > 0) and -1 or 1
                                    amount_currency = sign * (line.amount)
                        else:
                            # if the rate is specified on the voucher, it will be used thanks to the special keys in the context
                            # otherwise we use the rates of the system
                            amount_currency = currency_obj.compute(cr, uid, company_currency, line.move_line_id.currency_id.id, move_line['debit']-move_line['credit'], context=ctx)
                    if line.amount == line.amount_unreconciled:
                        sign = voucher.type in ('payment', 'purchase') and -1 or 1
                        # PCARBALLO uso de la variable corregido.
                        # Si estamos en los casos particulares anteriormente descritos,
                        # entonces el signo cambia, para evitar que foreign_currency_diff de un valor no nulo.
                        if corregido:
                            sign = sign * -1
                            foreign_currency_diff = sign * line.move_line_id.amount_residual_currency + amount_currency
                        else:
                            foreign_currency_diff = (line.move_line_id.amount_residual_currency - abs(amount_currency))
                        # ECHAVIANO cambio
                # PCARBALLO eliminar creacion lineas con cero
                rec_ids = []
                if amount_currency != 0 or amount != 0:
                    if corregido and ajuste_negativo:
                        amount_currency = amount_currency * -1
                    move_line['amount_currency'] = amount_currency

                    voucher_line = move_line_obj.create(cr, uid, move_line, context=context_line)
                    rec_ids = [voucher_line, line.move_line_id.id]
                if len(rec_ids) == 0:
                    rec_ids = [line.move_line_id.id]
                # PCARBALLO fin eliminar creacion lineas con cero

                if not currency_obj.is_zero(cr, uid, voucher.company_id.currency_id, currency_rate_difference):
                    # Change difference entry in company currency
                    exch_lines = self._get_exchange_lines(cr, uid, line, move_id, currency_rate_difference, company_currency, current_currency, context=context)
                    #009-Agregando flag
                    exch_lines[0].update({'exchange_line':True})
                    exch_lines[1].update({'exchange_line':True})
                    new_id = move_line_obj.create(cr, uid, exch_lines[0],context_line)
                    move_line_obj.create(cr, uid, exch_lines[1], context_line)
                    rec_ids.append(new_id)

                if line.move_line_id and line.move_line_id.currency_id and \
                        not currency_obj.is_zero(cr, uid, line.move_line_id.currency_id, foreign_currency_diff):
                    # Change difference entry in voucher currency
                    move_line_foreign_currency = {
                        'journal_id': line.voucher_id.journal_id.id,
                        'period_id': line.voucher_id.period_id.id,
                        'name': _('change')+': '+(line.name or '/'),
                        'account_id': line.account_id.id,
                        'move_id': move_id,
                        'partner_id': line.voucher_id.partner_id.id,
                        'currency_id': line.move_line_id.currency_id.id,
                        'amount_currency': -1 * foreign_currency_diff,
                        'quantity': 1,
                        'credit': 0.0,
                        'debit': 0.0,
                        'date': line.voucher_id.date,
                        #009- pasando campo en true cuando se genera tipo de cambio
                        'exchange_line': True,
                    }
                    new_id = move_line_obj.create(cr, uid, move_line_foreign_currency, context=context_line)
                    rec_ids.append(new_id)
                if line.move_line_id.id:
                    rec_lst_ids.append(rec_ids)
            return (tot_line, rec_lst_ids)
        else:
            return super(GrpInternalPayOrder, self).voucher_move_line_create(cr, uid, voucher_id, line_total,
                                                                                 move_id, company_currency,
                                                                                 current_currency,context=context)

    # TODO: M SPRING 11 GAP 474 varianza
    # TODO modificando el campo vc=true en el apunte de la cuenta del proveedor
    def first_move_line_get(self, cr, uid, voucher_id, move_id, company_currency, current_currency, context=None):
        res = super(GrpInternalPayOrder, self).first_move_line_get(cr, uid, voucher_id, move_id, company_currency, current_currency)
        voucher_obj = self.browse(cr, uid, voucher_id)
        if voucher_obj.opi:
            line_vc = voucher_obj.mapped('line_dr_ids').filtered(lambda x: x.concepto_id.devolucion_vc)
            if line_vc:
                res.update({'vc': True})
        return res

    # RAGU se implementa por perdida de contexto en el core
    @api.multi
    def action_compute_opi_total(self):
        for voucher in self:
            voucher_amount = 0.0
            for line in voucher.line_ids:
                voucher_amount += line.untax_amount or line.amount
                line.write({'amount': line.untax_amount or line.amount})

            if not voucher.tax_id:
                self.write({'amount': voucher_amount, 'tax_amount': 0.0})
                continue

            tax = [voucher.tax_id.id]
            partner = voucher.partner_id.id
            tax = self.env['account.fiscal.position'].map_tax(partner and partner.property_account_position or False, tax)

            total = voucher_amount
            total_tax = 0.0

            if not tax[0].price_include:
                for line in voucher.line_ids:
                    for tax_line in self.env['account.tax'].compute_all(tax, line.amount, 1).get('taxes', []):
                        total_tax += tax_line.get('amount', 0.0)
                total += total_tax
            else:
                for line in voucher.line_ids:
                    line_total = 0.0
                    line_tax = 0.0

                    for tax_line in self.env['account.tax'].compute_all(tax, line.untax_amount or line.amount, 1).get('taxes', []):
                        line_tax += tax_line.get('amount', 0.0)
                        line_total += tax_line.get('price_unit')
                    total_tax += line_tax
                    untax_amount = line.untax_amount or line.amount
                    line.write({'amount': line_total, 'untax_amount': untax_amount})

            self.write({'amount': total, 'tax_amount': total_tax})
        return True


class grpInternalPayOrderLine(models.Model):
    _inherit= 'account.voucher.line'

    concepto_id = fields.Many2one('grp_concepto_gasto_cc_viaticos', 'Concepto', ondelete='restrict')

    @api.onchange('concepto_id')
    def onchange_concepto_id(self):
        if self.concepto_id:
                self.account_id = self.concepto_id.cuenta_id and self.concepto_id.cuenta_id.id or False


class GrpAccountMoveLine(models.Model):

    _inherit = 'account.move.line'



    internal_pay_order = fields.Many2one('account.voucher', string=u'Orden de pago interno', compute='_compute_internal_pay_order')
    # TODO: M SPRING 11 GAP 474 Varianza
    vc = fields.Boolean('VC', default=False)

    @api.multi
    def _compute_internal_pay_order(self):
        for rec in self:
            internal_pay_order = self.env['account.voucher'].search([('move_id','=',rec.move_id.id),('opi','=',True)])
            if internal_pay_order:
                rec.internal_pay_order = internal_pay_order
        # return True
