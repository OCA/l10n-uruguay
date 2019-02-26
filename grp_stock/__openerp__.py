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
    'name':     u'GRP - Stock',
    'author':   'Quanam',
    'website':  'http://www.quanam.com',
    'category': 'GRP',
    'license':  'AGPL-3',
    'version':  '1.0',
    'description': u"""
Stock GRP
=============

* Recuento de stock
""",
    "depends": ['stock','product_expiry'],
    'data': [
        'views/stock_view.xml',
        'views/stock_quant_view.xml',
        'views/stock_picking_view.xml',
        'views/stock_transfer_details_view.xml',
        'wizard/orderpoint_procurement_view.xml',
        'data/grp_stock_data.xml',
        'report/stock_picking_list_report.xml',
        'report/stock_picking_report.xml',
    ],
    'auto_install': False,
    'installable': True,
    'application': True
}
