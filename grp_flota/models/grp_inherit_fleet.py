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
from openerp.osv import osv
from datetime import *
import time
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)

class GrpControlCambioCubierta(models.Model):
    _inherit = 'fleet.vehicle.log.services'
    _name = 'fleet.vehicle.log.services'

    cantidad_cubiertas = fields.Integer(string="Cantidad de cubiertas", size=1)
    origen_cubierta = fields.Selection([('stock', 'De Stock'), ('noStock', 'No son de stock')], string=u"De dónde se obtuvieron")
    ocultar = fields.Boolean(string='Hide', compute="_compute_hide")

    @api.depends('cost_subtype_id')
    def _compute_hide(self):
        cambio_cubierta = self.env.ref('fleet.type_service_45')
        if self.cost_subtype_id.id == cambio_cubierta.id:
            self.ocultar = False
        else:
            self.ocultar = True


            # TODO SPRING 5 GAP 41


# TODO SPRING 5 GAP 41
class fleet_vehicle(osv.Model):
    _inherit = 'fleet.vehicle'
    _name = 'fleet.vehicle'

    @api.model
    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False, context=None):
        res = super(fleet_vehicle, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                         toolbar=toolbar, submenu=submenu)
        is_private_vehicle_group = self.user_has_groups('grp_flota.group_fleet_private_vehicle')
        if view_type == 'form' and is_private_vehicle_group:
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='type']"):
                node.set('modifiers', '{"readonly":1,"required":1}')
            res['arch'] = etree.tostring(doc)
        return res

    def _default_type(self):
        if self.pool.get('res.users').has_group(self._cr, self._uid, 'grp_flota.group_fleet_private_vehicle'):
            return 'private'
        else:
            return False

    type = fields.Selection([('official', 'Oficial'), ('private', 'Particular')], string='Tipo de vehículo', required=True, default=_default_type)

    # CAMPOS PARA TIPO OFICIAL
    state = fields.Selection([('available', 'Disponible'), ('unavailable', 'No disponible')], string='Estado', default='available')
    motive = fields.Char(string="Motivo", size=40)
    engine_number = fields.Char(string="Número de motor")
    register_date = fields.Date(string="Fecha de alta en inciso")
    equipment_ids = fields.One2many('grp.fleet.vehicle.equipment', 'vehicle_id', string='Equipamientos', groups="fleet.group_fleet_manager")
    equipment_count = fields.Integer('Total de equipamientos', compute='_compute_equipment_count', groups="fleet.group_fleet_manager",
                                     help='Total de equipamiento asociado al vehículo')
    situation_ids = fields.One2many('grp.fleet.vehicle.situation', 'vehicle_id', string='Incidentes', groups="fleet.group_fleet_manager")
    situation_count = fields.Integer('Total de incidentes', compute='_compute_situation_count', groups="fleet.group_fleet_manager", help='Total de incidentes asociado al vehículo')
    drive_ids = fields.Many2many('grp.fleet.chofer',string='Choferes', ondelete='restrict')

    # CAMPOS PARA TIPO PARTICULAR
    name_holder = fields.Char(string="Nombre del titular")
    employee_id = fields.Many2one('hr.employee', string="Funcionario")
    sticker = fields.Integer(string="Número de sticker")
    drive_book_warning = fields.Boolean(string="Libreta de conducir", compute='_compute_drive_book_warning',
                                        help='Se ha adjuntado la libreta de conducir para vehículos particulares')

    # TODO SPRING 5 GAP 44
    policy_number = fields.Integer('Número de póliza', required=True)

    # TODO SPRING 5 GAP 49
    preventive_service_ids = fields.One2many('fleet.vehicle.preventive.service', 'vehicle_id', 'Servicios Preventivos')
    preventive_service_count = fields.Integer('Cantidad de servicio', compute='_compute_preventive_service_count')

    # TODO: L VARIANZA GRP
    _sql_constraints = [
        ('license_plate_unique', 'unique(license_plate)', u'No pueden existir dos vehículos con la misma matrícula.')
    ]

    @api.one
    @api.constrains('type', 'sticker')
    def _check_sticker_length(self):
        if self.type == 'private' and len(str(self.sticker)) > 5:
            raise ValidationError(_('El número del sticker debe tener una longitud máxima de 5!'))

    # TODO SPRING 5 GAP 44
    @api.one
    @api.constrains('policy_number')
    def _check_policy_number(self):
        if len(str(self.policy_number)) > 10:
            raise ValidationError(_('El número de póliza debe tener una longitud máxima de 10!'))

    @api.onchange('type')
    def _onchange_type(self):
        if not self.type:
            self.state = 'available'
            self.motive = None
            self.engine_number = None
            self.register_date = None

    @api.multi
    def _compute_equipment_count(self):
        for rec in self:
            rec.equipment_count = len(rec.equipment_ids)

    @api.multi
    def _compute_situation_count(self):
        for rec in self:
            rec.situation_count = len(rec.situation_ids)

    # TODO SPRING 5 GAP 49
    @api.multi
    def _compute_preventive_service_count(self):
        for rec in self:
            rec.preventive_service_count = len(rec.preventive_service_ids)

    @api.multi
    def _compute_drive_book_warning(self):
        Attachment = self.env['ir.attachment']
        for rec in self:
            rec.drive_book_warning = True if rec.type == 'private' and not Attachment.search_count([('res_model', '=', self._name), ('res_id', '=', rec.id)]) else False

    # TODO SPRING 5 GAP 49
    @api.model
    def alert_service_pending(self):
        vehicles = self.search([])
        for vehicle in vehicles:
            for service in vehicle.preventive_service_ids.filtered(lambda x: x.state == 'pendiente'):
                if (service.name - vehicle.odometer) <= 1000:
                    self.action_send_email(vehicle, service)
        return True


    def action_send_email(self, cr, uid, record, service, context=None):
        data = self.pool.get('ir.model.data')
        context = context or {}
        local_context = context.copy()
        template = data.get_object(cr,uid,'grp_flota', 'grp_fleet_vehicle_alert_mail')

        trans_obj = self.pool.get('ir.translation')
        user_obj = self.pool.get('res.users')
        context_lang = user_obj.browse(cr, uid, uid, context=context).lang
        existing_trans_ids = trans_obj.search(cr, uid,[('name', '=', 'fleet.service.type,name'),('name', '=', 'fleet.service.type,name'),('src', '=', service.service_id.name),('res_id', '=', service.service_id.id),('lang','=',context_lang)], limit=1)
        if existing_trans_ids:
            service_name = trans_obj.browse(cr,uid,existing_trans_ids).value
        else:
            service_name  = service.service_id.name
        # self.pool.get('ir.translation').search([()])
        local_context['service'] = service_name
        _model, group_id = data.get_object_reference(cr, uid, 'fleet', 'group_fleet_manager')
        users = self.pool.get('res.users').search(cr, uid, [('groups_id', 'in', group_id)])
        if users:
            for user in self.pool.get('res.users').browse(cr, uid, users, context=context):
                local_context['partner'] = user.partner_id
                self.pool.get('email.template').send_mail(cr, uid, template.id, record.id, force_send=True,
                                                     raise_exception=False, context=local_context)

    def _get_state(self, cr, uid, context):
        model_id = self.pool.get('fleet.vehicle.state').search(cr, uid, [('name', '=', 'Operativo')])
        if len(model_id)> 0:
            return model_id[0]
        return False

    _defaults = {
        'state_id': _get_state,
    }


class grp_fleet_vehicle_equipment(models.Model):
    """Equipamiento de vehículo"""
    _name = 'grp.fleet.vehicle.equipment'

    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehículo', required=True)
    name = fields.Char('Equipamiento', required=True)
    deliver_date = fields.Date('Fecha de entrega', required=True)
    due_date = fields.Date('Fecha de vencimiento', required=True)
    description = fields.Char('Descripción', size=40)

    @api.one
    @api.constrains('deliver_date','due_date')
    def _check_dates(self):
        if self.due_date < self.deliver_date:
            raise ValidationError(_(u'La fecha de vencimiento no puede ser menor que la fecha de entrega!'))


class grp_fleet_vehicle_situation(models.Model):
    """Incidente de vehículo"""
    _name = 'grp.fleet.vehicle.situation'

    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehículo', required=True)
    name = fields.Char('Incidente', required=True, size=30)
    date = fields.Date('Fecha', required=True)
    description = fields.Char('Descripción', size=40)


# TODO SPRING 5 GAP 42
# CHOFER
class grp_fleet_chofer(models.Model):
    """"Chofer"""
    _name = 'grp.fleet.chofer'

    is_employee = fields.Boolean('Es funcionario', help="Si el chofer es funcionario")
    employee_id = fields.Many2one('hr.employee', 'Funcionario')
    name = fields.Char(related='employee_id.name', string=u'Nombre', required=False, size=30)
    phone = fields.Char(related='employee_id.work_phone', string=u'Teléfono', store=True)
    email = fields.Char(related='employee_id.work_email', string=u'Email', store=True, size=40)
    notebook_duedate = fields.Date('Fecha de vencimiento de la libreta', required=True)
    notebook_category = fields.Selection([('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D'), ('e', 'E'), ('f', 'F'), ('g', 'G')], 'Categoría libreta', required=True)
    fine_ids = fields.One2many('grp.fleet.multa', 'driver_id', 'Multas')
    fine_count = fields.Integer('Cantidad de multas', compute='_compute_fine_count', help='Total de multas asociadas al chofer')
    equipment_ids = fields.One2many('grp.fleet.chofer.equipamiento', 'driver_id', 'Equipamientos')
    equipment_count = fields.Integer('Cantidad de equipamientos', compute='_compute_equipment_count', help='Total de equipamientos asociadas al chofer')
    ci = fields.Char(related='employee_id.identification_id', string='CI', store=True)  # TODO: L VARIANZA GRP

    @api.one
    @api.constrains('phone')
    def _check_phone(self):
        if len(self.phone) > 15:
            raise ValidationError(_('El teléfono debe tener una longitud máxima de 15!'))

    @api.onchange('is_employee')
    def _onchange_is_employee(self):
        if not self.is_employee:
            self.employee_id = False
            self.name = False
            self.phone = None
            self.email = False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.name = self.employee_id.name
        else:
            self.name = False

    @api.multi
    def _compute_fine_count(self):
        for rec in self:
            rec.fine_count = len(rec.fine_ids)

    @api.multi
    def _compute_equipment_count(self):
        for rec in self:
            rec.equipment_count = len(rec.equipment_ids)

    #RAGU: controlando no se pueda eliminar chofer
    @api.multi
    def unlink(self):
        fleet_driver_ids = []
        for vehicle_id in self.env['fleet.vehicle'].search([]):
            fleet_driver_ids.extend(vehicle_id.drive_ids.ids)
        for rec in self:
            if rec.id in fleet_driver_ids:
                raise ValidationError(_(u"El chofer %s está asociado a un vehículo. No puede ser eliminado!") % (rec.name_get()[0][1]))
        return super(grp_fleet_chofer, self).unlink()

    # TODO SPRING 5 GAP 49
    @api.model
    def alert_driver(self):
        current_date = date.today()
        limit_date = (current_date + relativedelta(months=+2)).strftime('%Y-%m-%d')
        limit_date_15 = (current_date + relativedelta(days=+15)).strftime('%Y-%m-%d')
        drivers = self.search(['|',('notebook_duedate', '=', limit_date_15),('notebook_duedate', '=', limit_date)])

        if len(drivers):
            self.action_send_email(drivers)
        return True

    def action_send_email(self,cr, uid, drivers,context=None):
        data = self.pool.get('ir.model.data')
        local_context = context.copy()
        template = data.get_object(cr, uid, 'grp_flota', 'grp_fleet_chofer_alert_mail')
        _model, group_id = data.get_object_reference(cr, uid, 'fleet', 'group_fleet_manager')
        users = self.pool.get('res.users').search(cr, uid, [('groups_id', 'in', group_id)])
        if users:
            for user in self.pool.get('res.users').browse(cr, uid, users, context=context):
                local_context['partner'] = user.partner_id
                for driver in drivers:
                    self.pool.get('email.template').send_mail(cr, uid, template.id, driver.id, force_send=True,
                                                              raise_exception=False,context=local_context)


class grp_fleet_multa(models.Model):
    """Multa de chofer"""
    _name = 'grp.fleet.multa'

    driver_id = fields.Many2one('grp.fleet.chofer',string='Chofer', required=True)
    vehicle_id = fields.Many2one('fleet.vehicle','Vehículo', required=True)
    type = fields.Char('Tipo de multa', size=30, required=True)
    amount = fields.Float('Monto',digits=(16,2))
    currency_id = fields.Many2one('res.currency','Moneda')
    date = fields.Date('Fecha', required=True)
    description = fields.Char('Descripción', size=50)


class grp_fleet_chofer_equipamiento(osv.Model):
    """Equipamiento de chofer"""
    _name = 'grp.fleet.chofer.equipamiento'

    driver_id = fields.Many2one('grp.fleet.chofer',string='Chofer', required=True)
    name = fields.Char('Equipamiento', required=True)
    deliver_date = fields.Date('Fecha de entrega', required=True)
    description = fields.Char('Descripción', size=40)

# TODO SPRING 5 GAP 249
class account_invoice(models.Model):
    _inherit = 'account.invoice'

    fleet_contract_id = fields.Many2one('fleet.vehicle.log.contract','Contrato')

# TODO SPRING 5 GAP 249
class grp_fleet_vehicle_log_contract(models.Model):
    _inherit = 'fleet.vehicle.log.contract'

    invoice_ids = fields.One2many('account.invoice', 'fleet_contract_id', string='Facturas')

# TODO SPRING 5 GAP 49
class fleet_vehicle_preventive_service(models.Model):
    """Servicios Preventivos"""
    _name = 'fleet.vehicle.preventive.service'

    service_id = fields.Many2one('fleet.service.type', 'Servicio',required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehiculo',required=True)
    name = fields.Integer('Km',required=True)
    state = fields.Selection([('pendiente', 'Pendiente'), ('realizado', 'Realizado')], 'Estado',required=True)

    @api.model
    def create(self, values):
        # Name de region solo en mayusculas
        if values['vehicle_id']:
            if self.search([('vehicle_id','=',values['vehicle_id']),('service_id','=',values['service_id'])]):
                raise ValidationError(_('No se podrá cargar el servicio preventivo, ya fue cargado anteriormente.'))
        return super(fleet_vehicle_preventive_service, self).create(values)


# TODO: L SPRING 13 GAP 48
class GrpFlotaRegistroCombustible(models.Model):
    _inherit = 'fleet.vehicle.log.fuel'

    rendimiento = fields.Float(string=u'Rendimiento', compute='_compute_rendimiento', store=True)

    # TODO: L SPRING 13 GAP 48
    @api.multi
    @api.depends('liter', 'odometer')
    def _compute_rendimiento(self):
        for record in self:
            record.rendimiento = record.odometer / record.liter if record.liter != 0 else 0

    # TODO: L SPRING 13 GAP 370
    @api.one
    @api.constrains('liter')
    def _check_liter(self):
        if self.liter <= 0:
            raise ValidationError(
                u"Deben llenar el campo litro")
        return True

# # TODO L VARIANZA GRP
# class GrpVehicleCost(models.Model):
#     _inherit = 'fleet.vehicle.cost'
#
#     @api.one
#     @api.constrains('vehicle_id', 'cost_subtype_id', 'odometer_id')
#     def _check_service(self):
#         if self.odometer_id:
#             _odometer = self.odometer_id.value
#             _odometer_text = 'odometer_id.value'
#         else:
#             _odometer = False
#             _odometer_text = 'odometer_id'
#         if self.search([('vehicle_id', '=', self.vehicle_id.id), ('cost_subtype_id', '=', self.cost_subtype_id.id),
#                         (_odometer_text, '=', _odometer), ('id', '!=', self.id)], limit=1):
#             raise ValidationError(
#                 u"No se puede repetir un servicio para vehículo con el mismo valor de odometro.")
#         return True
