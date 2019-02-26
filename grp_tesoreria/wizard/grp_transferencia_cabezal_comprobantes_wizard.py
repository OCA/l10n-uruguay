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


# TODO: SPRING 11 GAP 285 C
class GrpTransferenciaCabezalCompWizard(models.TransientModel):
    _name = "grp.transferencia.cabezal.comp.wizard"

    line_ids = fields.Many2many('account.move.line', string=u'Comprobantes')
    transfer_id = fields.Many2one('grp.transferencia.cabezal', string='Transferencia cabezal', ondelete='cascade')

    @api.multi
    def confirm_line_ids(self):
        lines = self.mapped('line_ids')
        comp_lines = []
        for line in lines:
            bank = len(line.partner_id.bank_ids) and line.partner_id.bank_ids[0].bank.id or False
            comp_lines.append((0, 0, {'move_line_id': line.id, 'bank_id': bank}))
        self.transfer_id.write({'line_ids': comp_lines})
        return True
