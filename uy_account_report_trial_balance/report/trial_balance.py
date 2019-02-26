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

from openerp.addons.account_financial_report_webkit.report.webkit_parser_header_fix \
    import HeaderFooterTextWebKitParser
from openerp.addons.account_financial_report_webkit.report.trial_balance \
    import TrialBalanceWebkit

class TrialBalanceWebkitExt(TrialBalanceWebkit):

    def set_context(self, objects, data, ids, report_type=None):
        self.localcontext.update({
            'display_accounts': data.get('form',{}).get('display_accounts', False) or False,
            'financial_report': data.get('form',{}).get('financial_report', False) or False,
        })
        return super(TrialBalanceWebkitExt, self).set_context(objects, data, ids, report_type=report_type)

    def _get_account_details(self, account_ids, target_move, fiscalyear,
                             main_filter, start, stop, initial_balance_mode,
                             context=None):
        accounts_by_id = super(TrialBalanceWebkitExt, self)._get_account_details(account_ids, target_move, fiscalyear,
                               main_filter, start, stop, initial_balance_mode, context=context)
        if not self.localcontext.get('financial_report', False) and \
           self.localcontext.get('display_accounts', False):
            currency_obj = self.pool.get('res.currency')
            currency = self.pool.get('res.users').browse(self.cursor, self.uid, self.uid).company_id.currency_id
            for key, value in accounts_by_id.items():
                if self.localcontext['display_accounts'] == 'movement':
                    if currency_obj.is_zero(self.cursor, self.uid, currency, value['credit']) \
                       and currency_obj.is_zero(self.cursor, self.uid, currency, value['debit']) \
                       and currency_obj.is_zero(self.cursor, self.uid, currency, value['balance']):
                        account_ids.remove(key)
                        accounts_by_id.pop(key)
                elif self.localcontext['display_accounts']=='not_zero':
                    if currency_obj.is_zero(self.cursor, self.uid, currency, value['balance']):
                        account_ids.remove(key)
                        accounts_by_id.pop(key)
        return accounts_by_id

    def compute_balance_data(self, data, filter_report_type=None):
        objects, new_ids, context_report_values = super(TrialBalanceWebkitExt, self).\
                compute_balance_data(data, filter_report_type=filter_report_type)

        if not self._get_form_param('financial_report', data, default=False) and \
           self._get_form_param('display_curr_columns', data, default=False):

            dict_account_ids = {}
            for account in objects:
                children_and_consolidated = account._get_children_and_consol()
                if children_and_consolidated:
                    dict_account_ids[account.id] = children_and_consolidated
                else:
                    dict_account_ids[account.id] = []

            main_filter = self._get_form_param('filter', data, default='filter_no')
            target_move = self._get_form_param('target_move', data, default='all')
            start_date = self._get_form_param('date_from', data)
            stop_date = self._get_form_param('date_to', data)
            start_period = self.get_start_period_br(data)
            stop_period = self.get_end_period_br(data)
            if main_filter == 'filter_no':
                fiscalyear = self.get_fiscalyear_br(data)
                start_period = self.get_first_fiscalyear_period(fiscalyear)
                stop_period = self.get_last_fiscalyear_period(fiscalyear)
            if main_filter == 'filter_date':
                start = start_date
                stop = stop_date
            else:
                start = start_period
                stop = stop_period

            move_lines_memoizer = self._compute_account_move_lines(
                dict_account_ids, main_filter, target_move, start, stop)

            context_report_values.update({'lines_accounts': move_lines_memoizer})

        return objects, new_ids, context_report_values

    def _compute_account_move_lines(self, dict_accounts_ids, main_filter,
                                      target_move, start, stop):
        res = {}
        accounts_ids = dict_accounts_ids.keys()
        for acount_id, child_ids in dict_accounts_ids.items():
            lines = []
            for acc_id in child_ids:
                if acc_id in accounts_ids:
                    move_line_ids = self.get_move_lines_ids(
                        acc_id, main_filter, start, stop, target_move)
                    if move_line_ids:
                        lines += self._get_move_line_datas(move_line_ids)
            res[acount_id] = lines
        return res


HeaderFooterTextWebKitParser(
    'report.account.account_report_trial_balance_webkit_ext',
    'account.account',
    'addons/account_financial_report_webkit/report/templates/account_report_trial_balance.mako',
    parser=TrialBalanceWebkitExt)
