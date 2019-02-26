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

from openerp import models, api, fields

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.one
    @api.depends('journal_id', 'period_id')
    def _compute_journal_period(self):
        if self.journal_id and self.period_id:
            #TODO: Validate that exists an account.journal.period record ??
            self.journal_period = self.journal_id.name + " - " + self.period_id.name

    journal_period = fields.Char(string="Journal Period", compute="_compute_journal_period", readonly=True, store=True)
