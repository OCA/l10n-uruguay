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

import openerp
from openerp import models, fields, api, _


# TODO Spring 5 GAP 51: Agregando a la clase calendar.event los datos del viaje
class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    def get_search_fields(self, browse_event, order_fields, r_date=None):
        sort_fields = {}
        for ord in order_fields:
            if ord == 'id' and r_date:
                sort_fields[ord] = '%s-%s' % (browse_event[ord], r_date.strftime("%Y%m%d%H%M%S"))
            else:
                sort_fields[ord] = browse_event[ord]
                if type(browse_event[ord]) is openerp.osv.orm.browse_record:
                    name_get = browse_event[ord].name_get()
                    if len(name_get) and len(name_get[0]) >= 2:
                        sort_fields[ord] = name_get[0][1]
        if r_date:
            sort_fields['sort_start'] = r_date.strftime("%Y%m%d%H%M%S")
        elif browse_event['display_start']:
            sort_fields['sort_start'] = browse_event['display_start'].replace(' ', '').replace('-', '')
        return sort_fields

    employee_ids = fields.Many2many('hr.employee', 'calendar_event_hr_employee_rel',
                                   'calendar_event_id', 'hr_employee_id', 'Empleados')
    target = fields.Char('Destino', size=30)
    vehicle_type = fields.Selection([('auto', 'Auto'), ('van', 'Camioneta')], 'Tipo de vehículo')
    date_travel = fields.Datetime('Fecha y hora')
    estimated_duration = fields.Char('Duración estimada', size=20)
    driver_id = fields.Many2one('grp.fleet.chofer', 'Chofer')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehículo')
    is_travel = fields.Boolean('Corresponde a viaje?', compute='_compute_is_travel', store=True)
    travel_create = fields.Boolean('Creado por solicitud de viaje?', default=False)

    # TODO Spring 5 GAP 52
    state_travel = fields.Selection([('pending', 'Pendiente'), ('done', 'Realizado'), ('undone', 'No realizado')], 'Estado',
                                    default='pending')
    travel_done = fields.Selection([('si', 'Si'), ('no', 'No')], 'Viaje realizado?', default='si')

    date_travel_str = fields.Char('Fecha y hora')

    @api.multi
    @api.depends('categ_ids')
    def _compute_is_travel(self):
        for rec in self:
            rec.is_travel = len(rec.categ_ids.filtered(lambda x: x.name == 'Viajes')) > 0

    @api.onchange('date_travel')
    def _onchange_date_travel(self):
        self.date_travel_str = str(self.date_travel) if self.date_travel else ''

    # TODO Spring 5 GAP 52
    @api.multi
    def action_register_travel(self):
        for rec in self:
            if rec.travel_done == 'si':
                rec.write({'state_travel': 'done'})
            else:
                rec.write({'state_travel': 'undone'})
