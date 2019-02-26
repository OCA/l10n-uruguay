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
    'name': 'Account Financial Reports',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'author': 'Quanam',
    'website': 'http://www.quanam.com',
    'description': u"""
Account Financial Reports
=========================

* Reportes contables Pérdidas y Ganancias e Informes financieros con nuevas dimensiones
* Reporte comparativo entre ejecución presupuestal y contabilidad patrimonial
""",
    'depends': ['account_financial_report_aeroo_xls', 'grp_factura_siif', 'uy_account_chart_extensions', 'report_xls'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_financial_report_view.xml',
        'views/report_financial.xml',
        'views/grp_account_odg_config_view.xml',
        'report/report_balance_sheet.xml',
        'wizard/evolucion_patrimonio_view.xml',
        'report/evolucion_patrimonio_report_view.xml',
        'report/evolucion_patrimonio_qweb.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
