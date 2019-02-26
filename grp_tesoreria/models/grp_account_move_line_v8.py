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
import time
from openerp.exceptions import ValidationError
from openerp.tools import float_compare
import base64
import StringIO
from datetime import *
import openerp.addons.decimal_precision as dp

class GrpAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('credit', 'debit')
    def _get_ajuste(self):
        for rec in self:
            rec.ajuste = rec.credit - rec.debit

    invoice_id = fields.Many2one('account.invoice', u'Nro. Factura GRP', readonly=True,
                                          compute='_get_invoice_id', multi='_get_invoice_id', store=False)
    supplier_invoice_number = fields.Char(string=u'Nro. de documento',
                                          compute='_get_invoice_id', multi='_get_invoice_id')
    ajuste = fields.Float(string=u'Ajuste', compute='_get_ajuste', digits=dp.get_precision('Account'))

    # PCAR adicionando origen a las lineas del move y UE
    def _get_origin_dict(self):
        invoice_id = self.env['account.invoice'].search([('move_id', '!=', False), ('move_id', '=', self.move_id.id)])
        if invoice_id:
            to_return = {
                'invoice_id': invoice_id.id,
                'supplier_invoice_number': invoice_id.supplier_invoice_number
            }
        else:
            origin_voucher_id = self.env['account.voucher'].search([('move_id', '=', self.move_id.id)])
            to_return = {
                'invoice_id': False,
                'supplier_invoice_number': self.move_id.name_get()[0][1]
            }
            if origin_voucher_id:
                if origin_voucher_id.rendicion_viaticos_id:
                    to_return.update({'supplier_invoice_number': origin_voucher_id.rendicion_viaticos_id.name})
                elif origin_voucher_id.solicitud_viatico_id:
                    to_return.update({'supplier_invoice_number': origin_voucher_id.solicitud_viatico_id.name})

        return to_return

    @api.multi
    def _get_invoice_id(self):
        for rec in self:
            vals = rec._get_origin_dict()
            rec.invoice_id = vals['invoice_id']
            rec.supplier_invoice_number = vals['supplier_invoice_number']

    @api.model
    def create(self, vals):
        # RAGU si no asume moneda poner la del diario en OPI
        _context_voucher = self._context.get('voucher')
        if _context_voucher and _context_voucher.opi and vals['account_id']:
            account_id = self.env['account.account'].browse(vals['account_id'])
            if account_id.currency_id and not vals.get('currency_id'):
                vals['currency_id'] = account_id.currency_id.id
                vals['amount_currency'] = self._context.get('line_amount')

        return super(GrpAccountMoveLine, self).create(vals)
