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

LISTA_ESTADOS = [
    ('paid', 'Pagado'),
    ('confirm', 'Cerrado')
]


class grp_agrupar_fondo_rotarios(models.Model):
    _name = 'grp.agrupar.fondo.rotarios'
    _auto = False
    _order = 'id_documento desc, tipo_documento, id'

    tipo_documento = fields.Selection([('account_invoice_fr', 'Facturas de fondo rotatorio'),
                                       ('account_invoice_refund_fr', u'Nota de Crédito fondo rotatorio'),
                                       ('hr_expense_anticipo', u'Rendición de anticipo'),
                                       ('hr_expense', u'Rendición de viático'),
                                       ('hr_expense_v', 'Vales'),
                                       ('bank_statement', u'Líneas de Registros de caja'),
                                       ('caja_chica', u'Líneas de Caja efectivo'),
                                       ('hr_expense_a', u'Abonos')], 'Tipo de Documento', size=86,
                                      default='account_invoice_fr')
    proveedor = fields.Char(string='Proveedor')
    fecha_factura = fields.Date(string='Fecha factura')
    n_documento = fields.Char(string='N° documento')
    n_documento2 = fields.Char(string='N° documento 2')
    total = fields.Float(string='Total')
    estado = fields.Selection(LISTA_ESTADOS, 'Estado', size=86, readonly=True, default='paid')
    ue = fields.Char(string='UE')
    inciso = fields.Char(string='Inciso')
    id_documento = fields.Integer(string='Documento')
    journal_id = fields.Many2one('account.journal', 'Diario')
    operating_unit_id = fields.Many2one('operating.unit', 'Unidad ejecutora')
    fecha_pago = fields.Date('Fecha de pago', compute='_compute_fecha_pago', search='_search_fecha_pago')

    currency_id = fields.Many2one('res.currency', string=u'Moneda')
    company_id = fields.Many2one('res.company', string=u'Compañía')

    @api.multi
    def _get_fecha_pago(self):
        self = self.sudo()
        self.ensure_one()
        if self.tipo_documento == 'account_invoice_fr':
            payment_ids = self.env['account.invoice'].browse(self.id_documento).payment_ids
            if payment_ids:
                _fecha_pago = payment_ids[0].date
            else:
                _fecha_pago = False
        elif self.tipo_documento == 'bank_statement':
            _fecha_pago = self.env['account.bank.statement.line'].browse(self.id_documento).date or False
        elif self.tipo_documento in ['hr_expense', 'hr_expense_anticipo']:
            _fecha_pago = self.env['hr.expense.expense'].browse(self.id_documento).account_move_id.date or False
        elif self.tipo_documento == 'caja_chica':
            _fecha_pago = self.env['grp.caja.chica.tesoreria.line'].browse(self.id_documento).account_move_id.date or False
        else:
            _fecha_pago = False
        return _fecha_pago

    @api.one
    def _compute_fecha_pago(self):
        self.fecha_pago = self._get_fecha_pago()

    def _search_fecha_pago(self, operator, value):
        ids = []
        if operator == '=':
            operator = '=='
        for line in self.search([]):
            _fecha_pago = line._get_fecha_pago()
            if eval("'%s' %s '%s'" % (_fecha_pago,operator,value)):
                ids.append(line.id)
        return [('id', 'in', ids)]

    def _subquery(self):
        return """(select
                        'account_invoice_fr' as tipo_documento,
                        l.id as id_documento,
                        p.name as proveedor,
                        l.date_invoice as fecha_factura,
                        l.nro_factura_grp as n_documento,
                        l.amount_total as total,
                        l.state as estado,
                        ue.ue as ue,
                        i.inciso as inciso,
                        l.journal_id as journal_id,
                        l.operating_unit_id as operating_unit_id,
                        l.currency_id,
                        l.company_id,
                        '' as n_documento2
                    from
                        account_invoice l
                        left join res_partner p on (l.partner_id = p.id)
                        left join grp_estruc_pres_ue ue on (ue.id=l.ue_siif_id)
                        left join grp_estruc_pres_inciso i on (l.inciso_siif_id=i.id)
                        left join tipo_ejecucion_siif ej on (l.siif_tipo_ejecucion=ej.id)
                        where l.state = 'paid' and l.type = 'in_invoice' and l.doc_type in ('invoice','3en1_invoice') and ej.codigo = 'P' and fondo_rotarios <> True)
                    UNION
                    (select
                        'account_invoice_refund_fr' as tipo_documento,
                        l.id as id_documento,
                        p.name as proveedor,
                        l.date_invoice as fecha_factura,
                        l.nro_factura_grp as n_documento,
                        - l.amount_total as total,
                        l.state as estado,
                        ue.ue as ue,
                        i.inciso as inciso,
                        l.journal_id as journal_id,
                        l.operating_unit_id as operating_unit_id,
                        l.currency_id,
                        l.company_id,
                        '' as n_documento2
                    from
                        account_invoice l
                        left join res_partner p on (l.partner_id = p.id)
                        left join grp_estruc_pres_ue ue on (ue.id=l.ue_siif_id)
                        left join grp_estruc_pres_inciso i on (l.inciso_siif_id=i.id)
                        left join tipo_ejecucion_siif ej on (l.siif_tipo_ejecucion=ej.id)
                        where l.state = 'paid' and l.type = 'in_refund' and l.doc_type in ('invoice','3en1_invoice') and ej.codigo = 'P' and fondo_rotarios <> True)"""

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_agrupar_fondo_rotarios')
        cr.execute("""
            create or replace view grp_agrupar_fondo_rotarios as (
                select
                    ROW_NUMBER() OVER(ORDER BY tipo_documento) as id,
                    tipo_documento,
                    id_documento,
                    proveedor,
                    fecha_factura,
                    n_documento,
                    total,
                    estado,
                    ue,
                    inciso,
                    journal_id,
                    operating_unit_id,
                    COALESCE(currency_id,(SELECT currency_id FROM res_company WHERE id = company_id LIMIT 1)) currency_id,
                    company_id,
                    n_documento2
                from(
                    %s
                    UNION
                    (select rv.tipo_documento,rv.id_documento,rv.proveedor,rv.fecha_factura,rv.n_documento,rv.total,rv.estado,rv.ue,rv.inciso,rv.journal_id,rv.operating_unit_id,rv.currency_id,rv.company_id,sv.name n_documento2 FROM
(select
                        'hr_expense' as tipo_documento,
                        hee.id as id_documento,
                        hr.name_related as proveedor,
                        hee.date as fecha_factura,
                        hee.x_sequence as n_documento,
                        hee.amount as total,
                        hee.state as estado,
                        '' as ue,
                        '' as inciso,
                        hee.journal_id AS journal_id,
                        hee.operating_unit_id as operating_unit_id,
                        hee.currency_id,
                        hee.company_id,
                        '' as n_documento2,
                        hee.solicitud_viatico_id
                    from
                        hr_expense_expense hee
                        left join hr_employee hr on (hee.employee_id = hr.id)
                        where hee.state = 'paid' and hee.doc_type = 'rendicion_viatico' and fondo_rotarios <> True) AS rv

                        left join grp_solicitud_viaticos sv ON rv.solicitud_viatico_id = sv.id)
                    UNION
                    (select ra.tipo_documento,ra.id_documento,ra.proveedor,ra.fecha_factura,ra.n_documento,ra.total,ra.estado,ra.ue,ra.inciso,ra.journal_id,ra.operating_unit_id,ra.currency_id,ra.company_id,sa.name n_documento2 FROM
(select
                        'hr_expense_anticipo' as tipo_documento,
                        hee.id as id_documento,
                        hr.name_related as proveedor,
                        hee.date as fecha_factura,
                        hee.x_sequence as n_documento,
                        hee.amount as total,
                        hee.state as estado,
                        '' as ue,
                        '' as inciso,
                        hee.journal_id AS journal_id,
                        hee.operating_unit_id as operating_unit_id,
                        hee.currency_id,
                        hee.company_id,
                        hee.solicitud_anticipos_id
                    from
                        hr_expense_expense hee
                        left join hr_employee hr on (hee.employee_id = hr.id)
                        where hee.state = 'paid' and hee.doc_type = 'rendicion_anticipo' and fondo_rotarios <> True) AS ra
                        left join grp_solicitud_anticipos_fondos sa ON ra.solicitud_anticipos_id = sa.id)
                    UNION
                    (select
                        'bank_statement' as tipo_documento,
                        abs.id as id_documento,
                        r.name as proveedor,
                        abs.date as fecha_factura,
                        abs.name as n_documento,
                        - abs.amount as total,
                        ab.state as estado,
                        ou.unidad_ejecutora as ue,
                        rc.inciso as inciso,
                        abs.journal_id as journal_id,
                        j.operating_unit_id as operating_unit_id,
                        j.currency,
                        j.company_id,
                        ab.name as n_documento2
                    from
                        account_bank_statement_line abs
                        left join res_partner r on (abs.partner_id = r.id)
                        left join account_bank_statement ab on (ab.id = abs.statement_id)
                        left join account_journal j on (abs.journal_id = j.id)
                        left join grp_concepto_gasto_cc_viaticos g on (abs.concepto_id = g.id)
                        left join operating_unit ou on (j.operating_unit_id=ou.id)
                        left join res_company rc on (ab.company_id=rc.id)
                        where ab.state = 'confirm' and j.type= 'cash' and fondo_rotarios <> True and g.a_rendir = true
                    )
                    UNION
                    (select
                        'caja_chica' as tipo_documento,
                        cctl.id as id_documento,
                        p.name as proveedor,
                        cctl.date as fecha_factura,
                        cctl.ref as n_documento,  -- TODO: take ref here?
                        - cctl.amount as total,
                        'confirm' as estado,
                        COALESCE(ou.unidad_ejecutora, ou2.unidad_ejecutora) as ue,
                        rc.inciso as inciso,
                        cct.journal_id as journal_id,
                        COALESCE(ccme.operating_unit_id, j.operating_unit_id) as operating_unit_id,
                        j.currency,
                        j.company_id,
                        '' as n_documento2
                    from
                        grp_caja_chica_tesoreria_line cctl
                        inner join grp_caja_chica_tesoreria cct ON (cctl.caja_chica_id=cct.id)
                        inner join grp_concepto_gasto_cc_viaticos g on (cctl.concept_cc_id = g.id)
                        left join grp_caja_chica_movimiento_efectivo ccme on (cctl.catch_mov_id = ccme.id)
                        left join res_partner p on (cctl.partner_id = p.id)
                        left join res_company rc on (cct.company_id=rc.id)
                        left join account_journal j on (cct.journal_id = j.id)
                        left join operating_unit ou on (ccme.operating_unit_id=ou.id)
                        left join operating_unit ou2 on (j.operating_unit_id=ou2.id)
                    where cct.state = 'check' and j.type= 'cash' and g.a_rendir = true and cctl.fondo_rotario <> true
                    )
                ) as fr
            )
        """ % self._subquery())

    def open_document(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids):
            mod_obj = self.pool.get('ir.model.data')
            if rec.tipo_documento == 'account_invoice':
                res = mod_obj.get_object_reference(cr, uid, 'grp_factura_siif',
                                                   'invoice_siif_retention_supplier_form_inherit')
                models = 'account.invoice'
                res_id = res and res[1] or False
                ctx = dict(context)
                invoice_id = rec.id_documento
                return {
                    'name': "Facturas de proveedor",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': models,
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': invoice_id,
                    'context': ctx,
                }
            elif rec.tipo_documento == 'account_invoice_fr':
                res = mod_obj.get_object_reference(cr, uid, 'grp_factura_siif',
                                                   'invoice_siif_retention_supplier_form_inherit')
                models = 'account.invoice'
                res_id = res and res[1] or False
                ctx = dict(context)
                invoice_id = rec.id_documento
                return {
                    'name': "Facturas de fondo rotatorio",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': models,
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': invoice_id,
                    'context': ctx,
                }
            elif rec.tipo_documento == 'account_invoice_refund_fr':
                res = mod_obj.get_object_reference(cr, uid, 'grp_factura_siif',
                                                   'view_account_form_credit_note')
                models = 'account.invoice'
                res_id = res and res[1] or False
                ctx = dict(context)
                invoice_id = rec.id_documento
                return {
                    'name': u"Nota de Crédito fondo rotatorio",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': models,
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': invoice_id,
                    'context': ctx,
                }
            elif rec.tipo_documento in ['hr_expense','hr_expense_anticipo']:
                models = 'hr.expense.expense'
                ctx = dict(context)
                hr_expense_id = rec.id_documento
                expense_id = self.pool.get('hr.expense.expense').browse(cr,uid,hr_expense_id)
                if expense_id.doc_type == u'rendicion_anticipo':
                    res = mod_obj.get_object_reference(cr, uid, 'grp_tesoreria', 'view_grp_rendicion_anticipo_form1')
                else:
                    res = mod_obj.get_object_reference(cr, uid, 'grp_hr_expense', 'grp_view_expenses_form')
                res_id = res and res[1] or False
                return {
                    'name': "Gastos",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': models,
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': hr_expense_id,
                    'context': ctx,
                }
            elif rec.tipo_documento == 'bank_statement':
                res = mod_obj.get_object_reference(cr, uid, 'facturas_uy', 'grp_view_bank_statement_form2')
                models = 'account.bank.statement'
                res_id = res and res[1] or False
                ctx = dict(context)
                bank_statement_line = self.pool.get('account.bank.statement.line').browse(cr, uid, rec.id_documento,
                                                                                          context)
                bank_statement_id = bank_statement_line.statement_id.id
                return {
                    'name': "Registros de caja",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': models,
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': bank_statement_id,
                    'context': ctx,
                }
            elif rec.tipo_documento == 'caja_chica':
                res = mod_obj.get_object_reference(cr, uid, 'grp_tesoreria', 'view_grp_caja_chica_line_form2')
                res_id = res and res[1] or False
                ctx = dict(context)
                return {
                    'name': "Registros de caja",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': 'grp.caja.chica.tesoreria.line',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': rec.id_documento,
                    'context': ctx,
                }
            return True

    # TODO: R RETENCIONES EN FR
    def _get_retentions_dict(self,cr,uid, invoice_ids, context=None):
        invoice_retention_obj = self.pool.get('account.invoice.summary.group.ret')
        retentions = []
        for line in invoice_retention_obj.browse(cr,uid,invoice_retention_obj.search(cr,uid,[('invoice_id','in',invoice_ids)],context=context),context=context):
            new_retention_group = True
            for retention in retentions:
                if retention[2]['creditor_id'] and retention[2]['iva'] and retention[2]['group_id'] and retention[2]['tipo_retencion']:
                    retention[2]['base_linea'] += line.base_linea
                    retention[2]['base_linea_pesos'] += line.base_linea_pesos
                    retention[2]['base_impuesto'] += line.base_impuesto
                    retention[2]['base_impuesto_pesos'] += line.base_impuesto_pesos
                    retention[2]['monto_retencion'] += line.monto_retencion
                    retention[2]['monto_retencion_unround'] += line.monto_retencion_unround
                    retention[2]['monto_retencion_pesos'] += line.monto_retencion_pesos
                    retention[2]['ret_amount_round'] += line.ret_amount_round
                    retention[2]['ret_amount_pesos_round'] += line.ret_amount_pesos_round
                    new_retention_group = False
                    break
            if new_retention_group:
                retentions.append((0,0,{'creditor_id':line.creditor_id.id,
                                        'iva':line.iva,
                                        'group_id':line.group_id.id,
                                        'tipo_retencion':line.tipo_retencion,
                                        'base_linea': line.base_linea,
                                        'base_linea_pesos': line.base_linea_pesos,
                                        'base_impuesto': line.base_impuesto,
                                        'base_impuesto_pesos': line.base_impuesto_pesos,
                                        'monto_retencion': line.monto_retencion,
                                        'monto_retencion_unround': line.monto_retencion_unround,
                                        'monto_retencion_pesos': line.monto_retencion_pesos,
                                        'ret_amount_round': line.ret_amount_round,
                                        'ret_amount_pesos_round': line.ret_amount_pesos_round
                                        }))
        return retentions

    def agrupar_comprobantes(self, cr, uid, ids, context=None):
        ue = ''
        line_invoice_ids = []
        invoice_ids = []
        line_invoice_fr_ids = []
        invoice_fr_ids = []
        line_expense_ids = []
        line_expense_vales_ids = []
        line_statement_ids = []
        statement_ids = []
        # TODO R SPRING 9 GAP 111 adicionando validacion de que sean las lineas a agrupar de la misma UE
        operating_unit = self.read_group(cr, uid, [('id', 'in', ids)], ['operating_unit_id'], 'operating_unit_id')
        if len(operating_unit) > 1:
            raise exceptions.ValidationError(_(u'No puede seleccionar documentos de distinta Unidad Ejecutora u Operativa!'))
        currency = self.read_group(cr, uid, [('id', 'in', ids)], ['currency_id'], 'currency_id')
        if len(currency) > 1:
            raise exceptions.ValidationError(
                _(u'No puede seleccionar documentos con diferentes monedas!'))
        operating_unit_id = operating_unit[0]['operating_unit_id'][0]
        currency_id = currency[0]['currency_id'][0]
        operating_unit = self.pool.get('operating.unit').browse(cr, uid, operating_unit_id)
        unidad_ejecutora_ids = self.pool.get('unidad.ejecutora').search(cr, uid, [('codigo', '=', int(operating_unit.unidad_ejecutora))])

        for rec in self.browse(cr, uid, ids):
            if rec.tipo_documento == 'account_invoice':
                vals_line = (0, 0, {
                    'supplier_invoice_id': rec.id_documento,
                    'tipo_documento': 'account_invoice',
                })
                line_invoice_ids.append(vals_line)
                invoice_ids.append(rec.id_documento)
            elif rec.tipo_documento == 'account_invoice_fr':
                vals_line = (0, 0, {
                    'supplier_invoice_id': rec.id_documento,
                    'tipo_documento': 'account_invoice_fr'
                })
                line_invoice_fr_ids.append(vals_line)
                invoice_fr_ids.append(rec.id_documento)
            elif rec.tipo_documento == 'account_invoice_refund_fr':
                vals_line = (0, 0, {
                    'supplier_invoice_id': rec.id_documento,
                    'tipo_documento': 'account_invoice_fr'
                })
                line_invoice_fr_ids.append(vals_line)
                invoice_fr_ids.append(rec.id_documento)
            elif rec.tipo_documento in ['hr_expense']:
                vals_line = (0, 0, {
                    'hr_expense_id': rec.id_documento,
                    'tipo_documento': 'hr_expense'
                })
                line_expense_ids.append(vals_line)
            elif rec.tipo_documento in ['hr_expense_anticipo']:
                vals_line = (0, 0, {
                    'hr_expense_id': rec.id_documento,
                    'tipo_documento': 'hr_expense_v'
                })
                line_expense_vales_ids.append(vals_line)
            elif rec.tipo_documento == 'bank_statement':
                vals_line = (0, 0, {
                    'bank_statement_id': rec.id_documento,
                    'tipo_documento': 'bank_statement'
                })
                line_statement_ids.append(vals_line)
                statement_ids.append(rec.id_documento)
            elif rec.tipo_documento == 'caja_chica':
                vals_line = (0, 0, {
                    'caja_chica_line_id': rec.id_documento,
                    'tipo_documento': 'bank_statement'
                })
                line_statement_ids.append(vals_line)
            if not ue:
                ue = rec.ue

        fiscal_year_id = self.pool['account.fiscalyear'].find(cr, uid, dt=fields.Date.today())
        inciso_company = self.pool['res.users'].browse(cr, uid, uid).company_id.inciso
        inciso_siif_llp_id = self.pool['grp.estruc_pres.inciso'].search(cr, uid, [('fiscal_year_id', '=', fiscal_year_id),
                                                             ('inciso', '=', inciso_company)])
        ue_siif_llp_id = False
        if len(inciso_siif_llp_id) > 0:
            inciso_siif_llp_id = inciso_siif_llp_id[0]

            ue_ids = self.pool.get('grp.estruc_pres.ue').search(cr, uid, [('inciso_id', '=', inciso_siif_llp_id),('ue', '=', operating_unit.unidad_ejecutora)], order='id desc', limit=1)
            ue_siif_llp_id = ue_ids and ue_ids[0] or False

        beneficiario_ids = self.pool.get('res.partner').search(cr, uid, [('es_inciso_default', '=', True)], limit=1)
        if not beneficiario_ids:
            raise exceptions.ValidationError(_(u'No esta definido el beneficiario SIIF.'))
        beneficiario_id = beneficiario_ids[0]

        vals = {
            'beneficiario_siif_id': beneficiario_id,
            'fiscal_year_id': fiscal_year_id,
            'ue_siif_llp_id': ue_siif_llp_id,
            'inciso_siif_llp_id': inciso_siif_llp_id,
            'state': 'draft',
            'currency_id': currency_id,
            'line_invoice_ids': line_invoice_ids,
            'line_invoice_fr_ids': line_invoice_fr_ids,
            'line_expense_ids': line_expense_ids,
            'line_expense_vales_ids': line_expense_vales_ids,
            'line_statement_ids': line_statement_ids,
            'operating_unit_id': operating_unit_id,
            'unidad_ejecutora_id': unidad_ejecutora_ids and unidad_ejecutora_ids[0] or False,
        }
        fondo_id = self.pool.get('grp.fondo.rotatorio').create(cr, uid, vals, context)
        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'grp_reposicion_fr', 'view_grp_fondo_rotatorio_form')
        res_id = res and res[1] or False
        value = {
            'name': "3 en 1-Fondo rotatorio",
            'view_mode': 'form',
            'view_id': res_id,
            'view_type': 'form',
            'res_model': 'grp.fondo.rotatorio',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': fondo_id,
        }
        return value

    def update_liquido_pagable_ajustado_currency(self, cr, uid, ids, context=None):
        _env = api.Environment(cr,uid,context)
        _env['grp.fondo.rotatorio'].search([('currency_id','=',False)]).write({'currency_id': _env.user.company_id.currency_id.id})
        _env['grp.fondo.rotatorio.line'].search([]).update_liquido_pagable_ajustado_currency()
        return True
