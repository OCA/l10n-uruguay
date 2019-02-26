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

from collections import defaultdict
from openerp.addons.account_financial_report_webkit.report.webkit_parser_header_fix \
    import HeaderFooterTextWebKitParser
from openerp.addons.account_financial_report_webkit.report.open_invoices \
    import PartnersOpenInvoicesWebkit
import time

class PartnersOpenInvoicesWebkitExt(PartnersOpenInvoicesWebkit):

    def set_context(self, objects, data, ids, report_type=None):
        self.localcontext.update({
            'only_residual_amount': data['form']['only_residual_amount'],
            'filter_currency_id': data['form']['filter_currency_id'] and data['form']['filter_currency_id'][0] or False,
        })
        return super(PartnersOpenInvoicesWebkitExt, self).set_context(objects, data, ids, report_type=report_type)

    def _get_partners_move_line_ids(self, filter_from, account_id, start, stop,
                                    target_move,
                                    opening_mode='exclude_opening',
                                    exclude_reconcile=False,
                                    partner_filter=None):
        if self.localcontext.get('filter_currency_id', False):
            final_res = defaultdict(list)

            sql_select = "SELECT account_move_line.id, \
                            account_move_line.partner_id FROM account_move_line"
            sql_joins = ''
            sql_where = " WHERE account_move_line.account_id = %(account_ids)s " \
                        " AND account_move_line.state = 'valid' "

            method = getattr(self, '_get_query_params_from_' + filter_from + 's')
            sql_conditions, search_params = method(start, stop)

            sql_where += sql_conditions

            if exclude_reconcile:
                sql_where += ("  AND ((account_move_line.reconcile_id IS NULL)"
                              "   OR (account_move_line.reconcile_id IS NOT NULL \
                                  AND account_move_line.last_rec_date > \
                                                          date(%(date_stop)s)))")

            if partner_filter:
                sql_where += "   AND account_move_line.partner_id \
                                                                in %(partner_ids)s"

            if target_move == 'posted':
                sql_joins += "INNER JOIN account_move \
                                    ON account_move_line.move_id = account_move.id"
                sql_where += " AND account_move.state = %(target_move)s"
                search_params.update({'target_move': target_move})

            sql_where += " AND account_move_line.transaction_curr_id = %(currency_id)s"
            search_params.update({
                'account_ids': account_id,
                'partner_ids': tuple(partner_filter),
                'currency_id': self.localcontext['filter_currency_id'],
            })

            sql = ' '.join((sql_select, sql_joins, sql_where))
            self.cursor.execute(sql, search_params)
            res = self.cursor.dictfetchall()
            if res:
                for row in res:
                    final_res[row['partner_id']].append(row['id'])
            return final_res

        return super(PartnersOpenInvoicesWebkitExt, self)._get_partners_move_line_ids(filter_from, account_id, start, stop,
                    target_move, opening_mode=opening_mode, exclude_reconcile=exclude_reconcile, partner_filter=partner_filter)

    def _partners_initial_balance_line_ids(self, account_ids, start_period,
                                           partner_filter,
                                           exclude_reconcile=False,
                                           force_period_ids=False,
                                           date_stop=None):
        if self.localcontext.get('filter_currency_id', False):
            period_ids = force_period_ids \
                if force_period_ids \
                else self._get_period_range_from_start_period(
                    start_period, fiscalyear=False, include_opening=False)

            if not period_ids:
                period_ids = [-1]
            search_param = {
                'date_start': start_period.date_start,
                'period_ids': tuple(period_ids),
                'account_ids': tuple(account_ids),
                'currency_id': self.localcontext['filter_currency_id'],
            }
            sql = ("SELECT ml.id, ml.account_id, ml.partner_id "
                   "FROM account_move_line ml "
                   "INNER JOIN account_account a "
                   "ON a.id = ml.account_id "
                   "WHERE ml.period_id in %(period_ids)s "
                   "AND ml.account_id in %(account_ids)s "
                   "AND ml.transaction_curr_id = %(currency_id)s ")
            if exclude_reconcile:
                if not date_stop:
                    raise Exception(
                        "Missing \"date_stop\" to compute the open invoices.")
                search_param.update({'date_stop': date_stop})
                sql += ("AND ((ml.reconcile_id IS NULL) "
                        "OR (ml.reconcile_id IS NOT NULL \
                        AND ml.last_rec_date > date(%(date_stop)s))) ")
            if partner_filter:
                sql += "AND ml.partner_id in %(partner_ids)s "
                search_param.update({'partner_ids': tuple(partner_filter)})

            self.cursor.execute(sql, search_param)
            return self.cursor.dictfetchall()

        return super(PartnersOpenInvoicesWebkitExt, self)._partners_initial_balance_line_ids(account_ids, start_period,
                    partner_filter, exclude_reconcile=exclude_reconcile, force_period_ids=force_period_ids, date_stop=date_stop)

    def _compute_open_transactions_lines(self, accounts_ids, main_filter,
                                         target_move, start, stop,
                                         date_until=False,
                                         partner_filter=False):
        res = super(PartnersOpenInvoicesWebkitExt, self)._compute_open_transactions_lines(accounts_ids,
                    main_filter, target_move, start, stop, date_until=date_until, partner_filter=partner_filter)
        if self.localcontext.get('only_residual_amount', False):
            #date_stop = time.strftime('%Y-%m-%d')
            #if main_filter in ('filter_period', 'filter_no'):
            #    date_stop = stop.date_stop
            #elif main_filter == 'filter_date':
            #    date_stop = stop
            invoice_obj = self.pool.get('account.invoice')
            all_line_ids = [ l['id'] for vals in res.values() for lines in vals.values() for l in lines ]
            for account_id, vals in res.items():
                for partner_id, lines in vals.items():
                    del_line_ids = []
                    for line in lines:
                        if line['id'] in del_line_ids:
                            res[account_id][partner_id].remove(line)
                            del_line_ids.remove(line['id'])
                            continue
                        if not line.get('invoice_id', False):
                            continue
                        if line.get('invoice_type') in ('out_invoice', 'in_invoice'):
                            invoice = invoice_obj.browse(self.cursor, self.uid, line['invoice_id'])
                            debit_total = line.get('debit') or 0.0
                            credit_total = line.get('credit') or 0.0
                            for pl in invoice.payment_ids:
                                #if pl.state == 'valid' and pl.account_id.id in accounts_ids and \
                                #   (not pl.reconcile_id or (pl.reconcile_id and pl.last_rec_date > date_stop)):
                                if pl.id in all_line_ids:
                                    debit_total += pl.debit
                                    credit_total += pl.credit
                                    del_line_ids.append(pl.id)
                            if hasattr(invoice, 'refund_ref_ids'): # notas de crédito asociadas
                                for refund in invoice.refund_ref_ids:
                                    for refund_line in refund.move_lines:
                                        #if refund_line.state == 'valid' and refund_line.account_id.id in accounts_ids and \
                                        #   (not refund_line.reconcile_id or (refund_line.reconcile_id and refund_line.last_rec_date > date_stop)):
                                        if refund_line.account_id.id in accounts_ids and refund_line.id in all_line_ids:
                                            debit_total += refund_line.debit
                                            credit_total += refund_line.credit
                                            del_line_ids.append(refund_line.id)
                                    for refund_pline in refund.payment_ids:
                                        if refund_pline.id in all_line_ids:
                                            debit_total += refund_pline.debit
                                            credit_total += refund_pline.credit
                                            del_line_ids.append(refund_pline.id)
                            line['debit'] = (debit_total - credit_total) if (debit_total - credit_total) > 0 else 0.0
                            line['credit'] = (credit_total - debit_total) if (credit_total - debit_total) > 0 else 0.0
                    if del_line_ids:
                        for line in lines:
                            if line['id'] in del_line_ids:
                                res[account_id][partner_id].remove(line)
                                del_line_ids.remove(line['id'])
                                if not del_line_ids:
                                    break
        return res

    def _group_lines_by_currency(self, account_br):
        # Fix a bug when grouping by currency. By irabaza
        if not hasattr(account_br, 'ledger_lines'):
            return
        super(PartnersOpenInvoicesWebkitExt, self)._group_lines_by_currency(account_br)

HeaderFooterTextWebKitParser(
    'report.account.account_report_open_invoices_webkit_ext',
    'account.account',
    'addons/account_financial_report_webkit/report/templates/account_report_open_invoices.mako',
    parser=PartnersOpenInvoicesWebkitExt)
