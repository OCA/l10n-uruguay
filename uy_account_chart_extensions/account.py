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

from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
from openerp import models, api, fields as fields2
import time

class account_account(osv.osv):
    _inherit = "account.account"

    def __compute_all(self, cr, uid, ids, field_names, arg=None, context=None,
                  query='', query_params=()):
        """ compute the balance, debit and credit expressed in the secundary currency
        for the provided account ids
        Arguments:
        `ids`: account ids
        `field_names`: the fields to compute (a list of any of
                       'curr_balance', 'curr_debit' and 'curr_credit')
        `query`: additional query filter (as a string)
        `query_params`: parameters for the provided query string as a tuple
        """
        mapping = {
            'curr_balance': "COALESCE(SUM(l.curr_debit),0) - COALESCE(SUM(l.curr_credit), 0) as curr_balance",
            'curr_debit': "COALESCE(SUM(l.curr_debit), 0) as curr_debit",
            'curr_credit': "COALESCE(SUM(l.curr_credit), 0) as curr_credit",
        }
        #get all the necessary accounts
        children_and_consolidated = self._get_children_and_consol(cr, uid, ids, context=context)
        #compute for each account the balance/debit/credit expressed in the Secundary Currency from the move lines
        accounts = {}
        res = {}
        null_result = dict((fn, 0.0) for fn in field_names)
        if children_and_consolidated:
            context = dict(context or {}, initial_bal=False)
            if (context.get('period_from', False) and context.get('period_to', False)) \
                   and not context.get('periods', False):
                    context['periods'] = self.pool.get('account.period').build_ctx_periods(cr, uid, context['period_from'], context['period_to'])

            aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)

            wheres = [""]
            if query.strip():
                wheres.append(query.strip())
            if aml_query.strip():
                wheres.append(aml_query.strip())
            filters = " AND ".join(wheres)

            request = ("SELECT l.account_id as id, " +\
                       ', '.join(mapping.values()) +
                       " FROM account_move_line l" \
                       " WHERE l.account_id IN %s " \
                            + filters +
                       " GROUP BY l.account_id")
            params = (tuple(children_and_consolidated),) + query_params
            cr.execute(request, params)

            for row in cr.dictfetchall():
                accounts[row['id']] = row

            # initial balance
            # checking context has enough arguments to compute initial balance
            if context.get('periods', False) or \
               (context.get('period_from', False) and context.get('period_to', False)) or \
               (context.get('date_from', False) and context.get('date_to', False)):

                mapping2 = {
                    'initial_balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as initial_balance",
                    'curr_initial_balance': "COALESCE(SUM(l.curr_debit),0) - COALESCE(SUM(l.curr_credit), 0) as curr_initial_balance",
                }
                ctx = context.copy()
                ctx['initial_bal'] = True

                aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=ctx)

                wheres = [""]
                if query.strip():
                    wheres.append(query.strip())
                if aml_query.strip():
                    wheres.append(aml_query.strip())
                filters = " AND ".join(wheres)

                request = ("SELECT l.account_id as id, " +\
                           ', '.join(mapping2.values()) +
                           " FROM account_move_line l" \
                           " WHERE l.account_id IN %s " \
                                + filters +
                           " GROUP BY l.account_id")
                cr.execute(request, params)

                for row in cr.dictfetchall():
                    if row['id'] in accounts:
                        accounts[row['id']].update(row)
                    else:
                        accounts[row['id']] = row

            # consolidate accounts with direct children
            children_and_consolidated.reverse()
            brs = list(self.browse(cr, uid, children_and_consolidated, context=context))
            sums = {}
            while brs:
                current = brs.pop(0)
                for fn in field_names:
                    sums.setdefault(current.id, {})[fn] = accounts.get(current.id, {}).get(fn, 0.0)
                    for child in current.child_id:
                        sums[current.id][fn] += sums[child.id][fn]

            for id in ids:
                res[id] = sums.get(id, null_result)
        else:
            for id in ids:
                res[id] = null_result

        return res

    _columns = {
        'curr_balance': fields.function(__compute_all, type="float", digits_compute=dp.get_precision('Account'), string='Balance %s', multi='_curr_balance'),
        'curr_credit': fields.function(__compute_all, type="float", digits_compute=dp.get_precision('Account'), string='Credit %s', multi='_curr_balance'),
        'curr_debit': fields.function(__compute_all, type="float", digits_compute=dp.get_precision('Account'), string='Debit %s', multi='_curr_balance'),
        'initial_balance': fields.function(__compute_all, type="float", digits_compute=dp.get_precision('Account'), string='Initial balance', multi='_curr_balance'),
        'curr_initial_balance': fields.function(__compute_all, type="float", digits_compute=dp.get_precision('Account'), string='Initial balance %s', multi='_curr_balance'),
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(account_account, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        currency_obj = self.pool.get('res.currency')
        alt_curr_ids = currency_obj.search(cr, uid, [('alt_currency','=',True)])
        alt_curr_id = alt_curr_ids and alt_curr_ids[0] or False
        if alt_curr_id:
            alt_curr_name = currency_obj.read(cr, uid, alt_curr_id, ['name'], context=context)['name']
            for field in res['fields']:
                if  field.startswith('curr_'):
                    res['fields'][field]['string'] = res['fields'][field]['string'].replace('%s', alt_curr_name)
        return res

class Account(models.Model):
    _inherit = "account.account"

    @api.one
    def _compute_balance_incl(self):
        initial_balance = self.initial_balance
        self.debit_incl = self.debit
        self.credit_incl = self.credit
        if initial_balance > 0:
            self.debit_incl += initial_balance
        else:
            self.credit_incl += abs(initial_balance)
        balance = self.balance
        self.balance_incl = balance + initial_balance

        curr_initial_balance = self.curr_initial_balance
        self.curr_debit_incl = self.curr_debit
        self.curr_credit_incl = self.curr_credit
        if curr_initial_balance > 0:
            self.curr_debit_incl += curr_initial_balance
        else:
            self.curr_credit_incl += abs(curr_initial_balance)
        self.curr_balance_incl = self.curr_balance + curr_initial_balance

        date_conversion = time.strftime("%Y-%m-%d")
        if self._context and self._context.get('date_to', False):
            date_conversion = self._context['date_to']
        elif self._context and self._context.get('period_to', False):
            date_conversion = self.env['account.period'].browse(self._context['period_to']).date_stop
        from_currency = self.env.user.company_id.currency_id.with_context(date=date_conversion)
        to_currency = self.env['res.currency'].search([('alt_currency','=',True)])
        self.curr_bal_end_period = 0.0
        if to_currency:
            self.curr_bal_end_period = from_currency.compute(balance, to_currency)
        if self._context and self._context.get('include_initial_bal', False):
            self.curr_bal_end_period += curr_initial_balance

    debit_incl = fields2.Float(string="Debit", digits=dp.get_precision('Account'), compute="_compute_balance_incl", readonly=True, store=False, help="Debit with initial balance included")
    credit_incl = fields2.Float(string="Credit", digits=dp.get_precision('Account'), compute="_compute_balance_incl", readonly=True, store=False, help="Credit with initial balance included")
    balance_incl = fields2.Float(string="Balance", digits=dp.get_precision('Account'), compute="_compute_balance_incl", readonly=True, store=False, help="Balance with initial balance included")

    curr_debit_incl = fields2.Float(string="Debit %s", digits=dp.get_precision('Account'), compute="_compute_balance_incl", readonly=True, store=False,  help="Debit secundary currency with initial balance included")
    curr_credit_incl = fields2.Float(string="Credit %s", digits=dp.get_precision('Account'), compute="_compute_balance_incl", readonly=True, store=False,  help="Credit secundary currency with initial balance included")
    curr_balance_incl = fields2.Float(string="Balance %s", digits=dp.get_precision('Account'), compute="_compute_balance_incl", readonly=True, store=False,  help="Balance secundary currency with initial balance included")

    curr_bal_end_period = fields2.Float(string="Balance %s End of Period", digits=dp.get_precision('Account'), compute="_compute_balance_incl", readonly=True, store=False)
