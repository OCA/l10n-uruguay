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

from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp
import time


# TODO: SPRING 8 GAP 111.228.339 K
class grp_hr_expense(models.Model):
    _inherit = 'hr.expense.expense'

    fondo_rotarios = fields.Boolean(string='En 3 en 1-Fondo rotatorio', default=False)
    fondo_rotatorio_id = fields.Many2one('grp.fondo.rotatorio', string='Fondo rotatorio',
                                              compute='_compute_fondo_rotatorio_id')

    @api.multi
    def _compute_fondo_rotatorio_id(self):
        FR_Line = self.env['grp.fondo.rotatorio.line'].suspend_security()
        for rec in self:
            rec.fondo_rotatorio_id = FR_Line.search([('hr_expense_id', '=', rec.id)],
                                                         limit=1).fondo_rotatorios_id.id

    def expense_canceled(self, cr, uid, ids, context):
        hr_expenses = self.read(cr, uid, ids, ['fondo_rotarios'])
        for hr_expense in hr_expenses:
            if hr_expense['fondo_rotarios'] == True:
                raise exceptions.ValidationError(
                    _(u'Este documento está en un documento 3-en1-Fondo rotatorio. No es posible cancelarlo.'))
        super(grp_hr_expense, self).expense_canceled(cr, uid, ids, context)
