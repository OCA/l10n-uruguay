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
import time
from openerp.exceptions import ValidationError

# TODO: SPRING 10 GAP 474 M
# TODO: M INCIDENCIA
class GrpCajaPagadoraTesoreria(models.Model):
    _name = 'grp.caja.pagadora.tesoreria'
    _inherit = ['mail.thread']
    _description = "Caja cheques"
    _order = 'closing_date desc'

    name = fields.Char(u'Nombre', default='/')
    box_id = fields.Many2one('grp.caja', string='Caja', domain="[('caja_pagadora','=', True),('type','=', 'bank'),('users','=',uid)]", readonly=True,
                             states={'draft': [('readonly', False)]})# TODO: M INCIDENCIA
    operating_unit_id = fields.Many2one('operating.unit', string='Unidad ejecutora')
    journal_id = fields.Many2one('account.journal', string=u'Diario', related='box_id.journal_id', store=True, readonly=True)
    user_uid = fields.Many2one('res.users', 'Responsable', readonly=True)
    open_date = fields.Datetime(u'Fecha de apertura', readonly=True,default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    closing_date = fields.Datetime(u'Cerrado en', readonly=True)
    state = fields.Selection(
                    [('draft', u'Borrador'),
                     ('open', u'Abierto'),
                     ('confirm', u'Confirmado'),
                     ('close', u'Cerrado'),
                     ('checked', u'Revisado')], u'Estado',
                    default='draft')
    opening_line_ids = fields.One2many('grp.caja.pagadora.tesoreria.line', 'payment_box_id',
                                       string=u'Apertura de cheques', domain=[('type', '=', 'opening_check')])

    check_line_ids = fields.One2many('grp.caja.pagadora.tesoreria.line', 'payment_box_id', string=u'Cheques',
                                     domain=[('type', '=', 'check')])
    closing_line_ids = fields.One2many('grp.caja.pagadora.tesoreria.line', 'payment_box_id',
                                       string=u'Cierre de Cheques', domain=[('type', '=', 'check'),('state', '=', 'issue')])

    move_line_ids = fields.One2many('account.move.line', 'payment_box_id', u'Asientos contables')
    opening_quantity_check = fields.Integer(compute='_compute_opening_line', string=u'Cantidad de cheques',multi='opening')
    total_amount = fields.Float(compute='_compute_opening_line', string=u'Total Importe', multi='opening')
    closing_quantity_check = fields.Integer(compute='_compute_closing_line',
                                            string=u'Cantidad de cheques de cierre',
                                            multi='closing')
    closing_total_amount = fields.Float(compute='_compute_closing_line', string=u'Total Importe de Cierre',
                                        multi='closing')

    initial_balance = fields.Float(string=u'Saldo inicial')
    total_entry_encoding = fields.Float(compute='_compute_total_entry_encoding',multi='transactions', string=u'Transacciones', store=True)
    close_balance = fields.Float(compute='_compute_total_entry_encoding',multi='transactions', string=u'Saldo teórico de cierre', store=True)
    in_amount = fields.Float(string="Total de ingresos", compute='_compute_total_entry_encoding', multi='transactions', store=True)
    out_amount = fields.Float(string="Total de egresos", compute='_compute_total_entry_encoding', multi='transactions', store=True)

    real_end_balance = fields.Float(compute='_compute_real_end_balance', string=u'Saldo de cierre real')
    difference = fields.Float(compute='_compute_difference', string=u'Diferencia')
    posted = fields.Boolean('Asiento creado', default=False)
    currency_id = fields.Many2one('res.currency', 'Divisa', compute='_compute_currency_id')

    @api.onchange('box_id')
    def _onchange_box_id(self):
        if self.box_id:
            opening_lines = []
            previous_box_id = self._get_previous_box(self.box_id.id, self.open_date)
            if previous_box_id and previous_box_id.closing_line_ids:
                for line in previous_box_id.closing_line_ids:
                    opening_lines.append([0, 0, {'voucher_id': line.voucher_id.id,
                                                 'type': 'opening_check', 'state': line.voucher_id.state}])
                self.opening_line_ids = opening_lines
            else:
                self.opening_line_ids = False

            domain = {
                'operating_unit_id': [('id', 'in', self.box_id.operating_unit_ids.ids)]
            }
            return {'domain': domain}

    @api.onchange('opening_line_ids')
    def _onchange_opening_line_ids(self):
        self.initial_balance = self._get_initial_balance()

    @api.multi
    @api.depends('box_id')
    def _compute_currency_id(self):
        for rec in self:
            if rec.box_id:
                rec.currency_id = rec.box_id.currency_id

    # TODO: M INCIDENCIA
    @api.multi
    @api.depends('opening_line_ids.state', 'closing_line_ids.state', 'check_line_ids.state')
    def _compute_opening_line(self):
        for rec in self:
            rec.opening_quantity_check = 0
            rec.total_amount = 0.0
            if rec.opening_line_ids:
                rec.opening_quantity_check = len(rec.opening_line_ids.ids)
                rec.total_amount = sum(map(lambda x: x.amount, rec.opening_line_ids))

    @api.multi
    @api.depends('closing_line_ids.state')
    def _compute_closing_line(self):
        for rec in self:
            rec.closing_quantity_check = 0
            rec.closing_total_amount = 0.0
            if rec.closing_line_ids:
                rec.closing_quantity_check = len(rec.closing_line_ids.ids)
                rec.closing_total_amount = sum(map(lambda x: x.amount, rec.closing_line_ids))

    def _get_initial_balance(self):
        self.ensure_one()
        caja_pagadora_id = self._get_previous_box(self.box_id.id, self.open_date)
        return caja_pagadora_id.close_balance if caja_pagadora_id else 0


    @api.multi
    @api.depends('state','initial_balance', 'check_line_ids.state','check_line_ids.apertura_recibo')
    def _compute_total_entry_encoding(self):
        for rec in self:
            transacciones_amount = sum(map(lambda x: x.amount, rec.check_line_ids.filtered(lambda x: not x.apertura_recibo and x.state != 'cancel')),0.0)
            posted_line_amount = sum(map(lambda x: x.amount, rec.check_line_ids.filtered(lambda x: (x.state == 'posted' and x.state != 'cancel') or (x.apertura_recibo and x.state == 'cancel'))),0.0)
            total_entry_encoding = transacciones_amount - posted_line_amount

            rec.in_amount = transacciones_amount
            rec.out_amount = posted_line_amount
            rec.total_entry_encoding = total_entry_encoding
            rec.close_balance = rec.initial_balance + total_entry_encoding

    @api.multi
    @api.depends('closing_line_ids.state')
    def _compute_real_end_balance(self):
        for rec in self:
            rec.real_end_balance = sum(map(lambda x: x.amount, rec.closing_line_ids))

    @api.multi
    @api.depends('close_balance','real_end_balance')
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.real_end_balance - rec.close_balance

    @api.multi
    def btn_open(self):
        for rec in self:
            if rec.state == 'open':
                raise exceptions.ValidationError(_(u'Error al abrir la caja, ya se encuentra en estado Abierto.'))
            if rec.search([('state', '=', 'open'), ('box_id', '=', rec.box_id.id),('id', '!=', rec.id)]):
                raise exceptions.ValidationError(
                    _(u'Existe para esta caja, otra en estado Abierto. No es posible abrir una nueva caja'))
            initial_balance = rec._get_initial_balance()
            # if rec.close_balance <> rec.total_amount:
            if initial_balance <> rec.total_amount:
                raise exceptions.ValidationError(
                    _(u'El total de la composición de la caja debe ser igual al total del saldo inicial %s.')% (rec.total_amount,))
            vals = rec.update_fields()
            vals['initial_balance'] = initial_balance
            rec.write(vals)
            rec.message_post(body=u"Caja pajadora %s abierta." % (rec.name,))

    @api.multi
    def btn_close(self):
        for rec in self:
            if rec.difference != 0:
                raise exceptions.ValidationError(
                    _(u'Existen diferencias en el saldo de cheques. Revisar la caja.'))

            posted_lines = rec.check_line_ids.filtered(lambda x: x.state == 'posted')
            if posted_lines:
                vouchers = posted_lines.mapped('voucher_id')
                for voucher in vouchers:
                    voucher.move_id.line_id.write({'payment_box_id': rec.id})
            rec.write({'state': 'close', 'closing_date': time.strftime('%Y-%m-%d %H:%M:%S')})
            rec.message_post(body=u"Caja pagadora %s cerrada." % (rec.name,))

    @api.multi
    def btn_cancel(self):
        for rec in self:
            next_caja_pagadora_id = rec._get_next_box(rec.box_id.id, rec.open_date)
            if next_caja_pagadora_id:
                raise exceptions.ValidationError(
                    _(u'No es posible cancelar la caja; existe una caja posterior.'))
            move_lines = [line.move_id for line in rec.move_line_ids]
            if move_lines:
                self.crear_extorno(move_lines)
                rec.move_line_ids.write({'payment_box_id': False})

            rec.write({'state': 'open'})
            rec.message_post(body=u"Caja pagadora %s abierta." % (rec.name,))

    def crear_extorno(self,moves):
        for move in moves:
            period_id = self.env['account.period'].find(fields.Date.today()).id
            move.create_reversals(
                fields.Date.today(),
                reversal_period_id=period_id,
            )


    @api.multi
    def btn_check(self):
        for rec in self:
            rec.write({'state': 'checked'})
            rec.message_post(body=u"Caja pagadora %s revisada." % (rec.name,))
        return True

    def update_fields(self):
        check_lines = []
        vals = {
            'state': 'open',
            'open_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'user_uid': self.env.uid
        }
        if self.journal_id.sequence_id:
            fiscalyear_id = self._get_fiscalyear()
            if fiscalyear_id:
                name = self.env['ir.sequence'].with_context(fiscalyear_id=fiscalyear_id[0].id).next_by_id(
                    self.journal_id.sequence_id.id)
                vals['name'] = name

        if self.opening_line_ids:
            for line in self.opening_line_ids:
                check_lines.append([0, 0, {'voucher_id': line.voucher_id.id, 'type': 'check','apertura_recibo':True}])
            vals['check_line_ids'] = check_lines

        return vals

    @api.multi
    def unlink(self):
        if self.filtered(lambda x: x.state != 'draft'):
            raise exceptions.ValidationError(_(u"Solo puede eliminar Cajas en estado 'Nuevo'!"))
        return super(GrpCajaPagadoraTesoreria, self).unlink()

    def _get_next_box(self, box_id, open_date):
        return self.search([('state', '!=', 'draft'), ('box_id', '=', box_id),
                                ('open_date', '>', open_date)], order='open_date asc', limit=1)

    def _get_previous_box(self, box_id, open_date):
        previous_box = self.search([('state', 'in', ['checked','close']), ('box_id', '=', box_id),
                                    ('closing_date', '<=', open_date)], order='closing_date desc', limit=1)
        return previous_box

    def _get_fiscalyear(self):
        fecha_hoy = time.strftime('%Y-%m-%d')
        uid_company_id = self.env['res.users'].browse(self._uid).company_id.id
        fiscalyear_id = self.env['account.fiscalyear'].search(
            [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
             ('company_id', '=', uid_company_id)])
        return fiscalyear_id


class GrpCajaPagadoraTesoreriaLine(models.Model):
    _name = 'grp.caja.pagadora.tesoreria.line'

    payment_box_id = fields.Many2one('grp.caja.pagadora.tesoreria', 'Caja Pagadora')
    voucher_id = fields.Many2one('account.voucher', 'Pago a proveedor')
    origin_voucher_id = fields.Many2one('account.voucher', 'Pago a proveedor origen')
    name = fields.Char(string=u'Nombre', related='voucher_id.name', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string=u'Proveedor', related='voucher_id.partner_id', readonly=True)
    journal_id = fields.Many2one('account.journal', string=u'Diario', related='voucher_id.journal_id', readonly=True)
    check_id = fields.Many2one('grp.checkbook.line', u'Cheque', related='voucher_id.check_id', readonly=True)
    # advance_account_id = fields.Many2one('account.account', string=u'Cuenta Bancaria',
    #                                      related='voucher_id.advance_account_id')
    amount = fields.Float(string=u'Importe', related='voucher_id.amount', store=True, readonly=True)
    state = fields.Selection([('draft', 'Borrador'),
                              ('confirm', 'Confirmado'),
                              ('issue', 'Emitido'),
                              ('proforma', 'Pro-forma'),
                              ('posted', 'Contabilizado'),
                              ('cancel', 'Cancelado'),
                              ('pagado', 'Pagado')
                              ], string='Estado')
    date = fields.Date(string=u'Fecha de pago', related='voucher_id.date', readonly=True)
    entry_date = fields.Date(string=u'Fecha de asiento', related='voucher_id.date', readonly=True)
    serial = fields.Char(string=u'Serie', related='voucher_id.serial', readonly=True)
    type = fields.Selection([('opening_check', 'Cheque Inicial'),
                             ('check', 'Cheque'),
                             ('closing_check', 'Cheque Cierre')], string='Tipo', store=True)
    payment_box_state = fields.Selection([('draft', u'Nuevo'),
                                          ('open', u'Abierto'),
                                          ('confirm', u'Confirmado'),
                                          ('close', u'Cerrado'),
                                          ('checked', u'Revisado')], related='payment_box_id.state', string='Estado', readonly=True)
    apertura_recibo = fields.Boolean(u'Saldo apertura', default=False)

    @api.multi
    def action_link_voucher_document(self):
        self.ensure_one()
        voucher_id = self.voucher_id
        _related_info_dict = {'related_model': 'account.voucher', 'related_id': voucher_id.id,
                              'module_name': 'account_voucher', 'view_id': 'view_vendor_payment_form'}
        # if voucher_id:
        #     _related_info_dict = voucher_id._get_related_document()
        # else:
        #     _related_info_dict = {'related_model': self._name, 'related_id': self.id}

        dict_toreturn = {
            'type': 'ir.actions.act_window',
            'res_model': _related_info_dict['related_model'],
            'display_name': 'Pago relacionado',
            'view_type': 'form',
            'name': 'Pago relacionado',
            'target': 'current',
            'view_mode': 'form',
            'res_id': _related_info_dict['related_id']
        }

        if _related_info_dict.get('view_id') and _related_info_dict['view_id']:
            res = self.env['ir.model.data'].get_object_reference(_related_info_dict['module_name'],
                                                                 _related_info_dict['view_id'])
            res_id = res and res[1] or False
            dict_toreturn.update({
                'view_id': res_id
            })
        return dict_toreturn

    # RAGU cheque en caja desde que se incluye la linea en la misma
    @api.model
    def create(self, vals):
        if vals.get('voucher_id', False):
            voucher = self.env['account.voucher'].browse(vals.get('voucher_id'))
            vals.update({'state':voucher.state})
        else:
            vals.update({'state': 'draft'})
        new_id = super(GrpCajaPagadoraTesoreriaLine, self).create(vals)
        new_id.check_id.write({'in_cashbox':True})
        new_id.voucher_id.write({'in_cashbox':True})
        return new_id

    # RAGU: controlando no se pueda eliminar
    @api.multi
    def unlink(self):
        if self.filtered(lambda x: x.apertura_recibo or x.state == 'posted'):
            raise ValidationError(_("No se pueden eliminar Transacciones de cheque que sean de 'Saldo de apertura' o estén 'Contabilizadas'!"))
        for rec in self:
            rec.check_id.write({'in_cashbox':False})
            rec.voucher_id.write({'in_cashbox':False})
        return super(GrpCajaPagadoraTesoreriaLine, self).unlink()


    @api.multi
    def btn_cancel_payment(self):
        for rec in self.suspend_security():
            rec.voucher_id.cancel_voucher()
            rec.voucher_id.write({'state': 'issue','in_cashbox':True})
            for line in rec.voucher_id.line_dr_ids.filtered(lambda x: x.amount > 0):
                if line.origin_voucher_id:
                    line.origin_voucher_id.write({'state': 'posted', 'in_cashbox': False})
                    line.origin_voucher_id.solicitud_viatico_id.write({'adelanto_pagado':False})
            rec.voucher_id.check_id.write({'state': 'issue','in_cashbox':True})
        return True


class GrpAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    payment_box_id = fields.Many2one('grp.caja.pagadora.tesoreria', 'Caja Pagadora')
