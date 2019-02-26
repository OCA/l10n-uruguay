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
from openerp import tools


class GrpBankStatementTraceReport(models.Model):
    _name = 'grp.bank.statement.trace.report'
    _auto = False
    _description = u'Trazabilidad de Caja chica'

    opi_id = fields.Many2one('account.voucher', string=u'Orden de pago interna')
    opi_number = fields.Char(u"Nro. OPI")
    opi_date = fields.Date(u"Fecha OPI")
    opi_amount = fields.Float(u"Importe OPI")
    bank_statement_id = fields.Many2one('account.bank.statement', u"Registro de caja")
    journal_id = fields.Many2one('account.journal', u"Caja chica")
    bank_statement_checked = fields.Boolean(u"Revisada")
    toreturn_amount = fields.Float(u"Importe a reponer")
    reposition_in_amount = fields.Float(u"Importe reposición ingresado en caja")
    reposition_date = fields.Date(u"Fecha de reposición")
    reposition_concept = fields.Char(u"Concepto de reposición")

    opi_paid = fields.Boolean('Paga', compute='_compute_opi_paid')

    @api.multi
    def _compute_opi_paid(self):
        for rec in self:
            rec.opi_paid = len(rec.opi_id.payment_ids) > 0

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_bank_statement_trace_report')
        cr.execute("""
            CREATE OR replace VIEW grp_bank_statement_trace_report AS (
                SELECT 
	opi.id AS opi_id, 
	opi.number AS opi_number,
	opi.date AS opi_date,
	opi.amount AS opi_amount,
	bs.id AS id,
	bs.journal_id AS journal_id,
	bs.id AS bank_statement_id,
	bs.name AS bank_statement_number,
	bs.state = 'revisado' AS bank_statement_checked,
	(
	SELECT
		SUM(bsl.amount)
	FROM
		account_bank_statement_line AS bsl, 
		grp_concepto_gasto_cc_viaticos AS concept 
	WHERE
		bsl.concepto_id = concept.id AND
		concept.caja_chica = True AND
		bsl.statement_id = bs.id
	) AS toreturn_amount,
	(SELECT
		SUM(bsl1.amount)
	FROM
		account_bank_statement AS bs1,
		account_bank_statement_line AS bsl1,
		grp_concepto_gasto_cc_viaticos AS concept1 
	WHERE
		bs1.id = bsl1.statement_id AND
		bsl1.concepto_id = concept1.id AND
		concept1.poner_dinero = True AND
		bsl1.statement_id = bs1.id AND
		bs1.journal_id = bs.journal_id AND
		bs1.date >= bs.date AND
		bs1.id != bs.id
	) AS reposition_in_amount,
	(SELECT
		bsl1.date
	FROM
		account_bank_statement AS bs1,
		account_bank_statement_line AS bsl1,
		grp_concepto_gasto_cc_viaticos AS concept1 
	WHERE
		bs1.id = bsl1.statement_id AND
		bsl1.concepto_id = concept1.id AND
		concept1.poner_dinero = True AND
		bsl1.statement_id = bs1.id AND
		bs1.journal_id = bs.journal_id AND
		bs1.date >= bs.date AND
		bs1.id != bs.id
	LIMIT 1
	) AS reposition_date,
	(SELECT
		bsl1.name
	FROM
		account_bank_statement AS bs1,
		account_bank_statement_line AS bsl1,
		grp_concepto_gasto_cc_viaticos AS concept1 
	WHERE
		bs1.id = bsl1.statement_id AND
		bsl1.concepto_id = concept1.id AND
		concept1.poner_dinero = True AND
		bsl1.statement_id = bs1.id AND
		bs1.journal_id = bs.journal_id AND
		bs1.date >= bs.date AND
		bs1.id != bs.id
	LIMIT 1
	) AS reposition_concept
FROM 
	account_voucher opi, 
	account_bank_statement bs 
WHERE 
	opi.opi = True AND 
	opi.bank_statement_id = bs.id
            )
        """)
