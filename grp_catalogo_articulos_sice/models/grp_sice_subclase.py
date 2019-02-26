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


class grpSiceSubClase(models.Model):

    # Atributos privados
    _name = 'grp.sice_subclase'
    _order = "fami_id, subf_id, clas_id, name"
    _description = u'SubClases de artículos SICE'

    # Declaración de campos
    # Campos SICE
    fami_id = fields.Many2one('grp.sice_familia', string='Familia', required=True)
    # fami_cod = fields.Integer(related='fami_id.cod', string=u'Código de Familia')

    subf_id = fields.Many2one('grp.sice_subflia', string='Subfamilia', required=True)
    # subf_cod = fields.Integer(related='subf_id.cod', string=u'Código de Subfamilia')

    clas_id = fields.Many2one('grp.sice_clase', string='Clase', required=True)
    # clas_cod = fields.Integer(related='clas_id.cod', string=u'Código de Clase')

    name = fields.Char(compute='_concatenar', string=u'Subclase', size=255, store=True)
    cod = fields.Integer(string=u'Código de Subclase', required=True, index=True)
    descripcion = fields.Char(string=u'Subclase', size=255, required=True, index=True)
    fecha_baja = fields.Date(string='Fecha de baja')
    motivo_baja = fields.Char(string='Motivo de baja', size=200)
    # Campos GRP
    active = fields.Boolean(string='Activo', default=True)
    modificado = fields.Boolean(string='Modificado', default=False)

    fami_cod = fields.Integer(related='fami_id.cod', string=u'Código de Familia', store=True, index=True)
    subf_cod = fields.Integer(related='subf_id.cod', string=u'Código de Subfamilia', store=True, index=True)
    clas_cod = fields.Integer(related='clas_id.cod', string=u'Código de Clase', store=True, index=True)

    # Restricciones SQL
    _sql_constraints = [
        ("unique_subclase_sice", "unique(fami_cod, subf_cod, clas_cod, cod)", u"Código de familia/subfamilia/clase/subclase debe ser único"),
    ]

    # Métodos CRUD (y sobreescrituras de name_get, name_search, etc)
    @api.one
    @api.depends('cod', 'descripcion')
    def _concatenar(self):
        self.name = str(self.cod) + '-' + self.descripcion
