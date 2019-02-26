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

from openerp.osv import osv
from openerp.addons.account.report.account_financial_report \
    import report_account_common

class report_account_common_ext(report_account_common):

    def set_context(self, objects, data, ids, report_type=None):
        self.localcontext.update({
            'display_multiprop_column': data.get('form', {}).get('display_multiprop_column', False),
            'display_org_unit_column': data.get('form', {}).get('display_org_unit_column', False),
            'display_analytic_acc_column': data.get('form', {}).get('display_analytic_acc_column', False),
            'get_dimensions_data': self.get_dimensions_data,
        })
        return super(report_account_common_ext, self).set_context(objects, data, ids, report_type=report_type)

    def get_dimensions_data(self, data, line, company):
        account_code = line.get('name','').split(' ')[0]
        if not account_code:
            return []
        account_obj = self.pool.get('account.account')
        account_ids = account_obj.search(self.cr, self.uid, [('code','=',account_code),('company_id','=',company.id)])
        account_id = account_ids and account_ids[0] or False
        if not account_id:
            return []

        sign = 1
        if 'debit' not in line or 'credit' not in line:
            account = account_obj.browse(self.cr, self.uid, account_id, context=data['form']['used_context'])
            debit = account.debit
            credit = account.credit
        else:
            debit = line.get('debit')
            credit = line.get('credit')
        if self.formatLang(debit - credit, currency_obj=company.currency_id) == self.formatLang(-1 * line.get('balance', 0.0), currency_obj=company.currency_id):
            sign = -1

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


class report_financial(osv.AbstractModel):
    _name = 'report.account.report_financial'
    _inherit = 'report.abstract_report'
    _template = 'account.report_financial'
    _wrapped_report_class = report_account_common_ext

