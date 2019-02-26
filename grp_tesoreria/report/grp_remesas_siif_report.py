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

class GrpRemesasSiif(models.Model):
    _name = 'grp.remesas.siif.report'
    _auto = False
    _description = u'Reporte de Remesas SIIF'

    @api.depends('caja_recaudadora_id', 'boleto_siif_id', 'remesa_id')
    def _get_unidad_ejecutora(self):
        for rec in self:
            ue = False
            if rec.caja_recaudadora_id.id:
                if rec.caja_recaudadora_id.cash_shipment_ids and \
                        rec.caja_recaudadora_id.cash_shipment_ids[0].operating_unit_id:
                    ue = rec.caja_recaudadora_id.cash_shipment_ids[0].operating_unit_id
                elif rec.caja_recaudadora_id.voucher_details_ids:
                    ue = rec.caja_recaudadora_id.voucher_details_ids[0].operating_unit_id
            elif rec.boleto_siif_id.id:
                if rec.boleto_siif_id.product_ue_shipment_ids and \
                        rec.boleto_siif_id.product_ue_shipment_ids[0].operating_unit_id:
                    ue = rec.boleto_siif_id.product_ue_shipment_ids[0].operating_unit_id
                elif rec.boleto_siif_id.voucher_details_ids:
                    ue = rec.boleto_siif_id.voucher_details_ids[0].operating_unit_id
            elif rec.remesa_id.id:
                if rec.type in ['rem_check']:
                    if rec.remesa_id.check_shipment_ids and \
                            rec.remesa_id.check_shipment_ids[0].operating_unit_id:
                        ue = rec.remesa_id.check_shipment_ids[0].operating_unit_id
                    elif rec.remesa_id.box_details_ids:
                        ue = rec.remesa_id.box_details_ids[0].operating_unit_id
                elif rec.type in ['rem_cash']:
                    if rec.remesa_id.cash_shipment_ids and \
                            rec.remesa_id.cash_shipment_ids[0].operating_unit_id:
                        ue = rec.remesa_id.cash_shipment_ids[0].operating_unit_id
                    elif rec.remesa_id.box_details_ids:
                        ue = rec.remesa_id.box_details_ids[0].operating_unit_id
            rec.operating_unit_id = ue

    caja_recaudadora_id = fields.Many2one('grp.caja.recaudadora.tesoreria', 'Caja recaudadora')
    boleto_siif_id = fields.Many2one('grp.caja.recaudadora.tesoreria.boleto.siif', u'Boleto SIIF')
    remesa_id = fields.Many2one('grp.remesa', u'Remesa')
    date = fields.Date(u'Fecha')
    siff_ticket = fields.Char(string=u'Boleto SIIF')
    user_uid = fields.Many2one('res.users', string=u'Responsable')
    operating_unit_id = fields.Many2one('operating.unit', string=u'Unidad Ejecutora', compute='_get_unidad_ejecutora')
    name = fields.Char(string=u'Origen')
    type = fields.Selection([('cr_cash', u'Caja Recaudadora Efectivo'),
                              ('cr_check', u'Caja Recaudadora Cheque'),
                              ('boleto_siif', u'Boleto SIIF'),
                              ('rem_check', u'Remesa cheque'),
                              ('rem_cash', u'Remesa efectivo'),
                             ], u'Tipo')
    importe = fields.Float(u'Importe')



    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_remesas_siif_report')
        cr.execute("""
            CREATE OR replace VIEW grp_remesas_siif_report AS (
            SELECT ROW_NUMBER() OVER(ORDER BY type DESC) AS id, * FROM
(SELECT
    id as caja_recaudadora_id,
    0 as boleto_siif_id,
    0 as remesa_id,
	remittance_date AS date, 
	cash_shipment_siff_ticket AS siff_ticket, 
	user_uid,
	name,
	'cr_cash' AS type,
	cash_total_shipment as importe
FROM grp_caja_recaudadora_tesoreria rt WHERE cash_shipment_siff_ticket IS NOT NULL
UNION ALL
SELECT
    id as caja_recaudadora_id,
    0 as boleto_siif_id,
    0 as remesa_id,
	remittance_date AS date, 
	check_shipment_siff_ticket AS siff_ticket, 
	user_uid,
	name,
	'cr_check' AS type,
	check_total_shipment as importe
FROM grp_caja_recaudadora_tesoreria rt WHERE check_shipment_siff_ticket IS NOT NULL
UNION ALL
SELECT
    0 as caja_recaudadora_id,
    bs.id as boleto_siif_id,
    0 as remesa_id,
	date AS date, 
	cash_shipment_siff_ticket AS siff_ticket, 
	user_uid,
	'Boleto SIIF' AS name,
	'boleto_siif' AS type,
	total_shipment as importe
FROM grp_caja_recaudadora_tesoreria_boleto_siif bs WHERE cash_shipment_siff_ticket IS NOT NULL
UNION ALL
SELECT
    0 as caja_recaudadora_id,
    0 as boleto_siif_id,
    r.id as remesa_id,
	r.date AS date,
	r.check_shipment_siff_ticket AS siff_ticket,
	r.user_uid,
	'Preparar Remesa' AS name,
	'rem_check' AS type,
	r.check_total_shipment as importe
FROM grp_remesa r WHERE check_shipment_siff_ticket IS NOT NULL
UNION ALL
SELECT
    0 as caja_recaudadora_id,
    0 as boleto_siif_id,
    r.id as remesa_id,
	date AS date,
	cash_shipment_siff_ticket AS siff_ticket, 
	user_uid,
	'Preparar Remesa' AS name, 
	'rem_cash' AS type,
	r.cash_total_shipment as importe
FROM grp_remesa r WHERE cash_shipment_siff_ticket IS NOT NULL) AS main_query
            )
        """)
