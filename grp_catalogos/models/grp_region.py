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

class grpRegion(models.Model):
    _name = 'grp.region'
    _description = u'Región'
    _order = 'name'

    name = fields.Char(string=u'Región', size=40, required=True, index=True)
    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        ('region_unique_name', 'UNIQUE (name)', u'La región ingresada ya existe.'),]

    @api.model
    def create(self, values):
        # Name de region solo en mayusculas
        values["name"] = values["name"].upper()
        return super(grpRegion, self).create(values)

    @api.multi
    def write(self, values):
        if values.get("name", False):
            # Name de region solo en mayuscuLas
            values["name"] = values["name"].upper()
        return super(grpRegion, self).write(values)





