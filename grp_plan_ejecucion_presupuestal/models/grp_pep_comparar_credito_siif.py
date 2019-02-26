# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 Datamatic. All rights reserved.
#    @author Roberto Garcés
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

from openerp import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class grp_pep_comparar_credito_siif(models.Model):
    _name = 'grp.pep.comparar.credito.siif'
    _order = "llave_nombre"

    plan_id = fields.Many2one(comodel_name='grp.pep.anual', string=u'Plan Anual')
    plan_state = fields.Selection(related='plan_id.state', string=u'Estado', readonly=True)
    llave_id = fields.Many2one(comodel_name='grp.pep.concepto.linea.gasto', string='Llave_id')
    llave_nombre = fields.Char(string='Llave presupuestal')
    monto_anual = fields.Float(string='Monto anual')
    credito_disponible = fields.Float(string=u'Crédito disponible')
    es_mayor_al_credito = fields.Boolean(string='El importe supera el crédito', compute='_compute_es_mayor_al_credito')
    observaciones = fields.Text(string='Observaciones')
    concepto_ids = fields.One2many(string=u'Conceptos involucrados', comodel_name='grp.pep.comparar.credito.siif.linea',
                                   inverse_name='comparar_id', copy=True)

    @api.one
    def _compute_es_mayor_al_credito(self):
        self.es_mayor_al_credito = (self.monto_anual > self.credito_disponible)

    @api.multi
    def abrir_comparar_conceptos(self):
        wiz_id = self.env['grp.pep.comparar.conceptos.wizard'].create({
            'comparar_id': self.id,})
        return {
            'name': "Llaves presupuestales del concepto %s" % self.concepto_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.presupuestal.llaves.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

grp_pep_comparar_credito_siif()


class grp_pep_comparar_credito_siif_linea(models.Model):
    _name = 'grp.pep.comparar.credito.siif.linea'

    comparar_id = fields.Many2one(comodel_name='grp.pep.comparar.credito.siif', string='Cabezal')
    concepto_id = fields.Many2one(comodel_name='grp.pep.concepto', string='Concepto')
    importe_concepto = fields.Float(compute='_compute_importe', string=u'Importe')

    @api.one
    def _compute_importe(self):
        importe = 0
        for llave in self.concepto_id.lineas_gasto:
            if llave.display_name == self.comparar_id.llave_nombre:
                importe = importe + (self.concepto_id.importe * llave.porcentaje_del_gasto / 100)
        self.importe_concepto = importe

grp_pep_comparar_credito_siif_linea()
