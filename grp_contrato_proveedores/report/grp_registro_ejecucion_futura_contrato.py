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
# TODO: SPRING 11 GAP 495 K

from openerp import fields, models, api
from openerp import tools
import openerp.addons.decimal_precision as dp

# TODO: K SPRING 13 GAP 452
class grp_registro_ejecucion_futura_contrato(models.Model):
    _name = 'grp.registro.ejecucion.futura.contrato'

    id_ejecucion = fields.Char(string=u"Id. ejecución")
    contrato_id = fields.Many2one('grp.contrato.proveedores', 'Contrato')
    nro_interno = fields.Char(related='contrato_id.nro_interno',string=u"Número Contrato", readonly=True)
    proveedor = fields.Many2one('res.partner', related='contrato_id.proveedor', string=u"Proveedor", readonly=True)
    moneda = fields.Char(string=u"Moneda")
    monto_ajustado = fields.Float(string='Monto contrato ajustado', digits_compute=dp.get_precision('Account'))
    monto_facturar = fields.Float(string='Saldo pendiente', digits_compute=dp.get_precision('Account'))
    monto_ejecutar_actual = fields.Float(string='Monto a ejecutar ejercicio actual',
                                         digits_compute=dp.get_precision('Account'))
    monto_ejecutar_futuro = fields.Float(string='Monto a ejecutar ejercicios futuros',
                                         digits_compute=dp.get_precision('Account'))
    tipo_cambio = fields.Float(string='Tipo de cambio', digits_compute=dp.get_precision('Account'))
    monto_ejecutar_fut_pesos = fields.Float(string='Monto a ejecutar ej. futuros (pesos)',
                                         digits_compute=dp.get_precision('Account'))
