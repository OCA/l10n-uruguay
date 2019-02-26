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

from openerp.osv import fields, orm

class AccountReportOpenInvoicesWizard(orm.TransientModel):
    _inherit = "open.invoices.webkit"

    _columns = {
        'filter_currency_id': fields.many2one('res.currency', 'Filter by currency'),
        'only_residual_amount': fields.boolean('Display only residual amount', default=True),
        'display_curr_columns': fields.boolean('Display columns secundary currency', default=True),
    }

    def pre_print_report(self, cr, uid, ids, data, context=None):
        data = super(AccountReportOpenInvoicesWizard, self).pre_print_report(
            cr, uid, ids, data, context)
        vals = self.read(cr, uid, ids,
                         ['filter_currency_id', 'display_curr_columns', 'only_residual_amount'],
                         context=context)[0]
        data['form'].update(vals)
        return data

    def _print_report(self, cr, uid, ids, data, context=None):
        context = context or {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'account.account_report_open_invoices_xls_ext',
                    'datas': data}
        else:
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'account.account_report_open_invoices_webkit_ext',
                    'datas': data}
