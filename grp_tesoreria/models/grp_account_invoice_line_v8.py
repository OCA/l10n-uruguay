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

from openerp import models, fields, api, exceptions, _
import amount_to_text_es
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.exceptions import ValidationError
import openerp.addons.decimal_precision as dp


class GrpAccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.depends("price_subtotal", "invoice_line_tax_id.amount")
    def _importe_moneda_report(self):
        for rec in self:
            if (rec.price_subtotal + rec.price_subtotal * rec.invoice_line_tax_id.amount) >= 0:
                rec.importe_moneda_report = rec.price_subtotal + rec.price_subtotal * rec.invoice_line_tax_id.amount
            else:
                rec.importe_moneda_report = -abs(rec.price_subtotal + rec.price_subtotal * rec.invoice_line_tax_id.amount)

    @api.depends('monto_moneda_base')
    def _monto_base_report(self):
        for rec in self:
            if rec.monto_moneda_base > 0:
                rec.monto_mon_base_report = rec.monto_moneda_base
            else:
                rec.monto_mon_base_report = -abs(rec.monto_moneda_base)

    monto_mon_base_report = fields.Float(compute='_monto_base_report', string="Monto base reporte",
                                         store=False, digits=dp.get_precision('Account'))
    importe_moneda_report = fields.Float(compute='_importe_moneda_report', string="Importe moneda reporte",
                                         store=False, digits=dp.get_precision('Account'))


