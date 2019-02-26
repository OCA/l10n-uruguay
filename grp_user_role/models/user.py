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

from openerp import api, fields, models, SUPERUSER_ID

class ResUsers(models.Model):
    _inherit = 'res.users'

    user_role_id = fields.Many2one('res.users.role', string=u"Rol")

    @api.model
    def create(self, vals):
        rec = super(ResUsers, self).create(vals)
        if vals.get('user_role_id', False):
            vals_role_lines = [(0, 0, {'role_id': vals['user_role_id'], 'user_id': rec.id})]
            ou_ids = self.env['res.users.role'].sudo().browse(vals['user_role_id']).operating_unit_ids.ids
            rec.sudo().role_line_ids.unlink()
            new_vals = {
                'role_line_ids': [(0, 0, { 'role_id': vals['user_role_id'], 'user_id': rec.id })],
                'operating_unit_ids': [(6, 0, ou_ids)],
            }
            if not ou_ids:
                new_vals['default_operating_unit_id'] = False
            else:
                if not rec.default_operating_unit_id or (rec.default_operating_unit_id and rec.default_operating_unit_id.id not in ou_ids):
                    new_vals['default_operating_unit_id'] = ou_ids[0]
            rec.sudo().write(new_vals)
        return rec

    @api.multi
    def write(self, vals):
        if vals.get('user_role_id', False):
            vals_role_lines = [(0, 0, { 'role_id': vals['user_role_id'], 'user_id': row.id }) for row in self ]
            ou_ids = self.env['res.users.role'].sudo().browse(vals['user_role_id']).operating_unit_ids.ids
            self.sudo().mapped('role_line_ids').unlink()
            vals.update({
                'role_line_ids': vals_role_lines,
                'operating_unit_ids': [(6, 0, ou_ids)],
            })
            if not ou_ids:
                vals['default_operating_unit_id'] = False
            else:
                for row in self:
                    if not row.default_operating_unit_id or (row.default_operating_unit_id and row.default_operating_unit_id.id not in ou_ids):
                        vals['default_operating_unit_id'] = ou_ids[0]
                        break
            return super(ResUsers, self.sudo()).write(vals)
        return super(ResUsers, self).write(vals)

