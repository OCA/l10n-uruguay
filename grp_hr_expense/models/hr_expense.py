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

from openerp import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class HrExpense(models.Model):
    _inherit = 'hr.expense.expense'

    is_patronato = fields.Boolean(related="employee_id.is_patronato", store=True, string="Patronato", readonly=True)
    is_comision_apoyo = fields.Boolean(related="employee_id.is_comision_apoyo", store=True, string=u"Comisión de apoyo", readonly=True)
    is_otros = fields.Boolean(related="employee_id.is_otros", store=True, string="Otros", readonly=True)
    detalle_otros = fields.Char(related="employee_id.detalle_otros", store=True, string="Detalle de Otros", readonly=True)
    entry_date = fields.Date(u'Fecha', default=lambda *a: fields.Date.today(), required=True)
    date = fields.Date(string='Date', select=True, readonly=True, required=True,
                       states={'draft': [('readonly', False)], 'confirm': [('readonly', False)],'accepted': [('readonly', False)]})

    @api.onchange('entry_date')
    def _onchange_date(self):
        for record in self:
            if record.entry_date:
                record.date = record.entry_date

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
    #     res = super(HrExpense, self).fields_view_get(view_id=view_id,
    #                                                  view_type=view_type,
    #                                                  context=context,
    #                                                  toolbar=toolbar, submenu=submenu)
    #     if view_type == 'tree':
    #         pool_groups = self.env['res.groups']
    #         data = self.env['ir.model.data']
    #         _model1, aprob_anticipo = data.get_object_reference('grp_tesoreria', 'group_grp_aprobador_anticipos')
    #         _model1, solic_anticipo = data.get_object_reference('grp_tesoreria', 'group_grp_solicitante_anticipos')
    #         lista_rendicion = [aprob_anticipo, solic_anticipo]
    #
    #         _model1, analista_contable = data.get_object_reference('grp_seguridad', 'grp_analista_contable')
    #         _model1, sv_solicitante = data.get_object_reference('grp_viaticos', 'grp_sv_solicitante')
    #         _model1, aprobar_rend_fin = data.get_object_reference('grp_viaticos', 'grp_aprobar_rendicion_f')
    #         _model1, aprobar_rend = data.get_object_reference('grp_viaticos', 'grp_aprobar_rendicion')
    #         lista_viatico = [analista_contable, sv_solicitante, aprobar_rend_fin, aprobar_rend]
    #
    #         context_tipo_doc = self._context.get('default_doc_type', False)
    #         if context_tipo_doc:
    #             i = 0
    #             index = 0
    #             for prnt in res['toolbar']['print']:
    #                 if context_tipo_doc in ['rendicion_viatico'] and\
    #                    prnt['report_name'] == 'hr_expense.report_expense':
    #                     prnt.update({'groups_id': lista_viatico})
    #                 elif context_tipo_doc in ['rendicion_anticipo'] and\
    #                      prnt['report_name'] == 'grp_hr_expense.report_expense_2':
    #                     prnt.update({'groups_id': lista_rendicion})
    #                 if context_tipo_doc in ['rendicion_viatico'] and\
    #                    prnt['report_name'] == 'grp_hr_expense.report_expense_2':
    #                     index = i
    #                 elif context_tipo_doc in ['rendicion_anticipo'] and\
    #                      prnt['report_name'] == 'hr_expense.report_expense':
    #                     index = i
    #                 i += 1
    #             del res['toolbar']['print'][index]
    #     return res
