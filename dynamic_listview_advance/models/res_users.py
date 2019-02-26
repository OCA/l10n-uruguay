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

class resUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _get_group(self):
        result = super(resUsers, self)._get_group()
        dataobj = self.env['ir.model.data']
        try:
            dummy,group_id = dataobj.sudo().get_object_reference('dynamic_listview_advance', 'group_show_fields')
            result.append(group_id)
        except ValueError:
            # If these groups does not exists anymore
            pass
        return result

    groups_id = fields.Many2many(default=_get_group)
