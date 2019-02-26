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

from openerp.addons.account_financial_report_webkit.report.webkit_parser_header_fix  \
    import HeaderFooterTextWebKitParser
from  openerp.addons.account_financial_report_webkit.report.general_ledger \
    import GeneralLedgerWebkit
from datetime import datetime


class GeneralLedgerWebkitExt(GeneralLedgerWebkit):

    def set_context(self, objects, data, ids, report_type=None):
        self.localcontext.update({
            'partner_ids': data['form']['filter_partner_ids'] or False,
            'operating_unit_ids': data['form']['filter_operating_unit_ids'] or False,
            'curr_rate_option': data['form']['curr_rate_option'],
            'curr_rate_date': data['form']['curr_rate_date'],
            'curr_rate': data['form']['curr_rate'],
            'fiscalyear': self.get_fiscalyear_br(data),
            'target_move_value': data['form']['target_move'],
        })
        return super(GeneralLedgerWebkitExt, self).set_context(objects, data, ids, report_type=report_type)

    def _get_move_ids_from_periods(self, account_id, period_start, period_stop,
                                   target_move):
        if self.localcontext.get('partner_ids', False) or self.localcontext.get('operating_unit_ids', False):
            move_line_obj = self.pool.get('account.move.line')
            period_obj = self.pool.get('account.period')
            periods = period_obj.build_ctx_periods(
                self.cursor, self.uid, period_start.id, period_stop.id)
            if not periods:
                return []
            search = [('period_id', 'in', periods), ('account_id', '=', account_id)]
            if target_move == 'posted':
                search += [('move_id.state', '=', 'posted')]
            partner_ids = self.localcontext.get('partner_ids', False)
            if partner_ids:
                search += [('partner_id', 'in', partner_ids)]
            operating_unit_ids = self.localcontext.get('operating_unit_ids', False)
            if operating_unit_ids:
                search += [('operating_unit_id', 'in', operating_unit_ids)]
            res_ids = move_line_obj.search(self.cursor, self.uid, search)
            return res_ids
        return super(GeneralLedgerWebkitExt, self)._get_move_ids_from_periods(
                    account_id, period_start, period_stop, target_move)

    def _get_move_ids_from_dates(self, account_id, date_start, date_stop,
                                 target_move, mode='include_opening'):
        if self.localcontext.get('partner_ids', False) or self.localcontext.get('operating_unit_ids', False):
            move_line_obj = self.pool.get('account.move.line')
            search_period = [('date', '>=', date_start),
                             ('date', '<=', date_stop),
                             ('account_id', '=', account_id)]
            if mode == 'exclude_opening':
                opening = self._get_opening_periods()
                if opening:
                    search_period += ['period_id', 'not in', opening]
            if target_move == 'posted':
                search_period += [('move_id.state', '=', 'posted')]
            partner_ids = self.localcontext.get('partner_ids', False)
            if partner_ids:
                search_period += [('partner_id', 'in', partner_ids)]
            operating_unit_ids = self.localcontext.get('operating_unit_ids', False)
            if operating_unit_ids:
                search_period += [('operating_unit_id', 'in', operating_unit_ids)]
            res_ids = move_line_obj.search(self.cursor, self.uid, search_period)
            return res_ids
        return super(GeneralLedgerWebkitExt, self)._get_move_ids_from_dates(
                    account_id, date_start, date_stop, target_move, mode=mode)

    # NOTE: Original addon ´´account_financial_report_webkit´´ does not compute
    # initial balance when main filter is by range of dates.
    # Adding this feature. By irabaza
    def is_initial_balance_enabled(self, main_filter):
        if main_filter == 'filter_date' and self.localcontext.get('fiscalyear', False):
            return True
        return super(GeneralLedgerWebkitExt, self).is_initial_balance_enabled(main_filter)

    def _get_initial_balance_mode(self, start_period):
        return 'initial_balance'


    def _compute_initial_balances(self, account_ids, start_period, fiscalyear):
        result = {}
        if isinstance(start_period, (str, unicode)): # period is date_start
            date_start = start_period

            move_state = ['draft', 'posted']
            if self.localcontext['target_move_value'] == 'posted':
                move_state = ['posted']

            search_params = { 'date_start': date_start, 'move_state': tuple(move_state) }
            sql = """
                SELECT sum(l.debit) AS debit,
                       sum(l.credit) AS credit,
                       sum(l.debit)-sum(l.credit) AS balance,
                       sum(l.curr_debit) AS usd_debit,
                       sum(l.curr_credit) AS usd_credit,
                       sum(l.curr_debit)-sum(l.curr_credit)  AS curr_balance
                FROM account_move_line l
                        LEFT JOIN account_move am ON (l.move_id=am.id)
                WHERE l.date < %(date_start)s
                      AND am.state IN %(move_state)s
                      AND l.account_id = %(account_id)s
            """
            if self.localcontext.get('partner_ids', False):
                sql += " AND l.partner_id in %(partner_ids)s"
                search_params['partner_ids'] = tuple(self.localcontext.get('partner_ids'))
            if self.localcontext.get('operating_unit_ids', False):
                sql += " AND l.operating_unit_id in %(operating_unit_ids)s"
                search_params['operating_unit_ids'] = tuple(self.localcontext.get('operating_unit_ids'))

            for acc_id in account_ids:
                search_params['account_id'] = acc_id

                try:
                    self.cursor.execute(sql, search_params)
                    res = self.cursor.dictfetchone()
                except Exception:
                    self.cursor.rollback()
                    raise

                result[acc_id] = {  'debit': res.get('debit') or 0.0,
                                    'credit': res.get('credit') or 0.0,
                                    'init_balance': res.get('balance') or 0.0,
                                    'usd_debit': res.get('usd_debit') or 0.0,
                                    'usd_credit': res.get('usd_credit') or 0.0,
                                    'usd_init_balance': (res.get('usd_debit') or 0.0) - (res.get('usd_credit') or 0.0),
                                    'init_balance_currency': res.get('curr_balance') or 0.0,
                                    'state': 'computed' }
        else:
            periods_ids = self._get_period_range_from_start_period(
                start_period, include_opening=True, stop_at_previous_opening=False)

            for acc_id in account_ids:
                result[acc_id] = self._compute_init_balance(acc_id, periods_ids)

        return result

    def _compute_init_balance(self, account_id=None, period_ids=None,
                              mode='computed', default_values=False):
        if not isinstance(period_ids, list):
            period_ids = [period_ids]
        res = {}

        if not default_values:

            move_state = ['draft', 'posted']
            if self.localcontext['target_move_value'] == 'posted':
                move_state = ['posted']

            if not account_id or not period_ids:
                raise Exception('Missing account or period_ids')
            search_params = { 'period_ids': tuple(period_ids), 'account_id': account_id, 'move_state': tuple(move_state) }
            sql = """
                SELECT sum(l.debit) AS debit,
                       sum(l.credit) AS credit,
                       sum(l.debit)-sum(l.credit) AS balance,
                       sum(curr_debit) AS usd_debit,
                       sum(curr_credit) AS usd_credit,
                       sum(l.curr_debit)-sum(l.curr_credit)  AS curr_balance
                FROM account_move_line l
                    LEFT JOIN account_move am ON (l.move_id=am.id)
                WHERE l.period_id in %(period_ids)s
                      AND l.account_id = %(account_id)s
                      AND am.state IN %(move_state)s

            """
#
#
#                       sum(CASE WHEN (l.debit>0 AND l.currency_id=(select id from res_currency where name='USD')) THEN abs(l.amount_currency) ELSE round(l.debit * (select rate from res_currency_rate where currency_id=(select id from res_currency where name='USD') and name=(select max(name) from res_currency_rate where currency_id=(select id from res_currency where name='USD') and name < l.date)), 2) END) AS usd_debit,
#                       sum(CASE WHEN (l.credit>0 AND l.currency_id=(select id from res_currency where name='USD')) THEN abs(l.amount_currency) ELSE round(l.credit * (select rate from res_currency_rate where currency_id=(select id from res_currency where name='USD') and name=(select max(name) from res_currency_rate where currency_id=(select id from res_currency where name='USD') and name < l.date)), 2) END) AS usd_credit,
#                       sum(l.amount_currency) AS curr_balance

            if self.localcontext.get('partner_ids', False):
                sql += " AND l.partner_id in %(partner_ids)s"
                search_params['partner_ids'] = tuple(self.localcontext.get('partner_ids'))
            if self.localcontext.get('operating_unit_ids', False):
                sql += " AND l.operating_unit_id in %(operating_unit_ids)s"
                search_params['operating_unit_ids'] = tuple(self.localcontext.get('operating_unit_ids'))
            try:
                self.cursor.execute(sql, search_params)
                res = self.cursor.dictfetchone()
            except Exception:
                self.cursor.rollback()
                raise

        return {'debit': res.get('debit') or 0.0,
                'credit': res.get('credit') or 0.0,
                'init_balance': res.get('balance') or 0.0,
                'usd_debit': res.get('usd_debit') or 0.0,
                'usd_credit': res.get('usd_credit') or 0.0,
                'usd_init_balance': (res.get('usd_debit') or 0.0) - (res.get('usd_credit') or 0.0),
                'init_balance_currency': res.get('curr_balance') or 0.0,
                'state': mode}


HeaderFooterTextWebKitParser(
    'report.account.account_report_general_ledger_webkit_ext',
    'account.account',
    'addons/uy_account_report_general_ledger/report/account_report_general_ledger.mako',
    parser=GeneralLedgerWebkitExt)
