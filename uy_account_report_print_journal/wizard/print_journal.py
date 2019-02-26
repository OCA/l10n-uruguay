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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class AccountReportPrintJournalWizard(osv.osv_memory):
    _inherit = "print.journal.webkit"

    _columns = {
        'gb_journal_period': fields.boolean("Group by Journal-Period", default=True),
        'gb_period': fields.boolean("Group by Period", default=True),
        'order_period': fields.selection([('asc', 'Ascendent'),('desc', 'Descendant')], 'Period order', default='asc'),
    }

    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear_id, context=None):
        return self.onchange_filter(cr, uid, ids, filter='filter_period', fiscalyear_id=fiscalyear_id, context=context)

    def visualize_report(self, cr, uid, ids, context=None):
        context = context or {}
        row = self.browse(cr, uid, ids[0], context=context)
        if row.amount_currency:
            context['currency'] = True
        if row.target_move == 'posted':
            context['search_default_posted'] = True
        if row.gb_journal_period:
            context['search_default_gb_journal_period'] = True
        elif row.gb_period:
            context['search_default_gb_period'] = True

        journal_ids = [ j.id for j in row.journal_ids ]
        period_ids = self.pool.get('account.period').build_ctx_periods(cr, uid, row.period_from.id, row.period_to.id)
        domain = [('period_id','in',period_ids),('journal_id','in',journal_ids)]

        mod_obj = self.pool.get('ir.model.data')
        tree_view = mod_obj.get_object_reference(cr, uid, 'uy_account_report_print_journal', 'view_rpt_print_journal_move_line_tree')
        form_view = mod_obj.get_object_reference(cr, uid, 'account', 'view_move_line_form')
        return {
                'type' : 'ir.actions.act_window',
                'name' :  _('Journals Report'),
                'res_model': 'account.move.line',
                'view_id': False,
                'views': [(tree_view[1],'tree'),(form_view[1],'form')],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'target': 'current',
                'domain': str(domain),
                'context': str(context)
        }

    def pre_print_report(self, cr, uid, ids, data, context=None):
        data = super(AccountReportPrintJournalWizard, self).pre_print_report(cr, uid, ids, data, context=context)
        vals = self.read(cr, uid, ids, ['gb_journal_period', 'gb_period', 'order_period'], context=context)[0]
        data['form'].update(vals)
        return data

    def _print_report(self, cr, uid, ids, data, context=None):
        context = context or {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        return {'type': 'ir.actions.report.xml',
                'report_name': 'account.account_report_print_journal_webkit_ext',
                'datas': data}
