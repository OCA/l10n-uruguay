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

from openerp import models, fields, api, _
from openerp.tools.translate import _
from openerp.exceptions import Warning
from openerp import models, api
import time

import logging
_logger = logging.getLogger(__name__)

class account_invoice_ext_api(models.Model):
    _inherit = 'account.transfer'
    _order = 'date desc'

    @api.depends('source_journal_id', 'target_journal_id')
    def _compute_misma_ue(self):
        for record in self:
            ue_source = False
            ue_target = False
            if record.source_journal_id.operating_unit_id:
                ue_source = record.source_journal_id.operating_unit_id.id
            if record.target_journal_id.operating_unit_id:
                ue_target = record.target_journal_id.operating_unit_id.id
            if ue_source and ue_target and (ue_source == ue_target):
                record.misma_ue = True
            else:
                record.misma_ue = False

    move_id = fields.Many2one(
        'account.move',
        'Asiento',
    )

    misma_ue = fields.Boolean(
        string=u'Misma UE',
        compute='_compute_misma_ue',
    )

    # TODO: SPRING 4 GAP 247
    entry_date = fields.Date(
        string=u'Fecha', default=lambda *a: fields.Date.today(),
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    # TODO: SPRING 4 GAP 247
    @api.onchange('entry_date')
    def _onchange_entry_date(self):
        for record in self:
            if record.entry_date:
                record.date = record.entry_date

    @api.multi
    def action_confirm(self):
        self.ensure_one()

        if self.amount <= 0.0:
            raise Warning(_('Amount must be greater than 0!'))

        # set date if not configured
        if not self.date:
            self.date = fields.Date.context_today(self)

        # set period if not configured
        period = self.period_id
        if not self.period_id:
            period = period.with_context(
                company_id=self.company_id.id).find(
                self.date)[:1]
            if not period:
                raise Warning(_('Not period found for current date'))
            self.period_id = period.id

        ue_source = False
        ue_target = False
        if self.source_journal_id.operating_unit_id:
            ue_source = self.source_journal_id.operating_unit_id.id
        if self.target_journal_id.operating_unit_id:
            ue_target = self.target_journal_id.operating_unit_id.id

        if ue_source and ue_target and (ue_source == ue_target):
            # create move
            move = self.source_move_id.create(self.get_move_vals('ue'))

            self.write({
                'move_id': move.id,
                'state': 'confirmed',
                })
        else:
            # create source move
            source_move = self.source_move_id.create(self.get_move_vals('source'))

            # create target move
            target_move = self.target_move_id.create(self.get_move_vals('target'))

            self.write({
                'target_move_id': target_move.id,
                'source_move_id': source_move.id,
                'state': 'confirmed',
                })

    @api.multi
    def get_move_vals(self, move_type):
        self.ensure_one()
        company_currency = self.company_id.currency_id

        if move_type not in ['ue']:
            transfer_account = self.company_id.transfer_account_id
            if not transfer_account:
                raise Warning(_(
                    'No transfer account configured con company %s!') % (
                    self.source_journal_id.company_id.name))

        if move_type == 'source':
        # TODO: C INCIDENCIA
            ref = _('%s (Origen)' % self.ref)
            journal = self.source_journal_id
            first_account = journal.default_debit_account_id
            second_account = transfer_account
            operating_unit_id = self.source_journal_id.operating_unit_id.id
        if move_type == 'target':
       # TODO: C INCIDENCIA
            ref = _('%s (Destino)' % self.ref)
            journal = self.target_journal_id
            first_account = transfer_account
            second_account = journal.default_credit_account_id
            operating_unit_id = self.target_journal_id.operating_unit_id.id

        # Se agrega el caso en que los diarios origen y destino tienen la misma ue
        if move_type == 'ue':
            ref = _(u'%s (Asiento único)' % self.ref)
            first_account = self.source_journal_id.default_credit_account_id
            second_account = self.target_journal_id.default_debit_account_id
            journal = self.source_journal_id

        name = journal.sequence_id.with_context(fiscalyear_id=self.period_id.fiscalyear_id.id)._next()
        move_vals = {
            'ref': ref,
            'name': name,
            'period_id': self.period_id.id,
            'date': self.date,
            'journal_id': journal.id,
            'company_id': self.company_id.id,
            }

        source_currency = self.source_journal_id.currency or company_currency
        diff_currency = source_currency != company_currency

        company_currency_amount = diff_currency and source_currency.with_context(date=self.date).compute(self.amount, company_currency) or self.amount

        first_line_vals = {
            'name': name,
            'debit': 0.0,
            'credit': company_currency_amount,
            'account_id': first_account.id,
            'currency_id': (diff_currency and first_account.currency_id and first_account.currency_id.id == self.source_journal_id.currency.id) and source_currency.id or False,
            'amount_currency': (diff_currency and first_account.currency_id and first_account.currency_id.id == self.source_journal_id.currency.id) and -1 * self.amount or False,
        }
        currency = second_account.currency_id or company_currency
        second_line_vals = {
            'name': name,
            'debit': company_currency_amount,
            'credit': 0.0,
            'account_id': second_account.id,
            'currency_id': (currency and currency.id != company_currency.id) and currency.id or False,
            'amount_currency': (currency and currency.id != company_currency.id) and source_currency.with_context(date=self.date).compute(self.amount, currency) or False,
        }
        if move_type == 'ue':
            move_vals.update({'operating_unit_id': self.source_journal_id.operating_unit_id.id})
        elif move_type in ['source', 'target']:
            move_vals.update({'operating_unit_id': operating_unit_id})
        move_vals['line_id'] = [
            (0, _, first_line_vals), (0, _, second_line_vals)]
        return move_vals

    # TODO: SPRING 10 GAP 493 C
    @api.one
    def action_cancel(self):
        if self.state == 'confirmed':
            # TODO: L Generando extornos
            period_id = self.env['account.period'].find(fields.Date.today()).id
            if self.source_move_id and self.target_move_id:
                self.source_move_id.create_reversals(
                    fields.Date.today(),
                    reversal_period_id=period_id,
                )
                self.target_move_id.create_reversals(
                    fields.Date.today(),
                    reversal_period_id=period_id,
                )
            elif self.move_id:
                self.move_id.create_reversals(
                    fields.Date.today(),
                    reversal_period_id=period_id,
                )
            self.write({'state': 'cancel', 'source_move_id': False, 'target_move_id': False, 'move_id': False})
        else:
            return super(account_invoice_ext_api, self).action_cancel()
