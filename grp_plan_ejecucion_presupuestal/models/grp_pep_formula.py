# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2018 Datamatic All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, tools
from openerp.exceptions import Warning, ValidationError


class grp_pep_formula_linea(models.Model):
    _name = 'grp.pep.formula.linea'
    _order = 'sequence'

    sequence = fields.Integer(string='Secuencia')
    parent_concepto_id = fields.Many2one(string=u'Concepto', comodel_name='grp.pep.concepto', ondelete='cascade')
    operador_linea = fields.Selection(string='', selection=[('+','+'),('-','-')], required=True)
    concepto_id = fields.Many2one(string='Concepto', comodel_name='grp.pep.concepto', required=True)
    concepto_importe = fields.Float(related='concepto_id.importe', string='Concepto importe', readonly=True)
    operador_interno = fields.Selection(string='', selection=[('*','*'),('/','/')], required=True)
    coeficiente = fields.Float(string='Coeficiente', required=True)
    subtotal = fields.Float(string='Subtotal', compute='compute_subtotal')

    def _eval_subtotal(self):
        expresion = self.operador_linea
        expresion = expresion + str(self.concepto_id.importe)
        expresion = expresion + self.operador_interno
        expresion = expresion + str(self.coeficiente)
        return eval(expresion)

    @api.onchange('operador_linea', 'concepto_id', 'operador_interno', 'coeficiente')
    def _refresh_subtotal(self):
        if self.operador_linea and self.concepto_id and self.operador_interno and self.coeficiente:
            self.subtotal = self._eval_subtotal()

    @api.multi
    # @api.depends('operador_linea', 'concepto_id', 'operador_interno', 'coeficiente')
    def compute_subtotal(self):
        for record in self:
            if record.operador_linea and record.concepto_id and record.operador_interno and record.coeficiente:
                record.subtotal = record._eval_subtotal()

    @api.one
    @api.constrains('coeficiente')
    def _coeficiente_no_cero(self):
        if self.coeficiente == 0:
            raise ValidationError(u"El coeficiente debe ser distinto de 0")

grp_pep_formula_linea()
