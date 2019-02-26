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

LISTA_ESTADOS_SOLICITUD = [
    ('borrador', u'Borrador'),
    ('en_aprobacion', u'En aprobación'),
    ('aprobado', u'Aprobado'),
    ('en_autorizacion', u'En autorización'),
    ('en_financiero', u'En financiero'),
    ('autorizado', u'Autorizado'),
    ('rechazado', u'Rechazado'),
    ('cancelado', u'Cancelado'),
]

LISTA_ESTADOS_RENDICION = [('draft', 'Borrador'),
          ('confirm', u'En Aprobación'),
          ('en_autorizacion', u'En Autorización'),
          ('en_financiero', u'En Financiero'),
          ('autorizado', 'Autorizado'),
          ('paid', 'Pagado'),
          ('cancelled', 'Rechazado'),
          ('cancelado', 'Cancelado'),
          ]

LISTA_ESTADOS_DEVOLUCION = [('draft', 'Borrador'),
          ('posted', 'Contabilizado'),
          ('cancel', 'Cancelado'),
          ('pagado', 'Pagado'),
          ]

class GrpViaticosReport(models.Model):
    _name = 'grp.viaticos.report'
    _auto = False
    _description = u'Reporte de viáticos'

    operating_unit_id = fields.Many2one('operating.unit', string=u'Unidad ejecutora')
    solicitud_viatico_id = fields.Many2one('grp.solicitud.viaticos', string=u'Solicitud de viático')
    rendicion_viatico_id = fields.Many2one('hr.expense.expense', string=u'Rendición de viático')
    devolucion_viatico_id = fields.Many2one('account.voucher', string=u'Devolución de viático')
    adelanto_solicitud_viatico_id = fields.Many2one('account.voucher', string=u'Adelanto Solicitud de viático')
    adelanto_rendicion_viatico_id = fields.Many2one('account.voucher', string=u'Adelanto Rendiciión de viático')

    sv_solicitante_id = fields.Many2one('res.users', string=u'Solicitante')
    sv_name = fields.Char(string=u'Nº Solicitud de Viajes')
    sv_fecha_desde = fields.Date(string=u'Solicitud Fecha Desde')
    sv_fecha_hasta = fields.Date(string=u'Solicitud Fecha Hasta')
    sv_state = fields.Selection(selection=LISTA_ESTADOS_SOLICITUD, string='Estado de Solicitud')
    sv_lleva_adelanto = fields.Boolean('Lleva adelanto')
    sv_total = fields.Float(string=u'Total de Solicitud', compute='_compute_nostore_fields', multi='nostore_fields')
    sv_paid_date = fields.Date('Fecha de pago de la solicitud', related='solicitud_viatico_id.paid_date', readonly=True)

    rv_sequence = fields.Char(u'Nº Rendición')
    rv_adelanto = fields.Float('Adelanto de Viáticos')
    rv_state = fields.Selection(LISTA_ESTADOS_RENDICION, 'Estado de Rendición')
    rv_currency_id = fields.Many2one('res.currency',u'Moneda')
    rv_amount = fields.Float(string=u'Total de Rendición')
    rv_entry_date = fields.Date(string=u'Fecha de rendición')
    rv_fecha_desde = fields.Date(string=u'Rendición Fecha Desde')
    rv_fecha_hasta = fields.Date(string=u'Rendición Fecha Hasta')
    rv_diferencia = fields.Float(string=u'Diferencia', compute='_compute_nostore_fields', multi='nostore_fields')

    dv_number = fields.Char(string=u'Nº Devolución de viático')
    dv_fecha = fields.Date(string=u'Fecha de Devolución')
    dv_state = fields.Selection(LISTA_ESTADOS_DEVOLUCION, 'Estado de devolución')
    dv_amount = fields.Float(u'Monto de la Devolución')

    adelanto_solicitud_number = fields.Char(string=u'Nº Adelanto de viático de la Solicitud')
    adelanto_solicitud_fecha = fields.Date(string=u'Fecha de adelanto de la Solicitud')
    adelanto_solicitud_state = fields.Selection(LISTA_ESTADOS_DEVOLUCION, u'Estado de adelanto de la Solicitud')
    adelanto_solicitud_amount = fields.Float(u'Monto de adelanto de la Solicitud')

    adelanto_rendicion_number = fields.Char(string=u'Nº Adelanto de viático de la Rendición')
    adelanto_rendicion_fecha = fields.Date(string=u'Fecha de adelanto de la Rendición')
    adelanto_rendicion_state = fields.Selection(LISTA_ESTADOS_DEVOLUCION, u'Estado de adelanto de la Rendición')
    adelanto_rendicion_amount = fields.Float(u'Monto de adelanto de la Rendición')

    @api.one
    def _compute_nostore_fields(self):
        sudo_self = self.suspend_security()
        total = sum(sudo_self.solicitud_viatico_id.lineas_ids.mapped('valor'))
        if sudo_self.solicitud_viatico_id.currency_id.name == 'USD' and sudo_self.solicitud_viatico_id.tipo == 'interior' and sudo_self.solicitud_viatico_id.tipo_cambio != 0:
            self.sv_total = total / sudo_self.solicitud_viatico_id.tipo_cambio
        else:
            self.sv_total = total
        #rv_diferencia
        self.rv_diferencia = sudo_self.rendicion_viatico_id.diferencia


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_viaticos_report')
        cr.execute("""
            CREATE OR replace VIEW grp_viaticos_report AS (
            SELECT *,ROW_NUMBER() OVER (ORDER BY rv_solicitud_viatico_id) AS id FROM
(SELECT * FROM
(
SELECT * FROM
(SELECT
  sv.id solicitud_viatico_id,
  sv.solicitante_id sv_solicitante_id,
  sv.name sv_name,
  sv.fecha_desde sv_fecha_desde,
  sv.fecha_hasta sv_fecha_hasta,
  sv.state sv_state,
	sv.lleva_adelanto sv_lleva_adelanto,
	--sv.paid_date,
  sv.operating_unit_id operating_unit_id
FROM
  public.grp_solicitud_viaticos sv) sv
LEFT JOIN
(SELECT
  rv.id rendicion_viatico_id,
  rv.x_sequence rv_sequence,
  rv.adelanto rv_adelanto,
  rv.amount rv_amount,
  rv.state rv_state,
  rv.currency_id rv_currency_id,
  rv.solicitud_viatico_id rv_solicitud_viatico_id,
	rv.entry_date rv_entry_date,
	rv.fecha_desde rv_fecha_desde,
	rv.fecha_hasta rv_fecha_hasta
				--rv.diferencia rv_diferencia
FROM
  hr_expense_expense as rv
WHERE rv.state NOT IN ('cancelado','cancelled') AND rv.doc_type = 'rendicion_viatico') rv
ON rv.rv_solicitud_viatico_id = sv.solicitud_viatico_id
							UNION ALL
SELECT
  NULL solicitud_viatico_id,
  NULL sv_solicitante_id,
  NULL sv_name,
  NULL sv_fecha_desde,
  NULL sv_fecha_hasta,
  NULL sv_state,
	False lleva_adelanto,
	--NULL paid_date,
  rv.operating_unit_id operating_unit_id,
  rv.id rendicion_viatico_id,
  rv.x_sequence rv_sequence,
  rv.adelanto rv_adelanto,
  rv.amount rv_amount,
  rv.state rv_state,
  rv.currency_id rv_currency_id,
  rv.solicitud_viatico_id rv_solicitud_viatico_id,
 	rv.entry_date rv_entry_date,
 	rv.fecha_desde rv_fecha_desde,
 	rv.fecha_hasta rv_fecha_hasta
			 --rv.diferencia rv_diferencia
FROM
  hr_expense_expense AS rv
WHERE solicitud_viatico_id IS NULL AND rv.state NOT IN ('cancelado','cancelled') AND rv.doc_type = 'rendicion_viatico'
) AS main_query
LEFT JOIN
(
SELECT
number dv_number,
date dv_fecha,
state dv_state,
amount dv_amount,
rendicion_viaticos_id dv_rendicion_viaticos_id
FROM
account_voucher WHERE type = 'sale') AS dv
ON main_query.rendicion_viatico_id = dv.dv_rendicion_viaticos_id
LEFT JOIN
(
SELECT
id adelanto_solicitud_viatico_id,
number adelanto_solicitud_number,
date adelanto_solicitud_fecha,
state adelanto_solicitud_state,
amount adelanto_solicitud_amount,
solicitud_viatico_id adelanto_solicitud_solicitud_viatico_id
FROM
account_voucher
WHERE
		account_voucher.rendicion_viaticos_id IS NULL
) AS avs
ON main_query.solicitud_viatico_id = avs.adelanto_solicitud_solicitud_viatico_id
LEFT JOIN
(
SELECT
id adelanto_rendicion_viatico_id,
number adelanto_rendicion_number,
date adelanto_rendicion_fecha,
state adelanto_rendicion_state,
amount adelanto_rendicion_amount,
rendicion_viaticos_id adelanto_rendicion_rendicion_viaticos_id
FROM
account_voucher
WHERE
		account_voucher.rendicion_viaticos_id IS NOT NULL AND
		account_voucher.type = 'payment'
) AS avr
ON main_query.rendicion_viatico_id = avr.adelanto_rendicion_rendicion_viaticos_id
) query

	)
        """)
