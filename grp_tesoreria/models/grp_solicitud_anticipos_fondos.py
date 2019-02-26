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

from openerp import models, fields, api, exceptions,_
import openerp.addons.decimal_precision as dp

# TODO: M SPRING 14 GAP 29_31

SOLICITUD_STATE = [('borrador', 'Borrador'),
                 ('en_aprobacion', u'En Aprobación'),
                 ('aprobado', 'Aprobado'),
                 ('en_autorizacion', u'En autorización'),
                 ('autorizado', u'Autorizado'),
                 ('rechazado', 'Rechazado'),
                 ('cancelado', 'Cancelado ')
                 ]

class GrpSolicitudAnticiposFondos(models.Model):
    _name = 'grp.solicitud.anticipos.fondos'
    _description = "Solicitud anticipos fondos"
    _inherit = ['mail.thread']
    _mail_post_access = 'read'

    # TODO: M SPRING 14 GAP 29_31
    @api.model
    def _get_employee_id(self):
        return self.env['hr.employee'].search([('user_id', '=', self._uid)], limit=1)

    # TODO: M SPRING 14 GAP 29_31
    @api.model
    def _get_currency_id(self):
        return self.env['res.currency'].search([('name', '=', 'UYU')], limit=1)

    @api.model
    def _get_fecha_ingreso(self):
        return fields.Datetime.now()

    # TODO: M SPRING 14 GAP 29_31
    name = fields.Char(string=u'Nº Solicitud anticipos fondos', default='Solicitud anticipos de fondos borrador')
    user_uid = fields.Many2one('res.users', 'Solicitante', required=True, readonly=True, default=lambda self: self._uid)
    user_employee_id = fields.Many2one('hr.employee', string=u'Empleado', compute='_compute_employee_id', store=True)
    descripcion = fields.Text(u'Descripción')
    operating_unit_id = fields.Many2one('operating.unit', string="Unidad Ejecutora",
                                        related='user_uid.default_operating_unit_id',store=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', string=u'Empleado', default=_get_employee_id)
    cedula = fields.Char(string=u'Cédula', related='employee_id.identification_id',
                         readonly=True, store=True)
    fecha_ingreso = fields.Datetime(string=u'Fecha de ingreso', required=True, default=_get_fecha_ingreso)
    currency_id = fields.Many2one('res.currency', string='Moneda', default=_get_currency_id,
                                  domain=[('name', 'in', ('UYU', 'USD'))], states={'borrador': [('readonly', False)]}, readonly=True)
    aprobador_id = fields.Many2one('res.users', 'Aprobado por')
    line_ids = fields.One2many('grp.informacion.solicitud', 'solicitud_id',
                                       string=u'Informacion')
    amount_total = fields.Float(string=u'Total', compute='_compute_amount_total', digits_compute=dp.get_precision('Account'))
    adelanto_pagado = fields.Boolean(string=u'Anticipo pagado', default=False)
    state = fields.Selection(SOLICITUD_STATE, u'Estado', default='borrador', track_visibility='onchange')

    @api.model
    @api.depends('user_uid')
    def _compute_employee_id(self):
        for rec in self:
            rec.user_employee_id = self.env['hr.employee'].search([('user_id', '=', rec.user_uid.id)], limit=1)

    @api.multi
    # @api.depends('line_ids.amount')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(map(lambda x: x.amount, rec.line_ids))

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def action_enviar_aprobar(self):
        for rec in self:
            if not rec.line_ids:
                raise exceptions.ValidationError(_(u"No se puede enviar a aprobar un registro sin líneas"
                                                   u" en la pestaña Información"))
            if rec.name == 'Solicitud anticipos de fondos borrador':
                dict_towrite = {'state': 'en_aprobacion', 'name': self.env['ir.sequence'].next_by_code('sol.antic.fondos.number')}
            else:
                dict_towrite = {'state': 'en_aprobacion'}
            rec.write(dict_towrite)

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def action_aprobar(self):
        self.write({'state': 'aprobado', 'aprobador_id':self.env.uid})

    @api.multi
    def action_autorizar(self):
        self.action_send_email()
        self.write({'state': 'en_autorizacion'})

    @api.multi
    def action_send_email(self):

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

        body = u'''La solicitud de anticipo de fondos <a href="%(web)s/web#id=%(anticipo_id)s&view_type=form&model=grp.solicitud.anticipos.fondos">%(anticipo_name)s</a> del solicitante <a href="%(web)s/web#id=%(user_id)s&view_type=form&model=res.users">%(user_name)s</a> está pendiente de autorización.'''\
               % {'web':web_base_url,
               'anticipo_name': self.name,
               'anticipo_id': self.id,
               'user_name': self.user_uid.name,
               'user_id': self.user_uid.id,}


        vals = {
            'subject': 'Solicitud de anticipo de fondos',
            'body_html': '<pre>%s</pre>' % body,
            'recipient_ids': [(6, 0, partner_ids)],
            'email_from': self.write_uid.email
        }
        mail_id = self.env['mail.mail'].create(vals).id
        Mail.send(self._cr, self._uid, [mail_id], context=self._context)

    @api.multi
    def action_autorizado(self):
        self.generar_anticipo_fondos()
        self.write({'state': 'autorizado'})

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def action_rechazar(self):
        self.write({'state': 'rechazado'})

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def action_pasar_borrador(self):
        self.write({'state': 'borrador'})

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def action_cancelar(self):
        anticipos_ids = self.env['account.voucher'].search([('solicitud_anticipos_id', '=', self.id),('rendicion_anticipos_id','=',False)], limit=1)
        if anticipos_ids:
            if anticipos_ids.filtered(lambda x: x.state != 'draft'):
                raise exceptions.ValidationError(_(u"Solo puede cancelar la solicitud anticipos de fondos sino existe un "
                                                   u"anticipo de fondos creado o si este está en estado borrador."))
            else:
                anticipos_ids.cancel_voucher()
                anticipos_ids.invoice_id.action_cancel()
        self.write({'state': 'cancelado'})

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def generar_anticipo_fondos(self):
        for rec in self:
            _user_employee_id = self.env['hr.employee'].search([('user_id', '=', rec.user_uid.id)], limit=1)
            if not _user_employee_id.address_home_id.supplier_advance_account_id or not _user_employee_id.address_home_id.property_account_payable:
                raise exceptions.ValidationError(_(u'El solicitante no tiene cuenta de pagos o cuenta anticipo de proveedores'))
            search_args = [('type', '=', 'purchase')]
            if rec.env.user.company_id.currency_id.id != rec.currency_id.id:
                search_args.append(('currency', '=', rec.currency_id.id))
                account_id = _user_employee_id.address_home_id.cuenta_a_pagar_me
            else:
                search_args.extend(
                    ['|', ('currency', '=', False), ('currency', '=', self.env.user.company_id.currency_id.id)])
                account_id = _user_employee_id.address_home_id.property_account_payable
            journal_id = self.env['account.journal'].search(search_args, limit=1)
            if not journal_id:
                raise exceptions.ValidationError(
                    _(u"No se ha encontrado un diario de compra asociado a la moneda de la solicitud"))
            if not account_id:
                raise exceptions.ValidationError(
                    _(u"No se ha encontrado una cuenta asociada a la moneda de la solicitud"))
            res_voucher = self.env['account.voucher'].create({
                'type': 'payment',
                'payment_rate': 0,
                'partner_id': _user_employee_id.address_home_id.id,
                'account_id': account_id.id,
                'date': fields.Date.from_string(fields.Date.today()),
                'operating_unit_id': rec.operating_unit_id.id,
                'solicitud_anticipos_id': rec.id,
                'line_dr_ids': [
                        (0, 0, {'concept_id': line.concept_id.id, 'account_id': line.account_id.id,
                                'amount_unreconciled': line.amount, 'amount': line.amount})
                        for
                        line in rec.line_ids],
                'amount': rec.amount_total,
                'journal_id': journal_id.id
            })
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
                    'amount_total': rec.amount_total,
                    'pago_aprobado': False,
                    'doc_type': 'vales_caja',
                    'state': 'open',
                    'journal_id': journal_id.id,
                    'operating_unit_id': rec.operating_unit_id.id,
                    'invoice_line': [
                        (0, 0, {'name': line.name or '', 'account_id': line.account_id.id, 'price_unit': line.amount})
                        for
                        line in res_voucher.line_dr_ids]
                })
                res_voucher.write({'invoice_id': res_invoice.id})
                res_invoice.write({'doc_type':'vales_caja'})


class GrpInformacionSolicitud(models.Model):
    _name = 'grp.informacion.solicitud'
    _description = u"Información solicitud anticipos fondos"

    # TODO: M SPRING 14 GAP 29_31
    solicitud_id = fields.Many2one('grp.solicitud.anticipos.fondos', u'Solicitud de anticipos fondos',
                                   ondelete='cascade', required=True)
    concept_id = fields.Many2one('grp_concepto_gasto_cc_viaticos', u'Concepto', domain="[('viaticos','=', True)]", required=True)
    account_id = fields.Many2one('account.account', 'Cuenta', compute='_compute_account_id', store=True, required=False)
    amount = fields.Float(string=u'Importe')

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    @api.depends('concept_id')
    def _compute_account_id(self):
        for rec in self:
            rec.account_id = rec.concept_id.cuenta_id.id


