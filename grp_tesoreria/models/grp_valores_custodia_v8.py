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

from openerp import models, fields, api, exceptions
from openerp.tools.translate import _
from datetime import *


class GrpValoresCustodia(models.Model):
    _inherit = 'grp.valores_custodia'

    @api.one
    @api.constrains('cedula')
    def _compute_control_cedula(self):
        if self.cedula:
            ci = self.clean_ci(self.cedula)

            # dig = int(str(self.cedula)[int(len(str(self.cedula))) - 1])
            # if dig != self.get_validation_digit(ci):
            dig = int(self.cedula[-1:])
            if dig != self.get_validation_digit(int(str(ci)[:-1])):
                raise exceptions.ValidationError(u'Número de cédula incorrecto')

    def clean_ci(self, ci):
        return int(str(ci).replace("-", "").replace('.', ''))

    def get_validation_digit(self, ci):
        a = 0
        i = 0
        if len(str(ci)) <= 6:
            for i in xrange(len(ci), 7):
                ci = '0' + ci
                i = i + 1

        for i in xrange(0, 7):
            a += (int("2987634"[i]) * int(str(ci)[i])) % 10
            i = i + 1

        if a % 10 == 0:
            return 0
        else:
            return 10 - a % 10

    @api.one
    @api.constrains('cedula')
    def _check_cedula(self):

        if self.cedula and not self.cedula.isdigit():
            raise exceptions.ValidationError(u'La cédula debe contener solo números')

    @api.one
    @api.constrains('tipo_procedimiento', 'fecha_vencimiento', 'fecha_fin_contrato')
    def _check_tipo_proc(self):
        if self.tipo_procedimiento == 'cumplimiento' and self.fecha_vencimiento < self.fecha_fin_contrato:
            raise exceptions.ValidationError('La fecha fin de contrato no puede ser mayor a la Fecha vencimiento')

    @api.one
    @api.depends('tipo_id.efectivo')
    def _compute_btn_entregar_inv(self):
        # compute visibility of button "Entregar" without security and states
        if self.tipo_id and self.tipo_id.efectivo and self._context.get('from_menu_valores_custodia', False):
            self.btn_entregar_inv = True
        else:
            self.btn_entregar_inv = False

    tipo_id = fields.Many2one('grp.tipo_valores_custodias', 'Tipo', required=True)
    tipo_procedimiento = fields.Selection(
        [('mantenimiento', 'Mantenimiento de oferta'), ('cumplimiento', 'Cumplimiento Oferta')],
        string='Tipo de procedimiento')
    fecha_fin_contrato = fields.Date('Fecha fin de contrato')
    representante = fields.Char('Representante', size=40)
    cedula = fields.Char('C.I:', store=True, size=8, help=u"El número de cédula no debe contener ni puntos ni guiones")
    # Asiento de Alta
    fecha_alta = fields.Date('Fecha')
    diario_alta = fields.Many2one('account.journal', 'Diario')
    asiento_alta = fields.Many2one('account.move', 'Asiento de Alta')

    # Asiento de Baja
    fecha_baja = fields.Date('Fecha')
    diario_baja = fields.Many2one('account.journal', 'Diario')
    asiento_baja = fields.Many2one('account.move', 'Asiento de Baja')

    # TODO: M SPRING 11 GAP 292
    caja_recaudadora_id = fields.Many2one('grp.caja.recaudadora.tesoreria', 'Caja recaudadora')
    boleto_siif = fields.Boolean(u'Boleto SIIF')
    efectivo = fields.Boolean(related='tipo_id.efectivo', string=u'Efectivo', readonly=True)

    # RAGU alterando funcionamiento del name
    sequence = fields.Char('Secuencua', copy=False)
    name = fields.Char('Nombre', compute='_compute_name', store=True)

    tipo_transferencia = fields.Boolean(string='Transferencia', related='tipo_id.transferencia', readonly=True)
    tipo_efectivo = fields.Boolean(string='Transferencia', related='tipo_id.efectivo', readonly=True)

    # RAGU campos para cheques caja recaudadora
    payment_method = fields.Selection([('check', 'Cheque'),
                                       ('cash', 'Efectivo')], string='Medio de pago')
    bank_id = fields.Many2one('res.bank', string=u'Banco')
    serie = fields.Char(u'Serie')
    # check_number = fields.Integer(string=u'Nº cheque')
    check_number = fields.Char(string=u'Nº cheque', size=20)
    check_date = fields.Date(u'Fecha cheque')
    # number_bank_account = fields.Integer(string=u'Nº cuenta bancaria')
    number_bank_account = fields.Char(string=u'Nº cuenta bancaria', size=20)
    readonly = fields.Boolean(u'En gestión de pagos')
    btn_entregar_inv = fields.Boolean(compute="_compute_btn_entregar_inv")
    # Operating unit
    operating_unit_id = fields.Many2one('operating.unit', 'Unidad ejecutora', required=True,
                                        default=lambda self: self.env.user.default_operating_unit_id )

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        self.serie = False
        self.check_number = False
        self.check_date = False
        self.number_bank_account = False

    @api.onchange('tipo_id')
    def _onchange_tipo_id(self):
        self.boleto_siif = False
        if self._context.get('from_menu_valores_custodia', False) and self.tipo_id and self.tipo_id.efectivo:
            return { 'warning': { 'title': "Error",
                                  'message': u"No puede crear valores en custodia en efectivo desde este menú."
                                }
                }
        if self._context.get('default_caja_recaudadora_id', False) and self.tipo_id and not self.tipo_id.efectivo:
            return { 'warning': { 'title': "Error",
                                  'message': u"Solo puede crear valores en custodia de tipo efectivo."
                                }
                }
    @api.one
    @api.constrains('tipo_id')
    def _check_tipo(self):
        if self._context.get('from_menu_valores_custodia', False) and self.tipo_id.efectivo:
            raise exceptions.ValidationError(u'No puede crear valores en custodia en efectivo desde este menú, solo desde la caja recaudadora.')

    # TODO: M SPRING 11 GAP 292
    @api.model
    def create(self, vals):
        if 'number_bank_account' in vals and vals.get('number_bank_account', False):
            if not vals['number_bank_account'].isdigit():
                raise exceptions.ValidationError(u'El nro. de Cuenta Bancaria solo admite dígitos numéricos.')
        if 'tipo_id' in vals and 'default_caja_recaudadora_id' in self._context:
            tipo = self.env['grp.tipo_valores_custodias']
            if not tipo.browse(vals['tipo_id']).efectivo:
                raise exceptions.ValidationError(u'Solo puede recibir valores que sean de tipo efectivo.')
        vals['sequence'] = self.env['ir.sequence'].next_by_code('sec.valores.custodia')
        return super(GrpValoresCustodia, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'number_bank_account' in vals and vals.get('number_bank_account', False):
            if not vals['number_bank_account'].isdigit():
                raise exceptions.ValidationError(u'El nro. de Cuenta Bancaria solo admite dígitos numéricos.')
        return super(GrpValoresCustodia, self).write(vals)

    @api.multi
    @api.depends('sequence','tipo_id')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s' % (rec.tipo_id.name, rec.sequence)

    # TODO: M SPRING 11 GAP 292
    @api.multi
    def action_recibido(self):
        valor_custodia_obj = self.env['grp.caja.recaudadora.tesoreria.line.valor.custodia']
        check_obj = self.env['grp.caja.recaudadora.tesoreria.line']

        for rec in self:
            if rec.caja_recaudadora_id:
                valor_custodia_obj.create({
                    'valor_custodia_id':rec.id,
                    'caja_recaudadora_id':rec.caja_recaudadora_id.id,
                    'product_id':rec.tipo_id.product_id.id
                })
                if rec.tipo_id.efectivo and rec.payment_method == 'check':
                    check_obj.create({
                        'type':'check',
                        'valor_custodia_id':rec.id,
                        'caja_recaudadora_id': rec.caja_recaudadora_id.id
                    })
            model, group_id = self.env['ir.model.data'].get_object_reference('grp_seguridad',
                                                                             'grp_compras_pc_Comprador')
            users = self.env['res.users'].search([('groups_id', 'in', group_id),('operating_unit_ids','in',rec.operating_unit_id.id)])
            partner_ids = []

            if users:
                partner_ids = [user.partner_id.id for user in users]


            context = dict(self._context)
            context.update({'mail_notify_noemail': True})
            # context = self._context
            # self._context.update({'mail_notify_noemail': True})
            msg = _(
                """Se confirmó la recepción del valor en custodia <a href="#action=mail.action_mail_redirect&amp;model=grp.valores_custodia&amp;res_id=%s">%s<a/>.
                 del proveedor <a href="#action=mail.action_mail_redirect&amp;model=res.partner&amp;res_id=%s">%s<a/>
                  para el pedido de compras <a href="#action=mail.action_mail_redirect&amp;model=grp.pedido.compra&amp;res_id=%s">%s<a/>.""") % (
                      rec.id,rec.name,rec.partner_id.id,rec.partner_id.name,rec.nro_licitacion.id,rec.nro_licitacion.name)

            self.pool.get('mail.thread').message_post(self._cr, self._uid, self.id, type="notification",
                                                      subject=u'Recepción de valor en custodia',

                                                      subtype='mt_comment', body=msg,
                                                      partner_ids=partner_ids, context=context)


        return super(GrpValoresCustodia, self).action_recibido()

    # TODO: M SPRING 11 GAP 292
    @api.multi
    def action_caja(self):
        return {
            'name': _('Caja recaudadora de tesoreria'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.caja_recaudadora_id.id,
            'res_model': 'grp.caja.recaudadora.tesoreria',
            # 'context': ctx,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.model
    def alert_vencimiento(self):
        valores_custodias = self.search([('fecha_vencimiento', '=', date.today())])
        if len(valores_custodias):
            self.send_vencimiento(valores_custodias)
        return True

    def send_vencimiento(self, cr, uid, valores_custodias, context=None):
        body = u"Se informa del vencimiento del siguiente valor: " \
               u" %s. " \
               u" %s. " \
               u" %s. "
        local_context = context.copy()
        ir_model_data = self.pool.get('ir.model.data')
        _model, group_id = ir_model_data.get_object_reference(cr, uid, 'grp_tesoreria', 'group_grp_tesoreria')
        res_users_obj = self.pool.get('res.users')
        for valor in valores_custodias:
            user_ids = res_users_obj.search(cr, uid, [('groups_id', 'in', group_id),
                                                      ('operating_unit_ids', 'in', valor.operating_unit_id.id)])
            partner_ids = []
            if user_ids:
                partner_ids = [user.partner_id.id for user in res_users_obj.browse(cr, uid, user_ids)]
            partner = valor.partner_id.name or ''
            msg = _(body) % \
                  (valor.name, valor.fecha_vencimiento, partner)

            self.message_post(cr, uid, [valor.id], body=msg, partner_ids=partner_ids, context=context)

        return True

    @api.multi
    def action_baja_oficio(self):
        if not self.tipo_id.efectivo:
            return {
                'name': _("Fecha de Baja"),
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'grp.fecha_entrega_garantia',
                'type': 'ir.actions.act_window',
                # 'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                'context': {
                    'form_view_ref': 'grp_tesoreria.view_grp_baja_oficio_form',
                    'default_garantia_id': self.id,
                }
            }
        else:
            return self.write({'state': 'baja'})


class GrpFechaEntregaGarantia(models.Model):
    _inherit = 'grp.fecha_entrega_garantia'

    @api.one
    @api.depends('garantia_id')
    def _get_tipo_custodia_efectivo(self):
        context = dict(self._context)
        ctx = context.copy()
        garantia_obj = self.env['grp.valores_custodia'].with_context(ctx).browse(self.garantia_id.id)
        self.tipo_custodia_efectivo = garantia_obj.tipo_id.efectivo or False

    @api.one
    @api.depends('garantia_id')
    def _get_estado_valor(self):
        context = dict(self._context)
        ctx = context.copy()
        garantia_obj = self.env['grp.valores_custodia'].with_context(ctx).browse(self.garantia_id.id)
        self.estado = garantia_obj.state

    @api.model
    def _default_account(self):
        if self._context.get('default_garantia_id', False):
            garantia = self.env['grp.valores_custodia'].browse(self._context['default_garantia_id'])
            if garantia.currency_id.name and garantia.currency_id.name != 'UYU':
                return self.env['account.journal'].search([('type', 'in', ['valores_custodia']),
                                                       ('currency', '=', garantia.currency_id.id)], limit=1)
        return self.env['account.journal'].search([('type', 'in', ['valores_custodia'])], limit=1)

    fecha_asiento = fields.Date('Fecha Asiento',required=True)
    diario_id = fields.Many2one('account.journal', 'Diario',
                                domain="[('type', 'in', ['valores_custodia'])]", default=_default_account,required=True)
    estado = fields.Char(compute='_get_estado_valor', string='Estado', store=False)
    tipo_custodia_efectivo = fields.Boolean('Efectivo', compute='_get_tipo_custodia_efectivo', store=False)

    @api.onchange('name')
    def _onchange_fecha_entrega(self):
        if self.name:
            self.fecha_asiento = self.name

    @api.multi
    def button_entregado(self):

        context = dict(self._context)
        ctx = context.copy()
        garantia_obj = self.env['grp.valores_custodia'].with_context(ctx).browse(self.garantia_id.id)

        if not garantia_obj.tipo_id.efectivo:
            period_pool = self.env['account.period']
            period_obj = period_pool.search([('date_start', '<=', self.fecha_asiento),
                                             ('date_stop', '>=', self.fecha_asiento)])

            if not period_obj:
                raise Warning(_('Not period found for current date'))

            company_currency = self.diario_id.company_id.currency_id.id
            current_currency = garantia_obj.currency_id.id

            diff_currency = current_currency != company_currency and current_currency
            if self.estado == 'borrador':

                move_vals = {
                    'name': self.diario_id.sequence_id.id,
                    'journal_id': self.diario_id.id,
                    'date': self.fecha_asiento,
                    'ref': garantia_obj.name,
                    'period_id': period_obj.id,
                    'operating_unit_id': garantia_obj.operating_unit_id.id,
                }

                move_id = self.env['account.move'].create(move_vals)

                # debit
                move_line_vals_debit = {
                    'name': garantia_obj.name,
                    'move_id': move_id.id,
                    'account_id': self.diario_id.default_debit_account_id.id,
                    'debit': diff_currency and garantia_obj.currency_id.rate * garantia_obj.monto or garantia_obj.monto,
                    'credit': 0.0,
                    'currency_id': diff_currency and current_currency or False,
                    'amount_currency': diff_currency and garantia_obj.monto or 0.0,
                }

                self.env['account.move.line'].create(move_line_vals_debit)

                # credit
                move_line_vals_credit = {
                    'name': garantia_obj.name,
                    'move_id': move_id.id,
                    'account_id': garantia_obj.tipo_id.account_id.id,
                    'debit': 0.0,
                    'credit': diff_currency and garantia_obj.currency_id.rate * garantia_obj.monto or garantia_obj.monto,
                    'currency_id': diff_currency and current_currency or False,
                    'amount_currency': diff_currency and - garantia_obj.monto or 0.0,
                }

                self.env['account.move.line'].create(move_line_vals_credit)
                garantia_obj.write(
                    {'fecha_alta': self.fecha_asiento, 'diario_alta': self.diario_id.id, 'asiento_alta': move_id.id,
                     'state': 'entregado'})

            elif self.estado == 'entrega_autorizada':
                move_vals = {
                    'name': self.diario_id.sequence_id.id,
                    'journal_id': self.diario_id.id,
                    'date': self.fecha_asiento,
                    'ref': garantia_obj.name,
                    'period_id': period_obj.id,
                    'operating_unit_id': garantia_obj.operating_unit_id.id,
                }

                move_id = self.env['account.move'].create(move_vals)

                # debit
                move_line_vals_debit = {
                    'name': garantia_obj.name,
                    'move_id': move_id.id,
                    'account_id': garantia_obj.tipo_id.account_id.id,
                    'debit': diff_currency and garantia_obj.currency_id.rate * garantia_obj.monto or garantia_obj.monto,
                    'credit': 0.0,
                    'currency_id': diff_currency and current_currency or False,
                    'amount_currency': diff_currency and garantia_obj.monto or 0.0,
                }

                self.env['account.move.line'].create(move_line_vals_debit)

                # credit
                move_line_vals_credit = {
                    'name': garantia_obj.name,
                    'move_id': move_id.id,
                    'account_id': self.diario_id.default_debit_account_id.id,
                    'debit': 0.0,
                    'credit': diff_currency and garantia_obj.currency_id.rate * garantia_obj.monto or garantia_obj.monto,
                    'currency_id': diff_currency and current_currency or False,
                    'amount_currency': diff_currency and - garantia_obj.monto or 0.0,
                }

                self.env['account.move.line'].create(move_line_vals_credit)
                garantia_obj.write(
                    {'fecha_baja': self.fecha_asiento, 'diario_baja': self.diario_id.id, 'asiento_baja': move_id.id,
                     'state': 'entrega_tesoreria'})
        else:
            if self.estado == 'borrador':
                garantia_obj.write({'state': 'entregado'})
            elif self.estado == 'entrega_autorizada':
                garantia_obj.write({'state': 'entrega_tesoreria'})

    @api.multi
    def button_baja(self):

        context = dict(self._context)
        ctx = context.copy()
        garantia_obj = self.env['grp.valores_custodia'].with_context(ctx).browse(self.garantia_id.id)

        if not garantia_obj.tipo_id.efectivo:
            period_pool = self.env['account.period']
            period_obj = period_pool.search([('date_start', '<=', self.fecha_asiento),
                                             ('date_stop', '>=', self.fecha_asiento)])

            if not period_obj:
                raise Warning(_('Not period found for current date'))

            company_currency = self.diario_id.company_id.currency_id.id
            current_currency = garantia_obj.currency_id.id
            diff_currency = current_currency != company_currency and current_currency

            move_vals = {
                'name': self.diario_id.sequence_id.id,
                'journal_id': self.diario_id.id,
                'date': self.fecha_asiento,
                'ref': garantia_obj.name,
                'period_id': period_obj.id,
                'operating_unit_id': garantia_obj.operating_unit_id.id,
            }

            move_id = self.env['account.move'].create(move_vals)

            # debit
            move_line_vals_debit = {
                'name': garantia_obj.name,
                'move_id': move_id.id,
                'account_id': self.diario_id.default_debit_account_id.id,
                'debit': diff_currency and garantia_obj.currency_id.rate * garantia_obj.monto or garantia_obj.monto ,
                'credit': 0.0,
                'currency_id': diff_currency and current_currency or False,
                'amount_currency': diff_currency and garantia_obj.monto or 0.0,
            }

            self.env['account.move.line'].create(move_line_vals_debit)

            # credit
            move_line_vals_credit = {
                'name': garantia_obj.id,
                'move_id': move_id.id,
                'account_id': garantia_obj.tipo_id.account_id.id,
                'debit': 0.0,
                'credit': diff_currency and garantia_obj.currency_id.rate * garantia_obj.monto or garantia_obj.monto,
                'currency_id': diff_currency and current_currency or False,
                'amount_currency': diff_currency and - garantia_obj.monto or 0.0,
            }

            self.env['account.move.line'].create(move_line_vals_credit)
            garantia_obj.write(
                {'fecha_baja': self.fecha_asiento, 'diario_baja': self.diario_id.id, 'asiento_baja': move_id.id,
                 'state': 'baja'})
        else:
            garantia_obj.write({'state': 'baja'})
