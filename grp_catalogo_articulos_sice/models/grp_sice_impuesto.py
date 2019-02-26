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

import logging
import openerp
from openerp import api, exceptions, fields, models
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class grpSiceImpuesto(models.Model):

    # Atributos privados
    _name = 'grp.sice_impuesto'
    _order = 'cod'
    _rec_name = 'descripcion'
    _description = u'Impuesto de artículos SICE'

    # Declaración de campos
    # Campos SICE
    cod = fields.Integer(string=u'Código de impuesto', required=True, index=True)
    descripcion = fields.Char(string=u'Descripción', size=30, required=True, index=True)
    fecha_baja = fields.Date(string='Fecha de baja')
    motivo_baja = fields.Char(string='Motivo de baja', size=200)
    porcentaje_ids = fields.One2many('grp.sice_porc_impuesto', 'imp_id', 'Valores de porcentajes del impuesto')

    # Campos GRP
    active = fields.Boolean(string='Activo', default=True)


    # Restricciones SQL
    _sql_constraints = [
        ("unique_sice_impuesto_cod", "unique(cod)", u"Ya existe un código de impuesto con el mismo código"),
    ]

    # Métodos CRUD (y sobreescrituras de name_get, name_search, etc)


class grpSicePorcImpuesto(models.Model):

    # Atributos privados
    _name = 'grp.sice_porc_impuesto'
    _description = u'Valor en porcentaje del impuesto de artículos SICE'

    # Declaración de campos
    imp_id = fields.Many2one('grp.sice_impuesto', string='Impuesto', required=True)
    imp_cod = fields.Integer(related='imp_id.cod', string=u'Código de impuesto')
    # imp_cod = fields.Integer(related='imp_id.cod', string=u'Código de impuesto', store=True, index=True)
    fecha_vigencia = fields.Date(string='Fecha de vigencia', required=True)
    porcentaje = fields.Float(string='Porcentaje', digits=(4,2), required=True)

    # Restricciones SQL
    _sql_constraints = [
        ("unique_sice_porc_impuesto", "unique(imp_id, fecha_vigencia)", u"Ya existe un valor de porcentaje de impuesto para la misma fecha de vigencia"),
    ]

    # Métodos CRUD (y sobreescrituras de name_get, name_search, etc)
