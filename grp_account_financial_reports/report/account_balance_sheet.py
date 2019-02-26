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

from openerp.addons.account_financial_report_aeroo_xls.report.account_balance_sheet \
    import Parser as BalanceSheetParser

class Parser(BalanceSheetParser):
    def __init__(self, cr, uid, name, context=None):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
            'get_dimensions_data': self.get_dimensions_data,
        })

    def get_lines(self, data):
        lines = []
        account_obj = self.pool.get('account.account')
        currency_obj = self.pool.get('res.currency')
        ids2 = self.pool.get('account.financial.report')._get_children_by_order(self.cr, self.uid, [data['form']['account_report_id'][0]], context=data['form']['used_context'])
        for report in self.pool.get('account.financial.report').browse(self.cr, self.uid, ids2, context=data['form']['used_context']):
            vals = {
                'name': report.name,
                'balance': report.balance * report.sign,
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type =='sum' and 'view' or False, #used to underline the financial report balances
            }
            if data['form']['debit_credit']:
                vals['debit'] = report.debit
                vals['credit'] = report.credit
            if data['form']['enable_filter']:
                vals['balance_cmp'] = self.pool.get('account.financial.report').browse(self.cr, self.uid, report.id, context=data['form']['comparison_context']).balance
            lines.append(vals)
            account_ids = []
            if report.display_detail == 'no_detail':
                #the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue
            if report.type == 'accounts' and report.account_ids:
                account_ids = account_obj._get_children_and_consol(self.cr, self.uid, [x.id for x in report.account_ids])
            elif report.type == 'account_type' and report.account_type_ids:
                account_ids = account_obj.search(self.cr, self.uid, [('user_type','in', [x.id for x in report.account_type_ids])])
            if account_ids:
                for account in account_obj.browse(self.cr, self.uid, account_ids, context=data['form']['used_context']):
                    #if there are accounts to display, we add them to the lines with a level equals to their level in
                    #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
                    #financial reports for Assets, liabilities...)
                    if report.display_detail == 'detail_flat' and account.type == 'view':
                        continue
                    flag = False
                    vals = {
                        'name': account.code + ' ' + account.name,
                        'balance':  account.balance != 0 and account.balance * report.sign or account.balance,
                        'type': 'account',
                        'level': report.display_detail == 'detail_with_hierarchy' and min(account.level + 1,6) or 6, #account.level + 1
                        'account_type': account.type,
                        'account_id': account.id,
                        'report_sign': report.sign,
                    }

                    if data['form']['debit_credit']:
                        vals['debit'] = account.debit
                        vals['credit'] = account.credit

                    if not currency_obj.is_zero(self.cr, self.uid, account.company_id.currency_id, vals['balance']):
                        flag = True
                    if data['form']['enable_filter']:
                        vals['balance_cmp'] = account_obj.browse(self.cr, self.uid, account.id, context=data['form']['comparison_context']).balance
                        if not currency_obj.is_zero(self.cr, self.uid, account.company_id.currency_id, vals['balance_cmp']):
                            flag = True
                    if flag:
                        lines.append(vals)
        return lines

    def get_dimensions_data(self, data, line, company=None):
        account_id = line.get('account_id', False)
        if not account_id:
            return []

        sign = line.get('report_sign', 1)
        query_where = self.pool.get('account.move.line')._query_get(self.cr, self.uid, obj='l', context=data['form']['used_context'])
        if data['form']['display_org_unit_column'] and data['form']['display_analytic_acc_column'] and data['form']['display_multiprop_column']:
            _sql = """  SELECT d.name as org_unit,
                               aaa.name as analytic_acc,
                               dm.name as multiprop,
                               sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) as debit,
                               sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END) as credit,
                               (sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) - sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END)) * %s as balance
                        FROM account_analytic_line aal
                             inner join account_move_line l on (aal.move_id=l.id)
                             left join hr_department d ON (aal.hr_department_id=d.id)
                             left join account_analytic_account aaa ON (aal.account_id=aaa.id)
                             left join grp_dimension_multiproposito dm ON (aal.dim_multi_id=dm.id)
                        WHERE %s AND aal.general_account_id = %%s and (d.name is not null or aaa.name is not null or dm.name is not null)
                        GROUP BY d.id, aaa.id, dm.id """ % (sign, query_where)
        elif data['form']['display_org_unit_column'] and data['form']['display_analytic_acc_column']:
            _sql = """  SELECT d.name as org_unit,
                               aaa.name as analytic_acc,
                               sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) as debit,
                               sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END) as credit,
                               (sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) - sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END)) * %s as balance
                        FROM account_analytic_line aal
                             inner join account_move_line l on (aal.move_id=l.id)
                             left join hr_department d ON (aal.hr_department_id=d.id)
                             left join account_analytic_account aaa ON (aal.account_id=aaa.id)
                        WHERE %s AND aal.general_account_id = %%s and (d.name is not null or aaa.name is not null)
                        GROUP BY d.id, aaa.id """ % (sign, query_where)
        elif data['form']['display_org_unit_column'] and data['form']['display_multiprop_column']:
            _sql = """  SELECT d.name as org_unit,
                               dm.name as multiprop,
                               sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) as debit,
                               sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END) as credit,
                               (sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) - sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END)) * %s as balance
                        FROM account_analytic_line aal
                             inner join account_move_line l on (aal.move_id=l.id)
                             left join hr_department d ON (aal.hr_department_id=d.id)
                             left join grp_dimension_multiproposito dm ON (aal.dim_multi_id=dm.id)
                        WHERE %s AND aal.general_account_id = %%s and (d.name is not null or dm.name is not null)
                        GROUP BY d.id, dm.id """ % (sign, query_where)
        elif data['form']['display_analytic_acc_column'] and data['form']['display_multiprop_column']:
            _sql = """  SELECT aaa.name as analytic_acc,
                               dm.name as multiprop,
                               sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) as debit,
                               sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END) as credit,
                               (sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) - sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END)) * %s as balance
                        FROM account_analytic_line aal
                             inner join account_move_line l on (aal.move_id=l.id)
                             left join account_analytic_account aaa ON (aal.account_id=aaa.id)
                             left join grp_dimension_multiproposito dm ON (aal.dim_multi_id=dm.id)
                        WHERE %s AND aal.general_account_id = %%s and (aaa.name is not null or dm.name is not null)
                        GROUP BY aaa.id, dm.id """ % (sign, query_where)
        elif data['form']['display_org_unit_column']:
            _sql = """  SELECT d.name as org_unit,
                               sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) as debit,
                               sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END) as credit,
                               (sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) - sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END)) * %s as balance
                        FROM account_analytic_line aal
                             inner join account_move_line l on (aal.move_id=l.id)
                             left join hr_department d ON (aal.hr_department_id=d.id)
                        WHERE %s AND aal.general_account_id = %%s and d.name is not null
                        GROUP BY d.id """ % (sign, query_where)
        elif data['form']['display_analytic_acc_column']:
            _sql = """  SELECT aaa.name as analytic_acc,
                               sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) as debit,
                               sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END) as credit,
                               (sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) - sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END)) * %s as balance
                        FROM account_analytic_line aal
                             inner join account_move_line l on (aal.move_id=l.id)
                             left join account_analytic_account aaa ON (aal.account_id=aaa.id)
                        WHERE %s AND aal.general_account_id = %%s and aaa.name is not null
                        GROUP BY aaa.id """ % (sign, query_where)
        elif data['form']['display_multiprop_column']:
            _sql = """  SELECT dm.name as multiprop,
                               sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) as debit,
                               sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END) as credit,
                               (sum(CASE WHEN aal.amount < 0 THEN -aal.amount ELSE 0 END) - sum(CASE WHEN aal.amount > 0 THEN aal.amount ELSE 0 END)) * %s as balance
                        FROM account_analytic_line aal
                             inner join account_move_line l on (aal.move_id=l.id)
                             left join grp_dimension_multiproposito dm ON (aal.dim_multi_id=dm.id)
                        WHERE %s AND aal.general_account_id = %%s and dm.name is not null
                        GROUP BY dm.id """ % (sign, query_where)
        else:
            return []

        self.cr.execute(_sql, (account_id,))
        return self.cr.dictfetchall()

