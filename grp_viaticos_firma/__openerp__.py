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
    'name': 'GRP - Viáticos Firma',
    'version': '1.0',
    'author': 'Quanam',
    'website': 'www.quanam.com',
    'category': '',
    'images': [],
    'depends': ['base','grp_viaticos','x_firma'],
    'description': """  Funcionalidad de firma electronica de viaticos
""",
    'demo': [],
    'test': [],
    'data': [
         'views/grp_hr_expense_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}

