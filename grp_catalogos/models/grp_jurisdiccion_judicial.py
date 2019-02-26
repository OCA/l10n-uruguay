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

class grpJurisdiccionJudicial(models.Model):
    _name = 'grp.jurisdiccion.judicial'
    _description = 'Jurisdicciones judiciales'
    _order = 'name'

    name = fields.Char(string=u'Jurisdicción judicial', size=40, required=True, index=True)
    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        ('juris_judicial_unique_name', 'UNIQUE (name)', u'La jurisdicción ingresada ya existe.'),]

    # Name de jurisdicción solo en mayusculas
    @api.model
    def create(self, values):
        values["name"] = values["name"].upper()
        return super(grpJurisdiccionJudicial, self).create(values)

    # Name de jurisdicción solo en mayusculas
    @api.multi
    def write(self, values):
        if values.get("name", False):
            values["name"] = values["name"].upper()
        return super(grpJurisdiccionJudicial, self).write(values)

