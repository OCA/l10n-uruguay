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


class GrpTipoValoresCustodia(models.Model):
    _name = 'grp.tipo_valores_custodias'
    _description = u'Catalogo de tipo de valores en custodia'

    name = fields.Char(string=u'Tipo', size=30, required=True, index=True)
    active = fields.Boolean(string='Activo', default=True)
    efectivo = fields.Boolean(string='Efectivo')
    transferencia = fields.Boolean(string='Transferencia')
    account_id = fields.Many2one('account.account', string="Cuenta contable", required=True)
    product_id = fields.Many2one('product.product', string="Producto", required=True)

    @api.constrains('name')
    def _check_name(self):
        for record in self:
            name = self.search([('name', '=', record.name), ('id', 'not in', self.ids)])

            if name:
                raise exceptions.ValidationError(_(u'El nombre de tipo de valores debe ser único.'))

    @api.constrains('efectivo','transferencia')
    def _check_name(self):
        for rec in self:
            if rec.transferencia and rec.efectivo:
                raise exceptions.ValidationError(_(u"Un Catálogo de tipo de valores en custodia no puede ser de 'Efectivo' y 'Transferencia' al mismo tiempo"))


class GrpAccountJournal(models.Model):
    _inherit = "account.journal"

    type = fields.Selection(selection_add=[('valores_custodia', 'Valores en custodia')])
