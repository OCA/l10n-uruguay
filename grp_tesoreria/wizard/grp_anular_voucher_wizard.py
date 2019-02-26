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


# RAGU anulando comprobante
class GrpAnularVoucherWizard(models.TransientModel):
    _name = "grp.anular.voucher.wizard"

    voucher_id = fields.Many2one('account.voucher',string=u'Comprobante', required=True)
    cancel_motive = fields.Char(string=u'Motivo de anulación', required=True)

    @api.multi
    def action_nullify_voucher(self):
        self.ensure_one()
        self.voucher_id.write({'cancel_motive':self.cancel_motive})
        self.voucher_id.btn_anular()
        return True
