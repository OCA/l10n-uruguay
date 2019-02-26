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
    'name':     u'GRP - Account',
    'author':   'Quanam',
    'website':  'http://www.quanam.com',
    'category': 'GRP',
    'license':  'AGPL-3',
    'version':  '1.0',
    'description': u"""
GRP - Account
=================================

* Consulta Líneas Registro de Caja
* Agrega campos de banco y sucursal en extracto bancario
* Quita restricción de multicompañía

""",
    'depends' : ['account', 'account_voucher','grp_compras_estatales'],
    'data': [
        'security/ir.model.access.csv',
        'views/grp_inherit_account_bank_view.xml',
        'views/grp_inherit_account_bank_statement.xml',
        'views/grp_dimension_multiproposito_view.xml',
        'views/grp_combinacion_cuentas_contables_view.xml',
        'views/grp_aprobacion_pagos.xml',
        'views/grp_inherit_account_voucher_view.xml',
        'wizard/grp_aprobar_pago_view.xml',
        'views/grp_inherit_account_invoice_view.xml',
        'views/grp_inherit_account_analytic_account_view.xml',
        'security/grp_account_security.xml',
    ],
    'auto_install': False,
    'installable': True,
    'application': True
}
