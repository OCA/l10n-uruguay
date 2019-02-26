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
# TODO: C SPRING 13 GAP_365_367_368
from openerp import models, fields, api, exceptions, _
from openerp import tools


class GrpCantidadViajesPeriodoReport(models.Model):
    _name = 'grp.cantidad.viajes.periodo.report'
    _auto = False
    _description = u'Cantidad de viajes por período'

    employee_id = fields.Many2one('hr.employee', string='Solicitante')
    travel_date = fields.Datetime('Fecha y hora')
    driver_id = fields.Many2one('grp.fleet.chofer', 'Chofer')
    target = fields.Char('Destino', size=30)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('to_approve', u'En Aprobación'),
        ('approved', 'Aprobada'),
        ('validate', 'Validada'),
        ('close', 'Cerrada')])
    cantidad_viaje = fields.Integer('Cantidad de viajes')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_cantidad_viajes_periodo_report')
        cr.execute("""
            CREATE OR replace VIEW grp_cantidad_viajes_periodo_report AS (
                SELECT
                    viaje.id AS id,
                    viaje.employee_id AS employee_id,
                    viaje.date AS travel_date,
                    viaje.driver_id AS driver_id,
                    viaje.target AS target,
                    1 AS cantidad_viaje,
                    viaje.state AS state
                    FROM grp_flota_solicitud_viaje viaje
                    where viaje.state = 'validate'
            )
        """)
