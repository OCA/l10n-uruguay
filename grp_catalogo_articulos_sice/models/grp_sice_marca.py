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


class grpSiceMarca(models.Model):

    # Atributos privados
    _name = 'grp.sice_marca'
    _rec_name = 'descripcion'
    _description = u'Marca de artículos SICE'

    # Declaración de campos
    # Campos SICE
    cod = fields.Integer(string=u'Código de marca', required=True, index=True)
    descripcion = fields.Char(string=u'Descripción', size=40, required=True, index=True)
    fecha_baja = fields.Date(string='Fecha de baja')
    motivo_baja = fields.Char(string='Motivo de baja', size=200)
    # Campos GRP
    active = fields.Boolean(string='Activo', default=True)

    # Restricciones SQL
    _sql_constraints = [
        ("unique_sice_marca_cod", "unique(cod)", u"Ya existe una marca con el mismo código"),
    ]

    # Métodos CRUD (y sobreescrituras de name_get, name_search, etc)
