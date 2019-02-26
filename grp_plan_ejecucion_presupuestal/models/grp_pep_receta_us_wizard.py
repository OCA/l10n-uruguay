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
import logging

_logger = logging.getLogger(__name__)


class grp_pep_receta_us_wizard(models.TransientModel):
    _name = 'grp.pep.receta.us.wizard'

    def _get_cant_nivel_2(self):
        self.cant_nivel_2 = self.env['grp.pep.unidad.de.servicio'].search_count([('estructura_id', '=', self.estructura_id.id),
                                                                                 ('nivel_nro', '=', 2)])

    def _get_cant_nivel_3(self):
        self.cant_nivel_3 = self.env['grp.pep.unidad.de.servicio'].search_count([('estructura_id', '=', self.estructura_id.id),
                                                                                 ('nivel_nro', '=', 3)])

    def _get_cant_nivel_4(self):
        self.cant_nivel_4 = self.env['grp.pep.unidad.de.servicio'].search_count([('estructura_id', '=', self.estructura_id.id),
                                                                                 ('nivel_nro', '=', 4)])

    def _get_cant_nivel_5(self):
        self.cant_nivel_5 = self.env['grp.pep.unidad.de.servicio'].search_count([('estructura_id', '=', self.estructura_id.id),
                                                                                 ('nivel_nro', '=', 5)])

    def _get_cant_nivel_6(self):
        self.cant_nivel_6 = self.env['grp.pep.unidad.de.servicio'].search_count([('estructura_id', '=', self.estructura_id.id),
                                                                                 ('nivel_nro', '=', 6)])

    def _get_cant_nivel_7(self):
        self.cant_nivel_7 = self.env['grp.pep.unidad.de.servicio'].search_count([('estructura_id', '=', self.estructura_id.id),
                                                                                 ('nivel_nro', '=', 7)])

    def _get_cant_nivel_8(self):
        self.cant_nivel_8 = self.env['grp.pep.unidad.de.servicio'].search_count([('estructura_id', '=', self.estructura_id.id),
                                                                                 ('nivel_nro', '=', 8)])

    def _get_cant_nivel_9(self):
        self.cant_nivel_9 = self.env['grp.pep.unidad.de.servicio'].search_count([('estructura_id', '=', self.estructura_id.id),
                                                                                 ('nivel_nro', '=', 9)])

    def _get_cant_nivel_10(self):
        self.cant_nivel_10 = self.env['grp.pep.unidad.de.servicio'].search_count([('estructura_id', '=', self.estructura_id.id),
                                                                                 ('nivel_nro', '=', 10)])

    receta_id = fields.Many2one(string=u'Receta', comodel_name='grp.pep.receta')
    plan_id = fields.Many2one(related='receta_id.plan_id', string='Plan anual')
    estructura_id = fields.Many2one(related='plan_id.estructura_de_servicios_id', string=u'Estructura de servicios')
    us_nivel_1 = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio',
                                 string="Unidad de servicios",
                                 default=lambda self: self.env['grp.pep.unidad.de.servicio'].search([('estructura_id', '=', self.estructura_id.id)]),
                                 required=False)
    us_nivel_2 = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio', string=" ")
    us_nivel_3 = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio', string=" ")
    us_nivel_4 = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio', string=" ")
    us_nivel_5 = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio', string=" ")
    us_nivel_6 = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio', string=" ")
    us_nivel_7 = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio', string=" ")
    us_nivel_8 = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio', string=" ")
    us_nivel_9 = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio', string=" ")
    us_nivel_10 = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio', string=" ")
    cant_nivel_2 = fields.Integer(string='cantidad nivel 2', compute='_get_cant_nivel_2')
    cant_nivel_3 = fields.Integer(string='cantidad nivel 3', compute='_get_cant_nivel_3')
    cant_nivel_4 = fields.Integer(string='cantidad nivel 4', compute='_get_cant_nivel_4')
    cant_nivel_5 = fields.Integer(string='cantidad nivel 5', compute='_get_cant_nivel_5')
    cant_nivel_6 = fields.Integer(string='cantidad nivel 6', compute='_get_cant_nivel_6')
    cant_nivel_7 = fields.Integer(string='cantidad nivel 7', compute='_get_cant_nivel_7')
    cant_nivel_8 = fields.Integer(string='cantidad nivel 8', compute='_get_cant_nivel_8')
    cant_nivel_9 = fields.Integer(string='cantidad nivel 9', compute='_get_cant_nivel_9')
    cant_nivel_10 = fields.Integer(string='cantidad nivel 10', compute='_get_cant_nivel_10')

    def guardo_path_niveles(self):
        path_niveles = ''
        if self.us_nivel_1:
            path_niveles = self.us_nivel_1.nivel_id.name
        if self.us_nivel_2:
            path_niveles = path_niveles + '|' + self.us_nivel_2.nivel_id.name
        if self.us_nivel_3:
            path_niveles = path_niveles + '|' + self.us_nivel_3.nivel_id.name
        if self.us_nivel_4:
            path_niveles = path_niveles + '|' + self.us_nivel_4.nivel_id.name
        if self.us_nivel_5:
            path_niveles = path_niveles + '|' + self.us_nivel_5.nivel_id.name
        if self.us_nivel_6:
            path_niveles = path_niveles + '|' + self.us_nivel_6.nivel_id.name
        if self.us_nivel_7:
            path_niveles = path_niveles + '|' + self.us_nivel_7.nivel_id.name
        if self.us_nivel_8:
            path_niveles = path_niveles + '|' + self.us_nivel_8.nivel_id.name
        if self.us_nivel_9:
            path_niveles = path_niveles + '|' + self.us_nivel_9.nivel_id.name
        if self.us_nivel_10:
            path_niveles = path_niveles + '|' + self.us_nivel_10.nivel_id.name
        self.receta_id.path_por_niveles = path_niveles

    @api.multi
    def guardar_path(self):
        path = ''
        if self.us_nivel_10:
            path = self.us_nivel_10.path
        elif self.us_nivel_9:
            path = self.us_nivel_9.path
        elif self.us_nivel_8:
            path = self.us_nivel_8.path
        elif self.us_nivel_7:
            path = self.us_nivel_7.path
        elif self.us_nivel_6:
            path = self.us_nivel_6.path
        elif self.us_nivel_5:
            path = self.us_nivel_5.path
        elif self.us_nivel_4:
            path = self.us_nivel_4.path
        elif self.us_nivel_3:
            path = self.us_nivel_3.path
        elif self.us_nivel_2:
            path = self.us_nivel_2.path
        elif self.us_nivel_1:
            path = self.us_nivel_1.path
        self.receta_id.path = path.split('| ', 1)[1]
        self.guardo_path_niveles()
        self.receta_id.computo_niveles()
        return True

grp_pep_receta_us_wizard()
