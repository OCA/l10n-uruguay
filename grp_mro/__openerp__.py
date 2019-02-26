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
    'name':     u'GRP - MRO',
    'author':   'Quanam',
    'website':  'http://www.quanam.com',
    'category': 'GRP',
    'license':  'AGPL-3',
    'version':  '1.0',
    'description': u"""
Ordenes de Mantenimieno GRP
=============
* Registro de los servicios
""",

    'depends' : ['mro','fleet','account_asset','grp_seguridad'],# TODO SPRING 5 GAP 46
    'data' : [
        'data/grp_mro_data.xml',
        'views/grp_inherit_mro_order_view.xml',
        'views/grp_inherit_mro_view.xml',
        'views/account_asset_category_view.xml',
        'security/grp_mro_security.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install': False,
    'installable': True,
    'application': True
}
