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

# TODO: M SPRING 14 GAP 29_31


class GrpAnticiposFondos(models.Model):
    _inherit = 'account.voucher'

    solicitud_anticipos_id = fields.Many2one('grp.solicitud.anticipos.fondos', string=u'Solicitud de anticipos de fondos',
                                            ondelete='restrict', required=False, readonly=True, states={'draft': [('readonly', False)]})
    se_contabilizo = fields.Boolean(string=u"Se contabilizó", compute='_compute_se_contabilizo')
    account_voucher_anticipo_id = fields.Many2one('account.voucher', string='Formulario de pago', compute='_compute_voucher')
    cuenta_bancaria_anticipo_id = fields.Many2one('account.journal', 'Cuenta bancaria',
                                         related='account_voucher_anticipo_id.journal_id', readonly=True)
    payment_ids = fields.Many2many('account.move.line', string='Payments',
                                   compute='_compute_payments')

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def _compute_voucher(self):
        for rec in self:
            if isinstance(rec.id, (int, long)):
                account_voucher_line_id = self.env['account.voucher.line'].search(
                    [('move_line_id.id', 'in', rec.move_id.line_id.ids)],
                    limit=1)
                rec.account_voucher_anticipo_id = account_voucher_line_id.voucher_id.id if account_voucher_line_id else False

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def _compute_payments(self):
        partial_lines = lines = self.env['account.move.line']
        for rec in self:
            for line in rec.move_id.line_id:
                if line.account_id != rec.account_id:
                    continue
                if line.reconcile_id:
                    lines |= line.reconcile_id.line_id
                elif line.reconcile_partial_id:
                    lines |= line.reconcile_partial_id.line_partial_ids
                partial_lines += line
            rec.payment_ids = (lines - partial_lines).sorted()

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    # @api.depends('line_ids.amount')
    def _compute_se_contabilizo(self):
        for rec in self:
            rec.se_contabilizo = rec.state != 'draft' and True or False

    @api.multi
    def proforma_voucher_auxiliary(self):
        result = super(GrpAnticiposFondos, self).proforma_voucher_auxiliary()
        for record in self:
            if record.solicitud_anticipos_id:
                sequence = self.env['ir.sequence'].next_by_code('antic.fondos.number')
                record.write({'number': sequence})
        return result

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def proforma_voucher(self):
        hr_expense = self.env['hr.expense.expense']
        res = super(GrpAnticiposFondos, self).proforma_voucher()
        for rec in self:
            for line_id in rec.line_ids.filtered(lambda x: x.amount > 0 and x.move_line_id.id):
                if not line_id.move_line_id.invoice:
                    voucher_id = self.env['account.voucher'].search(
                        [('move_id', '=', line_id.move_line_id.move_id.id)])
                    invoice_id = voucher_id.invoice_id
                    if voucher_id.solicitud_anticipos_id and not voucher_id.rendicion_anticipos_id:
                        voucher_id.solicitud_anticipos_id.write({'adelanto_pagado': True})
                        rendicion_anticipos_id = hr_expense.search([('solicitud_anticipos_id', '=',
                                                                     voucher_id.solicitud_anticipos_id.id)], limit=1)
                        if rendicion_anticipos_id:
                            voucher_paid_id = self.search([('rendicion_anticipos_id', '=',rendicion_anticipos_id.id),
                                                           ('state', '=', 'pagado')], limit=1)
                            if voucher_paid_id:
                                rendicion_anticipos_id.suspend_security().write({'state': 'paid'})
                    if voucher_id.rendicion_anticipos_id and \
                                    voucher_id.rendicion_anticipos_id.solicitud_anticipos_id.adelanto_pagado == True:
                        voucher_id.rendicion_anticipos_id.sudo().write({'state': 'paid'})
                    if invoice_id.doc_type == 'vales_caja':
                        voucher_id.write({'state': 'pagado'})
                    elif voucher_id.type == 'sale' and voucher_id.solicitud_anticipos_id and \
                        voucher_id.rendicion_anticipos_id:
                        voucher_id.write({'state': 'pagado'})
        return res
