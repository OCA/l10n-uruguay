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

class hrDepartment(models.Model):
    _inherit = 'hr.department'

    state_id = fields.Many2one("res.country.state", string="Departamento", ondelete="restrict", required=True)
    localidad = fields.Many2one("grp.localidad", string="Localidad", ondelete="restrict", required=True, domain="[('state_id', '=', state_id)]" )

    region = fields.Many2one("grp.region", string=u"Región", ondelete="restrict", required=True)
    jurisdiccion_judicial = fields.Many2one("grp.jurisdiccion.judicial", string =u"Jurisdicción Judicial", ondelete="restrict", required=True)
    active = fields.Boolean(string='Activo', default=True)
