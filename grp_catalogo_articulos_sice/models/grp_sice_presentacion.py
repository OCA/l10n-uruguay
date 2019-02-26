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


class grpSicePresentacion(models.Model):

    # Atributos privados
    _name = 'grp.sice_presentacion'
    _order = "cod"
    _rec_name = 'descripcion'
    _description = u'Presentaciones de artículos SICE'

    # Declaración de campos
    # Campos SICE
    cod = fields.Integer(string=u'Código de presentación', required=True, index=True)
    descripcion = fields.Char(string=u'Descripción', size=60, required=True, index=True)
    unme_id  = fields.Many2one('grp.sice_unidades_med', string='Unidad de medida', required=True)
    # unme_cod = fields.Integer(related='unme_id.cod', string=u'Código de unidad de medida')

    fecha_baja = fields.Date(string='Fecha de baja')
    motivo_baja = fields.Char(string='Motivo de baja', size=200)
    # Campos GRP
    active = fields.Boolean(string='Activo', default=True)

    unme_cod = fields.Integer(related='unme_id.cod', string=u'Código de unidad de medida', store=True, index=True)

    # Restricciones SQL
    _sql_constraints = [
        ("unique_sice_presentacion_cod", "unique(cod)", u"Ya existe una presentación con el mismo código"),
    ]

    # Métodos CRUD (y sobreescrituras de name_get, name_search, etc)
