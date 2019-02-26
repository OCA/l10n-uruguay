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

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
import openerp.addons.decimal_precision as dp
from openerp.tools import float_round


class GrpCashboxRegisterExecution(models.Model):
    _name = 'grp.cashbox.register.execution'
    _description = _(u"Ejecución de Arqueo de caja")
    _inherit = ['mail.thread']
    _rec_name = 'date'

    date = fields.Date(u'Fecha', default=lambda *x: fields.Date.today(), required=True,
                       readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    cashbox_register_id = fields.Many2one('grp.cashbox.register', u'Arqueo', required=True, ondelete='cascade',
                                          domain=[('state', '=', 'confirm')],
                                          readonly=True, states={'draft': [('readonly', False)]})

    hour_start = fields.Float(u'Hora de inicio', required=True,
                              readonly=True, states={'draft': [('readonly', False)]})
    hour_end = fields.Float(u'Hora de fin',
                            readonly=True, states={'draft': [('readonly', False)],
                                                   'confirm': [('readonly', False), ('required', True)]})

    observations = fields.Char(u'Observaciones', size=100,
                               readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})

    caja_pagadora_ids = fields.Many2many('grp.caja', readonly=True, related='cashbox_register_id.caja_pagadora_ids',
                                         string=u'Cajas pagadoras')
    caja_recaudadora_ids = fields.Many2many('grp.caja', readonly=True,
                                            related='cashbox_register_id.caja_recaudadora_ids',
                                            string=u'Cajas recaudadoras')
    caja_cheque_ids = fields.Many2many('grp.caja', readonly=True, related='cashbox_register_id.caja_cheque_ids',
                                       string=u'Cajas de cheques')
    caja_fondo_terceros_ids = fields.Many2many('grp.caja', readonly=True,
                                               related='cashbox_register_id.caja_fondo_terceros_ids',
                                               string=u'Cajas fondos de terceros')
    caja_otras_ids = fields.Many2many('grp.caja', readonly=True, related='cashbox_register_id.caja_otras_ids',
                                      string=u'Otras cajas')

    title_ids = fields.One2many('grp.cashbox.register.executiontitle', 'execution_id',
                                readonly=True, states={'draft': [('readonly', False)]})
    composition_ids = fields.One2many('grp.cashbox.register.executioncomposition', 'execution_id',
                                      readonly=True, states={'draft': [('readonly', False)]})

    state = fields.Selection([('draft', 'Borrador'),
                              ('confirm', 'Confirmado'),
                              ('checked', 'Revisado sin observaciones'),
                              ('checked_wobs', 'Revisado con observaciones'),
                              ('cancel','Cancelado')], u'Estado',
                             default='draft', track_visibility='onchange')

    @api.onchange('date', 'cashbox_register_id')
    def _onchange_header(self):
        compositions = [(5,)]
        if self.date and self.cashbox_register_id:
            currency_ids = self.env['res.currency'].browse(self._get_currency_ids())
            for currency_id in currency_ids:
                last_composition = self.env['grp.cashbox.register.composition'].search(
                    [('currency_id', '=', currency_id.id),
                     ('state', '=', 'confirm'),
                     ('cashbox_register_id', '=', self.cashbox_register_id.id),
                     ('date', '<=', self.date)],
                    order='date DESC', limit=1)
                if last_composition:
                    compositions.append((0, 0, {'currency_id': currency_id, 'composition_id': last_composition.id}))
        self.composition_ids = compositions

    @api.multi
    def action_draft(self):
        self.write({'state': 'draft'})

    @api.multi
    def action_confirm(self):
        self.write({'state': 'confirm'})

    @api.multi
    def action_checked(self):
        if self.hour_end == 0:
            raise ValidationError(_('La hora de fin debe ser distinta de 0'))
        self.write({'state': 'checked'})

    @api.multi
    def action_checked_wobservation(self):
        if self.hour_end == 0:
            raise ValidationError(_('La hora de fin debe ser distinta de 0'))
        self._validate_checked_wobservation()
        self.write({'state': 'checked_wobs'})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def action_print_report_xls(self):
        report_name = 'grp_tesoreria.report_grp_cashbox_register_xls'
        data = {}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'report_type': 'xlsx',
            'datas': data}

    def _validate_checked_wobservation(self):
        for rec in self:
            if not rec.observations:
                raise ValidationError(_(u"Debe llenar las observaciones antes de pasar a este estado!"))

    def _get_currency_ids(self):
        currency_dict = {}
        for line in self.cashbox_register_id.caja_pagadora_ids:
            if not line.currency_id:
                currency_id = self.env.user.company_id.currency_id.id
            else:
                currency_id = line.currency_id.id
            currency_dict.setdefault(currency_id, currency_id)
            currency_dict[currency_id] = currency_id
        for line in self.cashbox_register_id.caja_cheque_ids:
            if not line.currency_id:
                currency_id = self.env.user.company_id.currency_id.id
            else:
                currency_id = line.currency_id.id
            currency_dict.setdefault(currency_id, currency_id)
            currency_dict[currency_id] = currency_id
        for line in self.cashbox_register_id.caja_recaudadora_ids:
            if not line.currency_id:
                currency_id = self.env.user.company_id.currency_id.id
            else:
                currency_id = line.currency_id.id
            currency_dict.setdefault(currency_id, currency_id)
            currency_dict[currency_id] = currency_id
        for line in self.cashbox_register_id.caja_fondo_terceros_ids:
            if not line.currency_id:
                currency_id = self.env.user.company_id.currency_id.id
            else:
                currency_id = line.currency_id.id
            currency_dict.setdefault(currency_id, currency_id)
            currency_dict[currency_id] = currency_id
        for line in self.cashbox_register_id.caja_otras_ids:
            if not line.currency_id:
                currency_id = self.env.user.company_id.currency_id.id
            else:
                currency_id = line.currency_id.id
            currency_dict.setdefault(currency_id, currency_id)
            currency_dict[currency_id] = currency_id

        return [key for key, items in currency_dict.items()]

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(u"Solo puede eliminar un Arqueo en estado 'Borrador'."))
        return super(GrpCashboxRegisterExecution, self).unlink()


class GrpCashboxRegisterExecutionTittle(models.Model):
    _name = 'grp.cashbox.register.executiontitle'
    _description = _(u"Ejecución de Arqueo de caja Titulo")

    execution_id = fields.Many2one('grp.cashbox.register.execution', u'Ejecución', ondelete='cascade')

    name = fields.Char(u'Nombre', size=20)
    operating_unit = fields.Char(u'Unidad organizativa', size=20)


class GrpCashboxRegisterExecutionComposition(models.Model):
    _name = 'grp.cashbox.register.executioncomposition'
    _description = _(u"Composición asociada al Arqueo de caja")

    execution_id = fields.Many2one('grp.cashbox.register.execution', u'Ejecución', ondelete='cascade')

    currency_id = fields.Many2one('res.currency', u'Moneda')
    composition_id = fields.Many2one('grp.cashbox.register.composition', u'Composición', required=True,
                                     ondelete='cascade')
    date = fields.Date('Fecha', related='composition_id.date', readonly=True)
