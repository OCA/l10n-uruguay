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

import logging

from openerp import models, fields, api, exceptions
from lxml import etree

_logger = logging.getLogger(__name__)


# TODO: SPRING 11 GAP 292 M
class grpCajaRecaudadoraBoletoSiifVoucherWizard(models.TransientModel):
    _name = "grp.caja.recaudadora.boleto.siif.voucher.wizard"

    @api.model
    def default_get(self, fields):
        res = super(grpCajaRecaudadoraBoletoSiifVoucherWizard, self).default_get(fields)
        line_ids = []
        vouchers = self.env['account.voucher'].search(
            [('state', '=', 'posted'), ('payment_method', '=', 'transfer')])
        for voucher in vouchers:
            voucher_lines = voucher.mapped(lambda x: x.line_cr_ids).filtered(
                                    lambda x: x.amount > 0 and x.invoice_id)
            for voucher_line in voucher_lines:
                if not voucher_line.invoice_id.in_box:
                    line_ids.append([0, 0, {'voucher_id': voucher_line.voucher_id.id,
                                           'date': voucher_line.voucher_id.date,
                                           'invoice_id': voucher_line.invoice_id.id,
                                           'partner_id': voucher_line.invoice_id.partner_id.id,
                                           'currency_id': voucher_line.invoice_id.currency_id.id,
                                           'number': voucher_line.invoice_id.number,
                                           'operating_unit_id': voucher_line.invoice_id.operating_unit_id
                                                                and voucher_line.invoice_id.operating_unit_id.id or False,
                                           'amount': voucher_line.amount}])

        res['line_ids'] = line_ids
        return res

    line_ids = fields.One2many('grp.caja.recaudadora.boleto.siif.voucher.line.wizard', 'wizard_id', string=u'Lineas')
    boleto_siif_id = fields.Many2one('grp.caja.recaudadora.tesoreria.boleto.siif', string='Boleto SIIF')

    @api.multi
    def transfer_account_voucher(self):

        boleto_siif_line = self.env['grp.caja.recaudadora.tesoreria.line']
        if self.line_ids and self.line_ids.filtered(lambda x: x.select):
            for line in self.line_ids.filtered(lambda x: x.select):

                boleto_siif_line.suspend_security().create({
                    'voucher_id': line.voucher_id.id,
                    'invoice_id': line.invoice_id.id,
                    'type': 'voucher',
                    'amount': line.amount,
                    'boleto_siif_id': self.boleto_siif_id.id,
                    'shipment': True
                })
                line.invoice_id.write({'boleto_siif_id': self.boleto_siif_id.id})
                for invoice_line in line.invoice_id.invoice_line:
                    boleto_siif_line.suspend_security().create({
                        'voucher_id': line.voucher_id.id,
                        'invoice_id': line.invoice_id.id,
                        'type': 'details',
                        'product_id': invoice_line.product_id.id,
                        'price_subtotal': invoice_line.price_subtotal,
                        'amount': line.amount,
                        'boleto_siif_id': self.boleto_siif_id.id,
                        'shipment': True
                    })
            data = self.boleto_siif_id._update_remesa()
            self.boleto_siif_id.suspend_security().write(data)
        else:
            raise exceptions.ValidationError(u"Debe seleccionar al menos una linea.")
        return True


class grpCajaRecaudadoraBoletoSiifVoucherLineWizard(models.TransientModel):
    _name = "grp.caja.recaudadora.boleto.siif.voucher.line.wizard"

    wizard_id = fields.Many2one('grp.caja.recaudadora.boleto.siif.voucher.wizard', string='Wizard')
    voucher_id = fields.Many2one('account.voucher', u'Pago a proveedor')
    invoice_id = fields.Many2one('account.invoice', 'Factura')
    partner_id = fields.Many2one('res.partner', string=u'Cliente', related='invoice_id.partner_id', readonly=True)
    number = fields.Char(string=u'N° factura', related='invoice_id.number', readonly=True)
    operating_unit_id = fields.Many2one('operating.unit', u'Unidad ejecutora',
                                        related='invoice_id.operating_unit_id', readonly=True)
    currency_id = fields.Many2one('res.currency', u'Divisa', related='invoice_id.currency_id', readonly=True)
    date = fields.Date(u'Fecha de cobro', related='voucher_id.date', readonly=True)
    amount = fields.Float(string=u'Importe cobrado')
    select = fields.Boolean(u'Seleccionar', default=False)

