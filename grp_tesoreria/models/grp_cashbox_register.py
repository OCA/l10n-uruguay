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


class GrpCashboxRegister(models.Model):
    _name = 'grp.cashbox.register'
    _description = _(u"Configuración de Arqueo de caja")
    _inherit = ['mail.thread']

    name = fields.Char('Nombre', size=50, required=True, readonly=True, states={'draft': [('readonly', False)]},
                       track_visibility='onchange')
    active = fields.Boolean('Activo', default=True, track_visibility='onchange')

    caja_pagadora_ids = fields.Many2many('grp.caja', 'grp_cashbox_register_pagadora_rel', 'cr_id', 'cp_id',
                                         domain="[('caja_pagadora','=',True),('control_efectivo','=',True),('fondo_terceros','=',False),('otras_cajas','=',False)]",
                                         readonly=True, states={'draft': [('readonly', False)]},
                                         string=u'Cajas pagadoras')
    caja_cheque_ids = fields.Many2many('grp.caja', 'grp_cashbox_register_cheque_rel', 'cr_id', 'cch_id',
                                       domain="[('caja_pagadora','=',True),('control_efectivo','=',False),('fondo_terceros','=',False),('otras_cajas','=',False)]",
                                       readonly=True, states={'draft': [('readonly', False)]},
                                       string=u'Cajas de cheques')
    caja_recaudadora_ids = fields.Many2many('grp.caja', 'grp_cashbox_register_recaudadora_rel', 'cr_id', 'crec_id',
                                            domain="[('caja_recaudadora','=',True),('fondo_terceros','=',False),('otras_cajas','=',False)]",
                                            readonly=True, states={'draft': [('readonly', False)]},
                                            string=u'Cajas recaudadoras')
    caja_fondo_terceros_ids = fields.Many2many('grp.caja', 'grp_cashbox_register_terceros_rel', 'cr_id', 'ft_id',
                                               readonly=True, states={'draft': [('readonly', False)]},
                                               string=u'Cajas fondos de terceros',
                                               domain="[('fondo_terceros','=',True)]")
    caja_otras_ids = fields.Many2many('grp.caja', 'grp_cashbox_register_otras_rel', 'cr_id', 'co_id',
                                      domain="[('otras_cajas','=',True)]",
                                      readonly=True, states={'draft': [('readonly', False)]}, string=u'Otras cajas')
    state = fields.Selection([('draft', 'Borrador'), ('confirm', 'Confirmado'), ('cancel', 'Cancelado')], u'Estado',
                             default='draft',
                             track_visibility='onchange')

    @api.multi
    def action_confirm(self):
        self.write({'state': 'confirm'})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(u"Solo puede eliminar una configuración en estado 'Borrador'."))
        return super(GrpCashboxRegister, self).unlink()


class GrpCashboxRegisterComposition(models.Model):
    _name = 'grp.cashbox.register.composition'
    _description = _(u"Composición de Arqueo de caja")
    _inherit = ['mail.thread']

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, 'Fecha: %s, Moneda: %s, Arqueo: %s' % (rec.date, rec.currency_id.name_get()[0][1], rec.cashbox_register_id.name_get()[0][1])))
        return result

    date = fields.Date(u'Fecha', default=lambda *x: fields.Date.today(), required=True,
                       readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', u'Moneda', required=True,
                                  readonly=True, states={'draft': [('readonly', False)]}, track_visibility='onchange')
    cashbox_register_id = fields.Many2one('grp.cashbox.register', u'Arqueo', required=True, ondelete='cascade',
                                          domain=[('state','=','confirm')],
                                          readonly=True, states={'draft': [('readonly', False)]})

    caja_pagadora_line_ids = fields.One2many('grp.cashbox.register.composition.pline', 'composition_id',
                                             string=u'Cajas pagadoras en efectivo',
                                             readonly=True, states={'draft': [('readonly', False)]})
    caja_recaudadora_line_ids = fields.One2many('grp.cashbox.register.composition.rline', 'composition_id',
                                                domain=[('type', '=', 'recaudadora'), 
                                                '|', ('siff_ticket', '=', False), ('caja_config_id.caja_principal', '=', False)],
                                                string=u'Cajas recaudadoras en efectivo',
                                                readonly=True, states={'draft': [('readonly', False)]})
    fondo_terceros_ids = fields.One2many('grp.cashbox.register.composition.rline', 'composition_id',
                                         domain=[('type', '=', 'fterceros'), ('caja_recaudadora_line_id.apertura_recibo', '=', False)],
                                         string=u'Fondo de terceros en efectivo',
                                         readonly=True, states={'draft': [('readonly', False)]})

    # INFORMACIÓN DE MONEDAS
    caja_pagadora_monetaryline_ids = fields.One2many('grp.cashbox.register.composition.pmonetaryline', 'composition_id',
                                                     string=u'Monedas',
                                                     readonly=True, states={'draft': [('readonly', False)]})

    caja_recaudadora_monetaryline_ids = fields.One2many('grp.cashbox.register.composition.monetaryline',
                                                        'composition_id',
                                                        string=u'Monedas',
                                                        domain=[('type', '=', 'recaudadora')],
                                                        readonly=True, states={'draft': [('readonly', False)]})

    fterceros_monetaryline_ids = fields.One2many('grp.cashbox.register.composition.monetaryline',
                                                 'composition_id',
                                                 domain=[('type', '=', 'fterceros')],
                                                 string=u'Monedas',
                                                 readonly=True, states={'draft': [('readonly', False)]})

    monetaryline_ids = fields.One2many('grp.cashbox.register.composition.monetaryline',
                                       'composition_id',
                                       domain=[('type', '=', 'summary')],
                                       string=u'Monedas',
                                       readonly=True, states={'draft': [('readonly', False)]})

    state = fields.Selection([('draft', 'Borrador'), ('confirm', 'Confirmado'), ('cancel', 'Cancelado')], u'Estado',
                             default='draft', track_visibility='onchange')

    _sql_constraints = [
        ('control_unicidad_uniq', 'unique(date,currency_id,cashbox_register_id)', 'No pueden existir dos registros con misma fecha, moneda y Nombre arqueo'),
    ]

    @api.onchange('caja_pagadora_monetaryline_ids', 'caja_recaudadora_monetaryline_ids', 'fterceros_monetaryline_ids')
    def _onchange_moneraty_info(self):
        self.monetaryline_ids = [(5,)] + self._get_moneraty_items()

    @api.multi
    def action_draft(self):
        self.write({'state': 'draft'})

    def _validate_confirm(self):
        for rec in self:
            if float_round(sum(map(lambda x: x.cashbox_subtotal_amount, rec.caja_pagadora_monetaryline_ids)), 2) != float_round(sum(map(lambda x: x.subtotal_amount, rec.caja_pagadora_monetaryline_ids)), 2):
                raise ValidationError(_(u"En Caja pagadora los subtotales en las líneas de las Monedas deben coincidir!"))

            if float_round(sum(map(lambda x: x.amount, rec.caja_recaudadora_line_ids)),2) != float_round(sum(map(lambda x: x.subtotal_amount, rec.caja_recaudadora_monetaryline_ids)),2):
                raise ValidationError(_(u"En Caja Recaudadora el total de las Monedas debe coincidir con el total del Importe cobrado!"))

            if float_round(sum(map(lambda x: x.amount, rec.fondo_terceros_ids)),2) != float_round(sum(map(lambda x: x.subtotal_amount, rec.fterceros_monetaryline_ids)),2):
                raise ValidationError(_(u"En Fondo Terceros el total de las Monedas debe coincidir con el total del Importe cobrado!"))
        return True

    @api.multi
    def action_confirm(self):
        self._validate_confirm()
        self.write({'state': 'confirm'})

    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.multi
    def action_update(self):
        self.caja_pagadora_line_ids.unlink()
        self.caja_pagadora_monetaryline_ids.unlink()
        self.caja_recaudadora_line_ids.unlink()
        self.caja_recaudadora_monetaryline_ids.unlink()
        self.fondo_terceros_ids.unlink()
        self.fterceros_monetaryline_ids.unlink()
        self.monetaryline_ids.unlink()

        if self.date and self.currency_id:
            cajas_pagadoras, cajas_pagadoras_monetary_lines = self._get_cp_items()
            cajas_recaudadoras, cajas_recaudadoras_monetary_lines = self._get_cr_items('recaudadora')
            cajas_fterceros, cajas_fterceros_monetary_lines = self._get_cr_items('fterceros')

        self.write({
            'caja_pagadora_line_ids':cajas_pagadoras,
            'caja_pagadora_monetaryline_ids':cajas_pagadoras_monetary_lines,
            'caja_recaudadora_line_ids':cajas_recaudadoras,
            'caja_recaudadora_monetaryline_ids':cajas_recaudadoras_monetary_lines,
            'fondo_terceros_ids':cajas_fterceros,
            'fterceros_monetaryline_ids':cajas_fterceros_monetary_lines,
        })
        self.write({
            'monetaryline_ids': self._get_moneraty_items()
        })



    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(u"Solo puede eliminar una composición en estado 'Borrador'."))
        return super(GrpCashboxRegisterComposition, self).unlink()

    def _get_cp_items(self):
        cajas_efectivos = [(5,)]
        monetary_lines = [(5,)]
        monetary_dict = {}
        CajaEfectivo = self.env['grp.caja.chica.tesoreria']

        same_company_currency = self.env.user.company_id.currency_id.id == self.currency_id.id
        for cashbox_id in self.cashbox_register_id.caja_pagadora_ids.filtered(
                lambda x: x.currency_id.id == self.currency_id.id or (not x.currency_id and same_company_currency)):
            last_cashbox = CajaEfectivo.search([('box_id', '=', cashbox_id.id),
                                                ('state', 'in', ['end', 'check']),
                                                ('closing_date', '<=', self.date)], limit=1,
                                               order='closing_date DESC')
            cajas_efectivos.append((0, 0, {'caja_config_id': cashbox_id.id, 'caja_pagadora_id': last_cashbox.id}))

            for monetary_line in last_cashbox.closing_details_ids:
                monetary_dict.setdefault(monetary_line.pieces, {'number_closing': 0})
                monetary_dict[monetary_line.pieces]['number_closing'] += monetary_line.number_closing

        for key, data in monetary_dict.items():
            monetary_lines.append(
                (0, 0, {'pieces': key, 'cashbox_number': data['number_closing'], 'number': data['number_closing']}))

        return cajas_efectivos, monetary_lines

    def _get_cr_items(self, type):
        CajaRecaudadora = self.env['grp.caja.recaudadora.tesoreria']
        CajaRecaudadoraLine = self.env['grp.caja.recaudadora.tesoreria.line']
        cajas_recaudadoras = [(5,)]
        monetary_lines = [(5,)]
        monetary_dict = {}

        same_company_currency = self.env.user.company_id.currency_id.id == self.currency_id.id

        if type == 'recaudadora':
            cajas = self.cashbox_register_id.caja_recaudadora_ids
        else:
            cajas = self.cashbox_register_id.caja_fondo_terceros_ids

        cashboxs_config = cajas.filtered(lambda x: x.currency_id.id == self.currency_id.id or (not x.currency_id and same_company_currency)).ids
        for caja_recaudadora in CajaRecaudadora.search([
            ('box_id', 'in', cashboxs_config),
            ('state', 'in', ['close', 'checked']),
            ('closing_date', '<=', self.date)], order='closing_date DESC'):

            for voucher_detail_id in caja_recaudadora.voucher_details_ids.filtered(
                    lambda x: x.payment_method == 'cash'):
                _available = False
                if not voucher_detail_id.shipment and not voucher_detail_id.entrega_tesoreria:
                    _available = True
                else:
                    if voucher_detail_id.shipment and not voucher_detail_id.caja_recaudadora_id.box_id.caja_principal:
                        if not CajaRecaudadoraLine.search_count([('siif_reference_id', '=', voucher_detail_id.id), (
                                'boleto_siif_id.state', '!=', u'collection_send')]):
                            _available = False
                    if voucher_detail_id.entrega_tesoreria and not voucher_detail_id.caja_recaudadora_id.box_id.caja_principal:
                        if not CajaRecaudadoraLine.search_count([('origin_line_id', '=', voucher_detail_id.id),
                                                                 ('remesa_id.state', '=', 'collection_send')]):
                            _available = True
                    if voucher_detail_id.entrega_tesoreria:
                        if not CajaRecaudadoraLine.search_count([('origin_line_id', '=', voucher_detail_id.id),
                                                                 ('remesa_id.state', '=', 'collection_send')]):
                            _available = True

                if _available:
                    cajas_recaudadoras.append((0, 0, {'caja_config_id': caja_recaudadora.box_id.id,
                                                      'type': type,
                                                      'caja_recaudadora_line_id': voucher_detail_id.id}))

            for monetary_line in caja_recaudadora.closing_details_ids:
                monetary_dict.setdefault(monetary_line.pieces, {'number_closing': 0})
                # monetary_dict[monetary_line.pieces]['number_closing'] += monetary_line['number_closing']

        for key, data in monetary_dict.items():
            monetary_lines.append((0, 0, {'pieces': key, 'type': type, 'number': 0}))
        return cajas_recaudadoras, monetary_lines

    @api.onchange('currency_id', 'cashbox_register_id')
    def _recompute_cashbox_lines(self):
        cajas_pagadoras = [(5,)]
        cajas_recaudadoras = [(5,)]
        cajas_fterceros = [(5,)]
        cajas_pagadoras_monetary_lines = [(5,)]
        cajas_recaudadoras_monetary_lines = [(5,)]
        cajas_fterceros_monetary_lines = [(5,)]
        if self.date and self.currency_id:
            cajas_pagadoras, cajas_pagadoras_monetary_lines = self._get_cp_items()
            cajas_recaudadoras, cajas_recaudadoras_monetary_lines = self._get_cr_items('recaudadora')
            cajas_fterceros, cajas_fterceros_monetary_lines = self._get_cr_items('fterceros')

        self.caja_pagadora_line_ids = cajas_pagadoras
        self.caja_pagadora_monetaryline_ids = cajas_pagadoras_monetary_lines
        self.caja_recaudadora_line_ids = cajas_recaudadoras
        self.caja_recaudadora_monetaryline_ids = cajas_recaudadoras_monetary_lines
        self.fondo_terceros_ids = cajas_fterceros
        self.fterceros_monetaryline_ids = cajas_fterceros_monetary_lines

    @api.multi
    def _get_moneraty_items(self):
        self.ensure_one()
        monetary_lines = []
        monetary_dict = {}

        for line in self.caja_pagadora_monetaryline_ids:
            monetary_dict.setdefault(line.pieces, {'number': 0})
            monetary_dict[line.pieces]['number'] += line.number

        for line in self.caja_recaudadora_monetaryline_ids:
            monetary_dict.setdefault(line.pieces, {'number': 0})
            monetary_dict[line.pieces]['number'] += line.number

        # for line in self.fterceros_monetaryline_ids:
        #     monetary_dict.setdefault(line.pieces, {'number': 0})
        #     monetary_dict[line.pieces]['number'] += line.number

        for key, data in monetary_dict.items():
            monetary_lines.append((0, 0, {'pieces': key, 'number': data['number'], 'type': 'summary'}))

        return monetary_lines


class GrpCashboxRegisterCompositionPLine(models.Model):
    _name = 'grp.cashbox.register.composition.pline'
    _description = _(u"Línea de Composición Arqueo de caja pagadora")

    composition_id = fields.Many2one('grp.cashbox.register.composition', u'Composición', required=True,
                                     ondelete='cascade')
    caja_config_id = fields.Many2one('grp.caja', u'Caja', required=True)
    caja_pagadora_id = fields.Many2one('grp.caja.chica.tesoreria', u'Caja', required=False)

    name = fields.Char(u'Nombre', related='caja_pagadora_id.name', readonly=True)
    user_id = fields.Many2one('res.users', string=u'Responsable', related='caja_pagadora_id.user_id', readonly=True)
    date = fields.Datetime(string=u'Fecha de apertura', related='caja_pagadora_id.date', readonly=True)
    closing_date = fields.Datetime(string=u'Cerrado en', related='caja_pagadora_id.closing_date', readonly=True)
    balance_end_real = fields.Float('Total efectivo', related='caja_pagadora_id.balance_end_real', readonly=True)
    state = fields.Selection([('draft', 'Borrador'),
                              ('open', u'Abierto/a'),
                              ('end', 'Cerrado'),
                              ('check', 'Revisado')], related='caja_pagadora_id.state', readonly=True)


class GrpCashboxRegisterCompositionRLine(models.Model):
    _name = 'grp.cashbox.register.composition.rline'
    _description = _(u"Línea de Composición Arqueo de caja recaudadora")

    composition_id = fields.Many2one('grp.cashbox.register.composition', u'Composición', required=True,
                                     ondelete='cascade')
    type = fields.Selection([('recaudadora', 'Recaudadora'), ('fterceros', 'Fondo de terceros')])
    caja_config_id = fields.Many2one('grp.caja', u'Caja', required=True)
    caja_recaudadora_line_id = fields.Many2one('grp.caja.recaudadora.tesoreria.line', u'Caja', required=False)

    name = fields.Char(u'Nombre', related='caja_recaudadora_line_id.caja_recaudadora_id.name', readonly=True)
    user_id = fields.Many2one('res.users', string=u'Responsable',
                              related='caja_recaudadora_line_id.caja_recaudadora_id.user_uid', readonly=True)

    # ENLACE INTERNO
    voucher_line_id = fields.Many2one('account.voucher.line', u'Línea de comprobante',
                                      related='caja_recaudadora_line_id.vline_id', readonly=True)

    # DETALLES
    shipment = fields.Boolean(u'Entrega en tesorería', related='caja_recaudadora_line_id.shipment', readonly=True)
    siff_ticket = fields.Boolean(u'Preparar remesa', related='caja_recaudadora_line_id.siff_ticket', readonly=True)
    amount = fields.Float(string=u'Importe cobrado', related='caja_recaudadora_line_id.weight_amount', readonly=True)
    date = fields.Date(u'Fecha de cobro', related='caja_recaudadora_line_id.date', readonly=True)

    # RECIBOS
    no_recibo = fields.Char(string=u'No recibo', compute='_compute_recibo_info', store=True)

    @api.multi
    @api.depends('caja_recaudadora_line_id')
    def _compute_recibo_info(self):
        CajaRecaudadoraTesoreriaLine = self.env['grp.caja.recaudadora.tesoreria.line']
        for rec in self:
            rec.no_recibo = CajaRecaudadoraTesoreriaLine.search(
                [('vline_id', '=', rec.caja_recaudadora_line_id.vline_id.id), ('type', '=', 'voucher')],
                limit=1).no_recibo


# INFORMACIÓN DE MONEDAS
class GrpCashboxRegisterCompositionPMonetaryLine(models.Model):
    _name = 'grp.cashbox.register.composition.pmonetaryline'
    _description = _(u"Línea Monetaria de Composición Arqueo de caja CP")
    _order = 'pieces ASC'

    composition_id = fields.Many2one('grp.cashbox.register.composition', u'Composición', required=True,
                                     ondelete='cascade')
    pieces = fields.Float(u'Unidad de moneda', digits_compute=dp.get_precision('Account'))
    cashbox_number = fields.Float(u'Número de unidades en cajas')
    cashbox_subtotal_amount = fields.Float(u'Subtotal de cierre', compute='_compute_cashbox_subtotal_amount',
                                           store=True, digits_compute=dp.get_precision('Account'))
    number = fields.Float(u'Número de unidades')
    subtotal_amount = fields.Float(u'Composición real', compute='_compute_subtotal_amount', store=True,
                                   digits_compute=dp.get_precision('Account'))

    @api.multi
    @api.depends('pieces', 'cashbox_number')
    def _compute_cashbox_subtotal_amount(self):
        for rec in self:
            rec.cashbox_subtotal_amount = rec.cashbox_number * rec.pieces

    @api.multi
    @api.depends('pieces', 'number')
    def _compute_subtotal_amount(self):
        for rec in self:
            rec.subtotal_amount = rec.number * rec.pieces


class GrpCashboxRegisterCompositionMonetaryLine(models.Model):
    _name = 'grp.cashbox.register.composition.monetaryline'
    _description = _(u"Línea Monetaria de Composición Arqueo de caja CR")
    _order = 'pieces ASC'

    composition_id = fields.Many2one('grp.cashbox.register.composition', u'Composición', required=True,
                                     ondelete='cascade')
    type = fields.Selection([('recaudadora', 'Recaudadora'), ('fterceros', 'Fondo de terceros'), ('summary', 'Total')])
    pieces = fields.Float(u'Unidad de moneda', digits_compute=dp.get_precision('Account'))
    number = fields.Float(u'Número de unidades')
    subtotal_amount = fields.Float(u'Composición real', compute='_compute_subtotal_amount', store=True,
                                   digits_compute=dp.get_precision('Account'))

    @api.multi
    @api.depends('pieces', 'number')
    def _compute_subtotal_amount(self):
        for rec in self:
            rec.subtotal_amount = rec.number * rec.pieces