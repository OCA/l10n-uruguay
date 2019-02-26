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

from lxml import etree
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

# TODO SPRING 5 GRP 50

class hrDepartment(models.Model):
    _name = 'hr.department'
    _inherit = 'hr.department'

    travelrequest_destinyrequired = fields.Boolean('Destino requerido en Solicitud de viaje?')


class GrpFlotaSolicitudViaje(models.Model):
    _name = 'grp.flota.solicitud.viaje'
    _inherit = ['mail.thread']
    _description = "Solicitud de viaje"

    @api.model
    def _update_prefix(self):
        sequence= self.env['ir.sequence']
        seq_solicitud_viaje= sequence.search([('code','=','grp_flota_solicitud_viaje')])

        if seq_solicitud_viaje:
            if seq_solicitud_viaje.prefix != '%(fy)s--SV-':
                seq_solicitud_viaje.write({'prefix':'%(fy)s--SV-'})

        return True

    @api.model
    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False, context=None):
        res = super(GrpFlotaSolicitudViaje, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                                  toolbar=toolbar, submenu=submenu)
        sv_crear = self.env['res.users'].has_group('grp_flota.group_fleet_sv_solicitante_viaje')
        doc = etree.XML(res['arch'])

        if not sv_crear:
            for node_form in doc.xpath("//form"):
                node_form.set("create", 'false')
            for node_tree in doc.xpath("//tree"):
                node_tree.set("create", 'false')
        res['arch'] = etree.tostring(doc)
        return res

    @api.model
    def default_department_id(self):
        employee_pool = self.env['hr.employee']
        employee_obj = employee_pool.search([('user_id', '=', self.env.user.id)])
        if len(employee_obj) > 0:
            employee_obj = employee_obj[0]
        return employee_obj.department_id

    name = fields.Char('Nro. Solicitud', default='SV Borrador', readonly=True, required=True)
    employee_ids = fields.Many2many('hr.employee', string='Funcionarios que viajan',
                                    required=True, readonly=True, states={'draft': [('readonly', False)]})
    # employee_id = fields.Many2one('hr.employee', string='Funcionario que viaja', required=True,
    #                               readonly=True, states={'draft': [('readonly', False)]})
    target = fields.Char('Destino', size=30)
    vehicle_type = fields.Selection([('auto', 'Auto'), ('van', 'Camioneta'), ('microbus', 'Microbus')],
                                    u'Tipo de vehículo',
                                    readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Datetime('Fecha y hora', required=True,
                           readonly=True, states={'draft': [('readonly', False)],'approved': [('readonly', False)]})
    estimated_duration = fields.Char('Duración estimada',
                                     readonly=True, states={'draft': [('readonly', False)],'approved': [('readonly', False)] })
    driver_id = fields.Many2one('grp.fleet.chofer', 'Chofer')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehículo', domain=[('state_id.name','=','Operativo')])
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('to_approve', u'En Aprobación'),
        ('approved', 'Aprobada'),
        ('validate', 'Validada'),
        ('close', 'Cerrada')],'Estado', default='draft', track_visibility='onchange')

    #
    edit_fields_onapproved = fields.Boolean('Editar campos en estado aprobado', compute='_compute_edit_fields_onapproved')
    destinyrequired = fields.Boolean('Requerido destino en borrador', compute='_compute_destinyrequired')
    department_id = fields.Many2one(
        comodel_name='hr.department',
        string=u'Departamento',
        default=default_department_id
    )

    @api.multi
    @api.depends('state')
    def _compute_edit_fields_onapproved(self):
        is_responsible = self.pool.get('res.users').has_group(self._cr, self._uid, 'fleet.group_fleet_manager')
        for rec in self:
            rec.edit_fields_onapproved = is_responsible and rec.state == 'approved'

    @api.one
    def _compute_destinyrequired(self):
        employees = self.env['hr.employee'].search([('user_id', '=', self._uid)])
        self.destinyrequired = True if len(filter(lambda emp: emp.department_id.travelrequest_destinyrequired, employees)) else False


    @api.multi
    def action_to_approve(self):
        for rec in self:
            domain = [('date_start', '<=', rec.date), ('date_stop', '>=', rec.date)]
            if self.env.user.company_id and self.env.user.company_id.id:
                domain.append(('company_id','=',self.env.user.company_id.id))
            fiscal_year_id = self.env['account.fiscalyear'].search(domain)
            if fiscal_year_id:
                inciso=self.env.user.company_id.inciso
                sequence = self.env['ir.sequence'].with_context(fiscalyear_id=fiscal_year_id.id).next_by_code('grp_flota_solicitud_viaje')
                _logger.info('sequence %s',sequence)

                ind= sequence.index('-') +1
                name = sequence[0:ind] + inciso + sequence[ind:len(sequence)] or '/'
                rec.write({'state': 'to_approve', 'name': name})
            else:
                raise ValidationError(_(u'No está definido el año fiscal para la fecha seleccionada!'))

    @api.multi
    def action_draft(self):
        for rec in self:
            rec.write({'state': 'draft'})

    @api.multi
    def action_approved(self):
        for rec in self:
            rec.write({'state': 'approved'})

    @api.multi
    def action_validate(self):
        for rec in self:
            if not rec.driver_id or not rec.vehicle_id:
                raise ValidationError(_(u'Debe estar definido el chofer y el vehículo antes de continuar!'))
            rec.write({'state': 'validate'})
            rec.mail_notification()
            rec.create_event()

    @api.multi
    def action_refuse(self):
        self.write({'state': 'close'})

    @api.multi
    def action_cancel(self):
        # TODO: L VARIANZA GRP
        for rec in self:
            if (fields.Datetime.from_string(rec.date) - fields.Datetime.from_string(fields.Datetime.now())).days > 1:
                rec.write({'state': 'close'})
            else:
                raise ValidationError(_('No se puede cancelar una solicitud de viaje si queda menos de un día de antelación!'))

    @api.one
    def mail_notification(self):
        Mail = self.pool['mail.mail']
        employee_name=""
        for empl in self.employee_ids:
            employee_name =employee_name + empl.name + " "

        body = u'''
Nro. Solicitud: %(name)s
Funcionarios que viajan: %(employee_name)s
Fecha: %(date)s
Vehiculo: %(vehicle)s
Duración estimada: %(duration)s
Destino: %(target)s
Tipo de vehículo: %(vehicle_type)s

¡Gracias!
        ''' % {'name': self.name, 'date': self.date, 'employee_name': employee_name,
               'duration': self.estimated_duration if self.estimated_duration else '',
               'target': self.target if self.target else '',
               'vehicle_type': self.vehicle_type if self.vehicle_type else '',
               'vehicle': self.vehicle_id.name}
        vals = {'state': 'outgoing',
                'subject': 'Solicitud de viaje validada',
                'body_html': '<pre>%s</pre>' % body,
                'email_to': self.driver_id.email,
                'email_from': self.write_uid.email
                }

        mail_id = self.env['mail.mail'].create(vals).id
        Mail.send(self._cr, self._uid, [mail_id], context=self._context)

    # TODO Spring 5 GAP 51: Creando un calendar.event desde solicitud de viaje
    @api.one
    def create_event(self):
        # if self.env['res.users'].has_group('grp_flota.group_fleet_responsable_transporte'):
        tag = self.env['calendar.event.type'].search([('name', '=', 'Viajes')])
        CalendarEvent = self.env['calendar.event']
        CalendarEvent.create({'name': 'Solicitud de viaje',
                              'categ_ids': [(6, 0, [tag.id])],
                              'employee_ids': [(6, 0, list(set([x.id for x in self.employee_ids])))],
                              'target': self.target,
                              'vehicle_type': self.vehicle_type,
                              'date_travel': self.date,
                              'date_travel_str': str(self.date),
                              'start_datetime': self.date,
                              'stop_datetime': self.date,
                              'estimated_duration': self.estimated_duration,
                              'driver_id': self.driver_id.id,
                              'vehicle_id': self.vehicle_id.id,
                              'display_start':self.date,
                                  'travel_create': True})
