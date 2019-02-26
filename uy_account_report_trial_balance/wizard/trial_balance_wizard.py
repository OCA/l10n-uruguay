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

from openerp.osv import orm, osv, fields
import time
from openerp.tools.translate import _

class trial_balance_webkit_wizard(orm.TransientModel):
    _inherit = 'trial.balance.webkit'

    _columns = {
        'display_accounts': fields.selection([('movement','With movements'),
                                            ('not_zero','With balance not equal to 0'),
                                            ],'Display Accounts', required=False),
        # Secundary currency rate options
        'display_curr_columns': fields.boolean('Display columns secundary currency'),
        'curr_rate_option': fields.selection([ ('trans_date', 'Tipo de cambio según fecha de la transacción'),
                                               ('set_date', 'Tipo de cambio según una fecha dada'),
                                               ('set_curr_rate', 'Otro tipo de cambio')], 'Opciones de tipo de cambio'),
        'curr_rate_date': fields.date('Fecha'),
        'curr_rate': fields.float('Tipo de cambio'),
        # Financial report fields
        'financial_report': fields.boolean('Financial report (Excel)'),
        'account_report_id': fields.many2one('account.financial.report', 'Account Reports'),
    }

    _defaults = {
        'display_curr_columns': True,
        'curr_rate_option': 'trans_date',
        'curr_rate_date': time.strftime("%Y-%m-%d"),
    }

    def pre_print_report(self, cr, uid, ids, data, context=None):
        data = super(trial_balance_webkit_wizard, self).pre_print_report(
            cr, uid, ids, data, context)
        vals = self.read(cr, uid, ids,
                         ['display_accounts','display_curr_columns','curr_rate_option','curr_rate_date','curr_rate','financial_report','account_report_id'],
                         context=context)[0]
        data.get('form',{}).update(vals)
        return data

    def _print_report(self, cr, uid, ids, data, context=None):
        context = context or {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        if context.get('xls_export'):
            report_name = 'account.account_report_trial_balance_xls_ext'
            if data.get('form',{}).get('financial_report', False):
                report_name = 'account.account_financial_report_xls'
                if data.get('form',{}).get('filter', False)=='filter_opening' \
                   or data.get('form',{}).get('comp0_filter', False)=='filter_opening' \
                   or data.get('form',{}).get('comp1_filter', False)=='filter_opening' \
                   or data.get('form',{}).get('comp2_filter', False)=='filter_opening':
                    raise osv.except_osv("Error", _("Filtering or comparing by 'Only opening' is not available for financial reports."))
            return { 'type': 'ir.actions.report.xml',
                     'report_name': report_name,
                     'datas': data }
        if data.get('form',{}).get('financial_report', False):
            raise osv.except_osv("Error", _("Financial report is only available in excel format. For obtain it in pdf format you should go to the menu 'Financial report'."))
        return { 'type': 'ir.actions.report.xml',
                 'report_name': 'account.account_report_trial_balance_webkit_ext',
                 'datas': data }
