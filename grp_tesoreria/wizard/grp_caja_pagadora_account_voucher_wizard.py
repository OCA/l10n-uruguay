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


# TODO: SPRING 10 GAP 474 M
class grpCajaPagadoraAccuntVoucherWizard(models.TransientModel):
    _name = "grp.caja.pagadora.account.voucher.wizard"


    @api.model
    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False):
        res = super(grpCajaPagadoraAccuntVoucherWizard, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                                        toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        voucher_ids = []
        check_vouchere = []
        caja_pagadora = self.env['grp.caja.pagadora.tesoreria'].browse(self._context['default_caja_pagadora_id'])
        if caja_pagadora.check_line_ids:
            check_vouchere = caja_pagadora.check_line_ids.mapped('voucher_id')
        vouchers = self.env['account.voucher'].search(
            [('state', '=', 'issue'), ('payment_method', '=', 'check'), ('in_cashbox', '=', False),('type','=','payment'),
             ('journal_id.operating_unit_id', 'in', caja_pagadora.box_id.operating_unit_ids.ids)])#,('journal_id.currency', '=', caja_pagadora.box_id.currency_id.id)

        if check_vouchere and vouchers:
            voucher_ids.extend((vouchers - check_vouchere).ids)
        elif vouchers and not check_vouchere:
            voucher_ids.extend(vouchers.ids)
        for field in res['fields']:
            if field == 'account_voucher_ids':
                res['fields'][field]['domain'] = [
                    ('id', 'in', voucher_ids)]

        res['arch'] = etree.tostring(doc)
        return res

    account_voucher_ids = fields.Many2many('account.voucher', 'account_voucher_caja_pagadora_wizard_rel',
                                           'voucher_id', 'wizard_id', string=u'Pago a proveedores')
    caja_pagadora_id = fields.Many2one('grp.caja.pagadora.tesoreria', string='Caja pagadora')



    @api.multi
    def transfer_account_voucher(self):
        check_lines = []
        if self.account_voucher_ids:
            for line in self.account_voucher_ids:
                check_lines.append(
                    [0, 0, {'voucher_id': line.id, 'type': 'check', 'apertura_recibo': False}])
            self.caja_pagadora_id.write({'check_line_ids': check_lines})
        return True

