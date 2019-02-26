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

from lxml import etree
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
from openerp.osv import osv


# TODO SPRING 5 GAP 46
class GrpMroRequestCause(models.Model):
    _name = 'grp.mro.request.cause'

    name = fields.Char('Nombre', required=True, size=20)
    description = fields.Char('Característica', size=50)


class mro_request(models.Model):
    _name = 'mro.request'
    _inherit = 'mro.request'

    cause_id = fields.Many2one('grp.mro.request.cause', 'Causa', required=True, readonly=True, states={'draft': [('readonly', False)]})
    cause = fields.Char('Cause', related='cause_id.name', store=True, readonly=True)
    type = fields.Selection([('preventive', 'Preventivo'),
                             ('predictive', 'Predictivo'),
                             ('corrective', 'Correctivo')], 'Tipo', required=True, readonly=True, states={'draft': [('readonly', False)]})


class grp_categoria_activo(models.Model):
    _inherit = 'account.asset.category'

    is_asset_mro = fields.Boolean(string='Activo de mantenimiento')
