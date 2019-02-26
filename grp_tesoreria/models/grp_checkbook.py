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
from openerp.exceptions import ValidationError


class GrpCheckbook(models.Model):
    _name = 'grp.checkbook'
    _description = 'Gestión de chequeras'

    invoice_id = fields.Many2one('account.journal', string=u'Cuenta bancaria',
                                 domain="[('type', 'in', ['bank'])]", required=True)
    name = fields.Char(string=u'Nombre de chequera', size=15, required=True)
    number_from = fields.Integer(string=u'Número desde', required=True)
    number_to = fields.Integer(string=u'Número hasta', required=True)
    serial = fields.Char(string=u'Serie')
    active = fields.Boolean(string=u'Activo', default=True)
    state = fields.Selection([('draft', 'Borrador'), ('available', 'Disponible'), ('not_available', 'No Disponible'),('cancel', 'Cancelado')],
                             'Estado', readonly=True, default='draft', compute='_compute_state', store=True)
    check_ids = fields.One2many('grp.checkbook.line', 'checkbook_id', u'Cheques')

    @api.one
    @api.constrains('number_from', 'number_to')
    def _check_numbers(self):
        if self.number_from >= self.number_to:
            raise ValidationError(
                _(u'El Número desde debe ser menor que Número hasta!'))

    @api.multi
    @api.depends('check_ids','check_ids.state')
    def _compute_state(self):
        for rec in self:
            if not rec.check_ids:
                rec.state = 'draft'
            else:
                if self.state != 'cancel':
                    na_sum = self.env['grp.checkbook.line'].search_count(
                        [('checkbook_id', '=', rec.id), '|', ('state', 'not in', ['available']), ('cancel_use', '=', True)])
                    rec.state = 'not_available' if (len(self.check_ids) == na_sum) else 'available'

    @api.multi
    def button_available(self):
        tuples = []
        for i in range(self.number_from, self.number_to + 1):
            tuples.append(
                (0, 0, {'check_number': i}))
        self.check_ids = tuples
        self.state = 'available'

    @api.multi
    def button_cancel(self):
        if not all(ch.state == 'available' for ch in self.check_ids):
            raise ValidationError(u'La chequera no puede cancelarse pues no todos los cheques están en estado Disponible.')
        else:
            self.state = 'cancel'



# TODO: SPRING 10 GAP 283 L
class GrpCheckbookLine(models.Model):
    _name = 'grp.checkbook.line'
    _rec_name = 'check_number'

    checkbook_id = fields.Many2one('grp.checkbook', string=u'Chequera', required=True)
    # check_number = fields.Integer(string=u'Número cheque', readonly=True)
    check_number = fields.Char(string=u'Número cheque', readonly=True)
    partner_id = fields.Many2one('res.partner', string=u'Proveedor', readonly=True)
    amount = fields.Float(string=u'Monto', readonly=True)
    check_date = fields.Date(string=u'Fecha cheque', readonly=True)
    paid_date = fields.Date(string=u'Fecha pago', readonly=True)
    in_cashbox = fields.Boolean(string=u'En caja', readonly=True)
    cancel_use = fields.Boolean(string=u'Anulado sin uso')
    state = fields.Selection(
        [('available', 'Disponible'), ('assign', 'Asignado'), ('issue', 'Emitido'), ('paid', 'Pago'),
         ('cancel', 'Anulado')], 'Estado', readonly=True, default='available')

    # RAGU: controlando estado en caso de cancelacion de cheque
    @api.multi
    def _check_state_incancel_use(self):
        for rec in self:
            if rec.cancel_use:
                rec.write({'state':'cancel'})

    @api.model
    def create(self, vals):
        if vals.get('cancel_use') and vals['cancel_use']:
            vals.update({'state':'cancel'})
        return super(GrpCheckbookLine, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('cancel_use'):
            if not vals['cancel_use']:
                raise ValidationError(_(u'No puede volver a cambiar el valor Anulado sin uso!'))
            vals.update({'state': 'cancel'})
        super_value = super(GrpCheckbookLine, self).write(vals)
        return super_value
