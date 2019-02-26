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
    'name':     u'GRP - Account Distribution',
    'author':   'Quanam',
    'website':  'http://www.quanam.com',
    'category': 'GRP',
    'license':  'AGPL-3',
    'version':  '1.0',
    'description': u""" """,
    'depends' : ['account', 'purchase_analytic_plans', 'grp_account', 'grp_factura_siif', 'grp_compras_estatales', 'grp_activo_fijo', 'grp_tesoreria'],
    'data': [
        'security/ir.model.access.csv',
        'views/grp_account_dist_view.xml',
        'views/grp_solicitud_recursos_view.xml',
        'views/grp_solicitud_compra_view.xml',
        'views/grp_pedido_compra_view.xml',
        'views/grp_account_asset_asset_view.xml',
        'views/grp_cotizaciones_view.xml',
        'views/grp_hr_expense_view.xml',
        'views/grp_stock_view.xml',
        'report/report_analyticjournal.xml',
    ],
    'auto_install': False,
    'installable': True,
    'application': True
}
