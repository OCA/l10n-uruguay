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

from openerp.osv import fields, osv


class accounting_report(osv.osv_memory):
    _inherit = "accounting.report"

    _columns = {
        'display_org_unit_column': fields.boolean('Mostrar columna Unidad organizativa'),
        'display_analytic_acc_column': fields.boolean(u'Mostrar columna Cuenta analítica'),
        'display_multiprop_column': fields.boolean(u'Mostrar columna Multipropósito'),
    }

    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = super(accounting_report, self).check_report(cr, uid, ids, context=context)
        res['data']['form'].update(self.read(cr, uid, ids, ['display_org_unit_column', 'display_analytic_acc_column','display_multiprop_column'], context=context)[0])
        return res

    def _print_report_excel(self, cr, uid, ids, data, context=None):
        data['form'].update(self.read(cr, uid, ids, ['display_org_unit_column', 'display_analytic_acc_column','display_multiprop_column'], context=context)[0])
        return super(accounting_report, self)._print_report_excel(cr, uid, ids, data, context=context)
