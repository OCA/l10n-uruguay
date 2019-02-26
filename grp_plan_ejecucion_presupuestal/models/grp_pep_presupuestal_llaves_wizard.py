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
from openerp.exceptions import Warning, ValidationError
import openerp.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)


class grp_pep_presupuestal_llaves_wizard(models.TransientModel):
    _name = 'grp.pep.presupuestal.llaves.wizard'

    display_readonly = fields.Boolean()
    concepto_id = fields.Many2one(string=u'Concepto', comodel_name='grp.pep.concepto', readonly=True)
    linea_concepto_id = fields.Many2one(comodel_name='grp.pep.anual.linea.concepto')
    periodo_activo = fields.Integer(string=u'Período activo')
    llave_ids = fields.One2many(comodel_name='grp.pep.presupuestal.llaves.lineas.wizard', inverse_name='wizard_id',
                                string=u'Llave presupuestal')
    periodo_ids = fields.One2many(comodel_name='grp.pep.presupuestal.llaves.periodos.wizard', inverse_name='wizard_id',
                                  string=u'Llave presupuestal - Períodos')

    @api.model
    def create(self, values):
        res = super(grp_pep_presupuestal_llaves_wizard, self).create(values)
        for linea in res.concepto_id.lineas_gasto:
            llave_id = self.env['grp.pep.presupuestal.llaves.lineas.wizard'].create({'wizard_id': res.id,
                                                                                     'llave_id': linea.id,
                                                                                     'nombre': linea.display_name,
                                                                                     'porcentaje': linea.porcentaje_del_gasto,
                                                                                     'importe': res.concepto_id.importe * linea.porcentaje_del_gasto / 100
                                                                                     })
            periodo_id = self.env['grp.pep.presupuestal.llaves.periodos.wizard'].create({'wizard_id': res.id,
                                                                                         'llave_id': linea.id,
                                                                                         'nombre_llave': linea.display_name,
                                                                                         'porcentaje_llave': linea.porcentaje_del_gasto,
                                                                                         })
        return res

    def _suman_100(self):
        total = 0
        for linea in self.llave_ids:
            total = total + linea.porcentaje
        if round(total, 2) < 0 or round(total, 2) > 100:
            raise ValidationError(u"La suma de los porcentajes no puede ser inferior a 0 o superior a 100.")
        return True

    def _no_cero(self):
        for linea in self.llave_ids:
            if linea.porcentaje <= 0:
                raise ValidationError(u"Todos los porcentajes deben ser mayores a 0.")
        return True

    @api.one
    def actualizar_periodos(self, llave_id, porcentaje):
        for linea in self.periodo_ids:
            if linea.llave_id.id == llave_id.id:
                linea.actualizar_importes(porcentaje)

    @api.multi
    def button_actualizar_periodos(self):
        self.ensure_one()
        for linea in self.llave_ids:
            self.actualizar_periodos(linea.llave_id, linea.porcentaje)
        xml_id_obj = self.env['ir.model.data']
        vista = 'grp_pep_presupuestal_llaves_'+self.concepto_id.plan_id.periodicidad+'_wizard'
        view_id = xml_id_obj.get_object_reference('grp_plan_ejecucion_presupuestal', vista)[1]
        return {
            'name': "Llaves presupuestales del concepto %s" % self.concepto_id.name,
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'grp.pep.presupuestal.llaves.wizard',
            'res_id': self.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    @api.multi
    def guardar_llaves(self):
        if self._suman_100() and self._no_cero():
            for linea in self.llave_ids:
                linea.llave_id.porcentaje_del_gasto = linea.porcentaje

grp_pep_presupuestal_llaves_wizard()


class grp_pep_presupuestal_llaves_lineas_wizard(models.TransientModel):
    _name = 'grp.pep.presupuestal.llaves.lineas.wizard'

    wizard_id = fields.Many2one('grp.pep.presupuestal.llaves.wizard', string='Wizard')
    llave_id = fields.Many2one(comodel_name='grp.pep.concepto.linea.gasto', string='Llave_id')
    nombre = fields.Char(string='Llave', readonly=True)
    porcentaje = fields.Float(string='Porcentaje', digits=dp.get_precision('PEP Porcentajes'))
    importe = fields.Float(string='Importe', compute='_compute_importe')
    plan_anual_id = fields.Many2one(related='wizard_id.linea_concepto_id.plan_anual_id', string='Plan', readonly=True)
    plan_state = fields.Selection(related='plan_anual_id.state', string='Estado', readonly=True)

    @api.one
    def _compute_importe(self):
        self.importe = self.wizard_id.concepto_id.importe * self.porcentaje / 100

    @api.one
    @api.onchange('porcentaje')
    def onchange_porcentaje(self):
        if self.porcentaje:
            self.importe = self.wizard_id.concepto_id.importe * self.porcentaje / 100

grp_pep_presupuestal_llaves_lineas_wizard()


class grp_pep_presupuestal_llaves_periodos_wizard(models.TransientModel):
    _name = 'grp.pep.presupuestal.llaves.periodos.wizard'

    wizard_id = fields.Many2one(comodel_name='grp.pep.presupuestal.llaves.wizard', string='Wizard')
    llave_id = fields.Many2one(comodel_name='grp.pep.concepto.linea.gasto', string='Llave_id')
    nombre_llave = fields.Char(string='Llave', readonly=True)
    porcentaje_llave = fields.Float(string='Porcentaje', digits=dp.get_precision('PEP Porcentajes'))
    periodo1_importe = fields.Float(string=u'Período 1', compute='_compute_periodo1_importe')
    periodo2_importe = fields.Float(string=u'Período 2', compute='_compute_periodo2_importe')
    periodo3_importe = fields.Float(string=u'Período 3', compute='_compute_periodo3_importe')
    periodo4_importe = fields.Float(string=u'Período 4', compute='_compute_periodo4_importe')
    periodo5_importe = fields.Float(string=u'Período 5', compute='_compute_periodo5_importe')
    periodo6_importe = fields.Float(string=u'Período 6', compute='_compute_periodo6_importe')
    periodo7_importe = fields.Float(string=u'Período 7', compute='_compute_periodo7_importe')
    periodo8_importe = fields.Float(string=u'Período 8', compute='_compute_periodo8_importe')
    periodo9_importe = fields.Float(string=u'Período 9', compute='_compute_periodo9_importe')
    periodo10_importe = fields.Float(string=u'Período 10', compute='_compute_periodo10_importe')
    periodo11_importe = fields.Float(string=u'Período 11', compute='_compute_periodo11_importe')
    periodo12_importe = fields.Float(string=u'Período 12', compute='_compute_periodo12_importe')

    @api.one
    def _compute_periodo1_importe(self):
        periodo_activo = self.wizard_id.periodo_activo
        if periodo_activo <= 1:
            if 'porcentaje' in self.env.context:
                self.porcentaje_llave = self.env.context.get('porcentaje', False)
            wiz = self.wizard_id
            linea_concepto_id = wiz.linea_concepto_id
            porcentaje_periodo = float(linea_concepto_id.periodo1_porc) / 100
            self.periodo1_importe = (wiz.concepto_id.importe * self.porcentaje_llave / 100) * porcentaje_periodo

    @api.one
    def _compute_periodo2_importe(self):
        periodo_activo = self.wizard_id.periodo_activo
        if periodo_activo <= 2:
            if 'porcentaje' in self.env.context:
                self.porcentaje_llave = self.env.context.get('porcentaje', False)
            wiz = self.wizard_id
            linea_concepto_id = wiz.linea_concepto_id
            porcentaje_periodo = float(linea_concepto_id.periodo2_porc) / 100
            self.periodo2_importe = (wiz.concepto_id.importe * self.porcentaje_llave / 100) * porcentaje_periodo

    @api.one
    def _compute_periodo3_importe(self):
        periodo_activo = self.wizard_id.periodo_activo
        if periodo_activo <= 3:
            if 'porcentaje' in self.env.context:
                self.porcentaje_llave = self.env.context.get('porcentaje', False)
            wiz = self.wizard_id
            linea_concepto_id = wiz.linea_concepto_id
            porcentaje_periodo = float(linea_concepto_id.periodo3_porc) / 100
            self.periodo3_importe = (wiz.concepto_id.importe * self.porcentaje_llave / 100) * porcentaje_periodo

    @api.one
    def _compute_periodo4_importe(self):
        periodo_activo = self.wizard_id.periodo_activo
        if periodo_activo <= 4:
            if 'porcentaje' in self.env.context:
                self.porcentaje_llave = self.env.context.get('porcentaje', False)
            wiz = self.wizard_id
            linea_concepto_id = wiz.linea_concepto_id
            porcentaje_periodo = float(linea_concepto_id.periodo4_porc) / 100
            self.periodo4_importe = (wiz.concepto_id.importe * self.porcentaje_llave / 100) * porcentaje_periodo

    @api.one
    def _compute_periodo5_importe(self):
        periodo_activo = self.wizard_id.periodo_activo
        if periodo_activo <= 5:
            if 'porcentaje' in self.env.context:
                self.porcentaje_llave = self.env.context.get('porcentaje', False)
            wiz = self.wizard_id
            linea_concepto_id = wiz.linea_concepto_id
            porcentaje_periodo = float(linea_concepto_id.periodo5_porc) / 100
            self.periodo5_importe = (wiz.concepto_id.importe * self.porcentaje_llave / 100) * porcentaje_periodo

    @api.one
    def _compute_periodo6_importe(self):
        periodo_activo = self.wizard_id.periodo_activo
        if periodo_activo <= 6:
            if 'porcentaje' in self.env.context:
                self.porcentaje_llave = self.env.context.get('porcentaje', False)
            wiz = self.wizard_id
            linea_concepto_id = wiz.linea_concepto_id
            porcentaje_periodo = float(linea_concepto_id.periodo6_porc) / 100
            self.periodo6_importe = (wiz.concepto_id.importe * self.porcentaje_llave / 100) * porcentaje_periodo

    @api.one
    def _compute_periodo7_importe(self):
        periodo_activo = self.wizard_id.periodo_activo
        if periodo_activo <= 7:
            if 'porcentaje' in self.env.context:
                self.porcentaje_llave = self.env.context.get('porcentaje', False)
            wiz = self.wizard_id
            linea_concepto_id = wiz.linea_concepto_id
            porcentaje_periodo = float(linea_concepto_id.periodo7_porc) / 100
            self.periodo7_importe = (wiz.concepto_id.importe * self.porcentaje_llave / 100) * porcentaje_periodo

    @api.one
    def _compute_periodo8_importe(self):
        periodo_activo = self.wizard_id.periodo_activo
        if periodo_activo <= 8:
            if 'porcentaje' in self.env.context:
                self.porcentaje_llave = self.env.context.get('porcentaje', False)
            wiz = self.wizard_id
            linea_concepto_id = wiz.linea_concepto_id
            porcentaje_periodo = float(linea_concepto_id.periodo8_porc) / 100
            self.periodo8_importe = (wiz.concepto_id.importe * self.porcentaje_llave / 100) * porcentaje_periodo

    @api.one
    def _compute_periodo9_importe(self):
        periodo_activo = self.wizard_id.periodo_activo
        if periodo_activo <= 9:
            if 'porcentaje' in self.env.context:
                self.porcentaje_llave = self.env.context.get('porcentaje', False)
            wiz = self.wizard_id
            linea_concepto_id = wiz.linea_concepto_id
            porcentaje_periodo = float(linea_concepto_id.periodo9_porc) / 100
            self.periodo9_importe = (wiz.concepto_id.importe * self.porcentaje_llave / 100) * porcentaje_periodo

    @api.one
    def _compute_periodo10_importe(self):
        periodo_activo = self.wizard_id.periodo_activo
        if periodo_activo <= 10:
            if 'porcentaje' in self.env.context:
                self.porcentaje_llave = self.env.context.get('porcentaje', False)
            wiz = self.wizard_id
            linea_concepto_id = wiz.linea_concepto_id
            porcentaje_periodo = float(linea_concepto_id.periodo10_porc) / 100
            self.periodo10_importe = (wiz.concepto_id.importe * self.porcentaje_llave / 100) * porcentaje_periodo

    @api.one
    def _compute_periodo11_importe(self):
        periodo_activo = self.wizard_id.periodo_activo
        if periodo_activo <= 11:
            if 'porcentaje' in self.env.context:
                self.porcentaje_llave = self.env.context.get('porcentaje', False)
            wiz = self.wizard_id
            linea_concepto_id = wiz.linea_concepto_id
            porcentaje_periodo = float(linea_concepto_id.periodo11_porc) / 100
            self.periodo11_importe = (wiz.concepto_id.importe * self.porcentaje_llave / 100) * porcentaje_periodo

    @api.one
    def _compute_periodo12_importe(self):
        periodo_activo = self.wizard_id.periodo_activo
        if periodo_activo <= 12:
            if 'porcentaje' in self.env.context:
                self.porcentaje_llave = self.env.context.get('porcentaje', False)
            wiz = self.wizard_id
            linea_concepto_id = wiz.linea_concepto_id
            porcentaje_periodo = float(linea_concepto_id.periodo12_porc) / 100
            self.periodo12_importe = (wiz.concepto_id.importe * self.porcentaje_llave / 100) * porcentaje_periodo

    def actualizar_importes(self, porcentaje):
        self.with_context({'porcentaje': porcentaje})._compute_periodo1_importe()
        self.with_context({'porcentaje': porcentaje})._compute_periodo2_importe()
        self.with_context({'porcentaje': porcentaje})._compute_periodo3_importe()
        self.with_context({'porcentaje': porcentaje})._compute_periodo4_importe()
        self.with_context({'porcentaje': porcentaje})._compute_periodo5_importe()
        self.with_context({'porcentaje': porcentaje})._compute_periodo6_importe()
        self.with_context({'porcentaje': porcentaje})._compute_periodo7_importe()
        self.with_context({'porcentaje': porcentaje})._compute_periodo8_importe()
        self.with_context({'porcentaje': porcentaje})._compute_periodo9_importe()
        self.with_context({'porcentaje': porcentaje})._compute_periodo10_importe()
        self.with_context({'porcentaje': porcentaje})._compute_periodo11_importe()
        self.with_context({'porcentaje': porcentaje})._compute_periodo12_importe()

grp_pep_presupuestal_llaves_periodos_wizard()
