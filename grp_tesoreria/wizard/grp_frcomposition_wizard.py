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

import logging

from openerp import models,fields, api

_logger = logging.getLogger(__name__)


class GrpFRCompositionWizard(models.TransientModel):
    _name = "grp.fr.composition.wizard"
    date = fields.Date(u'Fecha', required=True, default=lambda *a:fields.Date.today())
    fiscal_year_id = fields.Many2one('account.fiscalyear',string='Año fiscal', compute='_compute_fiscal_year_id', store=True)
    inciso_id = fields.Many2one('grp.estruc_pres.inciso',u'Inciso', required=True, domain="[('fiscal_year_id','=',fiscal_year_id)]")
    operating_unit_id = fields.Many2one('operating.unit',u'Unidad ejecutora')
    operating_unit_code = fields.Char('Codigo', related='operating_unit_id.code', readonly=True)
    unidad_ejecutora = fields.Char('Codigo', related='operating_unit_id.unidad_ejecutora', readonly=True)
    fr_siif_id = fields.Many2one('fondo.rotatorio.siif',u'Fondo rotatorio SIIF',
                                 domain="[('fiscal_year','=',fiscal_year_id),('inciso','=',inciso_id),('ue.ue','=',unidad_ejecutora)]")

    @api.onchange('fiscal_year_id')
    def _onchange_date(self):
        if self.fiscal_year_id:
            _inciso_id = self.env['grp.estruc_pres.inciso'].search(
                [('inciso', '=', self.env.user.company_id.inciso), ('fiscal_year_id', '=', self.fiscal_year_id.id)],
                limit=1)
        else:
            _inciso_id = False
        self.inciso_id = _inciso_id

    @api.multi
    @api.depends('date')
    def _compute_fiscal_year_id(self):
        fiscal_year_obj = self.env['account.fiscalyear']
        for rec in self:
            rec.fiscal_year_id = fiscal_year_obj.search([('date_start', '<=', rec.date),
                                                         ('date_stop', '>=', rec.date)], limit=1)

    @api.multi
    def action_print_xls(self):
        report_name = 'grp_tesoreria.report_grp_fr_composition_xls'
        data = {'date':self.date}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'report_type': 'xlsx',
            'datas': data}
