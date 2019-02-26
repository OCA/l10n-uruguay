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

from openerp import models, fields, api,exceptions
from openerp.tools.translate import _


class aprobar_pago(models.TransientModel):
    _name = "aprobar.pago.guardar"
    _description = "Aprobar Pagos Guardar"

    fecha_aprobacion = fields.Date(string='Fecha de Aprobacion', required=True, default=lambda *a: fields.Date.today())
    cuenta_bancaria_id = fields.Many2one('account.journal', 'Cuenta Bancaria', required=True)

    @api.multi
    def pago_guardar(self, vals):
        voucher_obj = self.env['account.voucher']
        for invoice in self.env['account.invoice'].browse(vals['active_ids']):
            if not invoice.pago_aprobado:
                invoice.write({'pago_aprobado': True, 'cuenta_bancaria_id': self.cuenta_bancaria_id.id,
                           'fecha_aprobacion': self.fecha_aprobacion})
                voucher_id = voucher_obj.search([('invoice_id', '=', invoice.id)])
                voucher_id.proforma_voucher_auxiliary()
                voucher_id.write({'fecha_aprobacion_pago': self.fecha_aprobacion})
                voucher_id.move_ids.write({'operating_unit_id':voucher_id.operating_unit_id.id})
            elif invoice.pago_aprobado:
                raise exceptions.ValidationError(_('Ya existen línea/s con aprobación de pago.'))
        return {'type': 'ir.actions.act_window_close'}


class cancelar_pago(models.TransientModel):
    _name = "aprobar.pago.cancel"
    _description = "Cancelar aprobar pago"

    @api.multi
    def pagos_cancel(self, vals):
        voucher_obj = self.env['account.voucher']
        for invoice in self.env['account.invoice'].browse(vals['active_ids']):
            if invoice.fecha_inicio_pago:
                raise exceptions.ValidationError(
                    _('No se pueden cancelar la/s aprobaciones, ya existe una fecha de inicio de pago.'))
            if self.env['account.voucher.line'].search_count([('move_line_id.move_id', '=', invoice.move_id.id),
                                                              '|',
                                                              ('voucher_id.state', 'in', ['draft', 'confirm']),
                                                              '&', ('voucher_id.state', 'in', ['issue', 'posted']),
                                                              ('amount', '!=', 0)]):
                raise exceptions.ValidationError(
                    _('No se pueden cancelar la/s aprobaciones, el documento %s ya está incluido en un Pago!') % (invoice.name_get()[0][1]))
            if invoice.fecha_aprobacion:
                invoice.write({'pago_aprobado': False, 'cuenta_bancaria_id': False, 'fecha_aprobacion': False})
                voucher_ids = voucher_obj.search([('invoice_id', '=', invoice.id)])
                voucher_ids.cancel_voucher()
                voucher_ids.change_voucher()
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: