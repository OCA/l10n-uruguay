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

class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'

    def get_currency_rate_line(self, cr, uid, st_line, currency_diff, move_id, context=None):
        move_line = super(account_bank_statement_line, self).get_currency_rate_line(cr, uid, st_line, currency_diff, move_id, context=context)
        move_line.update({'change_diff': True})
        return move_line

class account_voucher(osv.osv):
    _inherit = 'account.voucher'

    def _get_exchange_lines(self, cr, uid, line, move_id, amount_residual, company_currency, current_currency, context=None):
        move_line, move_line_counterpart = super(account_voucher, self)._get_exchange_lines(cr, uid, line, move_id,
                                                amount_residual, company_currency, current_currency, context=context)
        move_line.update({'change_diff': True})
        move_line_counterpart.update({'change_diff': True})
        return move_line, move_line_counterpart

class account_move_line(osv.osv):
    _inherit = "account.move.line"

    _columns = {
        'change_diff': fields.boolean('Change difference'),
    }
