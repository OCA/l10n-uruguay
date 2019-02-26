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

from openerp import api, exceptions, fields, models

# TODO K SPRING 12 GAP 205
class grpContratoCompromiso(models.Model):
    _inherit = 'grp.compromiso'

    contrato_id = fields.Many2one('grp.contrato.proveedores', related='afectacion_id.contrato_id',
                                  string=u'Nro Contrato', readonly=True)


    # TODO: K SPRING 12 GAP 205
    @api.multi
    def abrir_contratos_form_view(self):
        for rec in self:
            if not rec.contrato_id:
                return
            else:
                context = dict(self._context)
                mod_obj = self.env['ir.model.data']
                res = mod_obj.get_object_reference('grp_contrato_proveedores', 'view_contract_proveedores_form')
                models = 'grp.contrato.proveedores'
                res_id = res and res[1] or False
                ctx = context.copy()
                return {
                    'name': "Contrato de condiciones generales",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': models,
                    'res_id': rec.contrato_id.id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': ctx,
                }
        return True
