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
from collections import defaultdict
from openerp.exceptions import ValidationError
from datetime import *
import time
from lxml import etree


class GrpRemesa(models.Model):
    _inherit = 'grp.caja.recaudadora.tesoreria.boleto.siif'
    _name = 'grp.remesa'
    _description = u"Preparar remesa"

    # TODO: K SPRING 15
    def _compute_move_line_ids(self):
        for rec in self:
            rec.move_line_ids = rec.move_ids.mapped('line_id')

    state = fields.Selection(
        [('draft', u'Nuevo'),
         ('collection_send', u'Remesa enviada')],
        u'Estado', default='draft')

    sequence = fields.Char(u'Secuencia de caja recaudadora', default='/')
    box_details_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line', 'remesa_id', 'Detalles de caja',
                                      domain=[('type', '=', 'box_details')])
    valores_custodia_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line.valor.custodia', 'remesa_id',
                                           'Valores Custodia')
    cash_shipment_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line.remesa', 'remesa_id',
                                        'Remesas efectivo',
                                        domain=[('type', '=', 'cash')])
    check_shipment_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line.remesa', 'remesa_id',
                                         'Remesas cheque',
                                         domain=[('type', '=', 'check')])
    total_shipment_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line.remesa', 'remesa_id',
                                         'Remesas',
                                         domain=[('type', '=', 'total')])
    check_ids = fields.One2many('grp.caja.recaudadora.tesoreria.line', 'remesa_id', 'Cheques',
                                         domain=[('type', '=', 'check')])

    move_line_ids = fields.One2many('account.move.line', compute='_compute_move_line_ids', string=u'Asientos contables')
    move_ids = fields.Many2many('account.move', 'grp_remesa_account_move', 'grp_remesa_id', 'account_move_id',
                                string='Asiento contable remesa')

    # TODO: K SPRING 15
    def _create_move_remesa(self):
        move_a_crear = defaultdict(lambda: [])
        for lineas in self.total_shipment_ids:
            key = str(lineas.journal_id.id) + str(lineas.operating_unit_id.id)
            move_a_crear[key].append(lineas.id)
        moves = []
        for k, v in move_a_crear.items():
            lines_remesas = self.env['grp.caja.recaudadora.tesoreria.line.remesa'].browse(v)
            period_id = self.env['account.period'].find(fields.Date.today()).id
            lines = []
            product_cuenta_dep = self.env['grp.producto.cuenta.deposito']
            company_currency = lines_remesas[0].journal_id.company_id.currency_id.id
            if lines_remesas[0].journal_id.currency:
                current_currency = lines_remesas[0].journal_id.currency.id
            else:
                current_currency = lines_remesas[0].journal_id.company_id.currency_id.id
            diff_currency = current_currency != company_currency and current_currency
            products = lines_remesas.mapped('product_id')
            product_cuenta_dep_ids = product_cuenta_dep.search([('product_id', 'in', products.ids)]).mapped('account_id')
            for cuenta in product_cuenta_dep_ids:
                products = product_cuenta_dep.search([('account_id', '=', cuenta.id)]).mapped('product_id')
                shipment_products = lines_remesas.filtered(lambda x: x.product_id.id in products.ids)
                amount = sum(map(lambda x: x.amount, shipment_products))
                if amount < 0:
                    debit_amount = -amount
                else:
                    debit_amount = amount
                lines.append((0, 0, {
                    'name': "/",
                    'account_id': cuenta.id,
                    'debit': diff_currency and self.currency_id.rate * debit_amount or debit_amount,
                    'credit': 0.0,
                    'currency_id': diff_currency and current_currency or False,
                    'amount_currency': diff_currency and debit_amount or 0.0
                }))
            if not len(lines):
                raise ValidationError(_(
                    u'Debe configurar el "Mapeo producto cuenta de depósito" para los productos implicados.'))
            total_shipment = sum(map(lambda x: x.amount, lines_remesas))
            if total_shipment < 0:
                credit_amount = -total_shipment
            else:
                credit_amount = total_shipment
            lines.append((0, 0, {
                'name': "/",
                'account_id': lines_remesas[0].journal_id.default_debit_account_id.id,
                'debit': 0.0,
                'credit': diff_currency and self.currency_id.rate * credit_amount or credit_amount,
                'currency_id': diff_currency and current_currency or False,
                'amount_currency': diff_currency and - credit_amount or 0.0
            }))

            move = self.env['account.move'].create({
                                                    'journal_id': lines_remesas[0].journal_id.id,
                                                    'period_id': period_id,
                                                    'operating_unit_id':  lines_remesas[0].journal_id.operating_unit_id.id,
                                                    'date': fields.Date.today(),
                                                    'name': self.sequence,
                                                    'ref': self.sequence or "/",
                                                    'line_id': lines
                                                })
            moves.append((4,move.id,False))
        return moves

    # TODO: K SPRING 15
    @api.multi
    def btn_collection_send(self):
        for rec in self:
            if not rec.check_shipment_siff_ticket and not rec.cash_shipment_siff_ticket and \
                not rec.total_shipment_siff_ticket:
                raise exceptions.ValidationError(
                    _(u'Debe ingresar un valor en algún campo Boleto SIIF de la pestaña Remesa.'))
            moves = rec._create_move_remesa()
            rec.write({'state': 'collection_send', 'move_ids':moves})

    # TODO: K SPRING 15
    @api.multi
    def btn_cancel(self):
        for move in self.mapped('move_ids'):
            period_id = self.env['account.period'].find(fields.Date.today()).id
            move.create_reversals(
                fields.Date.today(),
                reversal_period_id=period_id,
            )
        self.write({'state': 'draft', 'move_ids':[(5,)]})

    # TODO: K SPRING 15
    @api.multi
    def unlink(self):
        for rec in self:
            if rec.box_details_ids:
                for line in rec.box_details_ids:
                    line.origin_line_id.write({'preparar_remesa': False})
                rec.box_details_ids.unlink()
                rec.check_ids.unlink()
                rec.valores_custodia_ids.unlink()
        return super(GrpRemesa, self).unlink()

    # TODO: K SPRING 15
    def _update_remesa(self):
        for rec in self:
            cash_shipment_ids = []
            check_shipment_ids = []
            total_shipment_ids = []
            box_details = rec.box_details_ids.filtered(lambda x: x.shipment)
            valores_custodia = rec.valores_custodia_ids.filtered(lambda x: x.shipment)
            products = []
            if box_details or valores_custodia:
                products = list(set(box_details.mapped('product_id')) | set(valores_custodia.mapped('product_id')))

            rec.cash_shipment_ids.unlink()
            rec.check_shipment_ids.unlink()
            rec.total_shipment_ids.unlink()
            cash_expensive_line = False
            check_expensive_line = False
            total_expensive_line = False
            cash_residuals_amount = 0
            check_residuals_amount = 0
            total_residuals_amount = 0
            for product in products:
                operating_unit_ids = list(set(box_details.filtered(
                    lambda x: x.product_id.id == product.id).mapped('operating_unit_id')) | set(valores_custodia.filtered(
                    lambda x: x.product_id.id == product.id).mapped('operating_unit_id')))
                for operating_unit_id in operating_unit_ids:
                    total_cash = sum(map(lambda v: v.weight_amount, box_details.filtered(
                        lambda x: x.payment_method == 'cash' and x.product_id.id == product.id and
                        x.operating_unit_id.id == operating_unit_id.id))) * (-1)

                    total_cash += sum(map(lambda v: v.amount, valores_custodia.filtered(
                        lambda x: x.payment_method == 'cash' and x.product_id.id == product.id and
                        x.operating_unit_id.id == operating_unit_id.id))) * (-1)

                    if total_cash:
                        round_total = round(total_cash,0)
                        new_line = (0, 0, {'product_id': product.id, 'amount': total_cash,'amount_siif': round_total,
                                    'operating_unit_id': operating_unit_id.id,'type': 'cash'})
                        cash_shipment_ids.append(new_line)
                        cash_residuals_amount += total_cash - round_total

                        if not cash_expensive_line or cash_expensive_line[2]['amount_siif'] < round_total:
                            cash_expensive_line = new_line

                    total_check = sum(map(lambda v: v.weight_amount, box_details.filtered(
                        lambda x: x.payment_method == 'check' and x.product_id.id == product.id and
                        x.operating_unit_id.id == operating_unit_id.id))) * (-1)

                    total_check += sum(map(lambda v: v.amount, valores_custodia.filtered(
                        lambda x: x.payment_method == 'check' and x.product_id.id == product.id and
                        x.operating_unit_id.id == operating_unit_id.id))) * (-1)
                    if total_check:
                        round_total = round(total_check, 0)
                        new_line = (0, 0, {'product_id': product.id, 'amount': total_check, 'amount_siif': round_total,
                                    'operating_unit_id': operating_unit_id.id,'type': 'check'})
                        check_shipment_ids.append(new_line)
                        cash_residuals_amount += total_check - round_total
                        if not check_expensive_line or check_expensive_line[2]['amount_siif'] < round_total:
                            check_expensive_line = new_line
                    journal_ids = list(set(box_details.filtered(lambda x: x.product_id.id == product.id and
                                            x.operating_unit_id.id == operating_unit_id.id).mapped('journal_id')) |
                                       set(valores_custodia.filtered(lambda x: x.product_id.id == product.id and
                                            x.operating_unit_id.id == operating_unit_id.id).mapped('journal_id')))
                    for journal_id in journal_ids:
                        total = sum(map(lambda v: v.weight_amount, box_details.filtered(
                            lambda x: x.product_id.id == product.id and
                                      x.operating_unit_id.id == operating_unit_id.id and
                                      x.journal_id.id == journal_id.id))) * (-1)

                        total += sum(map(lambda v: v.amount, valores_custodia.filtered(
                            lambda x: x.product_id.id == product.id and
                                      x.operating_unit_id.id == operating_unit_id.id and
                                      x.journal_id.id == journal_id.id))) * (-1)
                        if total:
                            round_total = round(total, 0)
                            new_line = (0, 0, {'product_id': product.id, 'amount': total, 'amount_siif': round_total, 'journal_id': journal_id.id,
                                        'operating_unit_id': operating_unit_id.id, 'type': 'total'})
                            total_shipment_ids.append(new_line)
                            total_residuals_amount += total - round_total
                            if not total_expensive_line or total_expensive_line[2]['amount_siif'] < round_total:
                                total_expensive_line = new_line

                    total = sum(map(lambda v: v.weight_amount, box_details.filtered(
                        lambda x: x.product_id.id == product.id and
                        x.operating_unit_id.id == operating_unit_id.id and
                                      x.journal_id.id == False))) * (-1)

                    total += sum(map(lambda v: v.amount, valores_custodia.filtered(
                        lambda x: x.product_id.id == product.id and
                        x.operating_unit_id.id == operating_unit_id.id and
                                      x.journal_id.id == False))) * (-1)
                    if total:
                        round_total = round(total, 0)
                        new_line = (0, 0, {'product_id': product.id, 'amount': total,'amount_siif': round_total,
                                    'operating_unit_id': operating_unit_id.id,'type': 'total'})
                        total_shipment_ids.append(new_line)
                        total_residuals_amount += total - round_total
                        if not total_expensive_line or total_expensive_line[2]['amount_siif'] < round_total:
                            total_expensive_line = new_line

            if cash_expensive_line:
                cash_expensive_line[2]['amount_siif'] += round(cash_residuals_amount,0)
            if check_expensive_line:
                check_expensive_line[2]['amount_siif'] += round(check_residuals_amount,0)
            if total_expensive_line:
                total_expensive_line[2]['amount_siif'] += round(total_residuals_amount,0)
            data = {
                'cash_shipment_ids': cash_shipment_ids,
                'check_shipment_ids': check_shipment_ids,
                'total_shipment_ids': total_shipment_ids
            }

            return data

# TODO: K SPRING 15
class GrpCajaRecaudadoraTesoreriaLine(models.Model):
    _inherit = 'grp.caja.recaudadora.tesoreria.line'

    remesa_id = fields.Many2one('grp.remesa', u'Remesa')
    box_id = fields.Many2one('grp.caja', string='Caja')
    journal_id = fields.Many2one('account.journal', string=u'Diario', related='box_id.journal_id', store=True,
                                 readonly=True)
    origin_line_id = fields.Many2one('grp.caja.recaudadora.tesoreria.line', u'Linea original')
    name = fields.Char(u'Nombre')

    # TODO: K SPRING 15
    @api.multi
    def unlink(self):
        for rec in self:
            if rec.type == 'box_details' and rec.remesa_id:
                if rec.remesa_id.state == 'collection_send':
                    raise exceptions.ValidationError(
                        _(u'No se puede eliminar la línea ya que la remesa está enviada.'))
                rec.origin_line_id.write({'siff_ticket': False})
                if rec.voucher_id:
                    lineas_cheque = self.search([('remesa_id', '=', rec.remesa_id.id), ('type', 'in', ['check']), ('voucher_id', '=', rec.voucher_id.id)])
                    if lineas_cheque:
                        lineas_cheque.unlink()
        return super(GrpCajaRecaudadoraTesoreriaLine, self).unlink()

    # TODO: K SPRING 15
    # @api.multi
    # @api.depends('valor_custodia_id', 'voucher_id', 'invoice_id')
    # def _compute_origin_fields(self):
    #     super(GrpCajaRecaudadoraTesoreriaLine, self)._compute_origin_fields()
    #     for rec in self:
    #         if not rec.voucher_id:
    #             rec.operating_unit_id = rec.valor_custodia_id.operating_unit_id.id

# TODO: K SPRING 15
class GrpCajaRecaudadoraTesoreriaLineRemesa(models.Model):
    _inherit = 'grp.caja.recaudadora.tesoreria.line.remesa'

    remesa_id = fields.Many2one('grp.remesa', u'Remesa', ondelete='cascade')
    journal_id = fields.Many2one('account.journal', string=u'Diario')
    type = fields.Selection(selection_add=[('product_ue_journal', 'Remesa producto, ue y diario')])

# TODO: K SPRING 15
class GrpCajaRecaudadoraTesoreriaLineValorCustodia(models.Model):
    _inherit = 'grp.caja.recaudadora.tesoreria.line.valor.custodia'

    remesa_id = fields.Many2one('grp.remesa', u'Remesa')
    origin_line_id = fields.Many2one('grp.caja.recaudadora.tesoreria.line.valor.custodia', u'Linea original')
    box_id = fields.Many2one('grp.caja', string='Caja')
    journal_id = fields.Many2one('account.journal', string=u'Diario', related='box_id.journal_id', store=True,
                                 readonly=True)
    name = fields.Char(u'Nombre')

    # TODO: K SPRING 15
    @api.multi
    def unlink(self):
        for rec in self:
            if rec.remesa_id:
                if rec.remesa_id.state == 'collection_send':
                    raise exceptions.ValidationError(
                        _(u'No se puede eliminar la línea ya que la remesa está enviada.'))
                rec.origin_line_id.write({'siff_ticket': False})
        return super(GrpCajaRecaudadoraTesoreriaLineValorCustodia, self).unlink()


