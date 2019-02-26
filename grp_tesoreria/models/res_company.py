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
from openerp.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    agreement = fields.Char(string=u'Número de convenio bancario', size=6)
    box_refund_in_selection = fields.Selection([('out_box', 'En Caja pagadora'), ('in_box', 'En Caja recaudadora')],
                                     string=u'Cobro devolución adelantos y anticipos', required=True)

    @api.multi
    @api.constrains('agreement')
    def _check_agreement(self):
        for rec in self:
            if not str(rec.agreement).isdigit():
                raise ValidationError(u"El número de convenio bancario solo debe contener números!")
        return True
