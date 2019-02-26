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

from openerp import models, fields, api, exceptions, _
from openerp import tools

# TODO: L SPRING 13 GAP 370
class GrpRendimientoVehiculoReport(models.Model):
    _name = 'grp.rendimiento.vehiculo.report'
    _auto = False
    _description = u'Reporte rendimiento por vehículo'

    vehicle_id = fields.Many2one('fleet.vehicle', string=u'Vehículo')
    fecha = fields.Date(string=u'Fecha')
    purchaser_id = fields.Many2one('res.partner', u'Comprador')
    km = fields.Float(string=u'Km')
    litro = fields.Float(string=u'Litro')
    rendimiento = fields.Float(string=u'Rendimiento')
    precio_total = fields.Float(string=u'Precio total')

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_rendimiento_vehiculo_report')
        cr.execute("""
            CREATE OR replace VIEW grp_rendimiento_vehiculo_report AS (
                SELECT
                    t2.id AS id,
                    t1.vehicle_id AS vehicle_id,
                    t1.date AS fecha,
                    t2.purchaser_id AS purchaser_id,
                    t5.value AS km,
                    t2.rendimiento AS rendimiento,
                    t2.liter AS litro,
                    t1.amount AS precio_total
                    FROM fleet_vehicle_cost t1
                    INNER JOIN fleet_vehicle_log_fuel t2 ON t1.id = t2.cost_id
                    INNER JOIN fleet_vehicle t3 ON t1.vehicle_id = t3.id
                    LEFT JOIN res_partner t4 ON t2.purchaser_id = t4.id
                    LEFT JOIN fleet_vehicle_odometer t5 ON t1.odometer_id = t5.id
            )
        """)
