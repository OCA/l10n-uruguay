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
class grpLocalidad(models.Model):
    _name = 'grp.localidad'
    _description = 'Localidad'
    _order = 'state_id, name'

    name = fields.Char(string='Localidad', size=40, required=True, index=True)
    country_id = fields.Many2one('res.country',string=u'País', ondelete='restrict', required=True)
    state_id = fields.Many2one("res.country.state", string='Departamento', ondelete='restrict', required=True)
    code = fields.Char(string=u'Código de localidad', size=3, required=True)
    active = fields.Boolean(string='Activo', default=True)

    _sql_constraints = [
        ('localidades_unique_name_by_state', 'UNIQUE (name, state_id)', 'La localidad ingresada ya existe.'),]

    # Name de localidad solo en mayusculas
    @api.model
    def create(self, values):
        values["name"] = values["name"].upper()
        return super(grpLocalidad, self).create(values)

    # Name de localidad solo en mayusculas
    @api.multi
    def write(self, values):
        if values.get("name", False):
            values["name"] = values["name"].upper()
        return super(grpLocalidad, self).write(values)

    #@api.one
    @api.onchange('country_id')
    def _onchange_country_id(self):
        self.state_id = False
        if self.country_id:
            return {
                'domain': {'state_id': [('country_id','=',self.country_id.id)]}
            }
