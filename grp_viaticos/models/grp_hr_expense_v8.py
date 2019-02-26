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
import time
from datetime import datetime

import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from openerp import models, fields, api, _
from openerp import workflow
from openerp.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# TODO: SPRING 11 GAP 318 K
ESTADO = [('draft', 'Borrador'),
          ('confirm', 'En Aprobación'),
          ('en_autorizacion', 'En Autorización'),
          ('en_financiero', 'En Financiero'),
          ('autorizado', 'Autorizado'),
          ('paid', 'Paid'),
          ('cancelled', 'Refused'),
          ('cancelado', 'Cancelado'),
          ]
TIPO_VIATICO = [('interior', u'Viático Interior'),
                ('exterior', u'Viático Exterior')
                ]
TIPO_LOCOMOCION = [('bus', u'Bus'), ('locomocion_propia', u'Locomoción Propia'),
                   ('locomocion_oficial', u'Locomoción Oficial'),
                   ('locomocion_otras', u'Locomoción otras Instit/Organis')]


class hr_expense_expense_v8(models.Model):
    _inherit = 'hr.expense.expense'
    # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
    # _rec_name = 'sequence'
    _rec_name = 'x_sequence'

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self.env.user.has_group('grp_viaticos.grp_sv_solicitante') and not (
                self.env.user.has_group('grp_viaticos.grp_sv_autoriza') or
                self.env.user.has_group('grp_viaticos.grp_sv_aprobar_viaje') or
                self.env.user.has_group('grp_viaticos.grp_sv_autorizar_financiero') or
                self.env.user.has_group('grp_viaticos.grp_aprobar_rendicion') or
                self.env.user.has_group('grp_viaticos.grp_aprobar_rendicion_f')
        ) and not self.env.user.id == SUPERUSER_ID:
            if args:
                new_args = ['&','|',['employee_id.user_id', '=', self.env.user.id],['create_uid','=',self.env.user.id]]
                new_args.extend(args)
            else:
                new_args = ['|',['employee_id.user_id', '=', self.env.user.id],['create_uid','=',self.env.user.id]]
        else:
            new_args = args
        return super(hr_expense_expense_v8, self)._search(new_args, offset, limit, order, count=count,
                                                         access_rights_uid=access_rights_uid)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self.env.user.has_group('grp_viaticos.grp_sv_solicitante') and not (
                            self.env.user.has_group('grp_viaticos.grp_sv_autoriza') or
                            self.env.user.has_group('grp_viaticos.grp_sv_aprobar_viaje') or
                            self.env.user.has_group('grp_viaticos.grp_sv_autorizar_financiero') or
                            self.env.user.has_group('grp_viaticos.grp_aprobar_rendicion') or
                            self.env.user.has_group('grp_viaticos.grp_aprobar_rendicion_f')
        ) and not self.env.user.id == SUPERUSER_ID:
            domain.extend(['|',['employee_id.user_id', '=', self.env.user.id],['create_uid','=',self.env.user.id]])
        return super(hr_expense_expense_v8, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                            orderby=orderby, lazy=lazy)

    @api.model
    def _default_operating_unit_id(self):
        return self.env['res.users'].operating_unit_default_get(self.env.uid) or self.env['operating.unit']

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

    doc_type = fields.Selection([('rendicion_viatico', u'Rendición de viáticos'),], 'Tipo de documento')

    # TODO: SPRING 11 GAP 318 K
    solicitud_viatico_id = fields.Many2one('grp.solicitud.viaticos', u'Solicitud de Viáticos', ondelete='restrict')
    # TODO: M SPRING 14 GAP 29_31
    tipo = fields.Selection(TIPO_VIATICO, string=u'Tipo')
    motivo_viaje = fields.Many2one('grp.motivo.viaje', string=u'Motivo del viaje', ondelete="restrict")
    destino = fields.Many2one('grp.localidad', string='Localidad o zona', ondelete="restrict")
    fecha_desde = fields.Datetime(string=u'Fecha Desde')
    fecha_hasta = fields.Datetime(string=u'Fecha Hasta')

    voucher = fields.Integer(string=u'Voucher', size=8)
    matricula = fields.Char(string=u'Matricula', size=10)
    lugar_partida = fields.Char(string=u'Lugar de partida', size=50) # TODO: M SPRING 14 GAP 29_31
    operating_unit_id = fields.Many2one(comodel_name='operating.unit', string=u'Unidad ejecutora',
                                        default=lambda self: self._default_operating_unit_id(), required=True)
    tipo_locomocion = fields.Selection(TIPO_LOCOMOCION, string=u'Tipo de locomoción') # TODO: M SPRING 14 GAP 29_31
    km_recorrer = fields.Float(u'Distancia recorrida (sólo ida)')
    km_recorrer_cmp = fields.Float('KM a recorrer')
    amount = fields.Float(string=u'Total Amount', compute='_compute_amount')
    diferencia = fields.Float(string=u'Diferencia', compute='_compute_diferencia')

    state = fields.Selection(ESTADO, 'Status', readonly=True, track_visibility='onchange', copy=False,
                             help='When the expense request is created the status is \'Draft\'.\n It is confirmed by the user and request is sent to admin, the status is \'Waiting Confirmation\'.\
            \nIf the admin accepts it, the status is \'Accepted\'.\n If the accounting entries are made for the expense request, the status is \'Waiting Payment\'.')
    # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
    # sequence = fields.Char('Nombre', copy=False, default='Rendición en borrador', track_visibility='onchange')
    x_sequence = fields.Char('Nombre', copy=False, default='Rendición en borrador', track_visibility='onchange', oldname='sequence')
    #
    adelanto = fields.Float('Adelanto de Viáticos',
                            compute = '_compute_adelanto',
                            digits_compute=dp.get_precision('Account'), store=True)  # TODO: R GAP 318
    # TODO: SPRING 11 GAP 25 K
    requiere_alojamiento = fields.Boolean(string=u'¿Requiere alojamiento?', default=False)
    config_importe_viatico_id = fields.Many2one('grp.configuracion.importes.viaticos', string=u'Configuración usada',
                                                compute='_compute_config_importe_viatico_id', store=True,
                                                multi='configuracion_importe_viatico_expense',
                                                ondelete='restrict')
    config_complemento_viatico_id = fields.Many2one('grp.configuracion.importes.viaticos',
                                                    string=u'Configuración usada',
                                                    compute='_compute_config_importe_viatico_id', store=True,
                                                    multi='configuracion_importe_viatico_expense',
                                                    ondelete='restrict')
    locomocion_propia_id = fields.Many2one('grp.locomocion.propia', string=u'Configuración usada',
                                           compute='_compute_config_importe_viatico_id', store=True,
                                           multi='configuracion_importe_viatico_expense',
                                           ondelete='restrict')

    show_move_line_button = fields.Boolean(
        string=u'Mostrar botón de generar apuntes contables',
        default=True)

    user_operating_unit_id = fields.Many2one('operating.unit', compute = '_compute_user_operating_unit_id', default=_default_user_operating_unit_id)

    fecha_validacion_rendicion = fields.Date(u'Fecha Validación', select=True, copy=False)
    usuario_validacion_rendicion = fields.Many2one('res.users', 'Validado por', readonly=True, copy=False,
                                                   states={'draft': [('readonly', False)],
                                                           'confirm': [('readonly', False)]})
    fecha_aprobador_rendicion = fields.Date(u'Fecha Validación', select=True, copy=False)
    usuario_aprobador_rendicion = fields.Many2one('res.users', 'Aprobado por', readonly=True, copy=False,
                                                  states={'draft': [('readonly', False)],
                                                          'confirm': [('readonly', False)]})

    # RAGU
    tipo_cambio = fields.Float('Tipo de cambio', compute='_compute_tipo_cambio', digits=(12, 6),
                               help='El tipo de cambio usado en el pago.')
    edit_lines = fields.Boolean(u'Lineas editables', compute='_compute_edit_lines')
    currency_id = fields.Many2one(
        'res.currency',
        u'Moneda',
        required=True,
        readonly=True,
        states={
            'draft': [('readonly', False)],
            'confirm': [('readonly', False)]
        },
        domain=[('name', 'in', ['UYU', 'USD'])]
    )
    create_uid = fields.Many2one("res.users", string=u"Usuario", readonly=1)

    instance_editable = fields.Boolean('Editable', compute='_compute_instance_editable')
    solicitante_editable = fields.Boolean('Editable', compute='_compute_solicitante_editable')

    rendicion_multi = fields.One2many('grp.rendicion.viaticos.multi', 'rendicion_viatico_id', string=u'Múltiples destinos')

    flag_adelanto = fields.Boolean('Adelanto', related='solicitud_viatico_id.lleva_adelanto', readonly=True)
    categoria = fields.Selection(selection=[('categ_a', u'Categoría A'),('categ_b', u'Categoría B')], string=u'Categoría')

    paid_date = fields.Date('Fecha de pago', compute='_compute_paid_date')
    department_id = fields.Many2one('hr.department', string=u'Unidad organizativa', related='employee_id.department_id', readonly=True, store=True, states=None)

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        to_return = super(hr_expense_expense_v8, self).onchange_employee_id(cr, uid, ids, employee_id, context)
        if employee_id:
            rendicion_viaticos_ids = self.search(cr,SUPERUSER_ID,[('employee_id','=',employee_id),
                                                                  ('state','!=','cancelado'),
                                                                  ('solicitud_viatico_id','!=',False)],context = context)
            solicitud_rendidas = self.browse(cr,uid,rendicion_viaticos_ids,context).mapped(lambda x: x.solicitud_viatico_id).ids
            domain = {'solicitud_viatico_id': ['&', ('solicitante_id.employee_ids', 'in', employee_id),'&',('id', 'not in', solicitud_rendidas),'|', '&', ('lleva_adelanto', '=', True), ('adelanto_pagado', '=', True), '&',('lleva_adelanto', '=', False), ('state', '=', 'autorizado')]}
        else:
            domain = {'solicitud_viatico_id': [('id', 'in', [])]}
        if to_return.has_key('domain'):
            to_return['domain'].update(domain)
        else:
            to_return['domain'] = domain
        return to_return


    @api.onchange('tipo')
    def onchange_tipo(self):
        if self.tipo == 'exterior':
            self.currency_id = self.env['res.currency'].search([('name', '=', 'USD')], limit=1).id
            domain = {'destino': [('country_id', '!=', self.env.user.company_id.country_id.id)]}
            if self.destino.country_id.id in [self.env.user.company_id.country_id.id, False]:
                self.destino = False
        elif self.tipo:
            self.currency_id = self.env.user.company_id.currency_id.id
            domain = {'destino': ['|', ('country_id', '=', self.env.user.company_id.country_id.id),
                                  ('country_id', '=', False)]}
            if self.destino.country_id.id not in [self.env.user.company_id.country_id.id, False]:
                self.destino = False
        else:
            domain = {'destino': [('id', 'in', [])]}
            self.destino = False
            self.currency_id = False
        return {
            'domain': domain
        }

    @api.multi
    def _compute_paid_date(self):
        VoucherLine = self.env['account.voucher.line']
        for rec in self:
            rec.paid_date = VoucherLine.search(
                [('origin_voucher_id.rendicion_viaticos_id', '=', rec.id), ('amount', '!=', 0),
                 ('voucher_id.state', '=', 'posted')], limit=1).voucher_id.date

    @api.one
    @api.depends('state')
    def _compute_instance_editable(self):
        _instance_editable = False
        if self.state == 'draft' and self.env.user.has_group('grp_viaticos.grp_sv_solicitante'):
            _instance_editable = True
        if self.state in ('confirm') and self.env.user.has_group('grp_viaticos.grp_aprobar_rendicion'):
            _instance_editable = True
        if self.state == 'en_autorizacion' and self.env.user.has_group('grp_viaticos.grp_aprobar_rendicion'):
            _instance_editable = True
        if self.state == 'en_financiero' and self.env.user.has_group('grp_viaticos.grp_aprobar_rendicion_f'):
            _instance_editable = True
        if self.state == 'autorizado' and self.env.user.has_group('grp_viaticos.grp_aprobar_rendicion_f'):
            _instance_editable = True

        self.instance_editable = _instance_editable

    @api.one
    @api.depends('state')
    def _compute_solicitante_editable(self):
        self.solicitante_editable = self.env.user.has_group('grp_viaticos.grp_rv_solicitantesuperior')

    @api.multi
    @api.depends('solicitud_viatico_id')
    def _compute_adelanto(self):
        for rec in self:
            if rec.solicitud_viatico_id:
                adelanto_id = self.sudo().env['account.voucher'].search([
                    ('solicitud_viatico_id', '=', rec.solicitud_viatico_id.id),
                    ('state', '=', 'pagado'),
                    ('rendicion_anticipos_id', '=', False)], limit=1)
                rec.adelanto = adelanto_id and adelanto_id.amount or 0
            else:
                rec.adelanto = 0

    # RAGU restringiendo caracteres
    @api.one
    @api.constrains('voucher', 'tipo_locomocion')
    def _check_voucher(self):
        if self.tipo_locomocion == 'bus' and len(str(self.voucher)) > 8:
            raise ValidationError(_(
                u"El voucher no puede ser un número con más de 8 dígitos!"))

    @api.one
    @api.constrains('solicitud_viatico_id', 'employee_id')
    def _check_solicitud(self):
        if self.solicitud_viatico_id.exists() and self.employee_id.id not in self.solicitud_viatico_id.solicitante_id.employee_ids.ids:
            raise ValidationError(_(
                u"La Solicitud de Viáticos seleccionada no corresponde al mismo Empleado!"))

    # RAGU: lineas editables en estado En autorizacion para el rol SV Autorizar si Tipo Exterior
    @api.one
    @api.depends('tipo', 'state')
    def _compute_edit_lines(self):
        self.edit_lines = (self.state == 'draft' and self.env.user.has_group('grp_viaticos.grp_sv_solicitante')) or (
        self.env.user.has_group('grp_viaticos.grp_aprobar_rendicion_f') and self.state == 'en_financiero')

    @api.multi
    @api.constrains('solicitud_viatico_id', 'fecha_desde', 'fecha_hasta')
    def _check_solicitud_fechas(self):
        for rec in self:
            if rec.solicitud_viatico_id.id and rec.fecha_hasta < rec.solicitud_viatico_id.fecha_desde:
                raise ValidationError(
                    _('La fecha hasta de la rendicion no puede ser menor que la fecha desde de la solicitud.'))

    # TODO: SPRING 11 GAP 25 K
    @api.depends('categoria', 'fecha_desde', 'fecha_hasta')
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

    # RAGU: tipo de cambio
    @api.depends('currency_id')
    def _compute_tipo_cambio(self):
        for rec in self:
            rec.tipo_cambio = rec.currency_id.rate

    # @api.multi
    # def write(self, vals):
    #     if vals.get('state') == 'draft':
    #         vals.update({'solicitud_viatico_id': False})
    #     return super(hr_expense_expense_v8, self).write(vals)

    def expense_confirm(self):
        to_return = super(hr_expense_expense_v8, self).expense_confirm()
        if self.doc_type and self.doc_type == u'rendicion_viatico':
            Sequence = self.env['ir.sequence']
            for rec in self:
                if rec.employee_id.id in self.env.user.employee_ids.ids or rec.create_uid.id == self.env.user.id:
                    # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
                    # rec.write({'sequence': Sequence.get('rv.number')})
                    rec.write({'x_sequence': Sequence.get('rv.number')})
                    #
                else:
                    raise ValidationError(
                        _("Solo puede Enviar a Aprobar la Rendición el Usuario que la creó o el Solicitante!"))
        return to_return

    @api.multi
    def action_move_create(self):
        account_move_obj = self.env['account.move']
        account_move_line_obj = self.env['account.move.line']
        cur_obj = self.pool.get('res.currency')
        for rec in self:
            if not rec.employee_id.address_home_id:
                raise ValidationError(
                    _(u'El empleado debe tener una dirección de casa.'))
            if not rec.employee_id.address_home_id.supplier_advance_account_id.id:
                raise ValidationError(
                    _(
                        u'El empleado debe tener una cuenta anticipos de proveedores establecida en su dirección de casa.'))
            if len(rec.line_ids) > 0:
                # create the move that will contain the accounting entries
                a = rec.account_move_get(rec.id)
                move_id = account_move_obj.create(a)
                company_currency = rec.company_id.currency_id.id
                diff_currency_p = rec.currency_id.id <> company_currency
                currency_id = False
                amount = rec.amount
                amount_currency = False
                if diff_currency_p:
                    amount_currency = rec.amount * -1
                    currency_id = rec.currency_id.id
                    amount = cur_obj.compute(self._cr, self._uid, currency_id, company_currency, rec.amount,
                                             self._context)
                for linea in rec.line_ids:
                    property_obj = self.pool.get('ir.property')
                    if linea.product_id:
                        acc = linea.product_id.property_account_expense
                        if not acc:
                            acc = linea.product_id.categ_id.property_account_expense_categ
                        if not acc:
                            raise ValidationError(
                                _(
                                    u'No se ha encontrado una cuenta de compras para el producto %s (o para su categoría). Por favor, configure una.') % (
                                    linea.product_id.name))
                    else:
                        acc = property_obj.with_context(force_company=linea.company_id.id).get(
                            'property_account_expense_categ', 'product.category')
                        if not acc:
                            raise ValidationError(
                                _(
                                    u'Configure por favor la cuenta de gastos por defecto para la compra del producto: "property_account_expense_categ".'))

                    total_amount_currency = False
                    total_amount = linea.total_amount
                    if diff_currency_p:
                        total_amount_currency = linea.total_amount
                        total_amount = cur_obj.compute(self._cr, self._uid, currency_id, company_currency,
                                                       linea.total_amount, self._context)
                    account_move_line_obj.create({
                        'move_id': move_id.id,
                        'name': '/',
                        'partner_id': rec.employee_id.address_home_id.id or False,
                        'amount_currency': total_amount_currency,
                        'currency_id': currency_id,
                        'account_id': acc.id,
                        'credit': False,
                        'debit': total_amount,
                        'operating_unit_id': rec.operating_unit_id.id
                    })

                _account_id = rec.employee_id.address_home_id.supplier_advance_account_id.id
                if not _account_id:
                    raise ValidationError(_(u'No se ha podido identificar una cuenta para generar la información contable'))

                account_move_line_obj.create({
                    'move_id': move_id.id,
                    # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
                    # 'name': rec.sequence,
                    'name': rec.x_sequence,
                    #
                    'account_id': _account_id,
                    'debit': False,
                    'credit': amount,
                    'partner_id': rec.employee_id.address_home_id.id or False,
                    'amount_currency': amount_currency,
                    'currency_id': currency_id,
                    'operating_unit_id': rec.operating_unit_id.id
                })

                dict_write = {'account_move_id': move_id.id, 'show_move_line_button': False}
                if rec.diferencia == 0:
                    dict_write.update({'state': 'paid'})
                else:
                    rec.crear_recibo()
                rec.write(dict_write)

            else:
                raise ValidationError(_(u'Error, para generar apuntes contables'
                                                   u' de la Rendición de Viáticos primero debe crear líneas'))
            return True

    # RAGU correcciones varias para generar rendicion de viaticos
    def get_devolucion_product(self):
        return self.env['product.product'].search([('devolucion_viatico','=',True)],limit=1)

    @api.one
    def crear_recibo(self):
        account_voucher_obj = self.env['account.voucher']
        partner = self.employee_id.address_home_id
        if self.diferencia > 0:
            if self.journal_id and self.journal_id.type == 'purchase':
                journal_id = self.journal_id
            else:
                search_args = [('type', '=', 'purchase')]
                if self.env.user.company_id.currency_id.id != self.currency_id.id:
                    search_args.append(('currency', '=', self.currency_id.id))
                else:
                    search_args.extend(['|', ('currency', '=', False), ('currency', '=', self.env.user.company_id.currency_id.id)])
                journal_id = self.env['account.journal'].search(search_args, limit=1)
            if journal_id:
                account_id = partner.property_account_payable
                if not account_id:
                    account_id = journal_id.default_credit_account_id
                    if not account_id:
                        raise ValidationError(_(u'Error, debe configurar la cuenta a pagar'
                                                           u' del beneficierio o del diario contable utilizado.'))
                account_voucher_id = account_voucher_obj.create({
                    'partner_id': partner.id or False,
                    'date': fields.date.today(),
                    'journal_id': journal_id.id,
                    'type': 'payment',
                    'payment_rate': 0,
                    'account_id': account_id.id,
                    'amount': abs(self.diferencia),
                    'operating_unit_id': self.operating_unit_id.id,
                    'rendicion_viaticos_id': self.id,
                    'line_dr_ids': [
                        (0, 0, {
                            'account_id': partner.supplier_advance_account_id.id,
                            'amount_unreconciled': abs(self.diferencia),
                            'operating_unit_id': self.operating_unit_id.id,
                            'amount': abs(self.diferencia),
                            'journal_id': journal_id.id or False,
                            'partner_id': partner.id or False,
                        })
                    ]
                })

                tipo_ejecucion = self.env['tipo.ejecucion.siif'].search([('codigo', '=', 'P')])
                invoice_id = self.env['account.invoice'].create({
                    'partner_id': account_voucher_id.partner_id.id,
                    'account_id': account_voucher_id.account_id.id,
                    'date_invoice': account_voucher_id.date,
                    'internal_number': account_voucher_id.number,
                    'number': account_voucher_id.number,
                    'currency_id': account_voucher_id.currency_id.id,
                    'siif_tipo_ejecucion': tipo_ejecucion and tipo_ejecucion.id or False,
                    'type': 'in_invoice',
                    'amount_total': abs(self.diferencia),
                    'pago_aprobado': False,
                    'doc_type': 'adelanto_viatico',
                    'state': 'open',
                    'operating_unit_id': self.operating_unit_id.id,
                    'journal_id': journal_id.id,
                    'invoice_line': [
                        (0, 0, {'name': line.name or '', 'account_id': line.account_id.id, 'price_unit': line.amount})
                        for
                        line in account_voucher_id.line_dr_ids]
                })
                account_voucher_id.write({'invoice_id': invoice_id.id})
                invoice_id.write({'doc_type': 'adelanto_viatico'})
                # TODO: L VARIANZA GRP
                context = dict(self._context or {})
                # account_voucher_id.action_move_line_create()
            else:
                raise ValidationError(_(u'Error, debe seleccionar un diario compra'
                                                   u' o configurar un diario de compra de la compañia.'))
        else:
            # TODO: SPRING 11 GAP 28 L
            if self.journal_id and self.journal_id.type == 'sale':
                journal_id = self.journal_id
            else:
                search_args = [('type', '=', 'sale')]
                if self.env.user.company_id.currency_id.id != self.currency_id.id:
                    search_args.append(('currency', '=', self.currency_id.id))
                else:
                    search_args.extend(['|',('currency', '=', False),('currency','=',self.env.user.company_id.currency_id.id)])
                journal_id = self.env['account.journal'].search(search_args, limit=1)
            if not journal_id:
                raise ValidationError(_("No se ha podido identificar un Diario!"))
            if journal_id:
                account_id = partner.property_account_receivable
                if not account_id:
                    account_id = journal_id.default_debit_account_id
                    if not account_id:
                        raise ValidationError(_(u'Error, debe configurar la cuenta a cobrar'
                                                           u' del beneficierio o del diario contable utilizado.'))
                # product_id = self.env['product.product'].search([('devolucion_viatico','=',True)],limit=1)
                # product_id = self.sudo().operating_unit_id.viatico_product_id
                product_id = self.get_devolucion_product()
                if not product_id:
                    raise ValidationError(_(u"Debe configurar un producto Dev. Viáticos para la Unidad ejecutora seleccionada!"))
                account_voucher_obj.create({
                    'partner_id': partner.id or False,
                    'date': fields.date.today(),
                    'journal_id': journal_id.id,
                    'type': 'sale',
                    'account_id': account_id.id,
                    'amount': abs(self.diferencia),
                    'payment_rate': 0,
                    'operating_unit_id': self.operating_unit_id.id,
                    'rendicion_viaticos_id': self.id,
                    'solicitud_viatico_id': self.solicitud_viatico_id.id,
                    'line_cr_ids': [
                        (0, 0, {
                            'account_id': partner.supplier_advance_account_id.id,
                            'amount_unreconciled': abs(self.diferencia),
                            'amount': abs(self.diferencia),
                            'journal_id': journal_id.id or False,
                            'partner_id': partner.id or False,
                            'product_id': product_id.id,
                            'operating_unit_id': self.operating_unit_id.id,
                        })
                    ]
                }).proforma_voucher()
            else:
                raise ValidationError(_(u'Error, debe seleccionar un diario venta'
                                                   u' o configurar un diario de venta de la compañia.'))
        return True

    @api.depends('line_ids','line_ids.total_amount')
    def _compute_amount(self):
        for record in self:
            record.amount = sum(map(lambda x: x.total_amount, record.line_ids))

    @api.depends('amount', 'adelanto','state')
    def _compute_diferencia(self):
        for record in self:
            record.diferencia = 0 if record.state == 'paid' else record.amount - record.adelanto

    # TODO: SPRING 11 GAP 318 K
    @api.multi
    def expense_en_autorizacion(self):
        if self.doc_type and self.doc_type == u'rendicion_viatico':
            self.action_send_email()
        elif self.doc_type and self.doc_type == u'rendicion_anticipo':
            self.action_send_email_anticipo()


        return self.write(
            {'state': 'en_autorizacion', 'date_valid': time.strftime('%Y-%m-%d'), 'user_valid': self._uid, 'fecha_validacion_rendicion': time.strftime('%Y-%m-%d'), 'usuario_validacion_rendicion': self._uid})

    @api.multi
    def action_send_email_anticipo(self):

        Mail = self.pool['mail.mail']

        ir_model_data = self.env['ir.model.data']
        _model, group_id = ir_model_data.get_object_reference('grp_tesoreria',
                                                              'group_grp_autoriza_anticipo')
        users = self.env['res.users'].search(
            [('groups_id', 'in', group_id), ('operating_unit_ids', 'in', self.operating_unit_id.id)])

        web_base_url = self.pool.get('ir.config_parameter').get_param(self._cr, self._uid, 'web.base.url')

        partner_ids = []
        if users:
            partner_ids = [user.partner_id.id for user in users]

        body = u'''La rendición de anticipo de fondos <a href="%(web)s/web#id=%(anticipo_id)s&view_type=form&model=hr.expense.expense">%(anticipo_name)s</a> del funcionario <a href="%(web)s/web#id=%(emp_id)s&view_type=form&model=hr.employee">%(emp_name)s</a> está pendiente de autorización.''' \
               % {'web': web_base_url,
               # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
               # 'anticipo_name': self.sequence,
               'anticipo_name': self.x_sequence,
               #
               'anticipo_id': self.id,
               'emp_name': self.employee_id.name,
               'emp_id': self.employee_id.id,}

        vals = {
            'subject': 'Rendición de anticipo de fondos',
            'body_html': '<pre>%s</pre>' % body,
            'recipient_ids': [(6, 0, partner_ids)],
            'email_from': self.write_uid.email
        }
        mail_id = self.env['mail.mail'].create(vals).id
        Mail.send(self._cr, self._uid, [mail_id], context=self._context)

    @api.multi
    def action_send_email(self):

        Mail = self.pool['mail.mail']

        ir_model_data = self.env['ir.model.data']

        _model, group_id = ir_model_data.get_object_reference('grp_viaticos',
                                                              'grp_autorizar_rendicion')
        users = self.env['res.users'].search(
            [('groups_id', 'in', group_id), ('operating_unit_ids', 'in', self.operating_unit_id.id)])

        partner_ids = []
        if users:
            partner_ids = [user.partner_id.id for user in users]

        web_base_url = self.pool.get('ir.config_parameter').get_param(self._cr, self._uid, 'web.base.url')

        body = u'''La rendición de viáticos <a href="%(web)s/web#id=%(rendicion_id)s&view_type=form&model=hr.expense.expense">%(rendicion_name)s</a> del funcionario <a href="%(web)s/web#id=%(emp_id)s&view_type=form&model=hr.employee">%(emp_name)s</a> está pendiente de autorización.''' \
               % {'web':web_base_url,
               # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
               # 'rendicion_name': self.sequence,
               'rendicion_name': self.x_sequence,
               #
               'rendicion_id': self.id,
               'emp_name': self.employee_id.name,
               'emp_id': self.employee_id.id,}

        vals = {
            'subject': 'Rendición de viáticos',
            'body_html': '<pre>%s</pre>' % body,
            'recipient_ids': [(6, 0, partner_ids)],
            'email_from': self.write_uid.email
        }
        mail_id = self.env['mail.mail'].create(vals).id
        Mail.send(self._cr, self._uid, [mail_id], context=self._context)

    @api.multi
    def _action_autorizar(self):
        return workflow.trg_validate(self._uid, 'hr.expense.expense', self.id, 'autorizar', self.env.cr)


    @api.multi
    def action_autorizar(self):
        if len(self) == 1 and self.state=='en_autorizacion':
            #Se adiciona al if la condición len(self) == 1, si se quita entonces se debe iterar por self. Se asume que es desde uno de los botones.
            return self.suspend_security().check_comp_conf_viatico('_action_autorizar', [])
        else:
            return workflow.trg_validate(self._uid, 'hr.expense.expense', self.id, 'autorizar', self.env.cr)

    @api.multi
    def action_refuse2draft(self):
        self.ensure_one()
        self.write({'solicitud_viatico_id': False})
        return workflow.trg_validate(self._uid, 'hr.expense.expense', self.id, 'draft', self.env.cr)

    # TODO: SPRING 11 GAP 318 K
    @api.multi
    def expense_en_financiero(self):
        return self.write({'state': 'en_financiero', 'date_valid': time.strftime('%Y-%m-%d'), 'user_valid': self._uid, 'fecha_aprobador_rendicion': time.strftime('%Y-%m-%d'), 'usuario_aprobador_rendicion': self._uid})

    # TODO: SPRING 11 GAP 318 K
    @api.multi
    def expense_autorizado(self):
        if len(self) == 1 and self.state=='en_autorizacion':
            #Se adiciona al if la condición len(self) == 1, si se quita entonces se debe iterar por self. Se asume que es desde uno de los botones.
            return self.check_comp_conf_viatico('write', [{'state': 'autorizado', 'date_valid': time.strftime('%Y-%m-%d'), 'user_valid': self._uid}])
        else:
            return self.write({'state': 'autorizado', 'date_valid': time.strftime('%Y-%m-%d'), 'user_valid': self._uid})

    @api.multi
    def expense_canceled(self):
        return self.write({'state': 'cancelled','fecha_aprobador_rendicion': False, 'usuario_aprobador_rendicion': False,'fecha_validacion_rendicion': False, 'usuario_validacion_rendicion': False})


    # TODO: SPRING 11 GAP 318 K
    def crear_extorno(self):
        move = self.account_move_id
        if move:
            period_id = self.env['account.period'].find(fields.Date.today()).id
            move.create_reversals(
                fields.Date.today(),
                reversal_period_id=period_id,
            )

    def _get_voucher(self):
        voucher_obj = self.env['account.voucher']
        if self.doc_type == 'rendicion_viatico':
            return voucher_obj.search([('rendicion_viaticos_id', '=', self.id), ('state', '!=', 'cancel')], limit=1)
        else:
            return voucher_obj

    @api.multi
    def _check_expense_cancelado(self):
        for rec in self:
            voucher_line_ids = self.env['account.voucher.line'].search([('amount','!=',0),('origin_voucher_id.rendicion_viaticos_id', '=', rec.id),('voucher_id.state', 'not in', ['cancelado', 'cancel'])])
            for voucher_line_id in voucher_line_ids:
                if voucher_line_id.voucher_id.type == 'receipt':
                    raise ValidationError(_(u"No puede cancelarse la Rendición pues ya está incluida en el Pago de cliente %s!") % (voucher_line_id.voucher_id.name_get()[0][1]))
                else:
                    raise ValidationError(_(u"No puede cancelarse la Rendición pues ya está incluida en el Pago %s!") % (voucher_line_id.voucher_id.name_get()[0][1]))
        return True


    # TODO: SPRING 11 GAP 318 K
    @api.multi
    def expense_cancelado(self):
        self._check_expense_cancelado()
        for rec in self:
            voucher_id = rec._get_voucher()
            voucher_id.cancel_voucher()
            voucher_id.invoice_id.action_cancel()
            rec.crear_extorno()
        return self.write({'state': 'cancelado', 'date_valid': time.strftime('%Y-%m-%d'), 'user_valid': self._uid,'show_move_line_button': True})

    @api.one
    def generar_lineas(self):
        hr_expense_line = self.env['hr.expense.line']
        fecha_inicio = datetime.strptime(self.fecha_desde, "%Y-%m-%d %H:%M:%S")
        fecha_fin = datetime.strptime(self.fecha_hasta, "%Y-%m-%d %H:%M:%S")
        diference = fecha_fin - fecha_inicio
        cantidad_dias = diference.days
        cantidad_horas = round(diference.total_seconds() / 3600 - float(cantidad_dias) * 24, 2)
        configuracion = self.config_importe_viatico_id
        if configuracion:
            importe = configuracion.valor_alimentacion * cantidad_dias
            if cantidad_horas > self.employee_id.cantidad_horas_trabajadas:
                importe += configuracion.valor_porciento_alimentacion if cantidad_horas <= 12.0 else configuracion.valor_alimentacion
            hr_expense_line.create({
                'product_id': configuracion.product_alimentacion_id.id,
                'name': configuracion.product_alimentacion_id.name,
                'total': importe,
                'total_inicial': importe,
                'expense_id': self.id,
            })
            if cantidad_dias > 0 or self.requiere_alojamiento:
                if cantidad_dias == 0 and self.requiere_alojamiento:
                    importe = configuracion.valor_pernocte
                else:
                    importe = configuracion.valor_pernocte * cantidad_dias
                hr_expense_line.create({
                    'product_id': configuracion.product_pernocte_id.id,
                    'name': configuracion.product_pernocte_id.name,
                    'total': importe,
                    'total_inicial': importe,
                    'expense_id': self.id,
                })
        if self.tipo_locomocion == 'locomocion_propia':
            if self.locomocion_propia_id:
                locomocion_linea = self.locomocion_propia_id.valor_nafta_ids.sorted(key=lambda a: a.fecha_desde, reverse=True)[0]
                hr_expense_line.create({
                    'product_id': self.locomocion_propia_id.product_id.id,
                    'name': self.locomocion_propia_id.product_id.name,
                    'total': self.km_recorrer_cmp / self.locomocion_propia_id.relacion_km * locomocion_linea.importe,
                    'total_inicial': self.km_recorrer_cmp / self.locomocion_propia_id.relacion_km * locomocion_linea.importe,
                    'expense_id': self.id,
                })
        if self.destino != '' and self.config_complemento_viatico_id:
                localidad_id = self.config_complemento_viatico_id.complemento_ids.filtered(
                    lambda x: x.localidad == self.destino)
                if localidad_id:
                    importe = localidad_id.valor_alimentacion * cantidad_dias
                    if cantidad_horas > self.employee_id.cantidad_horas_trabajadas:
                        importe += round(localidad_id.valor_alimentacion * 0.5,2) if cantidad_horas <= 12.0 else localidad_id.valor_alimentacion
                    if importe:
                        hr_expense_line.create({
                            'product_id': localidad_id.product_alimentacion_id.id,
                            'name': localidad_id.product_alimentacion_id.name,
                            'total': importe,
                            'total_inicial': importe,
                            'expense_id': self.id,
                        })
                    if cantidad_dias > 0 or self.requiere_alojamiento:
                        if cantidad_dias == 0 and self.requiere_alojamiento:
                            importe = localidad_id.valor_pernocte
                        else:
                            importe = localidad_id.valor_pernocte * cantidad_dias
                        if importe:
                            hr_expense_line.create({
                                'product_id': localidad_id.product_pernocte_id.id,
                                'name': localidad_id.product_pernocte_id.name,
                                'total': importe,
                                'total_inicial': importe,
                                'expense_id': self.id,
                            })
        return True

    # TODO: SPRING 11 GAP 25 K
    @api.model
    def copy(self, default=None):
        if not isinstance(default, dict):
            default = {}
        default.update({'line_ids': False})
        return super(hr_expense_expense_v8, self).copy(default=default)

    @api.model
    def create(self, vals):
        res = super(hr_expense_expense_v8, self).create(vals)
        if res.tipo == 'interior' and res.km_recorrer > 50:
            res.generar_lineas()
        return res

    @api.multi
    def action_generar_lineas(self):
        self.line_ids.unlink()
        for rec in self:
            if rec.tipo == 'interior' and rec.km_recorrer > 50:
                rec.generar_lineas()
        for rec in self:
            _amount = sum(map(lambda x: x.total_amount, rec.line_ids))
            super(models.Model, rec).write({'amount': _amount})

    # TODO: R GAP 318
    @api.onchange('solicitud_viatico_id')
    def onchange_solicitud_viatico_id(self):
        if self.solicitud_viatico_id:
            # rec_adelanto = self.sudo().env['account.voucher'].search([
            #     ('solicitud_viatico_id', '=', self.solicitud_viatico_id.id),('state','!=','cancel')], limit=1)
            # self.adelanto = rec_adelanto and rec_adelanto.amount or 0
            self.fecha_desde = self.solicitud_viatico_id.fecha_desde
            self.fecha_hasta = self.solicitud_viatico_id.fecha_hasta
            self.requiere_alojamiento = self.solicitud_viatico_id.requiere_alojamiento
            self.categoria = self.solicitud_viatico_id.categoria
            self.currency_id = self.solicitud_viatico_id.currency_id.id
            self.tipo_locomocion = self.solicitud_viatico_id.tipo_locomocion
            self.tipo = self.solicitud_viatico_id.tipo
            self.motivo_viaje = self.solicitud_viatico_id.motivo_viaje.id
            self.destino = self.solicitud_viatico_id.destino.id
            self.lugar_partida = self.solicitud_viatico_id.lugar_partida
            self.km_recorrer = self.solicitud_viatico_id.km_recorrer
            self.km_recorrer_cmp = self.solicitud_viatico_id.km_recorrer_cmp
            self.operating_unit_id = self.solicitud_viatico_id.operating_unit_id.id
            #multi dest
            _values = [(5, False, False)]
            for v in self.solicitud_viatico_id.viaticos_multi:
                _values.append((0, 0, {
                    'origen': v.origen and v.origen.id or False,
                    'destino': v.destino and v.destino.id or False,
                    'fecha_desde': v.fecha_desde,
                    'fecha_hasta': v.fecha_hasta
                }))
            self.rendicion_multi = _values

        elif self.employee_id:
            self.categoria = self.employee_id.categoria

    @api.model
    def check_comp_conf_viatico(self, method, *args):
        if self.rendicion_multi:
            loc = self.env['grp.localidad']
            for line in self.rendicion_multi:
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
                                'name': u'Confirmar rendición',
                                'res_model': 'grp.rendicion.cmp.viatico.wzd',
                                'view_mode': 'form',
                                'target': 'new',
                                'context': ctx
                            }
        if hasattr(self, method):
            args = args and args[0] or []
            return getattr(self.with_context({'check_comp_conf_viatico_done':True}), method)(*args)
        return True

    # _sql_constraints = [
    #     ('solicitud_viatico_uniq', 'UNIQUE (solicitud_viatico_id)',
    #      'Esta Solicitud de Viáticos ya fue utilizada en otro Gasto')
    # ]

# TODO: SPRING 11 GAP 318 K
class grp_hr_expense_line_v8(models.Model):
    _inherit = 'hr.expense.line'

    # TODO: SPRING 11 GAP 318 K
    @api.multi
    @api.depends('expense_id')
    def _compute_horas(self):
        for record in self:
            if record.expense_id and record.expense_id.fecha_hasta and record.expense_id.fecha_desde:
                difference = datetime.strptime(record.expense_id.fecha_hasta, "%Y-%m-%d %H:%M:%S") - datetime.strptime(
                    record.expense_id.fecha_desde, "%Y-%m-%d %H:%M:%S")
                record.horas = difference.total_seconds() / 3600
            else:
                record.horas = 0

    @api.model
    def _get_edit_lines(self):
        return self._context.get('edit_lines', False)

    @api.model
    def create(self, vals):
        vals['total_init'] = vals.get('total',0)
        return super(grp_hr_expense_line_v8,self).create(vals)

    name = fields.Char('Expense Note', required=False)
    date_value = fields.Date('Date', required=False)
    uom_id = fields.Many2one('product.uom', 'Unit of Measure', required=False)
    horas = fields.Float(string=u'Horas', compute='_compute_horas')
    total = fields.Float(string='Monto ingresado', digits_compute=dp.get_precision('Account'))
    total_init = fields.Float("Monto calculado", readonly=True)
    total_amount = fields.Float(string=u'Tipo de cambio', compute='_compute_total_amount',
                                digits_compute=dp.get_precision('Account'))
    total_inicial = fields.Float(string='Total inicial', digits_compute=dp.get_precision('Account'))
    edit_lines = fields.Boolean(u'Lineas editables', related='expense_id.edit_lines', default=_get_edit_lines,
                                readonly=True)

    receipt_date = fields.Date(u'Fecha de comprobante')
    # ref = fields.Char(u'Referencia')
    company = fields.Char(u'Empresa')

    @api.depends('total')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.total

class GrpRendicionViaticosMulti(models.Model):
    _name = 'grp.rendicion.viaticos.multi'
    _description = u'Múltiples destinos'
    _rec_name = 'rendicion_viatico_id'

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
            if row.rendicion_viatico_id.fecha_desde > row.fecha_desde:
                raise ValidationError("Origen: %s \n Destino: %s \n La Fecha desde: %s de Múltiples destinos debe ser mayor o igual que la Fecha desde: %s de la solicitud" % (row.origen.name, row.destino.name, row.fecha_desde, row.rendicion_viatico_id.fecha_desde))
            if row.rendicion_viatico_id.fecha_hasta < row.fecha_hasta:
                raise ValidationError("Origen: %s \n Destino: %s \n La Fecha hasta: %s de Múltiples destinos debe ser menor o igual que la Fecha hasta: %s de la solicitud" % (row.origen.name, row.destino.name, row.fecha_hasta, row.rendicion_viatico_id.fecha_hasta))

    #Columns
    rendicion_viatico_id = fields.Many2one('hr.expense.expense', u'Solicitud viático')
    origen = fields.Many2one('grp.localidad', string='Origen', required=True)
    destino = fields.Many2one('grp.localidad', string='Destino', required=True)
    fecha_desde = fields.Datetime('Fecha desde', required=True)
    fecha_hasta = fields.Datetime('Fecha hasta', required=True)

class GrpRendicionCmpViaticoWzd(models.TransientModel):
    _name = 'grp.rendicion.cmp.viatico.wzd'
    _descripcion = u'Confirmar rendición'

    @api.multi
    def action_confirm(self):
        if self.env.context.get('active_id', False) and self.env.context.get('model_method', False):
            model_method = self.env.context['model_method']
            if not isinstance(self.env.context['model_method'], (list,)):
                model_method = [self.env.context['model_method']]
            method = model_method[0]
            args = len(model_method) > 1 and model_method[1] or []
            row = self.env['hr.expense.expense'].browse(self.env.context['active_id'])
            if hasattr(row, method):
                return getattr(row.with_context({'check_comp_conf_viatico_done':True}), method)(*args)
        return {'type': 'ir.actions.act_window_close'}
