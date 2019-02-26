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


class GrpRecaudacionReport(models.Model):
    _name = 'grp.recaudacion.report'
    _auto = False
    _description = u'Recaudación'

    box_id = fields.Many2one('grp.caja', string=u'Caja')
    user_uid = fields.Many2one('res.users', string=u'Responsable')
    product_id = fields.Many2one('product.product', u'Producto')
    voucher_id = fields.Many2one('account.voucher', u'Pago')
    invoice_id = fields.Many2one('account.invoice', 'Factura')
    partner_id = fields.Many2one('res.partner', 'Cliente')
    department_id = fields.Many2one('hr.department', string=u'Oficina')
    currency_id = fields.Many2one('res.currency', u'Moneda')
    operating_unit_id = fields.Many2one('operating.unit', u'UE')

    fecha = fields.Date(string=u'Fecha')
    open_date = fields.Datetime(string=u'Fecha de apertura')
    closing_date = fields.Datetime(string=u'Cerrado en')

    state = fields.Char(string=u'Estado')

    invoice_number = fields.Char(string=u'N° factura')
    payment_method = fields.Selection([('check', 'Cheque'),
                                       ('cash', 'Efectivo'),
                                       ('transfer', 'Transferencia')],
                                      string='Medio de pago')
    price_subtotal = fields.Float(string=u'Importe')
    companycurrency_amount = fields.Float(string=u'Importe en pesos')

    concept = fields.Char(string=u'Concepto')

    fecha_cobro = fields.Date('Fecha de cobro')

    def _subquery(self):
        return """SELECT
	t3.id AS box_id,
	t4.id AS user_uid,
	t2.product_id AS product_id,
	t2.voucher_id AS voucher_id,
	t2.invoice_id AS invoice_id,
	t6.department_id AS department_id,
	t6.partner_id AS partner_id,
    COALESCE((SELECT aj.currency FROM account_journal aj WHERE aj.id = t8.journal_id),(SELECT rc.currency_id FROM res_company rc WHERE rc.id = t8.company_id)) AS currency_id,
	t2.operating_unit_id AS operating_unit_id,
	t6.date_invoice AS fecha,
	t1.open_date AS open_date,
	t1.closing_date AS closing_date,
	t6.fecha_pago AS fecha_cobro,
	t1.state AS state,
	t6.number AS invoice_number,
	t8.payment_method AS payment_method,
	t2.price_subtotal AS price_subtotal,
	t2.companycurrency_amount AS companycurrency_amount,
	t5.name_template AS concept,
	1 AS doc_type
FROM 
	grp_caja_recaudadora_tesoreria t1
	INNER JOIN grp_caja_recaudadora_tesoreria_line t2 ON t1.id = t2.caja_recaudadora_id
	INNER JOIN grp_caja t3 ON t1.box_id = t3.id
	LEFT JOIN res_users t4 ON t1.user_uid = t4.id
	LEFT JOIN product_product t5 ON t2.product_id = t5.id
	LEFT JOIN account_invoice t6 ON t2.invoice_id = t6.id
	LEFT JOIN account_voucher t8 ON t2.voucher_id = t8.id
WHERE
	t2.apertura_recibo = False AND t2.type = 'details' AND
	t2.remove_transaction = False"""

    def _query(self):
        return """
            SELECT 
            query1.*, 
            ROW_NUMBER() OVER(ORDER BY doc_type) as id
            FROM (%s) AS query1
        """ % self._subquery()



    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_recaudacion_report')
        cr.execute("""
            CREATE OR replace VIEW grp_recaudacion_report AS (
            %s
            )
        """ % self._query())
