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

import logging
import time

import openerp.addons.decimal_precision as dp
from lxml import etree
from openerp import models, fields, api, exceptions, _
from openerp.exceptions import ValidationError
from openerp.tools import float_round

_logger = logging.getLogger(__name__)

# TODO: SPRING 8 GAP 111.228.339 K
LISTA_ESTADOS = [
    ('draft', 'Borrador'),
    ('confirmado', 'Confirmado'),
    ('obligado', 'Obligado'),
    ('intervenido', 'Intervenido'),
    ('priorizado', 'Priorizado'),
    ('anulado_siif', 'Anulado SIIF'),
    ('cancelado', 'Cancelado'),
    ('pagado', 'Pagado'),
]


# TODO: SPRING 8 GAP 111.228.339 K
class grp_fondo_rotatorio(models.Model):
    _name = 'grp.fondo.rotatorio'
    _inherit = ['mail.thread']
    _description = "3 en 1-Fondo rotatorio"

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.model
    def _default_siif_tipo_ejecucion(self):
        tipo_ejecucion_ids = self.env['tipo.ejecucion.siif'].search([('codigo', '=', 'P')])
        return tipo_ejecucion_ids and tipo_ejecucion_ids[0].id or self.env['tipo.ejecucion.siif']

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.model
    def _default_siif_concepto_gasto(self):
        concepto_gasto_ids = self.env['presupuesto.concepto'].search([('name', '=', '2 - Gastos')])
        return concepto_gasto_ids and concepto_gasto_ids[0].id or self.env['presupuesto.concepto']

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.model
    def _default_siif_financiamiento(self):
        financiamiento_ids = self.env['financiamiento.siif'].search([('name', '=', '11 - Rentas generales')])
        return financiamiento_ids and financiamiento_ids[0].id or self.env['financiamiento.siif']

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.model
    def _default_fiscal_year(self):
        fecha_hoy = time.strftime('%Y-%m-%d')
        uid_company_id = self.env['res.users'].browse(self._uid).company_id.id
        fiscal_year_id = self.env['account.fiscalyear'].search([('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
                                                                ('company_id', '=', uid_company_id)])
        return fiscal_year_id and fiscal_year_id[0].id or self.env['account.fiscalyear']

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.model
    def _default_inciso(self):
        fiscal_year_id = self._default_fiscal_year()

        if fiscal_year_id:
            ids_pres_inciso = self.env['grp.estruc_pres.inciso'].search([('fiscal_year_id', '=', fiscal_year_id)])
        return ids_pres_inciso and ids_pres_inciso[0].id or self.env['grp.estruc_pres.inciso']

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.model
    def _default_ue(self):
        ids_pres_inciso = self._default_inciso()
        if ids_pres_inciso:
            ids_pres_ue = self.env['grp.estruc_pres.ue'].search([('inciso_id', '=', ids_pres_inciso)])
        return ids_pres_ue and ids_pres_ue[0].id or False

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.model
    def _default_siif_codigo_sir(self):
        codigo_sir_ids = self.env['codigo.sir.siif'].search([('name', '=', '05004111520028920 - Rentas Generales')])
        return codigo_sir_ids and codigo_sir_ids[0].id or self.env['codigo.sir.siif']

    @api.model
    def _default_company_currency_id(self):
        return self.env.user.company_id.currency_id


    @api.model
    def _update_prefix(self):

        seq_tres_en_uno = self.env['ir.sequence'].search([('code','=','fr.number')])
        if seq_tres_en_uno:
            if seq_tres_en_uno.prefix != '%(fy)s-3en1-FR-':
                seq_tres_en_uno.write({'prefix':'%(fy)s-3en1-FR-'})

        return True

    name = fields.Char(string=u'Nº 3 en 1-Fondo rotatorio', readonly=True, default='3 en 1-FR Borrador')
    operating_unit_id = fields.Many2one('operating.unit', 'Unidad Ejecutora',
                                        default=lambda self:
                                        self.env['res.users'].
                                        operating_unit_default_get(self._uid))
    beneficiario_siif_id = fields.Many2one('res.partner', string=u'Beneficiario SIIF', ondelete='restrict',
                                           copy=False, required=True)
    benef_es_inciso_default = fields.Boolean(related='beneficiario_siif_id.es_inciso_default', string='Es inciso por defecto', readonly=True)
    unidad_ejecutora_id = fields.Many2one('unidad.ejecutora', string=u"Documento Beneficiario SIIF")
    res_partner_bank_id = fields.Many2one('res.partner.bank', string='Cuenta Bancaria', store=True)
    date_invoice = fields.Date(u'Fecha')
    fecha_vencimiento = fields.Date('Fecha vencimiento')
    fiscal_year_id = fields.Many2one('account.fiscalyear', u'Año fiscal', default=lambda self: self._default_fiscal_year())

    nro_afectacion = fields.Integer(u'Nro Afectación')
    nro_compromiso = fields.Integer(u'Nro Compromiso')
    nro_obligacion = fields.Integer(u'Nro Obligación')
    nro_obl_sist_aux = fields.Char(u'Nro Obligación Sist. Aux')
    siif_ult_modif = fields.Integer(u'Última modificación')
    siif_sec_obligacion = fields.Char(u'Secuencial obligación')
    monto_afectado = fields.Integer(u'Monto autorizado')
    monto_comprometido = fields.Integer('Monto comprometido')

    obligacion_paga_tgn = fields.Boolean(string=u'Obligación Paga por TGN', help=u'Obligación paga por TGN')
    siif_tipo_ejecucion = fields.Many2one("tipo.ejecucion.siif", string=u'Tipo de ejecución',
                                          default=lambda self: self._default_siif_tipo_ejecucion())
    tipo_ejecucion_codigo_rel = fields.Char(related='siif_tipo_ejecucion.codigo', string=u'Código tipo ejecución', readonly=True)
    siif_concepto_gasto = fields.Many2one("presupuesto.concepto", string='Concepto del gasto',
                                          default=lambda self: self._default_siif_concepto_gasto())
    siif_financiamiento = fields.Many2one("financiamiento.siif", string='Fuente de financiamiento',
                                          default=lambda self: self._default_siif_financiamiento())
    siif_codigo_sir = fields.Many2one("codigo.sir.siif", string=u'Código SIR',
                                      default=lambda self: self._default_siif_codigo_sir())
    siif_nro_fondo_rot = fields.Many2one("fondo.rotatorio.siif", string='Nro doc. fondo rotatorio',
                                         domain="[('financiamiento_id','=',siif_financiamiento),('inciso','=',inciso_siif_llp_id),('ue','=',ue_siif_llp_id)]")
    siif_tipo_documento = fields.Many2one('tipo.documento.siif', u'Tipo de documento',
                                          domain=[('visible_documento_obligacion', '=', True)])
    siif_descripcion = fields.Text(u"Descripción SIIF", size=100)

    state = fields.Selection(LISTA_ESTADOS, 'Estado', size=86, readonly=True, default='draft', track_visibility='onchange')
    # TODO R CONTROL DE CAMBIOS
    line_ids = fields.One2many('grp.fondo.rotatorio.line', 'fondo_rotatorios_id', u'Facturas de fondo rotatorio')

    line_invoice_fr_ids = fields.One2many('grp.fondo.rotatorio.line', 'fondo_rotatorios_id', u'Facturas de fondo rotatorio',
                                          domain=[('tipo_documento', '=', 'account_invoice_fr')])
    line_expense_ids = fields.One2many('grp.fondo.rotatorio.line', 'fondo_rotatorios_id', u'Rendición de viático',
                                       domain=[('tipo_documento', '=', 'hr_expense')])
    line_expense_vales_ids = fields.One2many('grp.fondo.rotatorio.line', 'fondo_rotatorios_id', u'Vales',
                                             domain=[('tipo_documento', '=', 'hr_expense_v')])
    line_statement_ids = fields.One2many('grp.fondo.rotatorio.line', 'fondo_rotatorios_id', u'Registro de caja',
                                         domain=[('tipo_documento', '=', 'bank_statement')])
    line_expense_abonos_ids = fields.One2many('grp.fondo.rotatorio.line', 'fondo_rotatorios_id', u'Abonos',
                                              domain=[('tipo_documento', '=', 'hr_expense_a')])

    total_importe_pago = fields.Float(compute='_get_totales', digits_compute=dp.get_precision('Account'),
                                      string='Total importe comprobante', store=True)
    total_impuestos = fields.Float(compute='_get_totales', digits_compute=dp.get_precision('Account'),
                                   string='Total impuestos', store=True)
    total_retenciones = fields.Float(compute='_get_totales', digits_compute=dp.get_precision('Account'),
                                     string='Total retenciones FR', store=True)
    total_reponer = fields.Float(compute='_get_totales', digits_compute=dp.get_precision('Account'),
                                 string='Total a reponer FR', store=True)
    liquido_pagable = fields.Float(compute='_get_totales', digits_compute=dp.get_precision('Account'),
                                   string='Liquido pagable FR', store=True)

    inciso_siif_llp_id = fields.Many2one('grp.estruc_pres.inciso', 'Inciso', default=lambda self: self._default_inciso())
    ue_siif_llp_id = fields.Many2one('grp.estruc_pres.ue', 'Unidad ejecutora')

    dlineas_llavep_invoice_fr_ids = fields.One2many('grp.detalles.lineas.llavep', 'fondo_rotarios_ld_id', u'Detalles de facturas de fondo rotatorio',
                                                    domain=[('tipo_documento', '=', 'account_invoice_fr')])
    dlineas_llavep_hr_expense_ids = fields.One2many('grp.detalles.lineas.llavep', 'fondo_rotarios_ld_id', u'Detalles de rendición de viático',
                                                    domain=[('tipo_documento', '=', 'hr_expense')])
    dlineas_llavep_hr_expense_vales_ids = fields.One2many('grp.detalles.lineas.llavep', 'fondo_rotarios_ld_id', u'Detalles de Vales',
                                                          domain=[('tipo_documento', '=', 'hr_expense_v')])
    dlineas_llavep_bank_statement_ids = fields.One2many('grp.detalles.lineas.llavep', 'fondo_rotarios_ld_id', u'Detalles de registro de caja',
                                                        domain=[('tipo_documento', '=', 'bank_statement')])
    dlineas_llavep_hr_expense_abonos_ids = fields.One2many('grp.detalles.lineas.llavep', 'fondo_rotarios_ld_id', u'Detalles de abonos',
                                                           domain=[('tipo_documento', '=', 'hr_expense_a')])
    llpapg_ids = fields.One2many('grp.fondo.rotatorio.llavep', 'fondo_rotatorios_llp_id', string=u'Líneas presupuesto')
    total_llavep = fields.Float(compute='_get_total_llavep', digits_compute=dp.get_precision('Account'),
                                string='Total llave presupuestal', store=True)
    retention_ids = fields.One2many('grp.fondo.rotarios.retencion', 'fr_id', string=u'Retenciones')  # TODO: R RETENCIONES DE FR

    modif_obligacion_log_fr_ids = fields.One2many('modif_obligacion_siif_fr_log', 'fondo_rotatorio_id', 'Log')

    anulacion_siif_log_ids = fields.One2many('obligacion.fr.anulacion.siif.log', 'fondo_rotatorio_id', 'Log anulaciones')
    #Priorizaciones
    fondo_prioritized_line = fields.One2many('grp.fondo.rotatorio.prioritized.line', 'fondo_grp_id', string='Priorizaciones')

    # TODO: SPRING 11 GAP 495 K
    procesado = fields.Boolean(string='Procesado', default=False)
    fecha_procesado = fields.Date('Fecha Procesado')

    intervenido_con_observ = fields.Boolean(u"Intervenido con observaciones")
    observacion_ids = fields.One2many('grp.observacion.tc.fr', 'fondo_rotatorio_id', u'Observación')
    recuperacion_move_id = fields.Many2one('account.move', string=u"Asiento recuperación Fondo Rotatorio")

    filtro_sir = fields.Char(string=u'Filtro código SIR', compute='_compute_filtro_sir')

    moneda_extranjera = fields.Boolean('Moneda extranjera',compute='_compute_company_currency_id', store=True)
    company_currency_id = fields.Many2one('res.currency', string='Moneda compañia',
                                          default = lambda self: self._default_company_currency_id(), store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda')
    currency_rate_date = fields.Date(u'Fecha tipo de cambio', required=False, default = lambda *a: fields.Date.today(),
                            states={'draft': [('required', True)], 'confirmado': [('required', True)]})

    currency_rate = fields.Float(u'Tipo de cambio',
                                 compute='_compute_currency_rate',multi='_compute_currency_rate', digits=(12, 6),
                                 store=True)
    currency_rate_presupuesto = fields.Float(u'Tipo de cambio presupuesto', digits=(12, 6),
                                              compute='_compute_currency_rate',multi='_compute_currency_rate',
                                              store=True)
    total_nominal_comprobantes = fields.Float(u'Total nominal comprobantes', compute='_compute_total_moneda',
                                              multi='_compute_total_moneda', store=True)
    total_retenciones_me = fields.Float(u'Total retenciones', compute='_compute_total_moneda',
                                     multi='_compute_total_moneda', store=True)
    total_liquido_pagable = fields.Float(u'Total liquido pagable', compute='_compute_total_moneda',
                                         multi='_compute_total_moneda', store=True)

    @api.multi
    @api.depends('company_currency_id', 'currency_id')
    def _compute_company_currency_id(self):
        for rec in self:
            rec.moneda_extranjera = rec.currency_id.id and rec.currency_id.id != rec.company_currency_id.id

    @api.multi
    @api.depends('moneda_extranjera', 'line_ids.amount_retentions_currency', 'line_ids.liquido_pagable_currency',
                 'line_ids.liquido_pagable_ajustado_currency')
    def _compute_total_moneda(self):
        for rec in self:
            if rec.moneda_extranjera:
                _total_retenciones = sum(rec.line_ids.mapped('amount_retentions_currency'))
                _total_nominal_comprobantes = sum(rec.line_ids.mapped('liquido_pagable_currency')) + _total_retenciones
                _total_liquido_pagable = sum(rec.line_ids.mapped('liquido_pagable_ajustado_currency'))
            else:
                _total_retenciones = 0
                _total_nominal_comprobantes = 0
                _total_liquido_pagable = 0
            rec.total_retenciones_me = _total_retenciones
            rec.total_nominal_comprobantes = _total_nominal_comprobantes
            rec.total_liquido_pagable = _total_liquido_pagable



    @api.multi
    @api.depends('currency_id','currency_rate_date')
    def _compute_currency_rate(self):
        CurrencyRate = self.env['res.currency.rate']
        company_currency = self.env.user.company_id.currency_id
        for rec in self:
            _currency_id = rec.currency_id and rec.currency_id or company_currency
            rec.currency_rate = CurrencyRate.search([('currency_id','=',_currency_id.id),('name','<=',rec.currency_rate_date)], order='name DESC', limit=1).rate or float(0)
            rec.currency_rate_presupuesto = CurrencyRate.search([('currency_id','=',_currency_id.id),('name','<=',rec.currency_rate_date)], order='name DESC', limit=1).rate_presupuesto or float(0)


    @api.multi
    @api.depends('inciso_siif_llp_id', 'ue_siif_llp_id', 'siif_financiamiento')
    def _compute_filtro_sir(self):
        for rec in self:
            # Si el financiamiento es 11 filtro solo por financiamiento
            if rec.siif_financiamiento and rec.siif_financiamiento.codigo.zfill(2) == '11':
                rec.filtro_sir = '_____' + rec.siif_financiamiento.codigo.zfill(2) + '__________'
            # Si tiene inciso_siif_llp_id, ue_siif_llp_id y financiamiento != 11, filtro por inciso, ue y financiamiento
            elif rec.inciso_siif_llp_id and rec.ue_siif_llp_id and rec.siif_financiamiento:
                rec.filtro_sir = rec.inciso_siif_llp_id.inciso + rec.ue_siif_llp_id.ue + rec.siif_financiamiento.codigo.zfill(
                    2) + '__________'
            # Si no finaciamiento, o el financiamiento es != 11 y no tiene inciso_siif_llp_id o ue_siif_llp_id, no muestra nada
            else:
                rec.filtro_sir = 'xxxxxxxxxxxxxxx'


    @api.onchange('operating_unit_id')
    def onchange_operating_unit_id(self):
        self.siif_nro_fondo_rot = False
        if self.operating_unit_id and self.operating_unit_id.unidad_ejecutora:
            unidad_ejecutora = self.env["unidad.ejecutora"].search([('codigo','=',int(self.operating_unit_id.unidad_ejecutora))])
            if unidad_ejecutora:
                self.unidad_ejecutora_id = unidad_ejecutora.id

    @api.onchange('fiscal_year_id', 'operating_unit_id')
    def onchange_fiscal_year_operating_unit(self):
        if self.fiscal_year_id and self.operating_unit_id:
            inciso_company = self.env['res.users'].browse([self._uid]).company_id.inciso
            inciso_siif_llp_id = self.env['grp.estruc_pres.inciso'].search([
                ('fiscal_year_id', '=', self.fiscal_year_id.id),
                ('inciso', '=', inciso_company)
            ], limit=1)
            ue_siif_llp_id = False
            if len(inciso_siif_llp_id) > 0:
                inciso_siif_llp_id = inciso_siif_llp_id[0]
                ue_ids = self.env['grp.estruc_pres.ue'].search([
                    ('inciso_id', '=', inciso_siif_llp_id.id),
                    ('ue', '=', self.operating_unit_id.unidad_ejecutora)
                ], order='id desc', limit=1)
                ue_siif_llp_id = ue_ids and ue_ids[0] or False
            self.ue_siif_llp_id = ue_siif_llp_id
            self.inciso_siif_llp_id = inciso_siif_llp_id

    @api.constrains('state', 'liquido_pagable', 'llpapg_ids')
    def _check_totales(self):
        if self.state not in ['draft', 'confirmado'] and sum(map(lambda x: x.importe, self.llpapg_ids)) != round(self.liquido_pagable, 0):
            raise ValidationError(u'La sumatoria de importes de llaves presupuestales no es igual al monto a pagar!')

    @api.one
    @api.constrains('date_invoice','fecha_vencimiento')
    def _check_fechas(self):

        if self.date_invoice and self.fecha_vencimiento and (self.date_invoice > self.fecha_vencimiento):
            raise exceptions.ValidationError('La fecha de vencimiento no puede ser menor a la fecha de factura')

    # TODO: SPRING 8 GAP 111.228.339 K
    def abrir_wizard_modif_obligacion_siif(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'grp_reposicion_fr', 'view_wizard_modif_obligacion_fr_siif')
        res_id = res and res[1] or False
        ue_id = self.browse(cr, uid, ids[0]).ue_siif_llp_id.id or False

        ctx = dict(context or {})
        ctx.update({
            'default_fondo_rotatorio_w_id': ids[0],
            'default_ue_id': ue_id
        })
        return {
            'name': "Modificaciones",  # Name You want to display on wizard
            'view_mode': 'form',
            'view_id': res_id,
            'view_type': 'form',
            'res_model': 'wiz.modificacion_obligacion_fr_siif',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.multi
    def _get_total_importe_pago(self):
        for rec in self:
            total_importe_pago = 0
            if rec.line_invoice_fr_ids:
                total_importe_pago += sum(
                    map(lambda x: x.amount, rec.line_invoice_fr_ids))
            if rec.line_expense_ids:
                total_importe_pago += sum(
                    map(lambda x: x.amount, rec.line_expense_ids))
            if rec.line_expense_vales_ids:
                total_importe_pago += sum(
                    map(lambda x: x.amount, rec.line_expense_vales_ids))
            if rec.line_statement_ids:
                total_importe_pago += sum(
                    map(lambda x: x.amount, rec.line_statement_ids))
            rec.total_importe_pago = round(total_importe_pago, 0)

    @api.multi
    @api.depends('llpapg_ids.importe')
    def _get_total_llavep(self):
        for rec in self:
            rec.total_llavep = 0.0
            if rec.llpapg_ids:
                rec.total_llavep = sum(map(lambda x: x.importe, rec.llpapg_ids))

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.multi
    def _get_total_impuestos(self):
        for rec in self:
            if rec.line_invoice_fr_ids:
                rec.total_impuestos += sum(
                    map(lambda x: x.amount_ttal_impuestos_pesos, rec.line_invoice_fr_ids.mapped(lambda x: x.supplier_invoice_id)))
            else:
                rec.total_impuestos = float(0)

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.multi
    def _get_total_retenciones(self):
        for rec in self:
            if rec.line_invoice_fr_ids:
                rec.total_retenciones += round(sum(map(lambda x: x.amount_ttal_ret_pesos, rec.line_invoice_fr_ids.mapped(lambda x: x.supplier_invoice_id))),0)
            else:
                rec.total_retenciones = float(0)

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.multi
    def _get_total_reponer(self):
        for rec in self:
            rec.total_reponer = round((rec.total_importe_pago + rec.total_retenciones), 0)

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.multi
    @api.depends('line_invoice_fr_ids.liquido_pagable', 'line_expense_ids.liquido_pagable', 'line_expense_vales_ids.liquido_pagable', 'line_statement_ids.liquido_pagable', 'line_expense_abonos_ids.liquido_pagable')
    def _get_totales(self):
        for rec in self:
            total_importe_pago = 0
            total_retenciones = 0
            total_impuestos = 0
            if rec.line_invoice_fr_ids:
                total_importe_pago += sum(map(lambda x: x.liquido_pagable, rec.line_invoice_fr_ids))
                total_retenciones += round(sum(map(lambda x: x.amount_ttal_ret_pesos,
                                                   rec.line_invoice_fr_ids.mapped(
                                                       lambda x: x.supplier_invoice_id))), 0)
                total_impuestos += sum(map(lambda x: x.amount_ttal_impuestos_pesos,
                                           rec.line_invoice_fr_ids.mapped(lambda x: x.supplier_invoice_id)))
            if rec.line_expense_ids:
                total_importe_pago += sum(map(lambda x: x.liquido_pagable, rec.line_expense_ids))
            if rec.line_expense_vales_ids:
                total_importe_pago += sum(map(lambda x: x.liquido_pagable, rec.line_expense_vales_ids))
            if rec.line_expense_abonos_ids:
                total_importe_pago += sum(map(lambda x: x.liquido_pagable, rec.line_expense_abonos_ids))
            if rec.line_statement_ids:
                total_importe_pago += sum(map(lambda x: x.liquido_pagable, rec.line_statement_ids))
            total_importe_pago = round(total_importe_pago, 0)
            rec.total_importe_pago = total_importe_pago
            rec.total_retenciones = total_retenciones
            rec.total_reponer = total_importe_pago + total_retenciones
            rec.liquido_pagable = total_importe_pago
            rec.total_impuestos = total_impuestos

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.multi
    def _get_liquido_pagable(self):
        for rec in self:
            rec.liquido_pagable = rec.total_reponer - rec.total_retenciones

    # TODO: SPRING 8 GAP 111.228.339 K
    def update_line_invoice_fr_ids(self):
        dlineas_llavep_invoice_fr_ids = []
        if self.line_invoice_fr_ids:
            # odg_auxiliar = {}
            for line in self.line_invoice_fr_ids:
                if not line.supplier_invoice_id.llpapg_ids:
                    line.supplier_invoice_id.action_llpapg_reload()
                if line.supplier_invoice_id.llpapg_ids:
                    for llpapg_id in line.supplier_invoice_id.llpapg_ids:
                        if len(dlineas_llavep_invoice_fr_ids) > 0:
                            added = False
                            for record in dlineas_llavep_invoice_fr_ids:
                                invoice = self.env['account.invoice'].browse(record[2]['invoice_id'])
                                if record[2]['odg_id'] == llpapg_id.odg_id.id \
                                        and record[2]['auxiliar_id'] == llpapg_id.auxiliar_id.id \
                                        and invoice.partner_id.id == line.proveedor.id \
                                        and line.supplier_invoice_id.nro_factura_grp == line.no_factura \
                                        and invoice.id == line.supplier_invoice_id.id:
                                    record[2]['importe'] += llpapg_id.importe
                                    added = True
                            if not added:
                                vals_llavep = (0, 0, {
                                    'invoice_id': line.supplier_invoice_id.id,
                                    'fondo_rotarios_line_id': line.id,
                                    'odg_id': llpapg_id.odg_id.id,
                                    'auxiliar_id': llpapg_id.auxiliar_id.id,
                                    'importe': llpapg_id.importe,
                                    'tipo_documento': 'account_invoice_fr',
                                    'proveedor_id': line.proveedor.id,
                                })
                                dlineas_llavep_invoice_fr_ids.append(vals_llavep)
                                # odg_auxiliar[llpapg_id.odg_id.id] = llpapg_id.auxiliar_id.id
                        else:
                            vals_llavep = (0, 0, {
                                'invoice_id': line.supplier_invoice_id.id,
                                'fondo_rotarios_line_id': line.id,
                                'odg_id': llpapg_id.odg_id.id,
                                'auxiliar_id': llpapg_id.auxiliar_id.id,
                                'importe': llpapg_id.importe,
                                'tipo_documento': 'account_invoice_fr',
                                'proveedor_id': line.proveedor.id,
                            })
                            dlineas_llavep_invoice_fr_ids.append(vals_llavep)
                            # odg_auxiliar[llpapg_id.odg_id.id] = llpapg_id.auxiliar_id.id
        return dlineas_llavep_invoice_fr_ids

    # TODO: SPRING 8 GAP 111.228.339 K
    def update_line_statement_ids(self):
        dlineas_llavep_statement = []
        if self.line_statement_ids:
            for line in self.line_statement_ids:
                if line.bank_statement_id and line.bank_statement_id.concepto_id:
                    if not line.bank_statement_id.concepto_id.odg_id \
                       or not line.bank_statement_id.concepto_id.auxiliar_id: # prevent data error
                        raise ValidationError("Por favor, configure el Objeto de Gasto y/o el Auxiliar del concepto de gasto '%s'" % (line.bank_statement_id.concepto_id.name))
                    fiscal_year_id = self.env['account.fiscalyear'].with_context(company_id=line.bank_statement_id.company_id.id).find(dt=fields.Date.today())
                    # TODO: evaluar tomar el año fiscal del concepto de gasto ´´line.bank_statement_id.concepto_id.fiscal_year´´
                    odg_domain = [('fiscal_year_id','=',fiscal_year_id),
                                  ('odg','=',line.bank_statement_id.concepto_id.odg_id)]
                    aux_domain = [('fiscal_year_id','=',fiscal_year_id),
                                  ('aux','=',line.bank_statement_id.concepto_id.auxiliar_id)]
                    if line.fondo_rotatorios_id.ue_siif_llp_id:
                        odg_domain.append(('ue_id','=',line.fondo_rotatorios_id.ue_siif_llp_id.id))
                        aux_domain.append(('ue_id','=',line.fondo_rotatorios_id.ue_siif_llp_id.id))
                    if line.fondo_rotatorios_id.inciso_siif_llp_id:
                        odg_domain.append(('inciso_id','=',line.fondo_rotatorios_id.inciso_siif_llp_id.id))
                        aux_domain.append(('inciso_id','=',line.fondo_rotatorios_id.inciso_siif_llp_id.id))
                    odg = self.env['grp.estruc_pres.odg'].search(odg_domain, order='id desc', limit=1)
                    aux_domain.append(('odg_id','=',odg.id))
                    aux = self.env['grp.estruc_pres.aux'].search(aux_domain, order='id desc', limit=1)
                    if odg and aux:
                        if len(dlineas_llavep_statement) > 0:
                            encontrado = False
                            for record in dlineas_llavep_statement:
                                if record[2]['odg_id'] == odg.id and \
                                   record[2]['auxiliar_id'] == aux.id and \
                                   record[2]['concepto_gasto'] == line.concepto_gasto.name:
                                    record[2]['importe'] += round(line.importe_pago_registro)
                                    encontrado = True
                            if not encontrado:
                                vals_llavep = (0, 0, {
                                    'bank_statement_id': line.bank_statement_id.id,
                                    'referencia': line.bank_statement_id.ref,
                                    'fondo_rotarios_line_id': line.id,
                                    'odg_id': odg.id,
                                    'auxiliar_id': aux.id,
                                    'importe': round(line.importe_pago_registro),
                                    'tipo_documento': 'bank_statement',
                                    'concepto_gasto': line.concepto_gasto.name
                                })
                                dlineas_llavep_statement.append(vals_llavep)
                        else:
                            vals_llavep = (0, 0, {
                                'bank_statement_id': line.bank_statement_id.id,
                                'referencia': line.bank_statement_id.ref,
                                'fondo_rotarios_line_id': line.id,
                                'odg_id': odg.id,
                                'auxiliar_id': aux.id,
                                'importe': round(line.importe_pago_registro),
                                'tipo_documento': 'bank_statement',
                                'concepto_gasto': line.concepto_gasto.name
                            })
                            dlineas_llavep_statement.append(vals_llavep)
                    elif not odg:
                        fy_obj = self.env['account.fiscalyear'].browse(fiscal_year_id)
                        raise ValidationError(u"No existe en la estructura de presupuesto un registro de ODG con los siguientes "
                                              u"datos: (Año fiscal: %s Inciso: %s UE: %s ODG: %s)" %
                                              (fy_obj.code,
                                               line.fondo_rotatorios_id.inciso_siif_llp_id.inciso,
                                               line.fondo_rotatorios_id.ue_siif_llp_id.ue,
                                               line.bank_statement_id.concepto_id.odg_id
                                               ))
                    elif not aux:
                        fy_obj = self.env['account.fiscalyear'].browse(fiscal_year_id)
                        raise ValidationError(u"No existe en la estructura de presupuesto un registro de Auxiliar"
                                              u" con los siguientes "
                                              u"datos: (Año fiscal: %s Inciso: %s UE: %s ODG: %s AUX: %s)" %
                                              (fy_obj.code,
                                               line.fondo_rotatorios_id.inciso_siif_llp_id.inciso,
                                               line.fondo_rotatorios_id.ue_siif_llp_id.ue,
                                               odg.odg,
                                               line.bank_statement_id.concepto_id.auxiliar_id
                                               ))
                if line.caja_chica_line_id and line.caja_chica_line_id.concept_cc_id:
                    if not line.caja_chica_line_id.concept_cc_id.odg_id \
                       or not line.caja_chica_line_id.concept_cc_id.auxiliar_id: # prevent data error
                        raise ValidationError("Por favor, configure el Objeto de Gasto y/o el Auxiliar del concepto de gasto '%s'" % (line.caja_chica_line_id.concept_cc_id.name))
                    fiscal_year_id = self.env['account.fiscalyear'].with_context(company_id=line.caja_chica_line_id.caja_chica_id.company_id.id).find(dt=fields.Date.today())
                    # TODO: evaluar tomar el año fiscal del concepto de gasto ´´line.caja_chica_line_id.concept_cc_id.fiscal_year´´
                    odg_domain = [('fiscal_year_id','=',fiscal_year_id),
                                  ('odg','=',line.caja_chica_line_id.concept_cc_id.odg_id)]
                    aux_domain = [('fiscal_year_id','=',fiscal_year_id),
                                  ('aux','=',line.caja_chica_line_id.concept_cc_id.auxiliar_id)]
                    if line.fondo_rotatorios_id.ue_siif_llp_id:
                        odg_domain.append(('ue_id','=',line.fondo_rotatorios_id.ue_siif_llp_id.id))
                        aux_domain.append(('ue_id','=',line.fondo_rotatorios_id.ue_siif_llp_id.id))
                    if line.fondo_rotatorios_id.inciso_siif_llp_id:
                        odg_domain.append(('inciso_id','=',line.fondo_rotatorios_id.inciso_siif_llp_id.id))
                        aux_domain.append(('inciso_id','=',line.fondo_rotatorios_id.inciso_siif_llp_id.id))
                    odg = self.env['grp.estruc_pres.odg'].search(odg_domain, order='id desc', limit=1)
                    aux_domain.append(('odg_id','=',odg.id))
                    aux = self.env['grp.estruc_pres.aux'].search(aux_domain, order='id desc', limit=1)
                    if odg and aux:
                        if len(dlineas_llavep_statement) > 0:
                            encontrado = False
                            for record in dlineas_llavep_statement:
                                if record[2]['odg_id'] == aux.odg_id.id and \
                                   record[2]['auxiliar_id'] == aux.id and \
                                   record[2]['concepto_gasto'] == line.concepto_gasto.name:
                                    record[2]['importe'] += line.importe_pago_registro
                                    encontrado = True
                            if not encontrado:
                                vals_llavep = (0, 0, {
                                    'caja_chica_line_id': line.caja_chica_line_id.id,
                                    'fondo_rotarios_line_id': line.id,
                                    'odg_id': odg.id,
                                    'auxiliar_id': aux.id,
                                    'importe': line.importe_pago_registro,
                                    'tipo_documento': 'bank_statement',
                                    'concepto_gasto': line.concepto_gasto.name
                                })
                                dlineas_llavep_statement.append(vals_llavep)
                            for record in dlineas_llavep_statement:
                                record[2]['importe'] += round(record[2]['importe'])
                        else:
                            vals_llavep = (0, 0, {
                                'caja_chica_line_id': line.caja_chica_line_id.id,
                                'fondo_rotarios_line_id': line.id,
                                'odg_id': odg.id,
                                'auxiliar_id': aux.id,
                                'importe': line.importe_pago_registro,
                                'tipo_documento': 'bank_statement',
                                'concepto_gasto': line.concepto_gasto.name
                            })
                            dlineas_llavep_statement.append(vals_llavep)
                    elif not odg:
                        fy_obj = self.env['account.fiscalyear'].browse(fiscal_year_id)
                        raise ValidationError(u"No existe en la estructura de presupuesto un registro de ODG con los siguientes "
                                              u"datos: (Año fiscal: %s Inciso: %s UE: %s ODG: %s)" %
                                              (fy_obj.code,
                                               line.fondo_rotatorios_id.inciso_siif_llp_id.inciso,
                                               line.fondo_rotatorios_id.ue_siif_llp_id.ue,
                                               line.bank_statement_id.concepto_id.odg_id
                                               ))
                    elif not aux:
                        fy_obj = self.env['account.fiscalyear'].browse(fiscal_year_id)
                        raise ValidationError(u"No existe en la estructura de presupuesto un registro de Auxiliar"
                                              u" con los siguientes "
                                              u"datos: (Año fiscal: %s Inciso: %s UE: %s ODG: %s AUX: %s)" %
                                              (fy_obj.code,
                                               line.fondo_rotatorios_id.inciso_siif_llp_id.inciso,
                                               line.fondo_rotatorios_id.ue_siif_llp_id.ue,
                                               odg.odg,
                                               line.bank_statement_id.concepto_id.auxiliar_id
                                               ))
        return dlineas_llavep_statement

    def update_line_expense_ids(self, tipo_doc):
        dlineas_llavep_hr_expense_ids = []
        lines_to_loop = self.line_expense_ids
        if tipo_doc == 'hr_expense_v':
            lines_to_loop = self.line_expense_vales_ids
        for line_expense in lines_to_loop:
            # added = False
            expense = line_expense.hr_expense_id
            fiscal_year_id = self.env['account.fiscalyear'].with_context(company_id=expense.company_id.id).find(dt=fields.Date.today())
            for line in expense.line_ids:
                domain = []
                if line.product_id and line.product_id.objeto_gasto:
                    domain = [('fiscal_year_id','=',fiscal_year_id),
                              ('odg_id.odg','=',line.product_id.objeto_gasto.name),
                              ('aux','=',line.product_id.objeto_gasto.auxiliar)]
                elif line.concept_id and line.concept_id.odg_id:
                    domain = [('fiscal_year_id','=',fiscal_year_id),
                              ('odg_id.odg','=',line.concept_id.odg_id),
                              ('aux','=',line.concept_id.auxiliar_id)]
                if domain:
                    if line_expense.fondo_rotatorios_id.ue_siif_llp_id:
                        domain.append(('ue_id','=',line_expense.fondo_rotatorios_id.ue_siif_llp_id.id))
                    if line_expense.fondo_rotatorios_id.inciso_siif_llp_id:
                        domain.append(('inciso_id','=',line_expense.fondo_rotatorios_id.inciso_siif_llp_id.id))
                    aux = self.env['grp.estruc_pres.aux'].search(domain, order='id desc', limit=1)
                    if not aux:
                        fy_obj = self.env['account.fiscalyear'].browse(fiscal_year_id)
                        raise ValidationError(u"No existe en la estructura de presupuesto un registro de Auxiliar"
                                              u" con los siguientes "
                                              u"datos: (Año fiscal: %s Inciso: %s UE: %s ODG: %s AUX: %s)" %
                                              (fy_obj.code,
                                               line_expense.fondo_rotatorios_id.inciso_siif_llp_id.inciso,
                                               line_expense.fondo_rotatorios_id.ue_siif_llp_id.ue,
                                               domain[1][2],
                                               domain[2][2]
                                               ))
                    if len(dlineas_llavep_hr_expense_ids) > 0:
                        encontrado = False
                        for record in dlineas_llavep_hr_expense_ids:
                            # invoice = self.env['account.invoice'].browse(record[2]['invoice_id'])
                            if record[2]['odg_id'] == aux.odg_id.id \
                                    and record[2]['auxiliar_id'] == aux.id \
                                    and record[2]['descripcion_gasto'] == line.expense_id.name \
                                    and record[2]['hr_expense_id'] == expense.id:
                                # record[2]['importe'] += round(line.total_amount)
                                record[2]['importe'] += line.total_amount
                                encontrado = True
                        if not encontrado:
                            vals_llavep = (0, 0, {
                                    'hr_expense_id': expense.id,
                                    'fondo_rotarios_line_id': line_expense.id,
                                    'odg_id': aux.odg_id.id,
                                    'auxiliar_id': aux.id,
                                    'importe': round(line.total_amount),
                                    'tipo_documento': line_expense.tipo_documento,
                                    'descripcion_gasto': line_expense.descripcion_gasto
                            })
                            dlineas_llavep_hr_expense_ids.append(vals_llavep)
                        for record in dlineas_llavep_hr_expense_ids:
                            record[2]['importe'] = round(record[2]['importe'])
                    else:
                        vals_llavep = (0, 0, {
                            'hr_expense_id': expense.id,
                            'fondo_rotarios_line_id': line_expense.id,
                            'odg_id': aux.odg_id.id,
                            'auxiliar_id': aux.id,
                            'importe': round(line.total_amount),
                            'tipo_documento': line_expense.tipo_documento,
                            'descripcion_gasto': line_expense.descripcion_gasto
                        })
                        dlineas_llavep_hr_expense_ids.append(vals_llavep)
        return dlineas_llavep_hr_expense_ids

    # TODO: SPRING 8 GAP 111.228.339 K
    def update_detalles_lineas_llavep(self, vals_write):
        llpapg_ids = []
        for key in vals_write:
            if len(vals_write[key]) > 0:
                for value in vals_write[key]:
                    if 'odg_id' in value[2] and 'auxiliar_id' in value[2]\
                            and value[2]['odg_id'] and value[2]['auxiliar_id']:
                        if len(llpapg_ids) > 0:
                            encontrado = False
                            for record in llpapg_ids:
                                if record[2]['odg_id'] == value[2]['odg_id'] and record[2]['auxiliar_id'] == value[2]['auxiliar_id']:
                                    record[2]['importe'] += value[2]['importe']
                                    encontrado = True
                            if not encontrado:
                                vals_llavep = (0, 0, {
                                    'odg_id': value[2]['odg_id'],
                                    'auxiliar_id': value[2]['auxiliar_id'],
                                    'importe': value[2]['importe'],
                                })
                                llpapg_ids.append(vals_llavep)
                        else:
                            vals_llavep = (0, 0, {
                                'odg_id': value[2]['odg_id'],
                                'auxiliar_id': value[2]['auxiliar_id'],
                                'importe': value[2]['importe'],
                            })
                            llpapg_ids.append(vals_llavep)
        return llpapg_ids

    # TODO: SPRING 8 GAP 111.228.339 K
    def update_write_detalles_lineas_llavep(self, vals_write):
        llpapg_ids = self.llpapg_ids
        llpapg_ids_return = []
        for key in vals_write:
            if len(vals_write[key]) > 0:
                for value in vals_write[key]:
                    if value[0] == 2:
                        detalles_lineas = self.env['grp.detalles.lineas.llavep'].search([('fondo_rotarios_line_id', '=', value[1])])
                        for detalles_linea in detalles_lineas:
                            if len(llpapg_ids) > 0:
                                for record in llpapg_ids:
                                    if record.odg_id.id == detalles_linea.odg_id.id and record.auxiliar_id.id == detalles_linea.auxiliar_id.id:
                                        record.importe -= detalles_linea.importe

        for record in llpapg_ids:
            if record.importe > 0:
                vals_llavep = (0, 0, {
                    'fondo_rotatorios_llp_id': record.fondo_rotatorios_llp_id.id if record.fondo_rotatorios_llp_id else False,
                    'fin_id': record.fin_id.id if record.fin_id else False,
                    'programa_id': record.programa_id.id if record.programa_id else False,
                    'proyecto_id': record.proyecto_id.id if record.proyecto_id else False,
                    'odg_id': int(record.odg_id.id) if record.odg_id else False,
                    'auxiliar_id': int(record.auxiliar_id.id) if record.auxiliar_id else False,
                    'mon_id': record.mon_id.id if record.mon_id else False,
                    'tc_id': record.tc_id.id if record.tc_id else False,
                    'disponible': record.disponible,
                    'importe': record.importe,
                })
                llpapg_ids_return.append(vals_llavep)
        return llpapg_ids_return

    # TODO R RESTRICCION PARA MONTOS DE LA LLAVE PRESUPUESTAL
    # no es un constrains, debe ser llamado por botones
    @api.multi
    def _check_totales(self):
        for rec in self:
            if rec.state != 'draft' and sum(map(lambda x: x.importe, rec.llpapg_ids)) != rec.total_reponer:
                raise ValidationError(u'La sumatoria de importes de llaves presupuestales no es igual al Total a reponer FR!')

    @api.multi
    def act_fr_confirmado(self):
        self._check_totales() #TODO: R Verificando totales
        for rec in self:
            if rec.name == '3 en 1-FR Borrador':
                rec.name = self.env['ir.sequence'].with_context(fiscalyear_id=rec.fiscal_year_id.id).get('fr.number')
        self.state = 'confirmado'

    @api.multi
    def fr_impactar_presupuesto(self):
        estructura_obj = self.env['presupuesto.estructura']
        for fondo_rotatorio in self:

            # Control: que la sumatoria de llave sea igual al total a reponer
            if fondo_rotatorio.total_llavep <> round(fondo_rotatorio.total_reponer):
                raise exceptions.ValidationError('La sumatoria de importes de llaves presupuestales no es igual al total a reponer.')

            for llave in fondo_rotatorio.llpapg_ids:
                estructura = estructura_obj.obtener_estructura(fondo_rotatorio.fiscal_year_id.id,
                                                               fondo_rotatorio.inciso_siif_llp_id.inciso,
                                                               fondo_rotatorio.ue_siif_llp_id.ue,
                                                               llave.programa, llave.proyecto,
                                                               llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)
                # Control: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (fondo_rotatorio.fiscal_year_id.code, fondo_rotatorio.inciso_siif_llp_id.inciso, fondo_rotatorio.ue_siif_llp_id.ue,
                                  llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon, llave.tc)
                    raise exceptions.ValidationError(u'No se encontró estructura con la llave presupuestal asociada al fondo rotatorio: ' + desc_error)

                # Se obliga en el presupuesto (es 3en1 se afecta, compromete y obliga)
                res_af = estructura_obj.afectar(fondo_rotatorio.id, 8, llave.importe, estructura)
                res_comp = estructura_obj.comprometer(fondo_rotatorio.id, 8, llave.importe, estructura)
                res_obligar = estructura_obj.obligar(fondo_rotatorio.id, 8, llave.importe, estructura)
        return True

    def fr_enviar_siif(self):
        generador_xml = self.env['grp.siif.xml_generator']
        siif_proxy = self.env['siif.proxy']

        # TODO revisar tipos de documento grp, dato a enviar a siif pero que no esta clara su definicion en grp
        tipo_doc_grp = '04'

        for fondo_rotatorio in self:
            if fondo_rotatorio.nro_obligacion:
                raise ValidationError("Este documento ya ha sido enviado a SIIF. Por favor, actualice el navegador.")

            # SERGIO
            # Retenciones: Lista de retenciones a enviar (cada elemento es un diciconario)
            # ret_creditor_id: diccionario que guarda en que posicion de la lista se encuetra la retencion para el acreedor (se agrupan por acreedor)
            retenciones = []
            ret_creditor_id = {}
            for retencion in fondo_rotatorio.retention_ids:
                if retencion.ret_amount_pesos_round > 0:
                    if retencion.tipo_retencion == 'siif':
                        if retencion.retention_id.base_compute == 'ret_tax':
                            base_imp = retencion.base_impuesto_pesos
                            base_imp_mon_ext = retencion.base_impuesto
                        else:
                            base_imp = retencion.base_linea_pesos
                            base_imp_mon_ext = retencion.base_linea
                        ret = {
                            'grupo': retencion.group_id.grupo,
                            'acreedor': retencion.creditor_id.acreedor,
                            'monto': retencion.ret_amount_pesos_round,
                            'base_impuesto': base_imp,
                            'es_manual': False,
                        }
                    else:
                        ret = {
                            'grupo': retencion.group_id.grupo,
                            'acreedor': retencion.creditor_id.acreedor,
                            'monto': retencion.ret_amount_pesos_round,
                            'base_impuesto': retencion.ret_amount_pesos_round,
                            'es_manual': True,
                        }
                    # si todavia no se cargo una retencion para el acreedor la inserto en la lista y actualizo el diccionario
                    if retencion.creditor_id.id not in ret_creditor_id:
                        ret_creditor_id[retencion.creditor_id.id] = len(retenciones)
                        retenciones.append(ret)
                    # si ya se cargo una retencion para el acreedor actualizo los valores monto y base impuesto sumando los nuevos valores
                    else:
                        retenciones[ret_creditor_id[retencion.creditor_id.id]]['monto'] += ret['monto']
                        retenciones[ret_creditor_id[retencion.creditor_id.id]]['base_impuesto'] += ret[
                            'base_impuesto']

            # Control de no enviar llave presupuestal vacia
            if len(fondo_rotatorio.llpapg_ids) == 0:
                raise exceptions.ValidationError(_(u'Debe cargar al menos una llave presupuestal.'))

            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if fondo_rotatorio.siif_financiamiento.exceptuado_sice or fondo_rotatorio.siif_tipo_ejecucion.exceptuado_sice or fondo_rotatorio.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.env['presupuesto.objeto.gasto']
                for llave_pres in fondo_rotatorio.llpapg_ids:
                    objeto_gasto_ids = objeto_gasto_obj.search([('name', '=', llave_pres.odg),
                                                                ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise exceptions.ValidationError(_(u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                            llave_pres.odg, llave_pres.auxiliar))

            # se obliga contra el SIIF
            context = dict(self._context or {})
            context.update({'fiscalyear_id': fondo_rotatorio.fiscal_year_id and fondo_rotatorio.fiscal_year_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(self._cr, self._uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_obl_sist_aux = self.pool.get('ir.sequence').get(self._cr, self._uid, 'sec.siif.obligacion', context=context)
            nro_obl_sist_aux = nro_obl_sist_aux[4:]

            xml_obligacion = generador_xml.gen_xml_obligacion_3en1_fr(fondo_rotatorio=fondo_rotatorio, llaves_presupuestales=fondo_rotatorio.llpapg_ids,
                                                                      importe=fondo_rotatorio.liquido_pagable, nro_carga=nro_carga, tipo_doc_grp=tipo_doc_grp,
                                                                      nro_modif_grp=0,
                                                                      tipo_modificacion='A',
                                                                      retenciones=retenciones,
                                                                      enviar_datos_sice=enviar_datos_sice,
                                                                      nro_obl_sist_aux=nro_obl_sist_aux)

            resultado_siif = siif_proxy.put_solic(xml_obligacion)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):
                if dicc_modif.get('nro_afectacion', None) is None and movimiento.find(
                        'nro_afectacion').text and movimiento.find('nro_afectacion').text.strip():
                    dicc_modif['nro_afectacion'] = movimiento.find('nro_afectacion').text
                if dicc_modif.get('nro_compromiso', None) is None and movimiento.find(
                        'nro_compromiso').text and movimiento.find('nro_compromiso').text.strip():
                    dicc_modif['nro_compromiso'] = movimiento.find('nro_compromiso').text
                if dicc_modif.get('nro_obligacion', None) is None and movimiento.find(
                        'nro_obligacion').text and movimiento.find('nro_obligacion').text.strip():
                    dicc_modif['nro_obligacion'] = movimiento.find('nro_obligacion').text
                if dicc_modif.get('resultado', None) is None and movimiento.find(
                        'resultado').text and movimiento.find('resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_obligacion', None) is None and movimiento.find(
                        'sec_obligacion').text and movimiento.find('sec_obligacion').text.strip():
                    dicc_modif['siif_sec_obligacion'] = movimiento.find('sec_obligacion').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find(
                        'nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise exceptions.ValidationError(_(descr_error or u'Error no especificado por el SIIF'))
                if dicc_modif.get('nro_obligacion', None) and dicc_modif.get('nro_compromiso', None) \
                        and dicc_modif.get('nro_afectacion', None) and dicc_modif.get('resultado', None):
                    break

            # error en devolucion de numero de obligacion
            if not dicc_modif.get('nro_obligacion', None):
                raise exceptions.ValidationError(_(descr_error or u'Error en devolución de número de obligación por el SIIF'))

            # Enviar factura como 3 en 1, actualizar Monto Autorizado y Comprometido, condicion de factura y etapa del gasto = 3en1

            dicc_modif['monto_afectado'] = int(round(fondo_rotatorio.total_reponer, 0))
            dicc_modif['monto_comprometido'] = int(round(fondo_rotatorio.total_reponer, 0))
            dicc_modif['nro_obl_sist_aux'] = nro_obl_sist_aux

            res_write_fr = fondo_rotatorio.write(dicc_modif)

            if res_write_fr:
                modif_obligacion_log_obj = self.env['modif_obligacion_siif_fr_log']
                for llave in fondo_rotatorio.llpapg_ids:
                    vals = {
                        'fondo_rotatorio_id': fondo_rotatorio.id,
                        'tipo': 'A',
                        'fecha': fields.Date.today(),
                        'programa': llave.programa,
                        'proyecto': llave.proyecto,
                        'moneda': llave.mon,
                        'tipo_credito': llave.tc,
                        'financiamiento': llave.fin,
                        'objeto_gasto': llave.odg,
                        'auxiliar': llave.auxiliar,
                        'importe': llave.importe,
                        'siif_sec_obligacion': dicc_modif.get('siif_sec_obligacion', False),
                        'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                    }
                    modif_obligacion_log_obj.create(vals)
        return True

    @api.multi
    def act_fr_obligado(self):
        self._check_totales()
        company = self.env.user.company_id
        integracion_siif = company.integracion_siif or False
        if integracion_siif and self.filtered(lambda r: r.nro_obligacion):
            raise ValidationError("Este documento ya ha sido enviado a SIIF. Por favor, actualice el navegador.")
        self.fr_impactar_presupuesto()
        if not integracion_siif:
            self.state = 'obligado'
        else:
            self.fr_enviar_siif()
            self.state = 'obligado'

    @api.multi
    def fr_cancel_presupuesto(self):
        estructura_obj = self.env['presupuesto.estructura']

        for fondo_rotatorio in self:

            for llave in fondo_rotatorio.llpapg_ids:
                estructura = estructura_obj.obtener_estructura(fondo_rotatorio.fiscal_year_id.id,
                                                               fondo_rotatorio.inciso_siif_llp_id.inciso,
                                                               fondo_rotatorio.ue_siif_llp_id.ue,
                                                               llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                               llave.fin, llave.odg, llave.auxiliar)
                # Control: que no exista una estructura
                if estructura is None:
                    desc_error = '(%s - %s - %s - %s - %s - %s - %s - %s - %s - %s)' % \
                                 (fondo_rotatorio.fiscal_year_id.code, fondo_rotatorio.inciso_siif_llp_id.inciso,
                                  fondo_rotatorio.ue_siif_llp_id.ue,
                                  llave.odg, llave.auxiliar, llave.fin, llave.programa, llave.proyecto, llave.mon,
                                  llave.tc)
                    raise exceptions.ValidationError(
                        u'No se encontró estructura con la llave presupuestal asociada al fondo rotatorio: ' + desc_error)

                # Se obliga en el presupuesto (* -1), si es 3en1 se afecta, compromete y obliga
                res_af = estructura_obj.afectar(fondo_rotatorio.id, 8, -1 * llave.importe, estructura)
                res_comp = estructura_obj.comprometer(fondo_rotatorio.id, 8, -1 * llave.importe, estructura)
                res_obligar = estructura_obj.obligar(fondo_rotatorio.id, 8, -1 * llave.importe, estructura)
        return True

    def fr_borrar_siif(self):
        generador_xml = self.env['grp.siif.xml_generator']
        siif_proxy = self.env['siif.proxy']

        tipo_doc_grp = '04'

        for fondo_rotatorio in self:

            context = dict(self._context or {})
            context.update({'fiscalyear_id': fondo_rotatorio.fiscal_year_id and fondo_rotatorio.fiscal_year_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(self._cr, self._uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]
            nro_obl_sist_aux = self.pool.get('ir.sequence').get(self._cr, self._uid, 'sec.siif.obligacion', context=context)
            nro_obl_sist_aux = nro_obl_sist_aux[4:]

            # SE OBLIGA CONTRA SIIF
            nro_modif_grp = fondo_rotatorio.siif_ult_modif

            enviar_datos_sice = False
            if fondo_rotatorio.siif_financiamiento.exceptuado_sice or fondo_rotatorio.siif_tipo_ejecucion.exceptuado_sice or fondo_rotatorio.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.env['presupuesto.objeto.gasto']
                for llave_pres in fondo_rotatorio.llpapg_ids:

                    objeto_gasto_ids = objeto_gasto_obj.search([('name', '=', llave_pres.odg),
                                                                ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise exceptions.ValidationError(
                            _(u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                llave_pres.odg, llave_pres.auxiliar))

            xml_borrar_obligacion = generador_xml.gen_xml_borrado_3en1_fr(fondo_rotatorio=fondo_rotatorio, nro_carga=nro_carga,
                                                                          tipo_doc_grp=tipo_doc_grp, nro_modif_grp=nro_modif_grp,
                                                                          nro_obl_sist_aux=fondo_rotatorio.nro_obl_sist_aux)
            resultado_siif = siif_proxy.put_solic(xml_borrar_obligacion)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            for movimiento in xml_root.findall('movimiento'):
                if movimiento.find('resultado').text == 'B':
                    dicc_modif['nro_afectacion'] = False
                    dicc_modif['nro_compromiso'] = False
                    dicc_modif['nro_obligacion'] = False
                    dicc_modif['siif_sec_obligacion'] = False
                    dicc_modif['siif_ult_modif'] = False
                    dicc_modif['nro_obl_sist_aux'] = False

                    # Historico
                    anulacion_fr_log_obj = self.env['obligacion.fr.anulacion.siif.log']

                    # anulacion_siif_log_ids
                    vals_history = {
                        'fondo_rotatorio_id': fondo_rotatorio.id,
                        'fecha': fields.Date.today(),
                        'nro_afectacion_siif': fondo_rotatorio.nro_afectacion or 0,
                        'nro_compromiso': fondo_rotatorio.nro_compromiso or 0,
                        'nro_obligacion': fondo_rotatorio.nro_obligacion or 0,
                        'nro_obl_sist_aux': fondo_rotatorio.nro_obl_sist_aux or False,
                    }
                    id = anulacion_fr_log_obj.create(vals_history)

                    # Borrando valores (log de llave presupuestal)
                    if fondo_rotatorio.modif_obligacion_log_fr_ids:
                        fondo_rotatorio.modif_obligacion_log_fr_ids.unlink()

                    fondo_rotatorio.write(dicc_modif)

                else:
                    descr_error = movimiento.find('comentario').text
                    raise exceptions.ValidationError(u'Error al intentar borrar obligación en SIIF: %s' % (descr_error or u'Error no especificado por el SIIF'))
            return True

    @api.multi
    def act_fr_borrar_siif(self):
        self.fr_cancel_presupuesto()

        company = self.env['res.users'].browse(self._uid).company_id
        integracion_siif = company.integracion_siif or False
        if integracion_siif:
            self.fr_borrar_siif()
        self.state = 'draft'

    @api.multi
    def act_fr_nueva_modificacion(self):
        return True

    def fr_cancel_siif(self):

        generador_xml = self.env['grp.siif.xml_generator']
        siif_proxy = self.env['siif.proxy']

        tipo_doc_grp = '04'

        for fondo_rotatorio in self:

            context = dict(self._context or {})
            context.update({'fiscalyear_id': fondo_rotatorio.fiscal_year_id and fondo_rotatorio.fiscal_year_id.id or False})
            nro_carga = self.pool.get('ir.sequence').get(self._cr, self._uid, 'num_carga_siif', context=context)  # AÑO-INCISO-UE
            nro_carga = nro_carga[4:]

            monto_desobligar = 0
            for llave in fondo_rotatorio.llpapg_ids:
                monto_desobligar += llave.importe
            monto_desobligar *= -1

            nro_modif_grp = fondo_rotatorio.siif_ult_modif + 1

            # Control de no enviar campos de SICE si alguna de las llaves tiene exceptuado_sice = True
            enviar_datos_sice = False
            if fondo_rotatorio.siif_financiamiento.exceptuado_sice or fondo_rotatorio.siif_tipo_ejecucion.exceptuado_sice or fondo_rotatorio.siif_concepto_gasto.exceptuado_sice:
                enviar_datos_sice = False
            else:
                objeto_gasto_obj = self.env['presupuesto.objeto.gasto']

                for llave_pres in fondo_rotatorio.llpapg_ids:

                    objeto_gasto_ids = objeto_gasto_obj.search([('name', '=', llave_pres.odg),
                                                                ('auxiliar', '=', llave_pres.auxiliar)])
                    if len(objeto_gasto_ids) > 0:
                        ogasto = objeto_gasto_obj.browse(objeto_gasto_ids[0])
                        if not ogasto.exceptuado_sice:
                            enviar_datos_sice = True
                    else:
                        raise exceptions.ValidationError(
                            _(u'No se encontró objeto del gasto con ODG %s, y Auxiliar %s.') % (
                                llave_pres.odg, llave_pres.auxiliar))

            # retenciones = []

            xml_cancel_obligacion = generador_xml.gen_xml_obligacion_3en1_fr(fondo_rotatorio=fondo_rotatorio,
                                                                             llaves_presupuestales=fondo_rotatorio.llpapg_ids,
                                                                             importe=monto_desobligar,
                                                                             nro_carga=nro_carga,
                                                                             tipo_doc_grp=tipo_doc_grp,
                                                                             nro_modif_grp=nro_modif_grp,
                                                                             tipo_modificacion='N',
                                                                             es_modif=True,
                                                                             motivo="Anulacion Obligacion 3en1 Fondo Rotatorio",
                                                                             # retenciones=retenciones,
                                                                             enviar_datos_sice=enviar_datos_sice,
                                                                             nro_obl_sist_aux=fondo_rotatorio.nro_obl_sist_aux)
            resultado_siif = siif_proxy.put_solic(xml_cancel_obligacion)

            # conversiones del xml resultado
            xml_root = etree.fromstring(resultado_siif)
            str_xml_list = xml_root.xpath("//*[local-name()='return']")
            str_xml = str_xml_list[0].text
            if str_xml.find('?>') != -1:
                str_xml = str_xml.split('?>')[1]
            xml_root = etree.fromstring(str_xml)

            dicc_modif = {}
            descr_error = ''
            for movimiento in xml_root.findall('movimiento'):
                if dicc_modif.get('nro_obligacion', None) is None and movimiento.find(
                        'nro_obligacion').text and movimiento.find('nro_obligacion').text.strip():
                    dicc_modif['nro_obligacion'] = movimiento.find('nro_obligacion').text
                if dicc_modif.get('resultado', None) is None and movimiento.find('resultado').text and movimiento.find(
                        'resultado').text.strip():
                    dicc_modif['resultado'] = movimiento.find('resultado').text
                if dicc_modif.get('siif_sec_obligacion', None) is None and movimiento.find(
                        'sec_obligacion').text and movimiento.find('sec_obligacion').text.strip():
                    dicc_modif['siif_sec_obligacion'] = movimiento.find('sec_obligacion').text
                if dicc_modif.get('siif_ult_modif', None) is None and movimiento.find(
                        'nro_modif_sist_aux').text and movimiento.find('nro_modif_sist_aux').text.strip():
                    dicc_modif['siif_ult_modif'] = movimiento.find('nro_modif_sist_aux').text
                if not descr_error and movimiento.find('comentario').text and len(movimiento.find('comentario').text) > 5:
                    descr_error = movimiento.find('comentario').text
                # Si viene E en alguno de los movimientos se larga el error
                if movimiento.find('resultado').text == 'E':
                    raise exceptions.ValidationError(u'Error al anular obligación 3e1 Fondo Rotatorio en SIIF: %s') % \
                          (descr_error or u'Error no especificado por el SIIF')
                if dicc_modif.get('nro_obligacion', None) and dicc_modif.get('resultado', None):
                    break

            # Historico
            anulacion_fr_log_obj = self.env['obligacion.fr.anulacion.siif.log']

            # anulacion_siif_log_ids
            vals_history = {
                'fondo_rotatorio_id': fondo_rotatorio.id,
                'fecha': fields.Date.today(),
                'nro_afectacion_siif': fondo_rotatorio.nro_afectacion or 0,
                'nro_compromiso': fondo_rotatorio.nro_compromiso or 0,
                'nro_obligacion': fondo_rotatorio.nro_obligacion or 0,
                'nro_obl_sist_aux': fondo_rotatorio.nro_obl_sist_aux or False,
            }
            id = anulacion_fr_log_obj.create(vals_history)

            modif_obligacion_log_obj = self.env['modif_obligacion_siif_fr_log']
            for llave in fondo_rotatorio.llpapg_ids:
                vals = {
                    'fondo_rotatorio_id': fondo_rotatorio.id,
                    'tipo': 'N',
                    'fecha': fields.Date.today(),
                    'programa': llave.programa,
                    'proyecto': llave.proyecto,
                    'moneda': llave.mon,
                    'tipo_credito': llave.tc,
                    'financiamiento': llave.fin,
                    'objeto_gasto': llave.odg,
                    'auxiliar': llave.auxiliar,
                    'importe': -llave.importe,
                    'siif_sec_obligacion': dicc_modif.get('siif_sec_obligacion', False),
                    'siif_ult_modif': dicc_modif.get('siif_ult_modif', False),
                }
                modif_obligacion_log_obj.create(vals)

            dicc_modif.update({'nro_obl_sist_aux': False, 'nro_obligacion': False, 'state': 'anulado_siif'})

            fondo_rotatorio.write(dicc_modif)

        return True

    @api.multi
    def act_fr_anulado_siif(self):
        self.fr_cancel_presupuesto()

        company = self.env['res.users'].browse(self._uid).company_id
        integracion_siif = company.integracion_siif or False
        if integracion_siif:
            self.fr_cancel_siif()
        self.state = 'anulado_siif'

    @api.multi
    def act_fr_cancelado(self):
        for rec in self:
            # desmarcar comprobantes al cancelar para que se vuelvan a agrupar
            for line in self.line_invoice_fr_ids:
                line.supplier_invoice_id.write({'fondo_rotarios': False})
            for line in self.line_expense_ids:
                line.hr_expense_id.write({'fondo_rotarios': False})
            for line in self.line_expense_vales_ids:
                line.hr_expense_id.write({'fondo_rotarios': False})
            for line in self.line_statement_ids:
                if line.caja_chica_line_id:
                    line.caja_chica_line_id.write({'fondo_rotario': False})
                if line.bank_statement_id:
                    line.bank_statement_id.write({'fondo_rotarios': False})
            for line in self.line_expense_abonos_ids:
                line.hr_expense_id.write({'fondo_rotarios': False})
            rec.write({'state': 'cancelado'})

    def _get_vals_write(self, vals):
        vals_write = {}
        # if vals.get('line_fondo_rotatorio_ids', False):
        #     vals_write['dlineas_llavep_invoice_ids'] = fondo_rotatorio.update_line_invoice_ids()
        if vals.get('line_invoice_fr_ids', False):
            vals_write['dlineas_llavep_invoice_fr_ids'] = self.update_line_invoice_fr_ids()
        if vals.get('line_statement_ids', False):
            vals_write['dlineas_llavep_bank_statement_ids'] = self.update_line_statement_ids()
        if vals.get('line_expense_ids', False):
            vals_write['dlineas_llavep_hr_expense_ids'] = self.update_line_expense_ids('hr_expense')
        if vals.get('line_expense_vales_ids', False):
            vals_write['dlineas_llavep_hr_expense_vales_ids'] = self.update_line_expense_ids('hr_expense_v')
        return vals_write

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.model
    def create(self, vals):
        fondo_rotatorio = super(grp_fondo_rotatorio, self).create(vals)
        vals_write = fondo_rotatorio._get_vals_write(vals)

        if vals_write:
            llpapg_ids = fondo_rotatorio.update_detalles_lineas_llavep(vals_write)
            if llpapg_ids:
                vals_write['llpapg_ids'] = llpapg_ids
            fondo_rotatorio.write(vals_write)

        fondo_rotatorio.action_update_retentions()
        return fondo_rotatorio

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.multi
    def write(self, values):
        vals_write = {}
        vals_write_aux = {}
        if values.get('line_invoice_fr_ids', False):
            vals_write_aux['line_invoice_fr_ids'] = values.get('line_invoice_fr_ids', False)
            values['dlineas_llavep_invoice_fr_ids'] = [(5,)]
        if values.get('line_expense_ids', False):
            values['dlineas_llavep_hr_expense_ids'] = [(5,)]
        if values.get('line_statement_ids', False):
            vals_write_aux['line_statement_ids'] = values.get('line_statement_ids', False)
            values['dlineas_llavep_bank_statement_ids'] = [(5,)]
        if len(vals_write_aux) > 0:
            llpapg_ids = self[0].update_write_detalles_lineas_llavep(vals_write_aux)
            if len(llpapg_ids) > 0:
                vals_write['llpapg_ids'] = llpapg_ids
        # if values.get('line_invoice_ids', False) or values.get('line_invoice_fr_ids', False) or values.get('line_expense_ids', False) or values.get('line_statement_ids', False):
        if values.get('line_invoice_fr_ids', False) or values.get('line_expense_ids', False) or values.get('line_statement_ids', False):
            values['llpapg_ids'] = [(5,)]

        fondo_rotatorios = super(grp_fondo_rotatorio, self).write(values)

        if values.get('line_invoice_fr_ids', False):
            dlineas_llavep_invoice_fr_ids = self[0].update_line_invoice_fr_ids()
            if len(dlineas_llavep_invoice_fr_ids) > 0:
                vals_write['dlineas_llavep_invoice_fr_ids'] = dlineas_llavep_invoice_fr_ids
                vals_write['retention_ids'] = self._get_retentions_dict()
        if values.get('line_statement_ids', False):
            dlineas_llavep_bank_statement_ids = self[0].update_line_statement_ids()
            if len(dlineas_llavep_bank_statement_ids) > 0:
                vals_write['dlineas_llavep_bank_statement_ids'] = dlineas_llavep_bank_statement_ids
        if len(vals_write) > 0:
            super(grp_fondo_rotatorio, self).write(vals_write)
        return fondo_rotatorios

    # TODO: SPRING 8 GAP 111.228.339 K
    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids):
            # ps7.id=3019 "3 en 1 FR - No dejar suprimir...." La solución solicitada fue no suprimir si no es borrador
            if rec.state != 'draft':
                raise ValidationError(_('Error! Solamente se permite suprimir documentos en estado Borrador.'))
            fondo_rotarios_line_obj = self.pool.get('grp.fondo.rotatorio.line')
            fondo_rotatorios_line_ids = fondo_rotarios_line_obj.search(cr, uid, [('fondo_rotatorios_id', '=', rec.id)])
            fondo_rotarios_line_obj.unlink(cr, uid, fondo_rotatorios_line_ids, context)
        return super(grp_fondo_rotatorio, self).unlink(cr, uid, ids, context=context)

    # TODO R LLAVES PRESUPUESTALES
    @api.multi
    def action_llpapg_reload(self):
        for rec in self:
            llpapgs = [(5,)]
            sql = """SELECT odg_id,auxiliar_id,SUM(importe) AS importe
                FROM grp_detalles_lineas_llavep
                WHERE fondo_rotarios_ld_id = %s
                GROUP BY odg_id,auxiliar_id""" % (rec.id)
            self._cr.execute(sql)
            for line in self._cr.dictfetchall():
                llpapgs.append((0, 0, {'odg_id': line['odg_id'], 'auxiliar_id': line['auxiliar_id'],
                                       'importe': line['importe']}))
            rec.write({'llpapg_ids': llpapgs})

    # TODO: R RETENCIONES EN FR
    def _get_retentions_dict(self):
        retentions = []
        for line in self.env['account.invoice.summary.group.ret'].search([('invoice_id', 'in', [x.supplier_invoice_id.id for x in self.line_invoice_fr_ids])]):
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
                retentions.append((0, 0, {'creditor_id': line.creditor_id.id,
                                          'retention_id':line.retention_id.id,
                                          'iva': line.iva,
                                          'group_id': line.group_id.id,
                                          'tipo_retencion': line.tipo_retencion,
                                          'base_linea': line.base_linea,
                                          'base_linea_pesos': line.base_linea_pesos,
                                          'base_impuesto': line.base_impuesto,
                                          'base_impuesto_pesos': line.base_impuesto_pesos,
                                          'monto_retencion': line.monto_retencion,
                                          'monto_retencion_unround': line.monto_retencion_unround,
                                          'monto_retencion_pesos': line.monto_retencion_pesos,
                                          'monto_retencion': line.monto_retencion,
                                          'monto_retencion_unround': line.monto_retencion_unround,
                                          'monto_retencion_pesos': line.monto_retencion_pesos,
                                          'ret_amount_round': line.ret_amount_round,
                                          'ret_amount_pesos_round': line.ret_amount_pesos_round
                                          }))
        retentions.insert(0, (5,))
        return retentions

    # TODO: R RETENCIONES EN FR
    @api.one
    def action_update_retentions(self):
        self.write({
            'retention_ids': self._get_retentions_dict()
        })


    @api.multi
    def btn_observ_tribunal(self):
        siif_proxy = self.env['siif.proxy']
        motivo_intervencion = self.env['motivo.intervencion.tc']
        observacion = self.env['grp.observacion.tc.fr']

        for rec in self:
            # _logger.info('rec.state: %s', rec.state)
            # _logger.info('rec.fiscal_year_id: %s', rec.fiscal_year_id.name)
            # _logger.info('rec.nro_afectacion: %s', rec.nro_afectacion)
            # _logger.info('rec.nro_compromiso: %s', rec.nro_compromiso)
            # _logger.info('rec.nro_obligacion: %s', rec.nro_obligacion)
            # _logger.info('rec.inciso_siif_llp_id: %s', rec.inciso_siif_llp_id.inciso)
            # _logger.info('rec.ue_siif_llp_id: %s', rec.ue_siif_llp_id.ue)

            intervencion = siif_proxy.get_intervenciones(rec.fiscal_year_id.name, rec.inciso_siif_llp_id.inciso, rec.ue_siif_llp_id.ue, rec.nro_afectacion, rec.nro_compromiso, rec.nro_obligacion, 0)
            # intervencion = siif_proxy.get_intervenciones('2017', '12', '001', '297', '1', '1', '0')
            _logger.info('intervencion: %s', intervencion)

            if intervencion.resultado == 1:

                # _logger.info('intervencion.motivoDeIntervencion: %s', intervencion.motivoDeIntervencion)
                # _logger.info('intervencion.descripcionMotivoIntervencion: %s',
                #              intervencion.descripcionMotivoIntervencion)
                # _logger.info('intervencion.observacionInterv: %s', intervencion.observacionInterv)

                motivo = motivo_intervencion.search([('codigo', '=', intervencion.motivoDeIntervencion)])
                if not motivo:
                    raise exceptions.ValidationError(_(
                        u'No se ha encontrado motivo de intervención en el catálogo de Motivo Intervenciones para el código %s retornado por SIIF') % (
                        intervencion.motivoDeIntervencion))
                else:
                    if motivo.impacta_documento:
                        # Crear registro en grilla de Observaciones
                        obs = {
                            'fondo_rotatorio_id': self.id,
                            'motivo_intervencion_id': motivo.id,
                            # 'observacion': intervencion.observacionInterv,
                        }
                        obs = observacion.create(obs)

                        # Marcar campo 'Intervenido con Observaciones'
                        self.write({'intervenido_con_observ': True})
                    else:
                        # Desmarcar campo 'Intervenido con Observaciones'
                        if rec.intervenido_con_observ:
                            self.write({'intervenido_con_observ': False})



# TODO: SPRING 8 GAP 111.228.339 K
class grp_fondo_rotatorio_line(models.Model):
    _name = 'grp.fondo.rotatorio.line'

    @api.one
    @api.depends('bank_statement_id', 'caja_chica_line_id')
    def _compute_caja_vals(self):
        if self.bank_statement_id or self.caja_chica_line_id:
            self.referencia = self.bank_statement_id and self.bank_statement_id.name or self.caja_chica_line_id.ref
            self.fecha_registro = self.bank_statement_id and self.bank_statement_id.date or self.caja_chica_line_id.date
            self.concepto_gasto = self.bank_statement_id and self.bank_statement_id.concepto_id or self.caja_chica_line_id.concept_cc_id
            self.importe_pago_registro = self.bank_statement_id and (-1)*self.bank_statement_id.amount or (-1)*self.caja_chica_line_id.amount

    fondo_rotatorios_id = fields.Many2one('grp.fondo.rotatorio', string=u'Fondo rotatorio', ondelete='cascade')

    hr_expense_id = fields.Many2one('hr.expense.expense', u'Rendición')
    bank_statement_id = fields.Many2one('account.bank.statement.line', u'Registro de caja')
    caja_chica_line_id = fields.Many2one('grp.caja.chica.tesoreria.line', u'Registro de caja')
    supplier_invoice_id = fields.Many2one('account.invoice', u'Facturas de proveedor')

    proveedor = fields.Many2one(related='supplier_invoice_id.partner_id', string='Proveedor', store=True, readonly=True)
    fecha_factura = fields.Date(related='supplier_invoice_id.date_invoice', string='Fecha', store=True, readonly=True)
    no_factura = fields.Char(related='supplier_invoice_id.nro_factura_grp', string='Nº Factura', store=True, readonly=True)
    importe_nominal_factura = fields.Float(related='supplier_invoice_id.total_nominal_divisa_cpy', string='Importe nominal', store=True, readonly=True)
    importe_pago_factura = fields.Float(related='supplier_invoice_id.importe_pago', string='Importe comprobante', store=True, readonly=True)
    total_retenciones_factura = fields.Float(related='supplier_invoice_id.amount_total_retention', string='Total retenciones', store=True, readonly=True)
    empleado = fields.Many2one(related='hr_expense_id.employee_id', string='Empleado', store=True, readonly=True)
    fecha_gasto = fields.Date(related='hr_expense_id.date', string='Fecha', store=True, readonly=True)
    descripcion_gasto = fields.Char(related='hr_expense_id.name', string='Descripción', store=True, readonly=True)
    importe_pago_gasto = fields.Float(related='hr_expense_id.amount', string='Importe comprobante', store=True, readonly=True)

    #referencia = fields.Char(related='bank_statement_id.name', string='Referencia', store=True)
    #fecha_registro = fields.Date(related='bank_statement_id.date', string='Fecha', store=True)
    #concepto_gasto = fields.Many2one(related='bank_statement_id.concepto_id', string='Concepto', store=True)
    #importe_pago_registro = fields.Float(related='bank_statement_id.amount', string='Importe comprobante', store=True)
    referencia = fields.Char(compute='_compute_caja_vals', string='Referencia', store=True)
    fecha_registro = fields.Date(compute='_compute_caja_vals', string='Fecha', store=True)
    concepto_gasto = fields.Many2one('grp_concepto_gasto_cc_viaticos', compute='_compute_caja_vals', string='Concepto', store=True)
    importe_pago_registro = fields.Float(compute='_compute_caja_vals', string='Importe comprobante', store=True)

    tipo_documento = fields.Selection([('account_invoice', 'Facturas de proveedor'),
                                       ('account_invoice_fr', 'Facturas de fondo rotatorio'),
                                       ('hr_expense', 'Rendición de viático'),
                                       ('hr_expense_v', 'Vales'),
                                       ('bank_statement', 'Registro de caja'),
                                       ('hr_expense_a', 'Abonos')], 'Tipo', size=86, default='account_invoice')

    currency_id = fields.Many2one('res.currency', string='Moneda', related='fondo_rotatorios_id.currency_id',
                                  readonly=True)

    amount_currency = fields.Float(u'Importe comprobante M/E',
                                   compute='_compute_currency_amounts',
                                   multi='_compute_currency_amounts',
                                   store=True)
    amount_retentions_currency = fields.Float(u'Retenciones M/E',
                                              compute='_compute_currency_amounts',
                                              multi='_compute_currency_amounts',
                                              store=True)
    liquido_pagable_currency = fields.Float(u'Líquido pagable M/E',
                                            compute='_compute_currency_amounts',
                                            multi='_compute_currency_amounts',
                                            store=True)
    liquido_pagable_ajustado_currency = fields.Float(u'Líquido pagable ajustado M/E')

    amount = fields.Float('Importe pago', compute='_compute_amount', store=False)

    liquido_pagable = fields.Float(u'Líquido pagable pesos', compute='_compute_liquido_pagable', store=True)

    def _get_company_currency_amount(self, voucher_id, currency_from, amount, move_line2currency_rate_id = False):
        company_currency_id = self.env.user.company_id.currency_id
        if voucher_id and currency_from.id != company_currency_id.id:
            _move_line2currency_rate_id = voucher_id.move_ids.filtered(
                lambda x: x.account_id.id == x.move_id.journal_id.default_credit_account_id.id)
            if _move_line2currency_rate_id:
                company_currency_amount = _move_line2currency_rate_id[0].debit + _move_line2currency_rate_id[0].credit
                company_currency_rate = company_currency_amount / voucher_id.amount
                _amount = amount * company_currency_rate
            else:
                _amount = voucher_id.currency_id.with_context(date=voucher_id.entry_date).compute(amount,
                                                                                                  company_currency_id,
                                                                                                  round=False)
        else:
            _amount = amount
        return _amount


    def _get_amount(self, voucher_line_id, ajuste_precision = 0):
        if voucher_line_id:
            difference = abs(float_round(voucher_line_id.voucher_id.amount, 2) - float_round(voucher_line_id.amount_unreconciled, 2))
            if ajuste_precision >= difference:
                _amount = voucher_line_id.voucher_id.amount
            else:
                voucher_rounding_amount = voucher_line_id.voucher_id.amount - voucher_line_id.voucher_id.topay_amount
                if voucher_line_id.voucher_id.currency_id.is_zero(voucher_rounding_amount):
                    _amount = voucher_line_id.voucher_id.currency_id.round(voucher_line_id.amount)
                else:
                    plus_amount = voucher_rounding_amount / len(
                        voucher_line_id.voucher_id.line_ids.filtered(lambda x: x.amount != 0))
                    _amount = voucher_line_id.voucher_id.currency_id.round(voucher_line_id.amount) + plus_amount
        else:
            _amount = 0
        return _amount


    @api.multi
    @api.depends('supplier_invoice_id', 'bank_statement_id', 'hr_expense_id')
    def _compute_amount(self):
        voucher_obj = self.env['account.voucher']
        voucher_line_obj = self.env['account.voucher.line']
        company_currency_id = self.env.user.company_id.currency_id
        ajuste_id = self.env['grp.ajuste.redondeo'].search([('moneda','=',company_currency_id.id)], limit=1)
        ajuste_precision = ajuste_id and ajuste_id.ajuste_redondeo or 0.50
        for rec in self:
            sudo_rec = rec.suspend_security()
            _amount = 0
            if sudo_rec.bank_statement_id.exists() or sudo_rec.caja_chica_line_id.exists():
                _amount = sudo_rec.importe_pago_registro
            elif sudo_rec.supplier_invoice_id.exists():
                voucher_line_ids = voucher_line_obj.search([('move_line_id.move_id','=',sudo_rec.supplier_invoice_id.move_id.id),
                                                           ('voucher_id.state', '=', 'posted'),
                                                           ('amount', '!=', 0)])
                for voucher_line_id in voucher_line_ids:
                    difference = abs(float_round(voucher_line_id.voucher_id.amount, 2) - float_round(voucher_line_id.amount_unreconciled,2))
                    if ajuste_precision >= difference:
                        _partial_amount = voucher_line_id.voucher_id.amount
                    else:
                        _partial_amount = voucher_line_id.voucher_id.currency_id.round(voucher_line_id.amount)
                    _amount += self._get_company_currency_amount(voucher_line_id.voucher_id, voucher_line_id.voucher_id.currency_id, _partial_amount)
            elif sudo_rec.hr_expense_id.exists():
                if (sudo_rec.hr_expense_id.solicitud_anticipos_id and sudo_rec.hr_expense_id.amount != sudo_rec.hr_expense_id.solicitud_anticipos_id.amount_total) or (
                        sudo_rec.hr_expense_id.solicitud_viatico_id and sudo_rec.hr_expense_id.amount != sudo_rec.hr_expense_id.solicitud_viatico_id.total):
                    if sudo_rec.hr_expense_id.doc_type == u'rendicion_anticipo':
                        # RENDICION AMOUNT
                        voucher_line_id = voucher_line_obj.search([
                            ('origin_voucher_id.rendicion_anticipos_id', '=', sudo_rec.hr_expense_id.id),
                            ('voucher_id.state', '=', 'posted'),
                            ('amount', '!=', 0)], limit=1)
                        if voucher_line_id:
                            _partial_amount = self._get_amount(voucher_line_id, ajuste_precision)
                            _unsign_amount = self._get_company_currency_amount(voucher_line_id.voucher_id,
                                                                               voucher_line_id.voucher_id.currency_id,
                                                                               _partial_amount)
                            if voucher_line_id.voucher_id.type == 'receipt':
                                _amount -= _unsign_amount
                            else:
                                _amount += _unsign_amount
                        else:
                            voucher_id = voucher_obj.search([('rendicion_anticipos_id', '=', sudo_rec.hr_expense_id.id)],limit=1)
                            _partial_amount = voucher_id.amount
                            _amount -= self._get_company_currency_amount(voucher_id, voucher_id.currency_id,
                                                                         _partial_amount)

                        # SOLICITUD AMOUNT
                        if sudo_rec.hr_expense_id.solicitud_anticipos_id:
                            voucher_line_id = voucher_line_obj.search([
                                ('origin_voucher_id.solicitud_anticipos_id', '=', sudo_rec.hr_expense_id.solicitud_anticipos_id.id),
                                ('origin_voucher_id.rendicion_anticipos_id', '=', False),#obviando adelanto de rendicion
                                ('voucher_id.state', '=', 'posted'),
                                ('voucher_id.type','=',u'payment'),
                                ('amount', '!=', 0)], limit=1)
                            _partial_amount = self._get_amount(voucher_line_id, ajuste_precision)
                            _amount += self._get_company_currency_amount(voucher_line_id.voucher_id,
                                                                        voucher_line_id.voucher_id.currency_id, _partial_amount)
                    elif sudo_rec.hr_expense_id.doc_type == u'rendicion_viatico':
                        # RENDICION AMOUNT
                        voucher_line_id = voucher_line_obj.search([
                            ('origin_voucher_id.rendicion_viaticos_id', '=', sudo_rec.hr_expense_id.id),
                            ('voucher_id.state', '=', 'posted'),
                            ('amount', '!=', 0)], limit=1)
                        if voucher_line_id:
                            _partial_amount = self._get_amount(voucher_line_id, ajuste_precision)
                            _unsign_amount = self._get_company_currency_amount(voucher_line_id.voucher_id,
                                                                               voucher_line_id.voucher_id.currency_id,
                                                                               _partial_amount)
                            if voucher_line_id.voucher_id.type == 'receipt':
                                _amount -= _unsign_amount
                            else:
                                _amount += _unsign_amount
                        else:
                            voucher_id = voucher_obj.search([('rendicion_viaticos_id', '=', sudo_rec.hr_expense_id.id)],limit=1)
                            _partial_amount = voucher_id.amount
                            _amount -= self._get_company_currency_amount(voucher_id, voucher_id.currency_id,
                                                                         _partial_amount)

                        # SOLICITUD AMOUNT
                        if sudo_rec.hr_expense_id.solicitud_viatico_id:
                            voucher_line_id = voucher_line_obj.search([
                                ('origin_voucher_id.solicitud_viatico_id', '=',sudo_rec.hr_expense_id.solicitud_viatico_id.id),
                                ('origin_voucher_id.rendicion_viaticos_id', '=',False),#obviando adelanto de rendicion
                                ('voucher_id.state', '=', 'posted'),
                                ('voucher_id.type', '=', 'payment'),
                                ('amount', '!=', 0)], limit=1)
                            _partial_amount = self._get_amount(voucher_line_id, ajuste_precision)
                            _amount += self._get_company_currency_amount(voucher_line_id.voucher_id,
                                                                         voucher_line_id.voucher_id.currency_id,
                                                                         _partial_amount)
                    else:
                        _amount = round(sudo_rec.hr_expense_id.amount)
                        # _amount = self._get_company_currency_amount(voucher_line_id, voucher_line_id.voucher_id.currency_id,_amount)
                else:
                    if sudo_rec.hr_expense_id.doc_type == u'rendicion_anticipo':
                        voucher_line_id = voucher_line_obj.search([
                            ('origin_voucher_id.rendicion_anticipos_id', '=', sudo_rec.hr_expense_id.id),
                            ('voucher_id.state', '=', 'posted'),
                            ('amount', '!=', 0)], limit=1)
                        if not voucher_line_id and sudo_rec.hr_expense_id.solicitud_anticipos_id:
                            voucher_line_id = voucher_line_obj.search([
                                ('origin_voucher_id.solicitud_anticipos_id', '=',sudo_rec.hr_expense_id.solicitud_anticipos_id.id),
                                ('voucher_id.state', '=', 'posted'),
                                ('amount', '!=', 0)], limit=1)
                    else:
                        voucher_line_id = voucher_line_obj.search([
                            ('origin_voucher_id.rendicion_viaticos_id','=',sudo_rec.hr_expense_id.id),
                            ('voucher_id.state', '=', 'posted'),
                            ('amount','!=',0)], limit=1)
                        if not voucher_line_id and sudo_rec.hr_expense_id.solicitud_viatico_id:
                            voucher_line_id = voucher_line_obj.search([
                                ('origin_voucher_id.solicitud_viatico_id', '=', sudo_rec.hr_expense_id.solicitud_viatico_id.id),
                                ('voucher_id.state', '=', 'posted'),
                                ('amount', '!=', 0)], limit=1)
                    _amount = self._get_amount(voucher_line_id, ajuste_precision)
                    _amount = self._get_company_currency_amount(voucher_line_id.voucher_id,
                                                                voucher_line_id.voucher_id.currency_id,
                                                                _amount)
            rec.amount = _amount

    @api.multi
    @api.depends('hr_expense_id', 'bank_statement_id', 'caja_chica_line_id', 'supplier_invoice_id')
    def _compute_currency_amounts(self):
        for rec in self:
            if not rec.fondo_rotatorios_id.moneda_extranjera:
                _amount_currency = 0
                _amount_retentions_currency = 0
                _liquido_pagable_currency = 0
            elif rec.supplier_invoice_id:
                self._cr.execute("""select amount_total,amount_total_retention from account_invoice where id = %s""" % (rec.supplier_invoice_id.id))
                invoice_data = self._cr.fetchone()
                _amount_currency = rec.supplier_invoice_id.total_nominal_divisa_cpy
                _liquido_pagable_currency = invoice_data[0]
                _amount_retentions_currency = invoice_data[1]
            elif rec.hr_expense_id:
                _amount_currency = rec.hr_expense_id.amount
                _amount_retentions_currency = 0
                _liquido_pagable_currency = rec.hr_expense_id.amount
            elif rec.bank_statement_id:
                _amount_currency = rec.amount
                _amount_retentions_currency = 0
                _liquido_pagable_currency = rec.amount
            elif rec.caja_chica_line_id:
                _amount_currency = rec.amount
                _amount_retentions_currency = 0
                _liquido_pagable_currency = rec.amount
            else:
                _amount_currency = 0
                _amount_retentions_currency = 0
                _liquido_pagable_currency = 0

            rec.amount_currency = _amount_currency
            rec.amount_retentions_currency = _amount_retentions_currency
            rec.liquido_pagable_currency = _liquido_pagable_currency

    @api.multi
    @api.depends('liquido_pagable_ajustado_currency','fondo_rotatorios_id.moneda_extranjera','fondo_rotatorios_id.currency_rate_presupuesto','amount')
    def _compute_liquido_pagable(self):
        for rec in self:
            if not rec.fondo_rotatorios_id.moneda_extranjera:
                rec.liquido_pagable = rec.amount
            else:
                rec.liquido_pagable = rec.liquido_pagable_ajustado_currency * rec.fondo_rotatorios_id.currency_rate_presupuesto

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.multi
    def unlink(self):
        for rec in self:
            if rec.supplier_invoice_id:
                rec.supplier_invoice_id.write({'fondo_rotarios': False})
            if rec.hr_expense_id:
                rec.hr_expense_id.write({'fondo_rotarios': False})
                if rec.hr_expense_id.doc_type == u'rendicion_viatico':
                    self.env['grp.caja.chica.tesoreria.line'].search(
                        [('voucher_id.rendicion_viaticos_id', '=', rec.hr_expense_id.id)]).write({'fondo_rotario': True})
                elif rec.hr_expense_id.doc_type == u'rendicion_anticipo':
                    self.env['grp.caja.chica.tesoreria.line'].search([
                        ('voucher_id.rendicion_anticipos_id', '=', rec.hr_expense_id.id)]).write({'fondo_rotario': True})
            if rec.bank_statement_id:
                rec.bank_statement_id.write({'fondo_rotarios': False})
            if rec.caja_chica_line_id:
                rec.caja_chica_line_id.write({'fondo_rotario': False})
        return super(grp_fondo_rotatorio_line, self).unlink()

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.model
    def create(self, vals):
        vals = self._update_currency_vals(vals)
        fondo_rotatorio_line = super(grp_fondo_rotatorio_line, self).create(vals)
        if fondo_rotatorio_line.supplier_invoice_id:
            fondo_rotatorio_line.supplier_invoice_id.write({'fondo_rotarios': True})
        if fondo_rotatorio_line.hr_expense_id:
            fondo_rotatorio_line.hr_expense_id.write({'fondo_rotarios': True})
            if fondo_rotatorio_line.hr_expense_id.doc_type == u'rendicion_viatico':
                self.env['grp.caja.chica.tesoreria.line'].search([
                    ('voucher_id.rendicion_viaticos_id','=',fondo_rotatorio_line.hr_expense_id.id)]).write({'fondo_rotario':True})
            elif fondo_rotatorio_line.hr_expense_id.doc_type == u'rendicion_anticipo':
                self.env['grp.caja.chica.tesoreria.line'].search([
                    ('voucher_id.rendicion_anticipos_id','=',fondo_rotatorio_line.hr_expense_id.id)]).write({'fondo_rotario':True})
        if fondo_rotatorio_line.bank_statement_id:
            fondo_rotatorio_line.bank_statement_id.write({'fondo_rotarios': True})
        if fondo_rotatorio_line.caja_chica_line_id:
            fondo_rotatorio_line.caja_chica_line_id.write({'fondo_rotario': True})
        return fondo_rotatorio_line

    # RAGU
    def _update_currency_vals(self, vals):
        if vals.get('fondo_rotatorios_id'):
            currency = self.env['grp.fondo.rotatorio'].search([('id','=',vals.get('fondo_rotatorios_id'))], limit=1).currency_id
            if currency.id != self.env.user.company_id.currency_id.id:
                if vals.get('hr_expense_id'):
                    _liquido_pagable_ajustado_currency = self.env['hr.expense.expense'].search(
                        [('id', '=', vals.get('hr_expense_id'))], limit=1).amount
                elif vals.get('bank_statement_id'):
                    _liquido_pagable_ajustado_currency = self.env['account.bank.statement.line'].search(
                        [('id', '=', vals.get('supplier_invoice_id'))], limit=1).amount
                elif vals.get('caja_chica_line_id'):
                    _liquido_pagable_ajustado_currency = self.env['grp.caja.chica.tesoreria.line'].search(
                        [('id', '=', vals.get('caja_chica_line_id'))], limit=1).amount
                elif vals.get('supplier_invoice_id'):
                    _liquido_pagable_ajustado_currency = self.env['account.invoice'].search(
                        [('id', '=', vals.get('supplier_invoice_id'))], limit=1).amount_total
                else:
                    _liquido_pagable_ajustado_currency = 0
                vals.update({'liquido_pagable_ajustado_currency': _liquido_pagable_ajustado_currency})
        return vals


    @api.multi
    def update_liquido_pagable_ajustado_currency(self):
        for rec in self:
            if rec.fondo_rotatorios_id.currency_id and rec.fondo_rotatorios_id.currency_id.id != self.env.user.company_id.currency_id.id:
                if rec.hr_expense_id:
                    _liquido_pagable_ajustado_currency = rec.hr_expense_id.amount
                elif rec.bank_statement_id:
                    _liquido_pagable_ajustado_currency = rec.bank_statement_id.amount
                elif rec.caja_chica_line_id:
                    _liquido_pagable_ajustado_currency = rec.caja_chica_line_id.amount
                elif rec.supplier_invoice_id:
                    _liquido_pagable_ajustado_currency = rec.supplier_invoice_id.amount_total
                else:
                    _liquido_pagable_ajustado_currency = 0
            else:
                _liquido_pagable_ajustado_currency = 0
            rec.liquido_pagable_ajustado_currency = _liquido_pagable_ajustado_currency


# TODO: SPRING 8 GAP 111.228.339 K
class grp_detalles_lineas_llavep(models.Model):
    _name = 'grp.detalles.lineas.llavep'
    _description = 'Detalles de llave presupuestal'

    # TODO: SPRING 8 GAP 111.228.339 K
    def _check_linea_llavep_odg(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.odg:
                if not llp.odg.isdigit():
                    return False
        return True

    # TODO: SPRING 8 GAP 111.228.339 K
    def _check_linea_llavep_auxiliar(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.auxiliar:
                if not llp.auxiliar.isdigit():
                    return False
        return True

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.one
    @api.depends('invoice_id','hr_expense_id','bank_statement_id','caja_chica_line_id')
    def _get_comprobante(self):
        if self.invoice_id:
            self.comprobante = self.invoice_id.nro_factura_grp
        if self.hr_expense_id:
            # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
            # self.comprobante = self.hr_expense_id.sequence
            self.comprobante = self.hr_expense_id.x_sequence
            #
        if self.bank_statement_id:
            self.comprobante = self.bank_statement_id.name
        if self.caja_chica_line_id:
            self.comprobante = self.caja_chica_line_id.ref

    fondo_rotarios_ld_id = fields.Many2one('grp.fondo.rotatorio', string='Fondo rotarios', ondelete='cascade')
    fondo_rotarios_line_id = fields.Many2one('grp.fondo.rotatorio.line', string='Linea fondo rotarios', ondelete='cascade')
    invoice_id = fields.Many2one('account.invoice', u'Factura', ondelete='cascade')
    hr_expense_id = fields.Many2one('hr.expense.expense', u'Rendición de viático', ondelete='cascade')
    bank_statement_id = fields.Many2one('account.bank.statement.line', u'Registro de caja', ondelete='cascade')
    caja_chica_line_id = fields.Many2one('grp.caja.chica.tesoreria.line', u'Registro de caja', ondelete='cascade')
    comprobante = fields.Char(compute='_get_comprobante', string='Comprobante')
    odg_id = fields.Many2one('grp.estruc_pres.odg', 'ODG')
    auxiliar_id = fields.Many2one('grp.estruc_pres.aux', 'Auxiliar')
    odg = fields.Char(type='char', string='ODG related', related='odg_id.odg', store=True, readonly=True)
    auxiliar = fields.Char(string='Auxiliar related', related='auxiliar_id.aux', store=True, readonly=True)
    importe = fields.Integer('Importe')
    tipo_documento = fields.Selection([('account_invoice', 'Facturas de proveedor'),
                                       ('account_invoice_fr', 'Facturas de fondo rotatorio'),
                                       ('hr_expense', 'Rendición de viático'),
                                       ('hr_expense_v', 'Vales'),
                                       ('bank_statement', 'Registro de caja'),
                                       ('hr_expense_a', 'Abonos')], 'Tipo', size=86, default='account_invoice')
    proveedor_id = fields.Many2one(comodel_name='res.partner', string=u'Proveedor')
    descripcion_gasto = fields.Char(string=u'Descripción gasto')
    concepto_gasto = fields.Char(string=u'Concepto gasto')
    referencia = fields.Char(string=u'Referencia')

    def _check_llavep_unica(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            lineas_duplicadas = self.search(cr, uid, [('invoice_id', '=', line.afectacion_id.id),
                                                      ('hr_expense_id', '=', line.apg_id.id),
                                                      ('bank_statement_id', '=', line.auxiliar_id.id),
                                                      ('invoice_id', '=', line.compromiso_id.id),
                                                      ('auxiliar_id', '=', line.order_id.id),
                                                      ('id', 'not in', ids),
                                                      ], context=context)
            if lineas_duplicadas:
                raise exceptions.ValidationError(_(u'No se pueden ingresar 2 líneas iguales para el mismo registro.'))
        return True

    _constraints = [
        (_check_linea_llavep_odg, u'Campo no es numérico', ['odg_id']),
        (_check_linea_llavep_auxiliar, u'Campo no es numérico', ['auxiliar_id']),
    ]

    # TODO: SPRING 8 GAP 111.228.339 K
    @api.onchange('odg_id')
    def onchange_objeto_del_gasto(self):
        if self.odg_id:
            auxiliar_id = False
            auxiliar_ids = self.env['grp.estruc_pres.aux'].search([('odg_id', '=', self.odg_id.id)])
            if len(auxiliar_ids) == 1:
                auxiliar_id = auxiliar_ids[0].id
            self.auxiliar_id = auxiliar_id

class grp_fondo_rotatorio_prioritized_line(models.Model):
    _name = 'grp.fondo.rotatorio.prioritized.line'

    fondo_grp_id = fields.Many2one('grp.fondo.rotatorio', 'Fondo Rotatorio', readonly=True)
    fecha_confirmado = fields.Date('Fecha', readonly=True)
    monto_priorizado = fields.Integer('Monto', readonly=True)

class modif_obligacion_siif_fr_log(models.Model):
    _name = 'modif_obligacion_siif_fr_log'
    _description = "Log de modificaciones de obligacion SIIF"

    fondo_rotatorio_id = fields.Many2one('grp.fondo.rotatorio', string='Fondo rotario', required=True, ondelete='cascade')
    tipo = fields.Selection((('A', 'A - Aumento'), ('R', u'R - Reducción'), ('N', u'N - Anulación')), 'Tipo')
    fecha = fields.Date('Fecha', required=True)
    importe = fields.Float(string='Importe', required=True)
    programa = fields.Char('Programa', size=3, required=True)
    proyecto = fields.Char('Proyecto', size=3, required=True)
    moneda = fields.Char('MON', size=2, required=True)
    tipo_credito = fields.Char('TC', size=1, required=True)
    financiamiento = fields.Char('FF', size=2, required=True)
    objeto_gasto = fields.Char('ODG', size=3, required=True)
    auxiliar = fields.Char('AUX', size=3, required=True)
    siif_sec_obligacion = fields.Char(u'Secuencial obligación')
    siif_ult_modif = fields.Integer(u'Última modificación')


class obligacion_fr_anulaciones_siif_log(models.Model):
    _name = 'obligacion.fr.anulacion.siif.log'
    _description = "Log obligacion fondo rotatorio anulaciones"

    fondo_rotatorio_id = fields.Many2one('grp.fondo.rotatorio', string='Fondo rotario', required=True, ondelete='cascade')
    fecha = fields.Date('Fecha', required=True)
    nro_afectacion = fields.Char(u'Nro Afectación')
    nro_compromiso = fields.Char(u'Nro Compromiso')
    nro_obligacion = fields.Char(u'Nro Obligación')
    nro_obl_sist_aux = fields.Char(u'Nro Obligación Sist. Aux')


class grp_observacion_tc_fr(models.Model):
    _name = 'grp.observacion.tc.fr'

    fondo_rotatorio_id = fields.Many2one('grp.fondo.rotatorio', string='Factura GRP')
    motivo_intervencion_id = fields.Many2one('motivo.intervencion.tc', string='Motivo')
    descripcion = fields.Char(related='motivo_intervencion_id.descripcion', readonly=True)
    observacion = fields.Char(string=u'Observación', size=100)

    _sql_constraints = [
        ('observacion_fr_unique', 'unique(fondo_rotatorio_id,motivo_intervencion_id,observacion)', u'Ya existe una intervención con la misma observación')
    ]
