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

from openerp import models, fields, api,SUPERUSER_ID, _
import logging
from datetime import *
import time
from openerp.exceptions import ValidationError

_logger = logging.getLogger(__name__)

TIPO_VIATICO = [('interior', u'Viático Interior'),
                ('exterior', u'Viático Exterior')
                ]

LISTA_ESTADOS_SOLICITUD = [
    ('borrador', u'Borrador'),
    ('en_aprobacion', u'En aprobación'),
    ('aprobado', u'Aprobado'),
    ('en_autorizacion', u'En autorización'),
    ('en_financiero', u'En financiero'),
    ('autorizado', u'Autorizado'),
    ('rechazado', u'Rechazado'),
    ('cancelado', u'Cancelado'),
]

TIPO_LOCOMOCION = [('bus', u'Bus'),
                   ('locomocion_propia', u'Locomoción Propia'),
                   ('locomocion_oficial', u'Locomoción Oficial'),
                   ('locomocion_otras', u'Locomoción otras Instit/Organis')]


class GrpSolicitudViaticos(models.Model):
    _name = 'grp.solicitud.viaticos'
    _description = u'Solicitud de Viajes'
    _inherit = ['mail.thread']
    _mail_post_access = 'read'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self.env.user.has_group('grp_viaticos.grp_sv_solicitante') and not (self.env.user.has_group(
                            'grp_viaticos.grp_sv_autoriza') or self.env.user.has_group(
                        'grp_viaticos.grp_sv_aprobar_viaje') or self.env.user.has_group(
                    'grp_viaticos.grp_sv_autorizar_financiero')) and not self.env.user.id == SUPERUSER_ID:
            if args:
                new_args = ['&','|', ['solicitante_id', '=', self.env.user.id], ['create_uid', '=', self.env.user.id]]
                new_args.extend(args)
            else:
                new_args = ['|', ['solicitante_id', '=', self.env.user.id], ['create_uid', '=', self.env.user.id]]
        else:
            new_args = args

        return super(GrpSolicitudViaticos, self)._search(new_args, offset, limit, order, count=count,
                                                         access_rights_uid=access_rights_uid)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self.env.user.has_group('grp_viaticos.grp_sv_solicitante') and not (self.env.user.has_group(
                            'grp_viaticos.grp_sv_autoriza') or self.env.user.has_group(
                        'grp_viaticos.grp_sv_aprobar_viaje') or self.env.user.has_group(
                    'grp_viaticos.grp_sv_autorizar_financiero')) and not self.env.user.id == SUPERUSER_ID:
            domain.extend(['|',['solicitante_id','=',self.env.user.id],['create_uid','=',self.env.user.id]])
        return super(GrpSolicitudViaticos, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                         orderby=orderby, lazy=lazy)

    @api.multi
    def copy(self, default=None):
        if default is None:
            default = {}
        for rec in self:
            default.update({
                'name': u'Viático Borrador',
            })
            lista = []
            for line in rec.lineas_ids:
                line_obj = line.copy()
                lista.append(line_obj.copy())
            default.update({'linea_ids': [(6, 0, lista)]})
        return super(GrpSolicitudViaticos, self).copy(default=default)

    @api.model
    def _get_partner(self):
        partner = self.env.user.partner_id.id
        return partner

    @api.depends('lineas_ids')
    def _get_total_monto(self):
        for rec in self:
            total = 0
            for linea in rec.lineas_ids:
                total += linea.valor
            rec.total = total / rec.tipo_cambio if rec.currency_id.name == 'USD' and rec.tipo == 'interior' else total  # TODO: L VARIANZA GRP

    @api.depends('lineas_ids')
    def _get_total_monto_adelanto(self):
        for rec in self:
            total_adelanto = 0
            if rec.lleva_adelanto:
                for linea in rec.lineas_ids:
                    if linea.adelanto:
                        total_adelanto += linea.valor
            rec.total_adelanto = total_adelanto

    @api.model
    def _default_solicitante_id(self):
        return self.env.user or self.env['res.users']

    @api.model
    def _default_operating_unit_id(self):
        return self.env['res.users'].operating_unit_default_get(self.env.user.id) or self.env['operating.unit']

    @api.one
    def _compute_user_operating_unit_id(self):
        self.user_operating_unit_id = self.env.user.default_operating_unit_id

    @api.model
    def _default_user_operating_unit_id(self):
        return self.env.user.default_operating_unit_id

    @api.onchange('km_recorrer')
    def onchange_km_recorrer(self):
        if self.tipo_locomocion == 'locomocion_propia':
            self.km_recorrer_cmp = self.km_recorrer * 2

    # definicion de campos
    name = fields.Char(string=u'Nº Solicitud de Viajes', readonly=True, default=u'Viático Borrador', copy=False)
    tipo = fields.Selection(selection=TIPO_VIATICO, string=u'Tipo', required=True)
    motivo_viaje = fields.Many2one('grp.motivo.viaje', string=u'Motivo del viaje', required=True, ondelete="restrict")
    destino = fields.Many2one('grp.localidad', string='Localidad o zona', ondelete='restrict', required=True)
    solicitante_id = fields.Many2one('res.users', string=u'Solicitante', required=True, ondelete="restrict",
                                     default=lambda self: self._default_solicitante_id())
    partner_id = fields.Many2one('res.partner', string=u'Solicitante', ondelete="restrict", readonly=True,
                                 default=_get_partner)
    asociados_ids = fields.Many2many(comodel_name='res.partner', domain=[('funcionario', '=', True)],
                                     string=u'Asociados')
    fecha_desde = fields.Datetime(string=u'Fecha Desde', required=True)
    fecha_hasta = fields.Datetime(string=u'Fecha Hasta', required=True)
    currency_id = fields.Many2one('res.currency', string=u'Moneda', ondelete="restrict",
                                  domain=[('name', 'in', ('UYU', 'USD'))], required=True)
    journal_id = fields.Many2one('account.journal', string=u'Rendición', domain=[('type', '=', 'cash')],
                                 ondelete="restrict", required=False)
    notas = fields.Text(string=u'Notas', size=300, help=u"Comentarios sobre Viáticos")
    total = fields.Float(string=u'Total', store=False, compute=_get_total_monto)
    total_adelanto = fields.Float(string=u'Total adelanto', compute='_get_total_monto_adelanto', store=False)
    lineas_ids = fields.One2many(comodel_name='grp.viaticos.lineas', inverse_name='solicitud_viatico_id',
                                 string=u'Líneas')
    state = fields.Selection(selection=LISTA_ESTADOS_SOLICITUD, string='Estado', track_visibility='onchange',
                             default='borrador')
    meeting_id = fields.Many2one('calendar.event', string=u'Calendario de ausencia')
    adelanto_pagado = fields.Boolean(string=u'Adelanto pagado',default=False, copy=False)
    employee_id = fields.Many2one('hr.employee', string=u'Empleado', compute='_compute_employee_id', store=True)
    department_id = fields.Many2one('hr.department', string=u'Unidad organizativa', related='employee_id.department_id', readonly=True, store=True)
    cedula = fields.Char(string=u'Cédula', related='employee_id.identification_id', readonly=True, store=True)
    domicilio_id = fields.Many2one('res.partner', string=u'Domicilio', related='employee_id.address_home_id', readonly=True, store=True)
    categoria = fields.Selection(related='employee_id.categoria', store=True, readonly=True)
    operating_unit_id = fields.Many2one(comodel_name='operating.unit', string=u'Unidad ejecutora',
                                        default=lambda self: self._default_operating_unit_id(),
                                        required=True)
    fecha_ingreso = fields.Datetime(string=u'Fecha de ingreso', readonly=True,
                                    default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    lugar_partida = fields.Char(string=u'Lugar de partida', size=50, required=True)
    tipo_locomocion = fields.Selection(selection=TIPO_LOCOMOCION, string=u'Tipo de locomoción')
    km_recorrer = fields.Float(u'Distancia recorrida (sólo ida)')
    km_recorrer_cmp = fields.Float('KM a recorrer')
    lleva_adelanto = fields.Boolean(string=u'¿Lleva adelanto?', default=True)
    a_borrador = fields.Boolean(string=u'A borrador', compute='_compute_a_borrador')
    # TODO: R SPRING 11 GAP 25
    config_importe_viatico_id = fields.Many2one('grp.configuracion.importes.viaticos', string=u'Configuración usada',
                                                compute='_compute_config_importe_viatico_id', store=True,
                                                multi = 'configuracion_importe_viatico',
                                                ondelete='restrict')
    config_complemento_viatico_id = fields.Many2one('grp.configuracion.importes.viaticos', string=u'Configuración usada',
                                                compute='_compute_config_importe_viatico_id', store=True,
                                                multi='configuracion_importe_viatico',
                                                ondelete='restrict')
    locomocion_propia_id = fields.Many2one('grp.locomocion.propia', string=u'Configuración usada',
                                                compute='_compute_config_importe_viatico_id', store=True,
                                                multi='configuracion_importe_viatico',
                                                ondelete='restrict')
    user_operating_unit_id = fields.Many2one('operating.unit', compute = '_compute_user_operating_unit_id', default=_default_user_operating_unit_id)
    requiere_alojamiento = fields.Boolean(string=u'¿Requiere alojamiento?', default=False)

    # RAGU
    edit_lines = fields.Boolean(u'Lineas editables', compute='_compute_edit_lines')
    tipo_cambio = fields.Float('Tipo de cambio', compute='_compute_tipo_cambio', digits=(12, 6),
                               help='El tipo de cambio usado en el pago.')

    solicitante_editable = fields.Boolean(u'Editable', compute = '_compute_solicitante_editable')
    instance_editable = fields.Boolean(u'Editable', compute = '_compute_instance_editable')
    create_uid = fields.Many2one("res.users",string=u"Usuario",readonly=1)

    paid_date = fields.Date('Fecha de pago', compute='_compute_paid_date')

    _sql_constraints = [
        ('check_dates', 'CHECK(fecha_hasta >= fecha_desde)', "'Fecha hasta' debe ser mayor o igual a 'Fecha desde'"),
    ]

    viaticos_multi = fields.One2many('grp.solicitud.viaticos.multi', 'solicitud_viatico_id', string=u'Múltiples destinos')

    # fechadesde > fechadesde y <fechahasta
    # fechahasta
    @api.one
    @api.constrains('fecha_desde','fecha_hasta','solicitante_id','state','tipo')
    def _check_dates(self):
        if self.state not in ['rechazado', 'cancelado'] and self.search_count(
                [('id','!=',self.id),('solicitante_id', '=', self.solicitante_id.id), ('tipo', '=', self.tipo),
                 ('state', 'not in', ['rechazado', 'cancelado']),'|',
                 '&', ('fecha_desde', '>=', self.fecha_desde), ('fecha_desde', '<=', self.fecha_hasta),'|',
                 '&', ('fecha_hasta', '>=', self.fecha_desde), ('fecha_hasta', '<=', self.fecha_hasta),
                 '&', ('fecha_desde', '<=', self.fecha_desde), ('fecha_hasta', '>=', self.fecha_hasta),
                 ]):
            raise ValidationError(_(u"Existe otra solicitud para el mismo Solicitante y Tipo que se solapa con este rango de fechas!"))


    @api.depends('solicitante_id')
    def _compute_employee_id(self):
        for rec in self:
            rec.employee_id = self.env['hr.employee'].search([('user_id', '=', rec.solicitante_id.id)], limit=1)

    @api.multi
    def _compute_paid_date(self):
        VoucherLine = self.env['account.voucher.line']
        for rec in self:
            rec.paid_date = VoucherLine.search(
                [('origin_voucher_id.solicitud_viatico_id', '=', rec.id), ('amount', '!=', 0),
                 ('voucher_id.state', '=', 'posted')], limit=1).voucher_id.date


    @api.one
    @api.depends('state')
    def _compute_instance_editable(self):
        _instance_editable = False
        if self.state == 'borrador' and self.env.user.has_group('grp_viaticos.grp_sv_solicitante'):
            _instance_editable = True
        if self.state in ('en_aprobacion','aprobado') and self.env.user.has_group('grp_viaticos.grp_sv_aprobar_viaje'):
            _instance_editable = True
        if self.state == 'en_autorizacion' and self.env.user.has_group('grp_viaticos.grp_sv_autoriza'):
            _instance_editable = True
        if self.state == 'en_financiero' and self.env.user.has_group('grp_viaticos.grp_sv_autorizar_financiero'):
            _instance_editable = True
        if self.state == 'ingresando_montos' and self.env.user.has_group('grp_viaticos.grp_sv_ingresa_monto'):
            _instance_editable = True

        self.instance_editable = _instance_editable

    @api.one
    @api.depends('state')
    def _compute_solicitante_editable(self):
        self.solicitante_editable = self.env.user.has_group('grp_viaticos.grp_sv_solicitantesuperior')

    # RAGU: lineas editables en estado En autorizacion para el rol SV Autorizar si Tipo Exterior
    @api.one
    @api.depends('tipo','state')
    def _compute_edit_lines(self):
        self.edit_lines = (self.state == 'borrador' and self.env.user.has_group('grp_viaticos.grp_sv_solicitante')) or (self.env.user.has_group('grp_viaticos.grp_sv_autoriza') and self.state == 'en_autorizacion')

    @api.depends('currency_id')
    def _compute_tipo_cambio(self):
        for rec in self:
            rec.tipo_cambio = rec.currency_id.rate

    @api.onchange('country_id')
    def _onchange_country_id(self):
        self.localidad = False
        self.country_state_id = False
        if self.country_id:
            return {
                'domain': {
                    'country_state_id': [('country_id', '=', self.country_id.id)],
                    'localidad': [('country_id', '=', self.country_id.id)]
                }
            }

    @api.onchange('tipo')
    def _onchange_tipo(self):
        self.destino = False
        if self.tipo == 'exterior':
            domain = {'destino': [('country_id', '!=', self.env.user.company_id.country_id.id)]}
            self.currency_id = self.env['res.currency'].search([('name', '=', 'USD')], limit=1).id
        elif self.tipo:
            self.currency_id = self.env.user.company_id.currency_id.id
            domain = {'destino': ['|', ('country_id', '=', self.env.user.company_id.country_id.id),
                                  ('country_id', '=', False)]}
        else:
            domain = {'destino': [('id', 'in', [])]}
            self.currency_id = False
        return {
            'domain': domain
        }

    @api.depends('categoria','fecha_desde','fecha_hasta')
    def _compute_config_importe_viatico_id(self):
        for rec in self:
            if rec.fecha_desde and rec.fecha_hasta:
                fecha_inicio = datetime.strptime(rec.fecha_desde, "%Y-%m-%d %H:%M:%S")
                fecha_fin = datetime.strptime(rec.fecha_hasta, "%Y-%m-%d %H:%M:%S")
                rec.config_importe_viatico_id = self.env['grp.configuracion.importes.viaticos'].search(
                    [('tipo', '=', rec.categoria), ('fecha_desde', '<=', fecha_inicio.strftime("%Y-%m-%d")),
                     ('fecha_hasta', '>=', fecha_fin.strftime("%Y-%m-%d"))], order='fecha_desde DESC', limit=1).id
                rec.config_complemento_viatico_id = self.env['grp.configuracion.importes.viaticos'].search(
                    [('tipo', '=', 'complemento'),
                     ('fecha_desde', '<=', fecha_inicio.strftime("%Y-%m-%d")),
                     ('fecha_hasta', '>=', fecha_fin.strftime("%Y-%m-%d"))], order='fecha_desde DESC', limit=1).id
                rec.locomocion_propia_id = self.env['grp.locomocion.propia'].search(
                    [('activo', '=', True),
                     ('fecha_desde', '<=', fecha_inicio.strftime("%Y-%m-%d")),
                     ('fecha_hasta', '>=', fecha_fin.strftime("%Y-%m-%d"))], order='fecha_desde DESC', limit=1).id
            else:
                rec.config_importe_viatico_id = False
                rec.config_complemento_viatico_id = False
                rec.locomocion_propia_id = False

    @api.multi
    def actualizar_calendario(self, rec_viatico):
        meeting_obj = self.env['calendar.event']
        meeting_vals = {
            'name': 'Ausencia por viaje',
            'categ_ids': [],
            'user_id': rec_viatico.solicitante_id.id,
            'start_datetime': rec_viatico.fecha_desde,
            'stop_datetime': rec_viatico.fecha_hasta,
            'allday': False,
            'state': 'open',  # to block that meeting date in the calendar
            'class': 'confidential',
            'partner_ids': [(6, 0, list(set([x.beneficiario_id.id for x in rec_viatico.lineas_ids])))]
        }
        ctx_no_email = dict(self._context or {}, no_email=True)
        meeting_id = meeting_obj.with_context(ctx_no_email).create(meeting_vals)
        return meeting_id

    @api.multi
    def generar_SC(self, rec_viatico):
        grp_sc_obj = self.env['grp.solicitud.compra']
        for linea in rec_viatico.lineas_ids:
            if linea.product_id.viatico_ok and linea.product_id.purchase_ok:
                datos = {
                    'company_id': self.env['res.company']._company_default_get('product.template'),
                    'solicitante_id': linea.solicitud_viatico_id.solicitante_id.id,
                    # 'departamento': linea.solicitud_viatico_id.solicitante_id.department_id.id,
                    'product_id': linea.product_id.id,
                    'cantidad_solicitada': linea.cant_personas * linea.dias,
                    'precio_estimado': linea.monto / (linea.cant_personas * linea.dias),
                    'description': linea.descripcion,
                    'solicitud_viatico_id': rec_viatico.id,
                }
                grp_sc_obj.create(datos)
        return True

    # WORKFLOW *********** INICIO **********
    # TODO: SPRING 11 GAP 24 L
    # Borrador
    @api.multi
    def action_enviar_aprobar(self):

    # TODO: L INCIDENCIA
        for rec in self:
            if self.env.user.id in [rec.solicitante_id.id,rec.create_uid.id]:
                write_dict = {'name': self.env['ir.sequence'].get('sv.number')} if rec.name == 'Viático Borrador' else {}
                if rec.tipo == 'interior':
                    write_dict.update({'state': 'en_aprobacion'})
                else:
                    write_dict.update({'state': 'en_autorizacion','lleva_adelanto':True})

                rec.write(write_dict)

                if rec.state == 'en_autorizacion':
                    self.action_send_email()

            else:
                raise ValidationError(_("Solo puede Enviar a Aprobar la Solicitud el Usuario que la creó o el Solicitante!"))

    @api.multi
    def action_send_email(self):

        Mail = self.pool['mail.mail']

        ir_model_data = self.env['ir.model.data']
        _model, group_id = ir_model_data.get_object_reference('grp_viaticos',
                                                              'grp_sv_autoriza')
        users = self.env['res.users'].search(
            [('groups_id', 'in', group_id), ('operating_unit_ids', 'in', self.operating_unit_id.id)])

        web_base_url = self.pool.get('ir.config_parameter').get_param(self._cr, self._uid, 'web.base.url')

        partner_ids = []
        if users:
            partner_ids = [user.partner_id.id for user in users]
        body = """La solicitud de viaje <a href="%(web)s/web#id=%(valor_id)s&view_type=form&model=grp.solicitud.viaticos">%(valor_name)s</a> del solicitante <a href="%(web)s/web#id=%(pedido_id)s&view_type=form&model=res.users">%(pedido_name)s</a> está pendiente de autorización.""" \
            % {'web':web_base_url,
               'valor_name': self.name,
               'valor_id': self.id,
               'pedido_name': self.solicitante_id.name,
               'pedido_id': self.solicitante_id.id
              }

        vals = {
            'subject': 'Solicitud de viaje en autorizacion',
            'body_html': '<pre>%s</pre>' % body,
            'recipient_ids': [(6, 0, partner_ids)],
            'email_from': self.write_uid.email
        }
        mail_id = self.env['mail.mail'].create(vals).id
        Mail.send(self._cr, self._uid, [mail_id], context=self._context)

        # En aprobacion
    @api.multi
    def action_aprobar(self):
        if self.tipo == 'interior':
            if self.lleva_adelanto:
                self.write({'state': 'aprobado'})
            else:
                self.write({'state': 'autorizado'})
        else:
            self.write({'state': 'autorizado'})

    @api.multi
    def action_rechazar(self):
        for rec in self:
            if rec.tipo == 'exterior':
                rec.write({'state': 'rechazado', 'lleva_adelanto': True})
            else:
                rec.write({'state': 'rechazado'})

    @api.multi
    def action_pasar_borrador(self):
        self.write({'state': 'borrador'})

    # Aprobado
    @api.multi
    def action_enviar_autorizar(self):
        if self.tipo == 'interior':
            self.write({'state': 'en_autorizacion'})
            self.action_send_email()

    @api.multi
    def action_cancelar(self):
        # TODO: SPRING 11 GAP 28 L
        for rec in self:
            adelanto_id = self.env['account.voucher'].suspend_security().search([('solicitud_viatico_id', '=', rec.id)],
                                                                                limit=1)
            if rec.state == 'autorizado':
                if self.env['hr.expense.expense'].suspend_security().search_count([('solicitud_viatico_id', '=', rec.id),('state','!=','cancelado')]):
                    raise ValidationError(_(u'La solicitud no puede ser cancelada pues tiene una rendición asociada y está no se encuentra cancelada!'))
                if adelanto_id and adelanto_id.state not in ['draft','cancel']:
                        raise ValidationError(_(u'Solo puede cancelar la solicitud de viaje sino existe un adelanto creado y/o '
                                                u'una rendición asociada a la solicitud!'))
            adelanto_id.suspend_security().cancel_voucher()
            adelanto_id.suspend_security().invoice_id.action_cancel()
        self.suspend_security().write({'state': 'cancelado'})

    @api.multi
    def check_comp_conf_viatico(self, method, *args):
        if self.viaticos_multi:
            loc = self.env['grp.localidad']
            for line in self.viaticos_multi:
                loc |= line.origen
                loc |= line.destino
            year = fields.Datetime.from_string(self.fecha_desde).year
            conf_v = self.env['grp.complemento.configuracion.viaticos'].search([
                                                ('configuracion_viaticos_id.fiscal_year_id.name','=',str(year)),
                                                ('configuracion_viaticos_id.tipo','=','complemento')])
            if conf_v:
                loc_conf = self.env['grp.localidad']
                for c in conf_v:
                    loc_conf |= c.localidad
                if loc_conf and loc:
                    if not(loc <= loc_conf):
                        if not(loc <= (loc - loc_conf)):
                            ctx = self.env.context.copy()
                            ctx.update({
                                'model_method': [method] + list(args) or []
                            })
                            return {
                                'type': 'ir.actions.act_window',
                                'name': 'Confirmar solicitud',
                                'res_model': 'grp.solicitud.cmp.viatico.wzd',
                                'view_mode': 'form',
                                'target': 'new',
                                'context': ctx
                            }
        if hasattr(self, method):
            args = args and args[0] or []
            return getattr(self.with_context({'check_comp_conf_viatico_done':True}), method)(*args)
        return True

    # En autorizacion -> Autorizar
    @api.multi
    def _autorizar(self, vals):
        self.write(vals)
        if self.lleva_adelanto:
            self.sudo().generar_adelanto()

    @api.multi
    def action_autorizar(self):
        if len(self) == 1 and self.state=='en_autorizacion':
                #Se adiciona al if la condición len(self) == 1, si se quita entonces se debe iterar por self. Se asume que es desde uno de los botones.
                return self.check_comp_conf_viatico('_autorizar', [{'state': 'autorizado'}])
        else:
            self.write({'state': 'autorizado'})
            if self.lleva_adelanto:
                self.sudo().generar_adelanto()

    @api.multi
    def action_enviar_financiero(self):
        if self.tipo == 'exterior':
            if len(self) == 1 and self.state=='en_autorizacion':
                #Se adiciona al if la condición len(self) == 1, si se quita entonces se debe iterar por self. Se asume que es desde uno de los botones.
                return self.check_comp_conf_viatico('write', [{'state': 'en_financiero', 'lleva_adelanto': True}])
            else:
                self.write({'state': 'en_financiero', 'lleva_adelanto': True})

    # TODO: SPRING 11 GAP 28 L
    @api.multi
    def generar_adelanto(self):
        self.ensure_one()
        if not self.solicitante_id.partner_id.supplier_advance_account_id or not self.solicitante_id.partner_id.property_account_payable:
            raise ValidationError(_(u'El solicitante no tiene cuenta de pagos o cuenta anticipo de proveedores'))
        search_args = [('type', '=', 'purchase')]
        if self.env.user.company_id.currency_id.id != self.currency_id.id:
            search_args.append(('currency', '=', self.currency_id.id))
        else:
            search_args.extend(['|', ('currency', '=', False),('currency', '=', self.env.user.company_id.currency_id.id)])
        journal_id = self.env['account.journal'].search(search_args, limit=1)
        if not journal_id:
            raise ValidationError(_(u"No se ha encontrado un diario de compra asociado a la moneda de la solicitud"))
        res_voucher = self.env['account.voucher'].create({
            'type': 'payment',
            'partner_id': self.solicitante_id.partner_id.id,
            'account_id': self.solicitante_id.partner_id.property_account_payable.id,
            'date': fields.Date.from_string(fields.Date.today()),
            'operating_unit_id': self.operating_unit_id.id,
            'solicitud_viatico_id': self.id,
            'payment_rate':0,
            'line_dr_ids': [
                (0, 0, {
                    'account_id': self.solicitante_id.partner_id.supplier_advance_account_id.id,
                    'amount_unreconciled':self.total_adelanto,
                    'amount': self.total_adelanto})
            ],
            'amount':self.total,
            'journal_id':journal_id.id
        })
        product_id = self.env['product.product'].search([('viatico_ok','=',True)], limit=1)
        if not product_id.exists():
            raise ValidationError(_("Debe existir configurado al menos un producto de Viático!"))
        if res_voucher.state == 'draft':
            tipo_ejecucion = self.env['tipo.ejecucion.siif'].search([('codigo', '=', 'P')])
            res_invoice = self.env['account.invoice'].create({
                'partner_id': res_voucher.partner_id.id,
                'account_id': res_voucher.account_id.id,
                'date_invoice': res_voucher.date,
                'internal_number': res_voucher.number,
                'number': res_voucher.number,
                'currency_id': res_voucher.currency_id.id,
                'siif_tipo_ejecucion': tipo_ejecucion and tipo_ejecucion.id or False,
                'type': 'in_invoice',
                'amount_total': self.total,
                'pago_aprobado': False,
                'doc_type': 'adelanto_viatico',
                'state': 'open',
                'operating_unit_id': self.operating_unit_id.id,
                'account_voucher_id':res_voucher.id,
                'journal_id': journal_id.id,
                'invoice_line': [
                    (0, 0, {'name': line.name or '', 'account_id': line.account_id.id, 'price_unit': line.amount, 'product_id':product_id.id}) for
                    line in res_voucher.line_dr_ids]
            })
            res_voucher.write({'invoice_id': res_invoice.id})
            res_invoice.write({'doc_type': 'adelanto_viatico'})
        # WORKFLOW *********** FIN **********

    # TODO: L SPRING 11 GAP 24
    @api.depends('state')
    def _compute_a_borrador(self):
        for item in self:
            item.a_borrador = False
            if (self.env.user.has_group('grp_viaticos.grp_sv_aprobar_viaje')
                and item.state in ['en_aprobacion', 'rechazado']) or (
                        self.env.user.has_group('grp_viaticos.grp_sv_autoriza') and item.state in [
                        'en_autorizacion',
                        'rechazado']) or (
                        self.env.user.has_group('grp_viaticos.grp_sv_autorizar_financiero') and item.state in [
                        'en_financiero', 'rechazado']):
                item.a_borrador = True

    # TODO: SPRING 11 GAP 25 K
    # TODO: R SPRING 11 GAP 25
    def generar_lineas(self):
        fecha_inicio = datetime.strptime(self.fecha_desde,"%Y-%m-%d %H:%M:%S")
        fecha_fin = datetime.strptime(self.fecha_hasta,"%Y-%m-%d %H:%M:%S")
        diference = fecha_fin - fecha_inicio
        cantidad_dias = diference.days
        cantidad_horas = round(diference.total_seconds() / 3600 - float(cantidad_dias) * 24, 2)
        configuracion = self.config_importe_viatico_id
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.solicitante_id.id)], limit=1)
        if not employee_id:
            raise ValidationError(_('No se ha podido identificar un empleado asociado al usuario solicitante'))
        if configuracion:
            importe = configuracion.valor_alimentacion * cantidad_dias
            if cantidad_horas > employee_id.cantidad_horas_trabajadas:
                importe += configuracion.valor_porciento_alimentacion if cantidad_horas <= 12.0 else configuracion.valor_alimentacion
            self.env['grp.viaticos.lineas'].create({
                'product_id': configuracion.product_alimentacion_id.id,
                'valor': importe,
                'solicitud_viatico_id': self.id,
            })
            if cantidad_dias > 0 or self.requiere_alojamiento:
                if cantidad_dias == 0 and self.requiere_alojamiento:
                    importe = configuracion.valor_pernocte
                else:
                    importe = configuracion.valor_pernocte * cantidad_dias
                self.env['grp.viaticos.lineas'].create({
                    'product_id': configuracion.product_pernocte_id.id,
                    'valor' : importe,
                    'solicitud_viatico_id':self.id,
                    })
        if self.tipo_locomocion == 'locomocion_propia' and self.locomocion_propia_id:
            locomocion_linea = self.locomocion_propia_id.valor_nafta_ids.sorted(key=lambda a: a.fecha_desde, reverse=True)
            self.env['grp.viaticos.lineas'].create({
                    'product_id': self.locomocion_propia_id.product_id.id,
                    'valor' : self.km_recorrer_cmp/self.locomocion_propia_id.relacion_km * (locomocion_linea and locomocion_linea[0].importe or float(0)),
                    'solicitud_viatico_id':self.id
                    })
        if self.destino != '' and self.config_complemento_viatico_id:
            localidad_id = self.config_complemento_viatico_id.complemento_ids.filtered(lambda x: x.localidad == self.destino)
            if localidad_id:
                importe = localidad_id.valor_alimentacion * cantidad_dias
                if cantidad_horas > employee_id.cantidad_horas_trabajadas:
                    importe += round(localidad_id.valor_alimentacion * 0.5, 2) if cantidad_horas <= 12.0 else localidad_id.valor_alimentacion
                if importe:
                    self.env['grp.viaticos.lineas'].create({
                        'product_id': localidad_id.product_alimentacion_id.id,
                        'valor': importe,
                        'solicitud_viatico_id': self.id
                    })
                if cantidad_dias > 0 or self.requiere_alojamiento:
                    if cantidad_dias == 0 and self.requiere_alojamiento:
                        importe = localidad_id.valor_pernocte
                    else:
                        importe = localidad_id.valor_pernocte * cantidad_dias
                    if importe:
                        self.env['grp.viaticos.lineas'].create({
                            'product_id': localidad_id.product_pernocte_id.id,
                            'valor' : importe,
                            'solicitud_viatico_id':self.id,
                            })
        return True

    # TODO: SPRING 11 GAP 25 K
    @api.model
    def create(self, vals):
        res = super(GrpSolicitudViaticos, self).create(vals)
        if res.tipo == 'interior' and res.km_recorrer > 50:
            res.generar_lineas()
        return res

    # TODO: SPRING 11 GAP 24 L
    @api.multi
    def write(self, vals):
        if vals.get('lineas_ids'):
            for rec in vals['lineas_ids']:
                msg = ''
                if rec[0] == 0:
                    _product = self.env['product.product'].search([('id', '=', rec[2]['product_id'])])
                    valor = rec[2]['valor'] if 'valor' in rec[2] else 0
                    descripcion = rec[2]['descripcion'] if 'descripcion' in rec[2] else ''
                    msg = _("Linea agregada: Producto: %s, Descripcion: %s e Importe: %s") % \
                          (_product.name, descripcion, valor)
                elif rec[0] == 1 or rec[0] == 2:
                    msg += "Linea modificada" if rec[0] == 1 else "Linea eliminada"
                    _linea = self.env['grp.viaticos.lineas'].search([('id', '=', rec[1])])
                    msg += _(": Producto: %s, Descripcion: %s, Horas: %s e Importe: %s") % \
                          (_linea.product_id.name, _linea.descripcion, round(_linea.horas, 2), _linea.valor)
                if msg:
                    self.message_post(body=msg)
        return super(GrpSolicitudViaticos, self).write(vals)

    @api.multi
    def unlink(self):
        if self.filtered(lambda x:x.state != 'borrador'):
            raise ValidationError(u"Para eliminar Solicitudes de Viajes deben estar en estado 'Borrador'")
        return super(GrpSolicitudViaticos, self).unlink()

    @api.multi
    def action_actualizar_lineas(self):
        self.lineas_ids.unlink()
        for rec in self:
            if rec.km_recorrer > 50 and rec.tipo == 'interior':
                rec.generar_lineas()

class GrpViaticosLineas(models.Model):
    _name = 'grp.viaticos.lineas'
    _descripcion = u'Líneas de Solicitud de Viajes'

    @api.one
    def _get_editar_monto(self):
        self.editar_monto = self.env.user.has_group('grp_viaticos.grp_sv_ingresa_monto')

    @api.depends('cant_personas', 'dias', 'valor')
    def _get_monto(self):
        for record in self:
            monto = record.cant_personas * record.dias * record.valor
            record.monto = monto

    @api.depends('product_id')
    def _es_adelanto(self):
        for record in self:
            record.adelanto = record.product_id.viatico_ok and record.product_id.hr_expense_ok

    @api.model
    def create(self, vals):
        vals['valor_init'] = vals.get('valor',0)
        return super(GrpViaticosLineas,self).create(vals)

    # definicion de campos
    solicitud_viatico_id = fields.Many2one(
        comodel_name='grp.solicitud.viaticos',
        string=u'Solicitud Viático',
        readonly=True,
        ondelete='cascade'
    )
    # TODO: SPRING 11 GAP 24 L
    beneficiario_id = fields.Many2one(
        comodel_name='res.partner',
        domain=[('funcionario', '=', True)],
        string=u'Beneficiario',
        required=False
    )
    product_id = fields.Many2one(comodel_name='product.product',
                                 domain=[('viatico_ok', '=', True), ('hr_expense_ok', '=', True)], string=u'Producto',
                                 required=True)
    descripcion = fields.Text(string=u'Descripción')
    cant_personas = fields.Integer(
        string=u'Cantidad Personas',
        size=10,
        required=False
    )
    dias = fields.Integer(
        string=u'Días',
        required=False
    )
    horas = fields.Float(string="Horas", compute='_compute_horas', store=True)
    valor = fields.Float(string="Monto ingresado")
    valor_init = fields.Float("Monto calculado", readonly=True)
    monto = fields.Float(
        compute='_get_monto',
        string='Monto',
        store=True
    )
    editar_monto = fields.Boolean(
        default=lambda self: self.env.user.has_group('grp_viaticos.grp_sv_ingresa_monto'),
        compute='_get_editar_monto',
        store=False
    )
    adelanto = fields.Boolean(
        compute='_es_adelanto',
        store=False,
        string='Corresponde adelanto',
        default=False
    )

    # fin definicion de campos

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            prod = self.env['product.product'].browse(self.product_id.id)
            es_prod_adelanto = prod.viatico_ok and prod.hr_expense_ok
            self.adelanto = es_prod_adelanto

    # TODO: SPRING 11 GAP 24 L
    @api.one
    @api.depends('solicitud_viatico_id.fecha_desde', 'solicitud_viatico_id.fecha_hasta')
    def _compute_horas(self):
        if self.solicitud_viatico_id and self.solicitud_viatico_id.fecha_desde and self.solicitud_viatico_id.fecha_hasta:
            desde = fields.Datetime.from_string(self.solicitud_viatico_id.fecha_desde)
            hasta = fields.Datetime.from_string(self.solicitud_viatico_id.fecha_hasta)
            _horas = ((hasta - desde).total_seconds()) / 3600
        else:
            _horas = 0
        self.horas = _horas


# TODO: SPRING 11 GAP 24 L
class GrpMotivoViaje(models.Model):
    _name = 'grp.motivo.viaje'
    _description = u'Motivo del viaje'

    name = fields.Char(string=u'Nombre', compute='_compute_name', store=True)
    codigo = fields.Char(string=u'Código', size=10, required=True)
    descripcion = fields.Char(string=u'Descripción', size=50, required=True)

    @api.depends('codigo', 'descripcion')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s' % (rec.codigo, rec.descripcion)


class GrpSolicitudCompra(models.Model):
    _inherit = 'grp.solicitud.compra'

    # definicion de campos
    solicitud_viatico_id = fields.Many2one(
        comodel_name='grp.solicitud.viaticos',
        string=u"Solicitud viático",
        readonly=True
    )
    # fin definicion de campos

class GrpSolicitudViaticosMulti(models.Model):
    _name = 'grp.solicitud.viaticos.multi'
    _description = u'Múltiples destinos'
    _rec_name = 'solicitud_viatico_id'

    @api.onchange('fecha_desde', 'fecha_hasta')
    def _onchange_date(self):
        if self.fecha_desde and self.fecha_hasta:
            if self.fecha_desde > self.fecha_hasta:
                return {
                            'warning': {
                                'title': "Error",
                                'message': "La Fecha desde: %s debe ser menor o igual que la Fecha hasta: %s" % (self.fecha_desde, self.fecha_hasta)
                            }
                        }

    @api.constrains('fecha_desde','fecha_hasta')
    def _check_date(self):
        for row in self:
            if row.fecha_desde > row.fecha_hasta:
                raise ValidationError("Origen: %s \n Destino: %s \n La Fecha desde: %s debe ser menor o igual que la Fecha hasta: %s" % (row.origen.name, row.destino.name, row.fecha_desde, row.fecha_hasta))
            if row.solicitud_viatico_id.fecha_desde > row.fecha_desde:
                raise ValidationError("Origen: %s \n Destino: %s \n La Fecha desde: %s de Múltiples destinos debe ser mayor o igual que la Fecha desde: %s de la solicitud" % (row.origen.name, row.destino.name, row.fecha_desde, row.solicitud_viatico_id.fecha_desde))
            if row.solicitud_viatico_id.fecha_hasta < row.fecha_hasta:
                raise ValidationError("Origen: %s \n Destino: %s \n La Fecha hasta: %s de Múltiples destinos debe ser menor o igual que la Fecha hasta: %s de la solicitud" % (row.origen.name, row.destino.name, row.fecha_hasta, row.solicitud_viatico_id.fecha_hasta))

    #Columns
    solicitud_viatico_id = fields.Many2one('grp.solicitud.viaticos', u'Solicitud viático')
    origen = fields.Many2one('grp.localidad', string='Origen', required=True)
    destino = fields.Many2one('grp.localidad', string='Destino', required=True)
    fecha_desde = fields.Datetime('Fecha desde', required=True)
    fecha_hasta = fields.Datetime('Fecha hasta', required=True)

class GrpSolicitudCmpViaticoWzd(models.TransientModel):
    _name = 'grp.solicitud.cmp.viatico.wzd'
    _descripcion = 'Confirmar solicitud'

    @api.multi
    def action_confirm(self):
        if self.env.context.get('active_id', False) and self.env.context.get('model_method', False):
            model_method = self.env.context['model_method']
            if not isinstance(self.env.context['model_method'], (list,)):
                model_method = [self.env.context['model_method']]
            method = model_method[0]
            args = len(model_method) > 1 and model_method[1] or []
            row = self.env['grp.solicitud.viaticos'].browse(self.env.context['active_id'])
            if hasattr(row, method):
                return getattr(row.with_context({'check_comp_conf_viatico_done':True}), method)(*args)
        return {'type': 'ir.actions.act_window_close'}
