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

class grp_ejecucion_presupuestal_siif_documentos(models.Model):
    _name = 'grp.ejecucion.presupuestal.siif.documentos'
    _auto = False

    apg_id = fields.Many2one('grp.compras.apg', string='APG')
    afectacion_id = fields.Many2one('grp.afectacion', string=u"Afectación")
    name = fields.Char(string="Documento")
    fiscalyear_siif_id = fields.Many2one('account.fiscalyear', u"Año fiscal id")
    fy_name = fields.Char(u"Año fiscal")
    inciso_siif_id = fields.Many2one('grp.estruc_pres.inciso', string='Inciso id')
    inciso = fields.Char(string='Inciso')
    ue_siif_id = fields.Many2one('grp.estruc_pres.ue', string='Unidad ejecutora id')
    ue = fields.Char(string='Unidad ejecutora')
    odg = fields.Char(string="ODG")
    auxiliar = fields.Char(string="Auxiliar")
    fin = fields.Char(string="Financiamiento")
    programa = fields.Char(string="Programa")
    proyecto = fields.Char(string="Proyecto")
    moneda = fields.Char(string="Moneda")
    tc = fields.Char(string=u"Tipo de crédito")
    importe = fields.Integer(string="Importe")
    llave_presupuestal = fields.Char(string="Llave presupuestal")

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_ejecucion_presupuestal_siif_documentos')
        cr.execute("""
            create or replace view grp_ejecucion_presupuestal_siif_documentos as (
                select
                    llave.id as id,
                    apg.id as apg_id,
                    null as afectacion_id,
                    apg.name as name,
                    apg.fiscalyear_siif_id,
                    fy.code as fy_name,
                    apg.inciso_siif_id,
                    inciso.inciso,
                    apg.ue_siif_id,
                    ue.ue,
                    llave.odg,
                    llave.auxiliar,
                    llave.fin,
                    llave.programa,
                    llave.proyecto,
                    llave.mon as moneda,
                    llave.tc,
                    llave.importe,
                    fy.code || '-' || inciso.inciso || '-' || ue.ue || '-' || llave.odg || '-' || llave.auxiliar || '-' || llave.fin || '-' || llave.programa || '-' || llave.proyecto || '-' || llave.mon || '-' || llave.tc as llave_presupuestal
                from grp_compras_lineas_llavep llave, grp_compras_apg apg
                left join account_fiscalyear fy on apg.fiscalyear_siif_id = fy.id
                left join grp_estruc_pres_inciso inciso on apg.inciso_siif_id = inciso.id
                left join grp_estruc_pres_ue ue on apg.ue_siif_id = ue.id
                where apg.id = llave.apg_id

                UNION

                select
                    llave.id as id,
                    null as apg_id,
                    afectacion.id as afectacion_id,
                    afectacion.name as name,
                    afectacion.fiscalyear_siif_id,
                    fy.code as fy_name,
                    afectacion.inciso_siif_id,
                    inciso.inciso,
                    afectacion.ue_siif_id,
                    ue.ue,
                    llave.odg,
                    llave.auxiliar,
                    llave.fin,
                    llave.programa,
                    llave.proyecto,
                    llave.mon as moneda,
                    llave.tc,
                    llave.importe,
                    fy.code || '-' || inciso.inciso || '-' || ue.ue || '-' || llave.odg || '-' || llave.auxiliar || '-' || llave.fin || '-' || llave.programa || '-' || llave.proyecto || '-' || llave.mon || '-' || llave.tc as llave_presupuestal
                from grp_compras_lineas_llavep llave, grp_afectacion afectacion
                left join account_fiscalyear fy on afectacion.fiscalyear_siif_id = fy.id
                left join grp_estruc_pres_inciso inciso on afectacion.inciso_siif_id = inciso.id
                left join grp_estruc_pres_ue ue on afectacion.ue_siif_id = ue.id
                where afectacion.id = llave.afectacion_id
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
