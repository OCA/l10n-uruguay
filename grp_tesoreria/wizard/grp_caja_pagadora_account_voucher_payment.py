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
from datetime import *
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


# TODO: SPRING 10 GAP 474 M
class grpCajaPagadoraAccuntVoucherPayment(models.TransientModel):
    _name = "grp.caja.pagadora.account.voucher.payment"

    payment_date = fields.Date('Fecha de pago', default=lambda *a: fields.Date.today())
    entry_date = fields.Date('Fecha de asiento', default=lambda *a: fields.Date.today(), required=True)
    box_line_id = fields.Many2one('grp.caja.pagadora.tesoreria.line', 'Linea Caja')

    @api.onchange('payment_date')
    def _onchange_payment_date(self):
        self.entry_date = self.payment_date

    @api.multi
    def btn_confirm(self):
        date = datetime.today().strftime('%Y-%m-%d')
        if self.payment_date and self.payment_date > date:
            raise exceptions.ValidationError(
                _(u'La fecha de pago no puede ser una fecha posterior a la fecha actual.'))
        if self.box_line_id.voucher_id:
            self.box_line_id.voucher_id.write({'date': self.payment_date,'entry_date': self.entry_date})
            self.box_line_id.voucher_id.sudo().proforma_voucher()
            self.box_line_id.payment_box_id.write({'posted': True})
        return {
            'name': 'Caja cheques',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_id': False,
            'view_mode': 'form',
            'res_model': 'grp.caja.pagadora.tesoreria',
            'res_id': self.box_line_id.payment_box_id.id,
            'target': 'current'
        }
