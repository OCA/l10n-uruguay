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

from openerp import models, fields, api, exceptions
from openerp.tools.translate import _
from datetime import *


# TODO: M SPRING 13 GAP 281

class GrpTipoRendicion(models.Model):
    _name = 'grp.tipo.rendicion'
    _description = u"Mapeo productos para rendición"

    type = fields.Selection([('recaudacion',u'Recaudación'),
                             ('fondos_terceros',u'Fondos de terceros'),
                             ('pagos',u'Pagos'),
                             ('fondos_garantia',u'Fondos de garantía')], 'Tipo')
    product_ids = fields.Many2many('product.product',
                                          'product_grp_tipo_rendicion_rel',
                                          'producto_id', 'tipo_rendicion_id', 'Productos')
    concept_ids = fields.Many2many('grp_concepto_gasto_cc_viaticos', 'concepto_gasto_cc_viaticos_tipo_rendicion_rel',
                                          'concepto_id', 'tipo_rendicion_id', 'Conceptos')
    code = fields.Char(u'Código recaudación',size=20)

    @api.multi
    def name_get(self):
        result = []
        tipos_dict = {'recaudacion': u'Recaudación',
                      'fondos_terceros': u'Fondos de terceros',
                      'pagos': u'Pagos',
                      'fondos_garantia': u'Fondos de garantía'}
        for rec in self:
            nombre = tipos_dict.get(rec.type, '')
            result.append((rec.id, nombre))
        return result

    @api.constrains('type')
    def _check_type(self):
        for rec in self:
            rendicion = self.search([('type', '=', rec.type)])
            if rendicion and len(rendicion.ids) > 1:
                raise exceptions.ValidationError(_(u'Solo debe existir un registro por tipo.'))

    @api.constrains('product_ids')
    def _check_product(self):
        for rec in self:
            rendicion = self.search([('product_ids', '=', rec.product_ids.ids)])
            if rendicion and len(rendicion.ids) > 1:
                raise exceptions.ValidationError(_(u'El mismo producto no puede estar en mas de un registro.'))

    @api.constrains('concept_ids')
    def _check_concept(self):
        for rec in self:
            rendicion = self.search([('concept_ids', '=', rec.concept_ids.ids)])
            if rendicion and len(rendicion.ids) > 1:
                raise exceptions.ValidationError(_(u'El mismo concepto no puede estar en mas de un registro.'))







