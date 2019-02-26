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

class res_currency(osv.osv):
    _inherit = "res.currency"

    _columns = {
        'alt_currency': fields.boolean('Alternative currency in reports'),
    }

    def create(self, cr, uid, vals, context=None):
        if vals.get('alt_currency', False):
            alt_curr_ids = self.search(cr, uid, [('alt_currency','=',True)])
            if alt_curr_ids:
                cr.execute('UPDATE res_currency SET alt_currency = false where id in %s',(tuple(alt_curr_ids),))
        return super(res_currency, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if vals.get('alt_currency', False):
            alt_curr_ids = self.search(cr, uid, [('alt_currency','=',True),('id','not in',ids)])
            if alt_curr_ids:
                cr.execute('UPDATE res_currency SET alt_currency = false where id in %s',(tuple(alt_curr_ids),))
        return super(res_currency, self).write(cr, uid, ids, vals, context=context)

    def init_set_alternative_currency(self, cr, uid, **args):
        _ids = self.search(cr, uid, [('alt_currency','=',True)])
        if not _ids:
            usd_ids = self.search(cr, uid, [('name','=','USD')])
            if usd_ids:
                self.write(cr, uid, usd_ids, { 'alt_currency': True })
        return True
