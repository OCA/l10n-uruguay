# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Enterprise Management Solution
#    GRP Estado Uruguay
#    Copyright (C) Quanam (ATEL SA., Uruguay)
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
#    Proyecto:    GRP
#    Fecha:       03/05/2017
#    Autor:       Quanam
#    Compañia:    Quanam - www.quanam.com
#    Descripción: 383. Agregar campos de banco y sucursal en extracto bancario.
##############################################################################
#Ref  Id Tarea  Tecnico    Fecha       Descripcion
#-----------------------------------------------------------------------------
#001            SVILLANUEVA 03/05/2017 Agregar campos de banco y sucursal
#                                       en extracto bancario.
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError


class GrpAccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'
    _name = 'account.bank.statement'

    bank_id = fields.Many2one('res.bank', string='Banco', compute='_compute_banco', store=False)
    agencia = fields.Char('Agencia', compute='_compute_banco', store=False)

    @api.multi
    @api.constrains('journal_id', 'state')
    def _check_account_bank_statement_journal(self):
        for rec in self:
            if rec.state == 'open' and self.search_count([('journal_id','=',rec.journal_id.id),('state','=','open'),('id','!=',rec.id)]):
                raise ValidationError(_(u"Solo debe existir un registro por diario en estado 'Abierto'!"))
        return True

    @api.depends('journal_id')
    def _compute_banco(self):
        for record in self:
            record.bank_id = False
            record.agencia = False
            if record.journal_id:
                domain = [('journal_id','=',record.journal_id.id)]
                cuenta_banco = self.env['res.partner.bank'].search(domain)
                if cuenta_banco:
                    record.bank_id = cuenta_banco.bank.id
                    record.agencia = cuenta_banco.agencia
