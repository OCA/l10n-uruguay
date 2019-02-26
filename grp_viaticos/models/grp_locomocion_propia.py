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

from openerp import models, fields, exceptions, api, _
import openerp.addons.decimal_precision as dp
import logging
import time

_logger = logging.getLogger(__name__)

# TODO: SPRING 11 GAP 25 K
class GrpLocomocionPropia(models.Model):
    _name = 'grp.locomocion.propia'
    _descripcion = u'Locomoción propia'

    # definicion de campos
    name = fields.Char(string=u'Nombre')
    fecha_desde = fields.Date(string=u'Fecha Desde', required=True)
    fecha_hasta = fields.Date(string=u'Fecha Hasta', required=True)
    relacion_km = fields.Float(string=u'Relación KM por Litros', required=True)
    product_id = fields.Many2one('product.product',domain=[('viatico_ok', '=', True)], required=True,string=u'Producto')
    activo = fields.Boolean(string=u'Activo', default=True)

    # Pestaña Valor Nafta
    valor_nafta_ids = fields.One2many('grp.valor.nafta', 'locomocion_propia_id',string=u'Valor nafta')

# TODO: SPRING 11 GAP 25 K
class GrpValorNafta(models.Model):
    _name = 'grp.valor.nafta'
    _descripcion = u'Valor nafta'


    fecha_desde = fields.Date(string=u'Fecha Desde', required=True)
    importe = fields.Float(string=u'Importe', required=True)
    locomocion_propia_id = fields.Many2one('grp.locomocion.propia', ondelete='cascade',
                                                string=u'Locomoción propia',required=True)



