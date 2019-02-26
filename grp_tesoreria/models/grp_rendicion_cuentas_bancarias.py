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
from openerp.exceptions import ValidationError
from datetime import *
from dateutil.relativedelta import relativedelta
import time
from lxml import etree


# TODO: M SPRING 13 GAP 281

class GrpRendicionCuentasBancarias(models.Model):
    _name = 'grp.rendicion.cuentas.bancarias'
    _rec_name = 'journal_id'

    period_id = fields.Many2one('account.period',string=u'Periodo')
    journal_id = fields.Many2one('account.journal', string='Diario',
                                          domain=[('type', '=', 'bank')])
    user_uid = fields.Many2one('res.users', 'Responsable', readonly=True, default=lambda self: self._uid)
    balance_inicial = fields.Float(compute='_compute_balance_inicial', string=u'Saldo inicial', store=True)
    state = fields.Selection([('draft', u'Borrador'),
                            ('to_be_reviewed', u'Listo para revisión'),
                            ('done', u'Finalizado')], u'Estado', default='draft')

    detalles_ids = fields.One2many('grp.rendicion.cuentas.bancarias.line', 'rendicion_c_bancaria_id', u'Detalles',
                                 domain=[('tipo', '=', 'detalle')])

    ajustes_ids = fields.One2many('grp.rendicion.cuentas.bancarias.line', 'rendicion_c_bancaria_id', u'Ajustes',
                                    domain=[('tipo', '=', 'ajuste')])

    balance_final_cargos = fields.Float(string=u"Cargos",
                                             compute='_compute_balance_final', multi='saldos')
    balance_final_descargos = fields.Float(string="Descargos",
                                                 compute='_compute_balance_final', multi='saldos')

    balance_final = fields.Float(compute='_compute_balance_final', string=u'Saldo final')




    @api.multi
    @api.depends('journal_id','period_id')
    def _compute_balance_inicial(self):
        for rec in self:
            rec.balance_inicial = 0.0
            if rec.journal_id and rec.period_id:
                rendicion_anterior = self.get_rendicion_periodo_anterior()
                # periodo_anterior = self._get_periodo_anterior()
                # if periodo_anterior:
                #     rendicion_caja = rec.search([('caja_recaudadora_id','=',rec.caja_recaudadora_id.id),('period_id','=',periodo_anterior.id)])
                if rendicion_anterior:
                    rec.balance_inicial = rendicion_anterior.balance_final

    @api.multi
    @api.depends('detalles_ids','ajustes_ids')
    def _compute_balance_final(self):
        for rec in self:
            rec.balance_final_cargos = 0.0
            rec.balance_final_descargos = 0.0
            rec.balance_final = 0.0
            if rec.detalles_ids or rec.ajustes_ids:
                rec.balance_final_cargos = self._get_total('cargos', rec.detalles_ids, rec.ajustes_ids)
                rec.balance_final_descargos = self._get_total('descargos', rec.detalles_ids, rec.ajustes_ids)
                rec.balance_final = rec.balance_inicial + rec.balance_final_cargos - rec.balance_final_descargos


    @api.onchange('period_id','journal_id')
    def onchange_period_id(self):
        if self.period_id and self.journal_id:
            self.detalles_ids = self._get_detalles_ids()

    #TODO: Se decidio utilizar un sql_constrain en vez de un constrains
    _sql_constraints = [
        ('journal_period_uniq', 'unique (journal_id, period_id)',
         u'Solo debe existir un registro por diario y periodo.')
    ]

    @api.multi
    def btn_review(self):
        return self.write({'state': 'to_be_reviewed'})

    @api.multi
    def btn_cancel(self):
        return self.write({'state': 'draft'})

    @api.multi
    def btn_done(self):
        return self.write({'state': 'done'})

    @api.multi
    def btn_refresh(self):
        return {
            'name': _('Rendición de cuentas bancareas'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'grp.rendicion.cuentas.bancarias',
            # 'context': ctx,
            'type': 'ir.actions.act_window',
        }

    def _get_detalles_ids(self):
        detalles_ids = []
        default_debit_account_id = self.journal_id.default_debit_account_id
        default_credit_account_id = self.journal_id.default_credit_account_id
        move_line = self.env['account.move.line'].search([('date','>=',self.period_id.date_start),
                                                          ('date', '<=', self.period_id.date_stop)])
        if move_line:
            move_line_filter = move_line.filtered(lambda x: x.account_id.id == default_debit_account_id.id
                                                    or x.account_id.id == default_credit_account_id.id)
            for line in move_line_filter:

                voucher_lines = self.env['account.voucher.line'].search([('move_line_id','=',line.id)])
                if voucher_lines:
                    for voucher_line in voucher_lines:
                        values = {
                            'date': line.date,
                            'operating_unit_id': line.operating_unit_id.id,
                            'no_afectacion': voucher_line.invoice_id and voucher_line.invoice_id.nro_afectacion_fnc,
                            'doc': line.operating_unit_id.code+'/'+ voucher_line.invoice_id and voucher_line.invoice_id.nro_afectacion_fnc,
                            'move_id': line.move_id.id,
                            'cargos': voucher_line.amount,
                            'descargos': voucher_line.amount,
                            'tipo': 'detalle',
                        }
                        detalles_ids.append([0, 0, values])
                else:
                    values = {
                        'date': line.date,
                        'operating_unit_id': line.operating_unit_id.id,
                        'no_afectacion': 0,
                        'doc': line.operating_unit_id.code,
                        'move_id': line.move_id.id,
                        'cargos': line.debit,
                        'descargos': line.credit,
                        'tipo': 'detalle',
                    }
                    detalles_ids.append([0, 0, values])

            return detalles_ids

    def _get_total(self, campo, detalles, ajustes):
        total = sum(map(lambda x: x[campo], detalles)) + sum(map(lambda x: x[campo], ajustes))
        return total

    def get_rendicion_periodo_anterior(self):
        periodo_anterior = self._get_periodo_anterior()
        if periodo_anterior:
            rendicion_anterior = self.search(
                [('journal_id', '=', self.journal_id.id), ('period_id', '=', periodo_anterior.id)])
            return rendicion_anterior


    def _get_periodo_anterior(self):
        date_start = datetime.strptime(self.period_id.date_start, "%Y-%m-%d")
        # date_stop = datetime.strptime(self.period_id.date_stop, "%Y-%m-%d")
        # date_start_anterior = (date_start - relativedelta(months=1)).strftime("%Y-%m-%d")
        date_stop_anterior = (date_start - relativedelta(days=1)).strftime("%Y-%m-%d")
        periodo_anterior = self.env['account.period'].search(
            [('date_start', '<=', date_stop_anterior), ('date_stop', '>=', date_stop_anterior)])
        return periodo_anterior




class GrpRendicionCuentasBancariasLine(models.Model):
    _name = 'grp.rendicion.cuentas.bancarias.line'

    rendicion_c_bancaria_id = fields.Many2one('grp.rendicion.cuentas.bancarias', 'Rendición de cuentas bancarias', ondelete='cascade') # TODO L VARIANZA GRP
    date = fields.Date(u'Fecha')
    code = fields.Char(string=u'Código')
    doc = fields.Char(string=u'Doc')
    operating_unit_id = fields.Many2one('operating.unit', string='UE')
    no_afectacion = fields.Float(string=u'Num afectación')
    move_id = fields.Many2one('account.move', 'Asiento contable')
    cargos = fields.Float(string=u'Cargos')
    descargos = fields.Float(string=u'Descargos')
    tipo = fields.Selection([('detalle', u'Detalle'),
                             ('ajuste', u'Ajuste')], string=u'Tipo', default='ajuste')

    period_id = fields.Many2one('account.period', string=u'Periodo', related='rendicion_c_bancaria_id.period_id', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Diario',related='rendicion_c_bancaria_id.journal_id', readonly=True)
    user_uid = fields.Many2one('res.users', 'Responsable', related='rendicion_c_bancaria_id.user_uid', readonly=True)
    balance_inicial = fields.Float(string=u'Saldo inicial',related='rendicion_c_bancaria_id.balance_inicial', readonly=True)







