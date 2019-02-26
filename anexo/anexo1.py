# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import fields, osv




class anexo1_cuenta(osv.osv):
    _name = 'anexo1.cuenta'
    _columns = {
        'anexo_id':fields.many2one('anexo1.anexo', 'ID Anexo1'),
        'codigoCuentas':fields.many2one('account.account', 'Codigo Cuenta Valores Originales'),
        'nombre': fields.char('Nombre de la Cuenta'),
        'codigoCuentaAmortizacion':fields.many2one('account.account', 'Codigo Cuenta Amortizacion'),
        'nombreCuentaAmortizacion': fields.char('Nombre de la Cuenta Amortizacion'),
    }

anexo1_cuenta()


class anexo1_anexo(osv.osv):
    _name = 'anexo1.anexo'
    _columns = {
        'tipo':fields.selection((('BU','Bienes de Uso'), ('INT', 'Intangibles')), 'Tipo'),
        'cuenta_ids': fields.one2many('anexo1.cuenta', 'anexo_id', 'Cuentas'),
    }
anexo1_anexo()
