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

from openerp import models, fields, exceptions, api, _
import openerp.addons.decimal_precision as dp
import logging
import time
from datetime import datetime

_logger = logging.getLogger(__name__)

# TODO: M SPRING 14 GAP 29_31

class GrpDevolucionAnticiposFondos(models.Model):
    _inherit = 'account.voucher'

    rendicion_anticipos_id = fields.Many2one('hr.expense.expense', string=u'Rendición de anticipos de fondos')

    @api.onchange('rendicion_anticipos_id')
    def _onchange_rendicion_anticipos_id(self):
        self.operating_unit_id = self.rendicion_anticipos_id.operating_unit_id.id


    def _get_nro_documento(self):
        documentos = super(GrpDevolucionAnticiposFondos, self)._get_nro_documento()
        if self.rendicion_anticipos_id:
            documentos.append(u'Devolución de anticipos de fondos %s' % (self.name_get()[0][1]))
        return documentos

    # def _get_nro_documento(self):
    #     documentos = super(GrpDevolucionAnticiposFondos, self)._get_nro_documento()
    #     for line in self.mapped(lambda x: x.line_ids).filtered(lambda x: x.amount > 0 and x.origin_voucher_id.rendicion_anticipos_id.id):
    #         documentos.append(line.origin_voucher_id.rendicion_anticipos_id.sequence)
    #     return documentos
