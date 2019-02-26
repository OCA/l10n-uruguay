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
from openerp.tools.translate import _
from openerp import models, api, fields as fields2
from openerp.tools import float_round
from lxml import etree

LINES_INIT_BAL = {}

class account_move_line(osv.osv):
    _inherit = "account.move.line"

    def _curr_debit_credit(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        if context is None:
            context = {}
        currency_obj = self.pool.get('res.currency')
        alt_curr_ids = currency_obj.search(cr, uid, [('alt_currency','=',True)])
        alt_curr_id = alt_curr_ids and alt_curr_ids[0] or False
        ctx = context.copy()
        for move_line in self.browse(cr, uid, ids, context=context):
            res[move_line.id] = {
                'curr_debit': 0.0,
                'curr_credit': 0.0,
            }
            if alt_curr_id:
                ml_currency_id = move_line.currency_id and move_line.currency_id.id or False
                if ml_currency_id==alt_curr_id:
                    res[move_line.id].update({
                        'curr_debit': move_line.debit > 0 and abs(move_line.amount_currency) or 0.0,
                        'curr_credit': move_line.credit > 0 and abs(move_line.amount_currency) or 0.0,
                    })
                else:
                    ctx['date'] = move_line.date
                    res[move_line.id].update({
                        'curr_debit': currency_obj.compute(cr, uid, move_line.company_id.currency_id.id, alt_curr_id, move_line.debit, round=False, context=ctx),
                        'curr_credit': currency_obj.compute(cr, uid, move_line.company_id.currency_id.id, alt_curr_id, move_line.credit, round=False, context=ctx),
                    })
        return res

    @api.one
    @api.depends('currency_id')
    def _transaction_currency(self):
        if self.currency_id:
            self.transaction_curr_id = self.currency_id.id
        else:
            self.transaction_curr_id = self.company_id.currency_id.id

    _columns = {
        'curr_debit': fields.function(_curr_debit_credit, type="float", digits_compute=dp.get_precision('Account'), string='Debit %s', multi='debit_credit', help="Debit in Secundary Currency",
                                    store = { 'account.move.line': (lambda self, cr, uid, ids, c=None: ids, ['debit', 'currency_id', 'amount_currency'], 20),
                                              'res.currency': (lambda self, cr, uid, ids, c=None: self.pool['account.move.line'].search(cr, uid, []), ['alt_currency'], 20), }),
        'curr_credit': fields.function(_curr_debit_credit, type="float", digits_compute=dp.get_precision('Account'), string='Credit %s', multi='debit_credit', help="Credit in Secundary Currency",
                                    store = { 'account.move.line': (lambda self, cr, uid, ids, c=None: ids, ['credit', 'currency_id', 'amount_currency'], 20),
                                              'res.currency': (lambda self, cr, uid, ids, c=None: self.pool['account.move.line'].search(cr, uid, []), ['alt_currency'], 20), }),
        'transaction_curr_id': fields.many2one('res.currency', 'Transaction currency', compute="_transaction_currency", readonly=True, help="Currency of this transaction."),
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(account_move_line, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        currency_obj = self.pool.get('res.currency')
        alt_curr_ids = currency_obj.search(cr, uid, [('alt_currency','=',True)])
        alt_curr_id = alt_curr_ids and alt_curr_ids[0] or False
        if alt_curr_id:
            alt_curr_name = currency_obj.read(cr, uid, alt_curr_id, ['name'], context=context)['name']
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        for field in res['fields']:
            if alt_curr_id and field.startswith('curr_'):
                res['fields'][field]['string'] = res['fields'][field]['string'].replace('%s', alt_curr_name)
            if field == 'initial_bal':
                res['fields'][field]['digits'] = (16, precision)
            if field == 'curr_initial_bal':
                res['fields'][field]['digits'] = (16, precision)
        if not context.get('show_curr_debit_credit', False):
            res['fields'].pop('curr_debit', None)
            res['fields'].pop('curr_credit', None)
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='curr_debit']"):
                node.getparent().remove(node)
            for node in doc.xpath("//field[@name='curr_credit']"):
                node.getparent().remove(node)
            res['arch'] = etree.tostring(doc)
        return res

    def open_account_move(self, cr, uid, ids, context=None):
        context = context or {}
        row = self.browse(cr, uid, ids, context=context)[0]
        return {
                'type' : 'ir.actions.act_window',
                'name' :  _('Journal Entry'),
                'res_model': 'account.move',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'current',
                'res_id': row.move_id.id,
                'context': str(context)
        }

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        context = context or {}
        res = super(account_move_line, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        if context.get('include_initial_bal', False) and ('initial_bal' in fields or 'curr_initial_bal' in fields):
            precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
            for line in res:
                lines = self.search(cr, uid, line.get('__domain', domain), context=context)
                lines_rec = self.browse(cr, uid, lines, context=context)
                if 'initial_bal' in fields:
                    line['initial_bal'] = sum(line_rec.initial_bal for line_rec in lines_rec)
                    line['initial_bal'] = float_round(line['initial_bal'], precision_digits=precision)
                if 'curr_initial_bal' in fields:
                    line['curr_initial_bal'] = sum(line_rec.curr_initial_bal for line_rec in lines_rec)
                    line['curr_initial_bal'] = float_round(line['curr_initial_bal'], precision_digits=precision)
        return res

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.one
    @api.depends('date', 'debit', 'credit', 'curr_debit', 'curr_credit', 'account_id')
    def _compute_initial_bal(self):
        self.initial_bal = 0.0
        self.curr_initial_bal = 0.0
        context = dict(self._context or {})
        if context.get('from_account_chart', False) and context.get('include_initial_bal', False) and self.account_id:
            if self.account_id.id in LINES_INIT_BAL and self.id in LINES_INIT_BAL[self.account_id.id]:
                self.initial_bal = LINES_INIT_BAL[self.account_id.id][self.id][0]
                self.curr_initial_bal = LINES_INIT_BAL[self.account_id.id][self.id][1]
            else:
                # update context and build domain from context
                domain = [('account_id','=',self.account_id.id)]
                if not context.get('range_dates', False):
                    if context.get('domain_periods', False):
                        domain += [('period_id','in',context.get('domain_periods'))]
                        context.update({'periods': context.get('domain_periods') })
                else:
                    if context.get('domain_date_from', False) and context.get('domain_date_to', False):
                        domain += [('date','>=',context.get('domain_date_from')),('date','<=',context.get('domain_date_to'))]
                        context.update({'date_from': context.get('domain_date_from'), 'date_to': context.get('domain_date_to')})
                if context.get('state', False) and context['state'] not in ['all']:
                    domain.append(('move_id.state','=',context['state']))

                # Check context has enough arguments to compute initial balance
                if context.get('periods', False) or \
                   (context.get('period_from', False) and context.get('period_to', False)) or \
                   (context.get('date_from', False) and context.get('date_to', False)):

                    if (context.get('period_from', False) and context.get('period_to', False)) \
                       and not context.get('periods', False):
                        context['periods'] = self.pool.get('account.period').build_ctx_periods(self._cr, self._uid, context['period_from'], context['period_to'])

                    if self.account_id.id not in LINES_INIT_BAL:
                        LINES_INIT_BAL[self.account_id.id] = {}

                    context['initial_bal'] = True
                    sql = """SELECT l1.id, COALESCE(SUM(l2.debit-l2.credit), 0), COALESCE(SUM(l2.curr_debit-l2.curr_credit), 0)
                                FROM account_move_line l1 LEFT JOIN account_move_line l2
                                ON (l1.account_id = l2.account_id
                                  AND l2.id < l1.id
                                  AND """ + \
                            self.pool.get('account.move.line')._query_get(self._cr, self._uid, obj='l2', context=context) + \
                            ") WHERE l1.id = %s GROUP BY l1.id"

                    lines = self.search(domain)
                    account_bal = 0.0
                    account_curr_bal = 0.0

                    no_init_bal_sum = 0.0
                    no_init_curr_bal_sum = 0.0
                    w_init_bal_count = 0
                    w_init_curr_bal_count = 0

                    for line in lines:
                        account_bal += line.debit - line.credit
                        account_curr_bal += line.curr_debit - line.curr_credit

                        self._cr.execute(sql, (line.id,))
                        res = self._cr.fetchone()
                        initial_bal = res and res[1] or False
                        curr_initial_bal = res and res[2] or False

                        if not initial_bal:
                            no_init_bal_sum += (line.debit - line.credit)
                        else:
                            w_init_bal_count += 1

                        if not curr_initial_bal:
                            no_init_curr_bal_sum += (line.curr_debit - line.curr_credit)
                        else:
                            w_init_curr_bal_count += 1

                    bal_part = no_init_bal_sum / w_init_bal_count if w_init_bal_count else 0.0
                    curr_bal_part = no_init_curr_bal_sum / w_init_curr_bal_count if w_init_curr_bal_count else 0.0

                    for line in lines:
                        self._cr.execute(sql, (line.id,))
                        res = self._cr.fetchone()
                        initial_bal = res and res[1] or 0.0
                        curr_initial_bal = res and res[2] or 0.0

                        LINES_INIT_BAL[line.account_id.id][line.id] = []

                        if initial_bal:
                            ib = ((line.debit - line.credit + bal_part) / account_bal) * initial_bal
                            if line.id == self.id:
                                self.initial_bal = ib
                            LINES_INIT_BAL[line.account_id.id][line.id].append(ib)
                        else:
                            LINES_INIT_BAL[line.account_id.id][line.id].append(0.0)

                        if curr_initial_bal:
                            cib = ((line.curr_debit - line.curr_credit + curr_bal_part) / account_curr_bal) * curr_initial_bal
                            if line.id == self.id:
                                self.curr_initial_bal = cib
                            LINES_INIT_BAL[line.account_id.id][line.id].append(cib)
                        else:
                            LINES_INIT_BAL[line.account_id.id][line.id].append(0.0)

    initial_bal = fields2.Float(string="Initial balance", digits=(16,6), compute="_compute_initial_bal", readonly=True, store=False)
    curr_initial_bal = fields2.Float(string="Initial balance %s", digits=(16,6), compute="_compute_initial_bal", readonly=True, store=False)
