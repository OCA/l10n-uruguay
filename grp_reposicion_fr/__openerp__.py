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
    'name': 'GRP - Reposicion FR',
    'version': '1.0',
    'author': 'Quanam',
    'website': 'www.quanam.com',
    'category': '',
    'images': [],
    'depends': ['grp_tesoreria', 'grp_hr_expense','base_suspend_security'],
    'description': """
GRP - Reposicion de fondo rotarorio
""",
    'demo': [],
    'data': [
        # TODO: SPRING 8 GAP 111.228.339 K
        'security/ir.model.access.csv',
        'security/grp_reposicion_fr_security.xml',
        'views/grp_fondo_rotatorio_view.xml',
        'views/grp_hr_expense_view.xml',
        'views/grp_account_bank_statement_view.xml',
        'views/grp_tesoreria_view.xml',
        'views/grp_rendicion_anticipo.xml',
        'views/account_supplier_invoice_view.xml',
        'views/config_recuperacion_fondo_rotatorio.xml',
        'data/grp_fondo_rotatorio_sequence.xml',
        'report/grp_agrupar_fondo_rotatorio_view.xml',
        'report/grp_control_credito_fondo_rotatorio_view.xml', # TODO: SPRING 11 GAP 495 K
        'report/grp_fondo_rotatorio_report.xml',
        'wizard/wizard_modif_obligacion_siif_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
