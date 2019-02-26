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

from openerp import models, fields
from openerp.tools.sql import drop_view_if_exists

class grpAccountBankStatement(models.Model):
    _name = "grp.account.bank.statement.lines"
    _description = "Listado de Registro de Caja"
    _auto = False


    user_id = fields.Many2one('res.users', 'Responsable')
    closing_date = fields.Datetime("Cerrado en")
    period_id = fields.Many2one('account.period', u'Período')
    state = fields.Char('Estado')
    date = fields.Date('Fecha')
    concepto_id = fields.Many2one('grp_concepto_gasto_cc_viaticos', 'Concepto', ondelete='restrict')
    name = fields.Char(u'Comunicación')
    ref = fields.Char('Referencia')
    partner_id = fields.Many2one('res.partner', 'Empresa')
    amount = fields.Float('Importe')
    amount_currency = fields.Float('Monto de dinero')
    account_id = fields.Many2one('account.account', 'Cuenta')
    bank_account_id = fields.Many2one('res.partner.bank','Cuenta Bancaria')
    fondo_rotarios = fields.Boolean(string='En 3 en 1-Fondo rotatorio')
    company_id = fields.Many2one('res.company', u'Compañía')
    journal_id = fields.Many2one('account.journal', 'Diario')
    note = fields.Text('Notas')
    partner_name = fields.Char('Nombre de la empresa')
    sequence = fields.Integer('Secuencia')
    operating_unit_id = fields.Many2one("operating.unit", 'Unidad ejecutora')


    #  line.company_id,line.journal_id,

    def init(self, cr):
        drop_view_if_exists(cr, 'grp_account_bank_statement_lines')
        cr.execute("""
            create or replace view grp_account_bank_statement_lines as (
            select line.id AS id,bank.user_id,bank.closing_date,bank.period_id, bank.state,
            line.date, line.concepto_id,line.name ,line.ref ,line.partner_id , line.amount, line.amount_currency, line.account_id,
            line.bank_account_id,line.company_id,line.journal_id,line.note,line.partner_name,line.sequence,line.fondo_rotarios, journal.operating_unit_id
            from account_bank_statement_line line , account_bank_statement bank, account_journal journal
            where bank.id = line.statement_id
            and bank.journal_id = journal.id
        )""")