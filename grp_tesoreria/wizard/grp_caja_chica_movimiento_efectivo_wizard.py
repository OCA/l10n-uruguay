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

from openerp import models, fields, api, exceptions
from lxml import etree

_logger = logging.getLogger(__name__)


# TODO: SPRING 10 GAP 474 C

class GrpCajaChicaTesoreriaMovEfectivo(models.Model):
    _name = 'grp.caja.chica.movimiento.efectivo'

    @api.model
    def default_get(self, fields):
        res = super(GrpCajaChicaTesoreriaMovEfectivo, self).default_get(fields)
        if self._context.get('caja_id', False):
            caja_id = self._context.get('caja_id', False)
            res['operating_unit_id'] = self.env['grp.caja.chica.tesoreria'].search(
                [('id', '=', caja_id)]).operating_unit_id.id
        return res

    @api.model
    def _domain_operating_unit_id(self):
        caja_chica_id = self._context.get('default_caja_chica_id', False)
        if caja_chica_id:
            operating_unit_ids = self.env['grp.caja.chica.tesoreria'].search([('id','=',caja_chica_id)], limit=1).box_id.operating_unit_ids.ids
        else:
            operating_unit_ids = []
        return [('id', 'in', operating_unit_ids)]

    wizard_id = fields.Many2one('grp.caja_chica.mov_efectivo.wizard', 'Wizard')
    concept_cc_id = fields.Many2one('grp_concepto_gasto_cc_viaticos', "Concepto", required=True,
                                    domain=[('caja_chica_t', '=', True)])
    partner_id = fields.Many2one('res.partner', "Proveedor")
    operating_unit_id = fields.Many2one('operating.unit', string="Unidad Ejecutora", required=True,
                                        domain=lambda self: self._domain_operating_unit_id())
    dimension_id = fields.Many2one('account.analytic.plan.instance', "Dimensiones", required=False)
    date = fields.Date(string='Fecha', required=True, default=lambda *a: fields.Date.today())
    amount = fields.Float(string='Importe', required=True)

    @api.multi
    def edit_mov(self):
        return True

    @api.multi
    def write(self, vals):
        mov = super(GrpCajaChicaTesoreriaMovEfectivo, self).write(vals)
        values = {}
        for k, v in vals.iteritems():
            values.update({k: v})
        if 'concept_cc_id' in values:
            concept_id = self.env['grp_concepto_gasto_cc_viaticos'].browse(values['concept_cc_id'])
            name = concept_id.name
            values.update({'ref': name})
        else:
            concept_id = False
        for rec in self:
            if not concept_id:
                concept_id = rec.concept_cc_id
            amount = abs(rec.amount) if concept_id.signo == 'pos' else -abs(rec.amount)
            values.update({'amount': amount, 'concept_cc_id': concept_id.id })
            rec.wizard_id.caja_chica_id.transaction_ids.filtered(lambda x: x.catch_mov_id.id == rec.id).write(values)
        return mov


class grpCajaChicaMovEfectivoWizard(models.Model):
    _name = "grp.caja_chica.mov_efectivo.wizard"

    catch_mov_ids = fields.One2many('grp.caja.chica.movimiento.efectivo', 'wizard_id',
                                    string=u'Movimientos en efectivo')
    caja_chica_id = fields.Many2one('grp.caja.chica.tesoreria', string='Caja chica', ondelete='cascade')

    @api.multi
    def transfer_catch_mov(self):
        transaction_ids = []
        for obj in self.mapped('catch_mov_ids'):
            amount = abs(obj.amount) if obj.concept_cc_id.signo == 'pos' else -abs(obj.amount)
            transaction_ids.append((0, 0, {'catch_mov_id': obj.id,
                                           'concept_cc_id': obj.concept_cc_id.id,
                                           'ref': obj.concept_cc_id.name,
                                           'date': obj.date,
                                           'partner_id': obj.partner_id.id,
                                           'amount': amount}))
        self.caja_chica_id.write({'transaction_ids': transaction_ids})
        return True
