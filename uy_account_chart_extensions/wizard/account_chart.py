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
from datetime import datetime
from openerp import api
import time

class account_chart(osv.osv_memory):
    _inherit = "account.chart"

    _columns = {
        'include_initial_bal': fields.boolean('Include initial balance'),
        'range_dates': fields.boolean('Range of dates'),
        'date_from': fields.date("Start Date"),
        'date_to': fields.date("End Date"),
    }

    _defaults = {
        'include_initial_bal': True,
        'date_from': time.strftime('%Y-01-01'),
        'date_to': time.strftime('%Y-%m-%d'),
    }

    def account_chart_open_window(self, cr, uid, ids, context=None):
        result = super(account_chart, self).account_chart_open_window(cr, uid, ids, context=context)
        ctx = eval(result.get('context', '{}'))
        data = self.read(cr, uid, ids, context=context)[0]
        if data['range_dates'] and data['date_from'] and data['date_to']:
            result.pop('periods', None)
            ctx.pop('periods', None)
            ctx.pop('period_from', None)
            ctx.pop('period_to', None)
            ctx.update({ 'date_from': data['date_from'], 'date_to': data['date_to'], 'range_dates': True })
            lang_code = self.pool.get('res.users').browse(cr, uid, uid).lang
            lang_obj = self.pool.get('res.lang')
            lang_id = lang_obj.search(cr, uid, [('code','=',lang_code)])[0]
            date_format = lang_obj.browse(cr, uid, lang_id).date_format
            date_start = datetime.strptime(data['date_from'], "%Y-%m-%d").strftime(date_format)
            date_end = datetime.strptime(data['date_to'], "%Y-%m-%d").strftime(date_format)
            range_str = " (" + date_start + " - " + date_end + ")"
            result['name'] += range_str
        elif data['period_from'] and data['period_to']:
            ctx.update({ 'period_from': data['period_from'][0],
                         'period_to': data['period_to'][0],
                         'periods': self.pool.get('account.period').build_ctx_periods(cr, uid, data['period_from'][0], data['period_to'][0]) })
            range_str = " (" + data['period_from'][1] + " - " + data['period_to'][1] + ")"
            result['name'] += range_str

        if ctx.get('state', False) == 'posted':
            ctx['search_default_posted'] = True
        ctx['include_initial_bal'] = data.get('include_initial_bal', False)
        domain_fields = self.build_ctx_domain_fields(cr, uid, ctx)
        ctx.update({'domain_periods': domain_fields[0], 'domain_date_from': domain_fields[1], 'domain_date_to': domain_fields[2]})
        ctx['from_account_chart'] = True
        result['context'] = str(ctx)
        return result

    def build_ctx_domain_fields(self, cr, uid, context):
        period_obj = self.pool.get('account.period')
        all_periods = period_obj.search(cr, uid, [], order='date_start')
        if context.get('periods', False):
            domain_periods = context['periods']
        else:
            domain_periods = all_periods # all periods
        if context.get('date_from', False) and context.get('date_to', False):
            domain_date_from = context['date_from']
            domain_date_to = context['date_to']
        else:
            if not all_periods: # should not enter here
                domain_date_from = time.strftime("%Y-01-01")
                domain_date_to = time.strftime("%Y-%m-%d")
            else:
                first_period = period_obj.browse(cr, uid, all_periods[0])
                domain_date_from = first_period.date_start
                last_period =  period_obj.browse(cr, uid, all_periods[-1])
                domain_date_to = last_period.date_stop
        return domain_periods, domain_date_from, domain_date_to

    @api.onchange('period_from','period_to')
    def onchange_periods(self):
        if self.period_from:
            self.date_from = self.period_from.date_start
        if self.period_to:
            self.date_to = self.period_to.date_stop
