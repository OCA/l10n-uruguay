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
from openerp import models, fields, exceptions, api, _
from openerp.exceptions import ValidationError
from lxml import etree
from openerp.addons.grp_viaticos.models.grp_hr_expense_v8 import hr_expense_expense_v8

_logger = logging.getLogger(__name__)


class GrpRendicionAnticipos(models.Model):
    _inherit = 'hr.expense.expense'
    # 28/12/2018 ASM comento, esto ya está definido en grp_viaticos
    # _rec_name = 'sequence'

    # RAGU alterando orden del sequence si anticipo de fondo
    @api.model
    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False):
        res = super(GrpRendicionAnticipos, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                                              toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        res['arch'] = etree.tostring(doc)
        if res['name'] == 'grp.rendicion.anticipo.fondo.form' and res['fields'].get('state'):
            res['fields']['state']['selection'] = [
                ('draft', u'Borrador'),
                ('confirm', u'En Aprobación'),
                ('aprobado', u'Aprobado'),
                ('en_autorizacion', u'En Autorización'),
                ('en_financiero', u'En Financiero'),
                ('autorizado', u'Autorizado'),
                ('paid', u'Pagado/a'),
                ('cancelled', u'Rechazado'),
                ('cancelado', u'Cancelado')
            ]
        return res

    # TODO: M SPRING 14 GAP 29_31
    doc_type = fields.Selection(selection_add=[('rendicion_anticipo', 'Rendición de anticipos')])
    # TODO: M SPRING 14 GAP 29_31
    solicitud_anticipos_id = fields.Many2one('grp.solicitud.anticipos.fondos',
                                             string=u'Solicitud de anticipos de fondos',
                                             ondelete='restrict')
    adelanto_anticipo = fields.Float('Adelanto de anticipo', compute='_compute_adelanto_anticipo',
                            digits_compute=dp.get_precision('Account'), store=True)
    state = fields.Selection(selection_add=[('aprobado', 'Aprobado')], string='Status', readonly=True, track_visibility='onchange', copy=False,
                             help='When the expense request is created the status is \'Draft\'.\n It is confirmed by the user and request is sent to admin, the status is \'Waiting Confirmation\'.\
                \nIf the admin accepts it, the status is \'Accepted\'.\n If the accounting entries are made for the expense request, the status is \'Waiting Payment\'.')

    solicitud_anticipos_domain_ids = fields.Many2many(comodel_name="grp.solicitud.anticipos.fondos", string="Solicitud de anticipos",
                                    compute='_compute_solicitud_anticipos_domain_ids')

    @api.multi
    @api.depends('date','solicitud_anticipos_id')
    def _compute_solicitud_anticipos_domain_ids(self):
        solicitud_rendidas = self.search([('state','not in',['cancelado'])]).mapped(lambda x: x.solicitud_anticipos_id).ids
        if not solicitud_rendidas:
            solicitud_rendidas = []
        anticipos_fondos_pagados = [x.solicitud_anticipos_id.id for x in self.env['account.voucher'].search(
            [('solicitud_anticipos_id', '!=', False), ('state', '=', 'pagado')])]
        solicitud_anticipos = self.env['grp.solicitud.anticipos.fondos'].search(
            [('user_uid', '=', self.env.uid), ('id', 'not in', solicitud_rendidas),
             ('id', 'in', anticipos_fondos_pagados), ('state', '=', 'autorizado')])
        for rec in self:
            rec.solicitud_anticipos_domain_ids = solicitud_anticipos.ids

    @api.multi
    @api.depends('amount', 'adelanto', 'state')
    def _compute_diferencia(self):
        for record in self:
            if record.state == 'paid':
                record.diferencia = 0
            elif record.solicitud_anticipos_id:
                record.diferencia = record.amount - record.adelanto_anticipo
            else:
                record.diferencia = record.amount - record.adelanto

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def expense_confirm(self):
        Sequence = self.env['ir.sequence']
        to_return = super(GrpRendicionAnticipos, self).expense_confirm()
        if self.doc_type and self.doc_type == u'rendicion_anticipo':
            for rec in self:
                # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
                # rec.write({'sequence': Sequence.get('rend.antic.number')})
                rec.write({'x_sequence': Sequence.get('rend.antic.number')})
                #
        return to_return


    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def expense_aprobado(self):
        self.write({'state': 'aprobado', 'date_valid': time.strftime('%Y-%m-%d'), 'user_valid':self.env.uid})

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def action_move_create(self):
        account_move_obj = self.env['account.move']
        account_move_line_obj = self.env['account.move.line']
        cur_obj = self.pool.get('res.currency')
        for rec in self:
            if not rec.employee_id.address_home_id:
                raise exceptions.ValidationError(
                    _(u'El empleado debe tener una dirección de casa.'))
            if not rec.employee_id.address_home_id.supplier_advance_account_id.id or not rec.employee_id.address_home_id.customer_advance_account_id.id:
                raise exceptions.ValidationError(
                    _(
                        u'El empleado debe tener las cuentas anticipos de proveedores y clientes establecida en su dirección de casa.'))
            if len(rec.line_ids) > 0:
                # create the move that will contain the accounting entries
                account_move_dict = rec.account_move_get(rec.id)
                account_move_dict.update({'operating_unit_id':rec.operating_unit_id.id})
                move_id = account_move_obj.create(account_move_dict)
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
                    if rec.solicitud_anticipos_id:
                        acc = linea.account_concept_id
                    elif linea.product_id:
                        acc = linea.product_id.property_account_expense
                        if not acc:
                            acc = linea.product_id.categ_id.property_account_expense_categ
                        if not acc:
                            raise exceptions.ValidationError(
                                _(
                                    u'No se ha encontrado una cuenta de compras para el producto %s (o para su categoría). Por favor, configure una.') % (
                                    linea.product_id.name))
                    else:
                        acc = property_obj.with_context(force_company=linea.company_id.id).get(
                            'property_account_expense_categ', 'product.category')
                    if not acc:
                        raise exceptions.ValidationError(
                            _(
                                u'No se ha podido identificar una cuenta para generar la información contable'))

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
                        'operating_unit_id':rec.operating_unit_id.id
                    })
                if rec.doc_type == 'rendicion_anticipo':
                    _account_id = rec.employee_id.address_home_id.customer_advance_account_id.id
                else:
                    _account_id = rec.employee_id.address_home_id.supplier_advance_account_id.id

                if not _account_id:
                    raise exceptions.ValidationError(_(u'No se ha podido identificar una cuenta para generar la información contable'))

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
                    'amount_currency': amount_currency > 0 and amount_currency * -1 or amount_currency,
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
                raise exceptions.ValidationError(_(u'Error, para generar apuntes contables'
                                                   u' de la anticipos de fondos primero debe crear líneas'))
            return True

    # TODO: M SPRING 14 GAP 29_31
    def get_anticipo_product(self):
        return self.env['product.product'].search([('devolucion_anticipo','=',True)],limit=1)

    @api.one
    def crear_recibo(self):
        if self.solicitud_anticipos_id:
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
                        search_args.extend(
                            ['|', ('currency', '=', False), ('currency', '=', self.env.user.company_id.currency_id.id)])
                    journal_id = self.env['account.journal'].search(search_args, limit=1)
                if journal_id:
                    account_id = partner.property_account_payable
                    if not account_id:
                        account_id = journal_id.default_credit_account_id
                        if not account_id:
                            raise exceptions.ValidationError(_(u'Error, debe configurar la cuenta a pagar'
                                                               u' del beneficierio o del diario contable utilizado.'))

                    sa_line_id = len(self.solicitud_anticipos_id.line_ids) and self.solicitud_anticipos_id.line_ids[0] or False
                    account_voucher_id = account_voucher_obj.create({
                        'partner_id': partner.id or False,
                        'date': fields.date.today(),
                        'journal_id': journal_id.id,
                        'type': 'payment',
                        'account_id': account_id.id,
                        'amount': abs(self.diferencia),
                        'payment_rate': 0,
                        'operating_unit_id': self.solicitud_anticipos_id.operating_unit_id.id,
                        'solicitud_anticipos_id': self.solicitud_anticipos_id.id,
                        'rendicion_anticipos_id': self.id,
                        'line_dr_ids':[(0,0,{'concept_id':sa_line_id and sa_line_id.concept_id.id or False,
                                             'account_id':sa_line_id and sa_line_id.account_id.id or False,
                                             'amount_unreconciled': abs(self.diferencia),
                                             'amount': abs(self.diferencia),
                                             'journal_id': journal_id.id or False,
                                             'partner_id': partner.id or False,
                                             })]
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
                        'doc_type': 'vales_caja',
                        'state': 'open',
                        'invoice_line': [
                            (0, 0, {'name': line.name or '', 'account_id': line.account_id.id, 'price_unit': line.amount})
                            for
                            line in account_voucher_id.line_dr_ids]
                    })
                    account_voucher_id.write({'invoice_id': invoice_id.id})
                    invoice_id.write({'doc_type': 'vales_caja'})
                else:
                    raise exceptions.ValidationError(_(u'Error, debe seleccionar un diario compra'
                                                       u' o configurar un diario de compra de la compañia.'))
            else:
                if self.journal_id and self.journal_id.type == 'sale':
                    journal_id = self.journal_id
                else:
                    search_args = [('type', '=', 'sale')]
                    if self.env.user.company_id.currency_id.id != self.currency_id.id:
                        search_args.append(('currency', '=', self.currency_id.id))
                    else:
                        search_args.extend(
                            ['|', ('currency', '=', False), ('currency', '=', self.env.user.company_id.currency_id.id)])
                    journal_id = self.env['account.journal'].search(search_args, limit=1)
                if journal_id:
                    account_id = partner.property_account_receivable
                    if not account_id:
                        account_id = journal_id.default_debit_account_id
                        if not account_id:
                            raise exceptions.ValidationError(_(u'Error, debe configurar la cuenta a cobrar'
                                                               u' del beneficierio o del diario contable utilizado.'))
                    # product_id = self.solicitud_anticipos_id and self.sudo().operating_unit_id.anticipo_product_id
                    product_id = self.get_anticipo_product()
                    if not product_id:
                        raise ValidationError(
                            _(u"Debe configurar un producto Dev. Anticipos para la Unidad ejecutora seleccionada!"))
                        # raise ValidationError(_(u"Debe configurar un producto con la opción 'Devolución de anticipos' seleccionada!"))
                    account_voucher_id = account_voucher_obj.create({
                        'partner_id': partner.id or False,
                        'date': fields.date.today(),
                        'journal_id': journal_id.id,
                        'type': 'sale',
                        'account_id': account_id.id,
                        'amount': abs(self.diferencia),
                        'payment_rate':0,
                        'operating_unit_id': self.solicitud_anticipos_id.operating_unit_id.id,
                        'rendicion_anticipos_id': self.id,
                        'solicitud_anticipos_id': self.solicitud_anticipos_id.id,
                        'line_cr_ids': [
                            (0, 0, {'account_id': partner.customer_advance_account_id.id,
                                    'amount_unreconciled': abs(self.diferencia), 'amount': abs(self.diferencia),
                                    'journal_id': journal_id.id or False,
                                    'partner_id': partner.id or False,
                                    'product_id':product_id.id
                                    })]
                    })

                    account_voucher_id.proforma_voucher()
                else:
                    raise exceptions.ValidationError(_(u'Error, debe seleccionar un diario venta'
                                                       u' o configurar un diario de venta de la compañia.'))
        else:
            super(GrpRendicionAnticipos, self).crear_recibo()
        return True


    # TODO: M SPRING 14 GAP 29_31
    @api.onchange('solicitud_anticipos_id')
    def onchange_solicitud_anticipos_id(self):
        if self.solicitud_anticipos_id:
            self.operating_unit_id = self.solicitud_anticipos_id.operating_unit_id.id
            self.currency_id = self.solicitud_anticipos_id.currency_id.id
            self.name = self.solicitud_anticipos_id.descripcion
            self.line_ids = [(0, 0, {'account_id': line.account_id.id,
                                     'total': line.amount}) for line in self.solicitud_anticipos_id.line_ids]
        else:
            self.operating_unit_id = False
            self.currency_id = False
            self.line_ids.unlink()
            self.line_ids = False

    @api.multi
    @api.depends('solicitud_anticipos_id')
    def _compute_adelanto_anticipo(self):
        voucher_obj = self.env['account.voucher'].suspend_security()
        for rec in self:
            sudo_rec = rec.suspend_security()
            if sudo_rec.solicitud_anticipos_id:
                rec.adelanto_anticipo = voucher_obj.suspend_security().search([
                    ('solicitud_anticipos_id', '=', sudo_rec.solicitud_anticipos_id.id),
                    ('rendicion_anticipos_id', '=', False),
                    ('state', '=', 'pagado')
                ], limit=1).amount
            else:
                rec.adelanto_anticipo = 0

    def _get_voucher(self):
        voucher_obj = self.env['account.voucher']
        if self.doc_type == 'rendicion_anticipo':
            return voucher_obj.search([('rendicion_anticipos_id', '=', self.id), ('state', '!=', 'cancel')])
        elif self.doc_type == 'rendicion_viatico':
            return voucher_obj.search([('rendicion_viaticos_id', '=', self.id), ('state', '!=', 'cancel')], limit=1)
        else:
            return voucher_obj

    @api.multi
    def _check_expense_cancelado(self):
        AccountVoucher = self.env['account.voucher']  # comprobantes de devolucion
        for rec in self:
            if rec.doc_type == u'rendicion_anticipo' and AccountVoucher.search_count([('in_cashbox', '=', True), (
            'rendicion_anticipos_id', '=',
            rec.id)]) or rec.doc_type == u'rendicion_viatico' and AccountVoucher.search_count(
                    [('in_cashbox', '=', True), ('rendicion_viaticos_id', '=', rec.id)]):
                raise ValidationError(
                    _(u"No puede cancelarse la Rendición pues está asociada a una Devolución que ya está incluida en una Caja!"))
        super(GrpRendicionAnticipos, self)._check_expense_cancelado()
        return True


# TODO: M SPRING 14 GAP 29_31
class GrpRendicionAnticiposLine(models.Model):
    _inherit = 'hr.expense.line'

    concept_id = fields.Many2one('grp_concepto_gasto_cc_viaticos', u'Concepto', domain="[('caja_chica','=', True),('a_rendir','=', True)]")
    account_concept_id = fields.Many2one('account.account', 'Cuenta')

    # TODO: M SPRING 14 GAP 29_31
    @api.onchange('concept_id')
    def _onchange_concept_id(self):
        self.account_concept_id = self.concept_id.cuenta_id.id
