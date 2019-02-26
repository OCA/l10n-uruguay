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

from openerp import fields, models, api, exceptions, _
from openerp import tools
from openerp.tools.safe_eval import safe_eval as eval

class grp_ejecucion_presupuestal_siif(models.Model):
    _name = 'grp.ejecucion.presupuestal.siif'
    _auto = False

    fy_name = fields.Char(u"Año fiscal")
    inciso = fields.Char(string='Inciso')
    ue = fields.Char(string='Unidad ejecutora')
    objeto_gasto = fields.Char(string="ODG")
    auxiliar = fields.Char(string="Auxiliar")
    financiamiento = fields.Char(string="Financiamiento")
    programa = fields.Char(string="Programa")
    proyecto = fields.Char(string="Proyecto")
    moneda = fields.Char(string="Moneda")
    tipo_credito = fields.Char(string=u"Tipo de crédito")
    credito_presupuestal = fields.Integer(string=u"Crédito presupuestal")
    importe = fields.Integer(string="Importe a afectar")
    importe_comprometer = fields.Integer(string="Importe a comprometer")
    saldo = fields.Integer(string=u"Saldo crédito disponible")
    llave_presupuestal = fields.Char(string="Llave presupuestal")

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_ejecucion_presupuestal_siif')
        cr.execute("""
            create or replace view grp_ejecucion_presupuestal_siif as (
                select
                    linea.id as id,
                    fy.code as fy_name,
                    pres.inciso,
                    linea.ue,
                    linea.objeto_gasto,
                    linea.auxiliar,
                    linea.financiamiento,
                    linea.programa,
                    linea.proyecto,
                    linea.moneda,
                    linea.tipo_credito,
                    fy.code || '-' || pres.inciso || '-' || linea.ue || '-' || linea.objeto_gasto || '-' || linea.auxiliar || '-' || linea.financiamiento || '-' || linea.programa || '-' || linea.proyecto || '-' || linea.moneda || '-' || linea.tipo_credito as llave_presupuestal,
                    linea.monto + linea.ajuste as credito_presupuestal,
                    (select COALESCE(sum(llave.importe),0) from grp_compras_lineas_llavep llave, grp_afectacion afectacion, grp_estruc_pres_inciso inciso, grp_estruc_pres_ue ue
                    where afectacion.id = llave.afectacion_id
                    and afectacion.fiscalyear_siif_id = fy.id
                    and afectacion.inciso_siif_id = inciso.id
                    and inciso.inciso = pres.inciso
                    and ue.ue = linea.ue
                    and afectacion.ue_siif_id = ue.id
                    and llave.odg = linea.objeto_gasto
                    and llave.auxiliar = linea.auxiliar
                    and llave.fin = linea.financiamiento
                    and llave.programa = linea.programa
                    and llave.proyecto = linea.proyecto
                    and llave.mon = linea.moneda
                    and llave.tc = linea.tipo_credito
                    and afectacion.state <> 'cancel'
                    ) +
                    (select COALESCE(sum(llave.importe),0) from grp_compras_lineas_llavep llave, grp_compras_apg apg, grp_estruc_pres_inciso inciso, grp_estruc_pres_ue ue
                    where apg.id = llave.apg_id
                    and apg.fiscalyear_siif_id = fy.id
                    and apg.inciso_siif_id = inciso.id
                    and inciso.inciso = pres.inciso
                    and ue.ue = linea.ue
                    and apg.ue_siif_id = ue.id
                    and llave.odg = linea.objeto_gasto
                    and llave.auxiliar = linea.auxiliar
                    and llave.fin = linea.financiamiento
                    and llave.programa = linea.programa
                    and llave.proyecto = linea.proyecto
                    and llave.mon = linea.moneda
                    and llave.tc = linea.tipo_credito
                    and apg.state not in ('desafectado','anulada')
                    )as importe,
                    linea.monto + linea.ajuste - (
                    (select COALESCE(sum(llave.importe),0) from grp_compras_lineas_llavep llave, grp_afectacion afectacion, grp_estruc_pres_inciso inciso, grp_estruc_pres_ue ue
                    where afectacion.id = llave.afectacion_id
                    and afectacion.fiscalyear_siif_id = fy.id
                    and afectacion.inciso_siif_id = inciso.id
                    and inciso.inciso = pres.inciso
                    and ue.ue = linea.ue
                    and afectacion.ue_siif_id = ue.id
                    and llave.odg = linea.objeto_gasto
                    and llave.auxiliar = linea.auxiliar
                    and llave.fin = linea.financiamiento
                    and llave.programa = linea.programa
                    and llave.proyecto = linea.proyecto
                    and llave.mon = linea.moneda
                    and llave.tc = linea.tipo_credito
                    and afectacion.state <> 'cancel'
                    ) +
                    (select COALESCE(sum(llave.importe),0) from grp_compras_lineas_llavep llave, grp_compras_apg apg, grp_estruc_pres_inciso inciso, grp_estruc_pres_ue ue
                    where apg.id = llave.apg_id
                    and apg.fiscalyear_siif_id = fy.id
                    and apg.inciso_siif_id = inciso.id
                    and inciso.inciso = pres.inciso
                    and ue.ue = linea.ue
                    and apg.ue_siif_id = ue.id
                    and llave.odg = linea.objeto_gasto
                    and llave.auxiliar = linea.auxiliar
                    and llave.fin = linea.financiamiento
                    and llave.programa = linea.programa
                    and llave.proyecto = linea.proyecto
                    and llave.mon = linea.moneda
                    and llave.tc = linea.tipo_credito
                    and apg.state not in ('desafectado','anulada')
                    ))as saldo,
                    (select COALESCE(sum(llave.importe),0) from grp_compras_lineas_llavep llave, grp_afectacion afectacion, grp_compromiso compromiso, grp_estruc_pres_inciso inciso, grp_estruc_pres_ue ue
                    where compromiso.id = llave.compromiso_id
                    and afectacion.id = compromiso.afectacion_id
                    and afectacion.fiscalyear_siif_id = fy.id
                    and afectacion.inciso_siif_id = inciso.id
                    and inciso.inciso = pres.inciso
                    and ue.ue = linea.ue
                    and afectacion.ue_siif_id = ue.id
                    and llave.odg = linea.objeto_gasto
                    and llave.auxiliar = linea.auxiliar
                    and llave.fin = linea.financiamiento
                    and llave.programa = linea.programa
                    and llave.proyecto = linea.proyecto
                    and llave.mon = linea.moneda
                    and llave.tc = linea.tipo_credito
                    and afectacion.state <> 'cancel'
                    and compromiso.state not in ('cancel','anulada_siif')
                    ) +
                    (select COALESCE(sum(llave.importe),0) from grp_cotizaciones_compromiso_proveedor_llavep llave, grp_compras_apg apg, grp_cotizaciones_compromiso_proveedor compromiso_proveedor, grp_estruc_pres_inciso inciso, grp_estruc_pres_ue ue
                    where compromiso_proveedor.id = llave.compromiso_id
                    and apg.id = compromiso_proveedor.apg_id
                    and apg.fiscalyear_siif_id = fy.id
                    and apg.inciso_siif_id = inciso.id
                    and inciso.inciso = pres.inciso
                    and ue.ue = linea.ue
                    and apg.ue_siif_id = ue.id
                    and llave.odg = linea.objeto_gasto
                    and llave.auxiliar = linea.auxiliar
                    and llave.fin = linea.financiamiento
                    and llave.programa = linea.programa
                    and llave.proyecto = linea.proyecto
                    and llave.mon = linea.moneda
                    and llave.tc = linea.tipo_credito
                    and apg.state not in ('desafectado','anulada')
                    and compromiso_proveedor.state not in ('recalled','anulado')
                    ) as importe_comprometer
                from presupuesto_linea linea,
                     presupuesto_presupuesto pres,
                     account_fiscalyear fy
                where linea.budget_id = pres.id
                and pres.fiscal_year = fy.id
            )
        """)

    # def open_document(self, cr, uid, ids, context=None):
    #     for rec in self.browse(cr, uid, ids):
    #         mod_obj = self.pool.get('ir.model.data')
    #         if rec.tipo_documento == 'account_invoice':
    #             res = mod_obj.get_object_reference(cr, uid, 'grp_factura_siif',
    #                                                'invoice_siif_retention_supplier_form_inherit')
    #             models = 'account.invoice'
    #             res_id = res and res[1] or False
    #             ctx = dict(context)
    #             invoice_id = rec.id_documento
    #             return {
    #                 'name': "Facturas de proveedor",
    #                 'view_mode': 'form',
    #                 'view_id': res_id,
    #                 'view_type': 'form',
    #                 'res_model': models,
    #                 'type': 'ir.actions.act_window',
    #                 'target': 'current',
    #                 'res_id': invoice_id,
    #                 'context': ctx,
    #             }
    #         elif rec.tipo_documento == 'account_invoice_fr':
    #             res = mod_obj.get_object_reference(cr, uid, 'grp_factura_siif',
    #                                                'invoice_siif_retention_supplier_form_inherit')
    #             models = 'account.invoice'
    #             res_id = res and res[1] or False
    #             ctx = dict(context)
    #             invoice_id = rec.id_documento
    #             return {
    #                 'name': "Facturas de fondo rotatorio",
    #                 'view_mode': 'form',
    #                 'view_id': res_id,
    #                 'view_type': 'form',
    #                 'res_model': models,
    #                 'type': 'ir.actions.act_window',
    #                 'target': 'current',
    #                 'res_id': invoice_id,
    #                 'context': ctx,
    #             }
    #         elif rec.tipo_documento == 'account_invoice_refund_fr':
    #             res = mod_obj.get_object_reference(cr, uid, 'grp_factura_siif',
    #                                                'view_account_form_credit_note')
    #             models = 'account.invoice'
    #             res_id = res and res[1] or False
    #             ctx = dict(context)
    #             invoice_id = rec.id_documento
    #             return {
    #                 'name': u"Nota de Crédito fondo rotatorio",
    #                 'view_mode': 'form',
    #                 'view_id': res_id,
    #                 'view_type': 'form',
    #                 'res_model': models,
    #                 'type': 'ir.actions.act_window',
    #                 'target': 'current',
    #                 'res_id': invoice_id,
    #                 'context': ctx,
    #             }
    #         elif rec.tipo_documento in ['hr_expense','hr_expense_anticipo']:
    #             models = 'hr.expense.expense'
    #             ctx = dict(context)
    #             hr_expense_id = rec.id_documento
    #             expense_id = self.pool.get('hr.expense.expense').browse(cr,uid,hr_expense_id)
    #             if expense_id.doc_type == u'rendicion_anticipo':
    #                 res = mod_obj.get_object_reference(cr, uid, 'grp_tesoreria', 'view_grp_rendicion_anticipo_form1')
    #             else:
    #                 res = mod_obj.get_object_reference(cr, uid, 'grp_hr_expense', 'grp_view_expenses_form')
    #             res_id = res and res[1] or False
    #             return {
    #                 'name': "Gastos",
    #                 'view_mode': 'form',
    #                 'view_id': res_id,
    #                 'view_type': 'form',
    #                 'res_model': models,
    #                 'type': 'ir.actions.act_window',
    #                 'target': 'current',
    #                 'res_id': hr_expense_id,
    #                 'context': ctx,
    #             }
    #         elif rec.tipo_documento == 'bank_statement':
    #             res = mod_obj.get_object_reference(cr, uid, 'facturas_uy', 'grp_view_bank_statement_form2')
    #             models = 'account.bank.statement'
    #             res_id = res and res[1] or False
    #             ctx = dict(context)
    #             bank_statement_line = self.pool.get('account.bank.statement.line').browse(cr, uid, rec.id_documento,
    #                                                                                       context)
    #             bank_statement_id = bank_statement_line.statement_id.id
    #             return {
    #                 'name': "Registros de caja",
    #                 'view_mode': 'form',
    #                 'view_id': res_id,
    #                 'view_type': 'form',
    #                 'res_model': models,
    #                 'type': 'ir.actions.act_window',
    #                 'target': 'current',
    #                 'res_id': bank_statement_id,
    #                 'context': ctx,
    #             }
    #         elif rec.tipo_documento == 'caja_chica':
    #             res = mod_obj.get_object_reference(cr, uid, 'grp_tesoreria', 'view_grp_caja_chica_line_form2')
    #             res_id = res and res[1] or False
    #             ctx = dict(context)
    #             return {
    #                 'name': "Registros de caja",
    #                 'view_mode': 'form',
    #                 'view_id': res_id,
    #                 'view_type': 'form',
    #                 'res_model': 'grp.caja.chica.tesoreria.line',
    #                 'type': 'ir.actions.act_window',
    #                 'target': 'current',
    #                 'res_id': rec.id_documento,
    #                 'context': ctx,
    #             }
    #         return True
