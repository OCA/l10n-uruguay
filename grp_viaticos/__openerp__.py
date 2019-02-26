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

{
    'name': 'GRP - Viáticos',
    'version': '1.0',
    'author': 'Quanam',
    'website': 'www.quanam.com',
    'category': '',
    'images': [],
    'depends': ['base','grp_compras_estatales','hr_expense','grp_hr_expense','base_suspend_security'],
    'description': """  Funcionalidad de viaticos
""",
    'demo': [],
    'test': [],
    'data': [
        'security/grp_viaticos_security.xml',
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'views/grp_solicitud_viaticos_view.xml',
        'views/grp_product_view.xml',
        'views/grp_adelanto_viaticos_view.xml',
        'views/grp_hr_expense_view.xml',
        'views/grp_configuracion_importes_viaticos_view.xml',  # TODO: SPRING 11 GAP 25 K
        'views/grp_locomocion_propia_view.xml',  # TODO: SPRING 11 GAP 25 K
        'data/grp_viaticos_sequence.xml',
        'data/grp_viaticos_translation.xml',
        'report/grp_solicitud_viaticos_report.xml',
        'report/grp_viaticos_report_view.xml',
        'views/grp_solicitud_viaticos_report_tmpl.xml',
        'views/hr_employee_view.xml',
        'views/grp_devolucion_viaticos_view.xml',  # TODO: SPRING 11 GAP 28 L
        'data/grp_viaticos_alertas_data.xml',  # TODO: K SPRING 12 GAP 33
        'views/grp_report_expense.xml',
        'views/res_config_view.xml',
        'views/res_partner_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}

