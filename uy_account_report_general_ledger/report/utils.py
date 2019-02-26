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

def compute_amounts_in_currency(self, cr, uid, amount, from_currency_id=None, to_currency_id=None, date=None, context=None):
    """ Computes the amounts in the currency and date given by parameters and rate options through context """
    currency_obj = self.pool.get('res.currency')
    if not to_currency_id:
        alternative_curr_ids = currency_obj.search(cr, uid, [('alt_currency','=',True)])
        to_currency_id = alternative_curr_ids and alternative_curr_ids[0] or False
    if not to_currency_id:
        return 0.0
    if not context or context.get('curr_rate_option', False) in ('trans_date','set_date'):
        if not from_currency_id:
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            from_currency_id = user.company_id.currency_id.id
        context = context or {}
        ctx = context.copy()
        if date and (not context or context.get('curr_rate_option', False)=='trans_date'):
            ctx['date'] = date
        if context.get('curr_rate_option', False)=='set_date' and context.get('curr_rate_date', False):
            ctx['date'] = context['curr_rate_date']
        return currency_obj.compute(cr, uid, from_currency_id, to_currency_id, amount, context=ctx)
    if context and context.get('curr_rate_option', False)=='set_curr_rate':
        return currency_obj.compute(cr, uid, to_currency_id, to_currency_id, amount * (context.get('curr_rate', False) or 0.0))
    return 0.0

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
