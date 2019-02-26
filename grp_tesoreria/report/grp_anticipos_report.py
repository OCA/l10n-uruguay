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

SOLICITUD_STATE = [('borrador', u'Borrador'),
                 ('en_aprobacion', u'En Aprobación'),
                 ('aprobado', u'Aprobado'),
                 ('en_autorizacion', u'En autorización'),
                 ('autorizado', u'Autorizado'),
                 ('rechazado', u'Rechazado'),
                 ('cancelado', u'Cancelado ')
                 ]

ANTICIPO_STATE = [('draft', u'Borrador'),
                 ('confirm', u'Confirmado'),
                 ('issue', u'Emitido'),
                 ('proforma', u'Pro-forma'),
                 ('posted', u'Contabilizado'),
                 ('pagado', u'Pagado'),
                 ('cancel', u'Cancelado ')
                 ]

RENDICION_STATE = [('draft', u'Borrador'),
                   ('confirm', u'En Aprobación'),
                   ('aprobado', u'Aprobado'),
                   ('en_autorizacion', u'En Autorización'),
                   ('en_financiero', u'En Financiero'),
                   ('autorizado', u'Autorizado'),
                   ('paid', u'Pagado'),
                   ('cancelled', u'Rechazado '),
                   ('cancelado', u'Cancelado ')
                 ]

class GrpAnticiposReport(models.Model):
    _name = 'grp.anticipos.report'
    _auto = False
    _description = u'Reporte de anticipos de fondo'

    solicitud_anticipo_id = fields.Many2one('grp.solicitud.anticipos.fondos', string=u'Solicitud de anticipo')
    anticipo_fondo_id = fields.Many2one('account.voucher', string=u'Anticipo de fondo')
    rendicion_anticipo_id = fields.Many2one('hr.expense.expense', string=u'Rendición de anticipo')
    devolucion_anticipo_id = fields.Many2one('account.voucher', string=u'Devolución de anticipo')

    sa_nro_solicitud = fields.Char(string=u'Nro. solicitud anticipo')
    sa_user_uid = fields.Many2one('res.users', string=u'Solicitante')
    sa_fecha_ingreso = fields.Datetime(string=u'Fecha de ingreso')
    sa_aprobador_id = fields.Many2one('res.users', string=u'Aprobado por')
    sa_operating_unit_id = fields.Many2one('operating.unit', string=u'Unidad ejecutora')
    sa_currency_id = fields.Many2one('res.currency', string=u'Moneda')
    sa_state = fields.Selection(SOLICITUD_STATE, u'Estado de solicitud')
    sa_amount_total= fields.Float(u'Total solicitud')

    af_number = fields.Char(string=u'Nro. pago solicitud')
    af_fecha_aprobacion_pago = fields.Date(u'Fecha aprobación de pago')
    af_date = fields.Date(u'Fecha anticipo')
    af_state = fields.Selection(ANTICIPO_STATE, u'Estado de anticipo')

    ra_sequence = fields.Char(string=u'Nro. Rendición anticipo')
    ra_entry_date = fields.Date(u'Fecha rendición')
    ra_name = fields.Char(string=u'Descripción')
    ra_amount = fields.Float(u'Total rendición')
    ra_diferencia = fields.Float(u'Diferencia')
    ra_state = fields.Selection(RENDICION_STATE, u'Estado de anticipo')

    da_number = fields.Char(string=u'Nro. pago rendición')
    da_fecha_aprobacion_pago = fields.Date(u'Fecha aprobación de pago de rendición')
    da_date = fields.Date(u'Fecha devolución')
    da_state = fields.Selection(ANTICIPO_STATE, u'Estado de devolución')



    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_anticipos_report')
        cr.execute("""
            CREATE OR replace VIEW grp_anticipos_report AS (
            SELECT 
	sa.id AS id,
	sa.id AS solicitud_anticipo_id,
	af.id AS anticipo_fondo_id,
	ra.id AS rendicion_anticipo_id,
	da.id AS devolucion_anticipo_id,
	sa.name AS sa_nro_solicitud,
	sa.user_uid AS sa_user_uid,
	sa.fecha_ingreso AS sa_fecha_ingreso,
	sa.aprobador_id AS sa_aprobador_id,
	sa.operating_unit_id AS sa_operating_unit_id,
	sa.currency_id AS sa_currency_id,
	sa.state AS sa_state,
	(SELECT SUM(amount) FROM grp_informacion_solicitud sal WHERE sal.solicitud_id = sa.id) AS sa_amount_total,
	af.number AS af_number,
	af.fecha_aprobacion_pago AS af_fecha_aprobacion_pago,
	af.date AS af_date,
	af.state AS af_state,
	ra.x_sequence AS ra_sequence,
	ra.entry_date AS ra_entry_date,
	ra.name AS ra_name,
	ra.amount AS ra_amount,
	ra.amount - ra.adelanto_anticipo AS ra_diferencia,
	ra.state AS ra_state,
	da.number AS da_number,
	da.fecha_aprobacion_pago AS da_fecha_aprobacion_pago,
	da.date AS da_date,
	da.state AS da_state
FROM
	grp_solicitud_anticipos_fondos sa LEFT JOIN
	(SELECT * FROM account_voucher WHERE type = 'payment') af ON af.solicitud_anticipos_id = sa.id LEFT JOIN
	hr_expense_expense ra ON ra.solicitud_anticipos_id = sa.id LEFT JOIN
	(SELECT * FROM account_voucher WHERE type = 'sale') da ON da.solicitud_anticipos_id = sa.id AND da.rendicion_anticipos_id = ra.id
            )
        """)
