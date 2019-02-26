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
from openerp.exceptions import ValidationError

class evolucion_patrimonio_wzd(models.TransientModel):
    _name = 'evolucion.patrimonio.wzd'
    _inherit = 'account.common.report'

    @api.multi
    def _print_report(self, data):
        fiscalyear_id = data['form']['fiscalyear_id']
        fiscal_year = self.env['account.fiscalyear'].search([('id','=',fiscalyear_id)])
        data['form'].update({
                                'wzd_ids': self.ids,
                                # 'period_from': start_period,
                                # 'period_to': end_period,
                                'date_from': fiscal_year.date_start,
                                'date_to': fiscal_year.date_stop,
                                'journal_ids': []
                            })
        data['form']['used_context'].update({
                                # 'period_from': start_period,
                                # 'period_to': end_period,
                                'date_from': fiscal_year.date_start,
                                'date_to': fiscal_year.date_stop,
                                'journal_ids': []
                            })
        if self._context.get('type_xls', False):
            return {
                        'type': 'ir.actions.report.xml',
                        'report_name': 'report_evolucion_patrimonio_xls',
                        'datas': data
                    }
        return self.env['report'].get_action(self, 'report_evolucion_patrimonio', data=data)
