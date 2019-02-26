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
import openerp.addons.decimal_precision as dp
import time
from openerp.exceptions import Warning
from openerp.exceptions import ValidationError

# TODO: SPRING 8 GAP 111.228.339 K
class account_invoice_fr(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    importe_pago = fields.Float(compute='_compute_importe_pago', digits_compute=dp.get_precision('Account'),
                                  string='Importe pago', store=True)
    fondo_rotarios = fields.Boolean(string='En 3 en 1-Fondo rotatorio', default=False)

    fondo_rotatorio_id = fields.Many2one('grp.fondo.rotatorio', string='Fondo rotatorio',
                                              compute='_compute_fondo_rotatorio_id')

    @api.multi
    def _compute_fondo_rotatorio_id(self):
        FR_Line = self.env['grp.fondo.rotatorio.line'].suspend_security()
        for rec in self:
            rec.fondo_rotatorio_id = FR_Line.search([('supplier_invoice_id', '=', rec.id)],
                                                         limit=1).fondo_rotatorios_id.id

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.multi
    @api.depends('payment_ids')
    def _compute_importe_pago(self):
        for rec in self.filtered(lambda inv: inv.type in ['in_invoice','in_refund']):
            rec.importe_pago = 0.0
            if rec.payment_ids:
                rec.importe_pago = sum(
                    map(lambda x: x.credit if x.credit > 0 else x.debit, rec.payment_ids))
            if rec.type == 'in_refund':
                rec.importe_pago *= -1

    def action_cancel(self, cr, uid, ids, context):
        invoices = self.read(cr, uid, ids, ['fondo_rotarios'])
        for invoice in invoices:
            if invoice['fondo_rotarios'] == True:
                raise exceptions.ValidationError(_(u'Este documento está en un documento 3-en1-Fondo rotatorio. No es posible cancelarlo.'))
        return super(account_invoice_fr, self).action_cancel(cr, uid, ids, context)

    def button_cancelar_pago(self, cr, uid, ids, context=None):
        invoices = self.read(cr, uid, ids, ['fondo_rotarios'])
        for invoice in invoices:
            if invoice['fondo_rotarios'] == True:
                raise exceptions.ValidationError(_(u'Este documento está en un documento 3-en1-Fondo rotatorio. No es posible cancelarlo.'))
        return super(account_invoice_fr, self).button_cancelar_pago(cr, uid, ids, context)


