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

from datetime import datetime
from openerp.osv import osv, fields, expression
from openerp import models, fields, api, _, exceptions
from openerp import tools
import psycopg2
from openerp import SUPERUSER_ID
import re

class GrpSeleccionVariantes(models.TransientModel):
    _name = 'grp.seleccion.variantes'

    product_variant_ids = fields.One2many(
        comodel_name='grp.seleccion.variantes.lineas',
        string=u'Líneas de selección de variantes',
        inverse_name='seleccion_id'
    )

    @api.multi
    def crear_variantes(self):
        # Mapeo de los datos del Artículo SICE
        for object in self:
            context = {}
            # Calcular las variantes a crear (adoptarlo del codigo estandar)
            lista_variantes = []  # (0, 0, {valores})
            context['default_product_variant_ids'] = lista_variantes

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'grp.seleccion.variantes',
            'target': 'new',
            'context': context,
        }

class GrpSeleccionVariantesLineas(models.TransientModel):
    _name = 'grp.seleccion.variantes.lineas'

    seleccion_id = fields.Many2one(
        comodel_name='grp.seleccion.variantes',
        string=u'Selección de variantes'
    )
    para_crear = fields.Boolean(u'Para Crear')
    producto_id = fields.Many2one(
        comodel_name='product.product',
        string=u'Producto'
    )
    med_cod_id = fields.Many2one('grp.sice_medida', string=u'Medida de la variante')
    pres_id = fields.Many2one('grp.sice_presentacion', string='Presentacion')
    med_cod_pres_id = fields.Many2one('grp.sice_medida', string=u'Medida de la presentación')
    det_variante_id = fields.Many2one('grp.sice_det_variante', string='Detalle de variante')
    sice_color_id = fields.Many2one('grp.sice_color', string='Color SICE')

    med_cod_desc = fields.Char(string=u'Medida variante')
    pres_desc = fields.Char(string=u'Presentación')
    med_cod_pres_desc = fields.Char(string=u'Medida presentación')
    det_variante_desc = fields.Char(string=u'Detalle variante')
    sice_color_desc = fields.Char(string=u'Color')
    marca_desc = fields.Char(string=u'Marca')

