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

from openerp import models, fields, api


class GrpExtractoBancario(models.Model):
    _inherit = 'account.bank.statement'

    expense_amount = fields.Float(u"Total de gastos", compute = '_compute_expense_amount', store=True)

    @api.multi
    @api.depends('line_ids','line_ids.amount')
    def _compute_expense_amount(self):
        for rec in self:
            rec.expense_amount = sum(rec.line_ids.filtered(lambda a: a.amount < 0).mapped('amount'))

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    concepto_editable = fields.Boolean('Es editable el concepto', compute='_compute_concepto_editable')

    @api.multi
    @api.depends('state')
    def _compute_concepto_editable(self):
        user_has_contabilidad_tesoreria_group = self.env['res.users'].has_group(
            'grp_tesoreria.group_grp_contabilidad_tesoreria')
        for rec in self:
            rec.concepto_editable = rec.state in ['open', False] or (
                        rec.state == 'revisado' and user_has_contabilidad_tesoreria_group)