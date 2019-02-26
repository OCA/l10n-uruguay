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
# TODO: C SPRING 13 GAP 494
from openerp import models, fields, api, exceptions, _
from openerp import tools


class GrpAccountEntriesReport(models.Model):
    _name = "account.entries.report"
    _inherit = "account.entries.report"

    operating_unit_id = fields.Many2one('operating.unit', string=u'Unidad ejecutora')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_entries_report')
        cr.execute("""
            create or replace view account_entries_report as (
            select
                l.id as id,
                am.date as date,
                l.date_maturity as date_maturity,
                l.date_created as date_created,
                am.ref as ref,
                am.state as move_state,
                l.state as move_line_state,
                l.reconcile_id as reconcile_id,
                l.partner_id as partner_id,
                l.product_id as product_id,
                l.product_uom_id as product_uom_id,
                am.company_id as company_id,
                am.journal_id as journal_id,
                p.fiscalyear_id as fiscalyear_id,
                am.period_id as period_id,
                am.operating_unit_id as operating_unit_id,
                l.account_id as account_id,
                l.analytic_account_id as analytic_account_id,
                a.type as type,
                a.user_type as user_type,
                1 as nbr,
                l.quantity as quantity,
                l.currency_id as currency_id,
                l.amount_currency as amount_currency,
                l.debit as debit,
                l.credit as credit,
                coalesce(l.debit, 0.0) - coalesce(l.credit, 0.0) as balance
            from
                account_move_line l
                left join account_account a on (l.account_id = a.id)
                left join account_move am on (am.id=l.move_id)
                left join account_period p on (am.period_id=p.id)
                where l.state != 'draft'
            )
        """)
