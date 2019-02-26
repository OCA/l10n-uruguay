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
    'name': 'Custom Group by',
    'summary': 'Custom Group by fields for Odoo v8',
    'author':   'Quanam',
    'website':  'http://www.quanam.com',
    'category': 'Web',
    'version': '1.0',
    'depends': ['web'],
    'data': [
        'views/search_group_by_custom_view.xml',
    ],
    'qweb': [ 'static/src/xml/template.xml'],
    'images': [],
    'auto_install': False,
    'app': False,
    'installable': True,
}
