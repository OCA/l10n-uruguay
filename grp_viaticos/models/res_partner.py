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

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def default_supplier_advance_account(self):
        return self.env.user.company_id.supplier_advance_account_id.id or self.env['account.account']

    @api.model
    def default_customer_advance_account(self):
        return self.env.user.company_id.customer_advance_account_id.id or self.env['account.account']

    supplier_advance_account_id = fields.Many2one(
        comodel_name='account.account',
        string=u'Cuenta anticipo de funcionarios',
        domain=[('type','!=','view')],
        default=default_supplier_advance_account
    )

    customer_advance_account_id = fields.Many2one(
        comodel_name='account.account',
        string=u'Cuenta anticipo de clientes',
        domain=[('type', '!=', 'view')],
        default=default_customer_advance_account
    )
