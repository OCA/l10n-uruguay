# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Enterprise Management Solution
#    GRP Estado Uruguay
#    Copyright (C) 2018 ATOS Uruguay
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
    'name': u'GRP CEIP Validaciones contra PEP',
    'author': 'ATOS Uruguay',
    'website': 'http://www.atos.com',
    'category': 'GRP',
    'license': 'AGPL-3',
    'version': '1.8.1',
    'description': u"""
GRP CEIP Validaciones contra PEP
================================
""",
    'depends': [ 'grp_plan_ejecucion_presupuestal', 'grp_factura_siif', 'grp_ceip_restricciones_almacen', 'account', ],
    'data': [ 
        'wizard/mensaje_de_advertencia_wizard_view.xml',

        'views/account_invoice_extention_view.xml',
        'views/grp_afectacion_extention_view.xml',
        'views/grp_compras_apg_extention_view.xml',
        'views/res_users_extention_view.xml',
    ],
    'demo': [],
    'test': [],
    'auto_install': False,
    'installable': True,
    'application': True
}
