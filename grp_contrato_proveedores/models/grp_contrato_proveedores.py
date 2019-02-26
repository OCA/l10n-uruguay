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

from openerp import exceptions, models, api, fields
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
import logging

_logger = logging.getLogger(__name__)
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
from openerp.exceptions import ValidationError

class GrpContratoProveedores(models.Model):
    _name = 'grp.contrato.proveedores'
    _inherit = ['mail.thread']
    _description = "Alta de Contrato de Proveedores"
    _rec_name = 'nro_interno'

    # 001 Incidencia inicio
    @api.onchange('pedido_compra')
    def onchange_pedido_compra(self):
        if self.pedido_compra:
            obj = self.pedido_compra
            self.tipo_compra = obj.tipo_compra
            self.description = obj.description
        else:
            self.tipo_compra = False
            self.description = False

    @api.multi
    def _get_oc_apg_inv(self):
        for contrato in self:
            # TODO: K SPRINT 12 GAP 67
            if contrato.contrato_general_id:
                purchase_order_ids = self.env["purchase.order"].search([('contrato_id','=',contrato.contrato_general_id.id),
                                                                    ('partner_id','=',contrato.nro_line_adj_id.proveedor_cot_id.id),
                                                                    ('currency_oc','=',contrato.nro_line_adj_id.currency.id)])
                invoice_ids = self.env["account.invoice"].search([('orden_compra_id','in', purchase_order_ids.ids)]).ids
                apg_ids = [o.pc_apg_id.id for o in purchase_order_ids]
                invoice_line_ids = self.env['account.invoice.line'].search([('orden_compra_linea_id.order_id','in',purchase_order_ids.ids),('product_id.grp_sice_cod','=',contrato.codigo_articulo)]).ids
                # invoice_line_ids = self.env['account.invoice.line'].search([('invoice_id','in',invoice_ids),('product_id.grp_sice_cod','=',contrato.codigo_articulo)]).ids
            else:
                purchase_order_ids = self.env["purchase.order"].search([('contrato_id', '=', contrato.id)])
                invoice_ids = self.env["account.invoice"].search([('orden_compra_id', 'in', purchase_order_ids.ids)]).ids
                apg_ids = [o.pc_apg_id.id for o in purchase_order_ids]
                invoice_line_ids = False
            contrato.orden_compra_ids = purchase_order_ids.ids
            contrato.apg_compra_ids = apg_ids
            contrato.invoice_ids = invoice_ids
            contrato.invoice_line_ids = invoice_line_ids

    @api.multi
    def _get_afec_comp_obl(self):
        for contrato in self:
            if contrato.convenio:
                contrato_id = contrato.id
                if contrato.contrato_general_id:
                    contrato_id = contrato.contrato_general_id.id
                contrato.afectaciones_p_ids = contrato.afectaciones_ids.ids # TODO: K INCIDENCIA 21-09-17
                contrato.compromisos_ids = self.env["grp.compromiso"].search([('state', '=', 'comprometido')]).filtered(
                                                                        lambda x: x.contrato_id.id == contrato_id).ids
                contrato.obligaciones_ids = self.env["account.invoice"].search([('doc_type', '=', 'obligacion_invoice'),
                                                                                ('state', '=', 'open')]).filtered(
                                                                        lambda x: x.contrato_id.id == contrato_id).ids

    @api.model
    def _default_convenio(self):
        convenio = self._context.get('default_convenio', False)
        return convenio

    @api.depends('parametrica_planificada_ids', 'contrato_particular_ids.parametrica_planificada_ids')
    def _get_realizado(self):
        for rec in self:
            resultado = False
            if rec.contrato_general_id:
                resultado = resultado or rec.parametrica_planificada_ids.filtered(
                    lambda x: x.ejecutado == True) and True or False
            else:
                resultado = resultado or rec.contrato_particular_ids.mapped('parametrica_planificada_ids').filtered(
                    lambda x: x.ejecutado == True) and True or False
            rec.realizado = resultado

    nro_interno = fields.Char(string=u"Nro. Interno",readonly="1")
    secuencia = fields.Integer(string=u"Secuencia")
    proveedor = fields.Many2one(string=u"Proveedor",comodel_name="res.partner")
    tipo_resolucion = fields.Many2one(comodel_name="grp.tipo.resolucion",string=u"Tipo Resolución")
    fecha_resolucion = fields.Date(string=u"Fecha Resolución")
    fecha_inicio = fields.Date(string=u"Fecha inicio")
    fecha_fin = fields.Date(string=u"Fecha final")
    nro_contrato = fields.Char(string=u"Nro. Resolución",size=20)
    moneda = fields.Many2one(string=u"Moneda",comodel_name="res.currency")
    monto_resolucion = fields.Char(string=u"Monto resolución",size=12)
    prorroga = fields.Boolean(string=u"Prórroga")
    state = fields.Selection(
        selection=[('draft', u'Borrador'), ('vigente', u'Vigente'), ('end', u'Finalizado'), ('cancel', u'Cancelado')],
        string=u"Estado", required=True, readonly=True, default='draft', track_visibility='onchange')
    tipo_prorroga = fields.Selection(selection=[('automatico', u'Automático'), ('manual', u'Manual')],
                                     string=u"Tipo prórroga")
    renovacion = fields.Char(string=u"Renovación",size=60)
    plazo = fields.Char(string=u"Plazo",size=60)
    note = fields.Text(string=u"Notas",size=250)
    orden_compra_ids = fields.Many2many(comodel_name="purchase.order", compute='_get_oc_apg_inv', multi='oc_apg_inv',
                                        string=u"OC")
    apg_compra_ids = fields.One2many(comodel_name="grp.compras.apg", compute='_get_oc_apg_inv', multi='oc_apg_inv',
                                     string=u"APG")
    invoice_ids = fields.One2many(comodel_name="account.invoice", string=u"Facturas", compute='_get_oc_apg_inv',
                                  multi='oc_apg_inv')
    invoice_line_ids = fields.One2many(comodel_name="account.invoice.line",string=u"Facturas",compute='_get_oc_apg_inv',multi='oc_apg_inv')
    pedido_compra = fields.Many2one(comodel_name="grp.pedido.compra",string=u"Pedido de compra")
    tipo_compra = fields.Many2one(related='pedido_compra.tipo_compra',comodel_name="sicec.tipo.compra",string=u"Tipo de compra", readonly=True)
    description = fields.Text(related='pedido_compra.description',string=u"Concepto",size=250, readonly=True)
    periodo_oc = fields.Char(string=u"Período OC",size=40)
    se_valido = fields.Boolean(string=u"Se valido",default=False)
    cession_type = fields.Selection(selection=[('amout_cession', u'Cesión de importes'),('total_cession', u'Cesión de totalidad del contrato')],string=u"Tipo de cesión", readonly=True,states={'draft': [('readonly', False)], 'vigente': [('readonly', False)]}
    )
    operating_unit_id = fields.Many2one('operating.unit', string='Unidad ejecutora', required=False)
    department_id = fields.Many2one('hr.department', string=u'Unidad responsable')
    nro_adj_id = fields.Many2one('grp.cotizaciones', string=u'Nro. de Adjudicación')
    tipo_contrato_id = fields.Many2one('grp.tipo.contrato', string=u'Tipo de contrato')
    nro_cuenta = fields.Char(string=u"Nº Cuenta/Obra", size=15)
    fecha_celebracion = fields.Date(string=u"Fecha celebración")
    monedas_ids = fields.One2many("grp.monedas.contrato", "contrato_id", string=u"Monedas")
    acciones_ids = fields.One2many("grp.acciones.contrato", "contrato_id", string=u"Acciones")

    # Datos de los contratos de condiciones particulares
    contrato_general_id = fields.Many2one('grp.contrato.proveedores', string=u'Contrato de condiciones generales')
    contrato_particular_ids = fields.One2many('grp.contrato.proveedores', 'contrato_general_id',
                                              string=u'Contratos particulares')
    nro_line_adj_id = fields.Many2one('grp.cotizaciones.lineas.aceptadas', string=u'Línea de adjudicación')
    codigo_articulo = fields.Integer(string='Producto')
    cantidad = fields.Float(string='Cantidad')
    currency = fields.Many2one('res.currency', string='Moneda')
    precio = fields.Float(string='Precio unitario original',digits=dp.get_precision('Account'))
    precio_ajustado = fields.Float(string='Precio unitario ajustado',digits=dp.get_precision('Account'))
    total_ajustado = fields.Float(string='Total contratado ajustado', compute='_compute_total_ajustado')
    total_oc = fields.Float(string='Total en OC', compute='_compute_total_oc')
    total_factura = fields.Float(string='Total en Factura', compute='_compute_total_factura')
    monto_facturar = fields.Float(string='Monto pendiente a facturar', compute='_compute_monto_facturar',
                                  help=u"Para el caso de contratos de convenios es el equivalente al Monto pendiente de obligar")

    retenciones_ids = fields.One2many('grp.retenciones', 'contrato_id', string=u'Retenciones')
    give_amount_total = fields.Float(string=u'Importe total cedido en pesos', readonly=True,
                                     states={'draft': [('readonly', False)], 'vigente': [('readonly', False)]})
    cession_ids = fields.One2many('grp.cession.contrato', 'contract_id', string=u'Cessiones', readonly=True,
                                  states={'draft': [('readonly', False)], 'vigente': [('readonly', False)]})
    factura_mensual = fields.Boolean(string=u"Factura mensual", default=False, readonly=True,
                                     states={'draft': [('readonly', False)]})
    cantidad_mensual = fields.Integer(string=u"Cantidad mensual", size=4)# TODO: C INCIDENCIA 21-09-17, compute='_compute_cantidad_mensual'
    estimado_mensual = fields.Float(string=u"Monto estimado mensual")# TODO: C INCIDENCIA 21-09-17, compute='_compute_estimado_mensual'
    finalizado_parcial = fields.Boolean(string='Finalizado parcial')
    finalizado_parcial_ids = fields.One2many('grp.historial.finalizado.parcial', 'contrato_id',
                                             string='Historial finalizado parcial')
    contrato_original_id = fields.Many2one('grp.contrato.proveedores', string=u'Contrato original')
    nro_renovacion = fields.Integer(string='Nro de renovación')
    renovacion_alert = fields.Boolean(u"Mostar alerta de renovación", default=False)
    show_warning = fields.Boolean(u"Mostar alerta de renovación", default=False)

    cantidad_renovaciones = fields.Integer(string='Cantidad de renovaciones')
    contador_renovaciones = fields.Integer(string='Contador de renovaciones')

    convenio = fields.Boolean(string='Contratos sin procedimiento de compras', default=lambda self: self._default_convenio())
    afectaciones_ids = fields.Many2many('grp.afectacion', string='Afectaciones', domain=[('state','=','afectado')])
    monto_afectado = fields.Float(string='Monto Afectado', compute='_compute_monto_afectado')

    total_comprometido = fields.Float(string='Total comprometido', compute='_compute_total_comprometido')
    total_obligado = fields.Float(string='Total obligado', compute='_compute_total_obligado')

    afectaciones_p_ids = fields.One2many("grp.afectacion", compute='_get_afec_comp_obl', multi='afec_comp_obl', string=u"Afectación")
    compromisos_ids = fields.One2many("grp.compromiso", compute='_get_afec_comp_obl', multi='afec_comp_obl', string=u"Compromiso")
    obligaciones_ids = fields.One2many("account.invoice", compute='_get_afec_comp_obl', multi='afec_comp_obl', string=u"Obligación")

    control_proveedores = fields.Boolean(string='Control de proveedores habilitados')
    proveedores_hab_ids = fields.One2many("grp.proveedores.habilitados.contrato", 'contrato_id', string=u"Proveedores habilitados")
    control_proveedores_ids = fields.One2many("grp.control.proveedores.contrato", 'contrato_id', string=u"Desvíos en factura")

    parametrica_formula_id = fields.Many2one('contracts_pro.formula', 'Fórmula paramétrica')
    parametrica_periodicidad_id = fields.Many2one('contracts_pro.period', 'Periodicidad del ajuste')
    fecha_base_ajuste = fields.Date('Fecha base de ajuste', required=False)
    ultima_actualizacion = fields.Date('Última actualización', copy=False)
    proxima_actualizacion = fields.Date('Próxima actualización', copy=False)
    parametrica_planificada_ids = fields.One2many('grp.parametrica.planificada', 'contrato_proveedor_id',
                                                  string='Paramétrica planificada')
    parametrica_historica_ids = fields.One2many('grp.parametrica.historica', 'contrato_proveedor_id',
                                                string='Paramétrica histórica')
    cantidad_pendiente = fields.Float(string='Cantidad pendiente', compute='_compute_cantidad_pendiente')
    incidente_ids = fields.One2many('grp.contrato.proveedores.incidente', 'contrato_proveedor_id',
                                                string='Reporte de incidentes')

    origen_adenda = fields.Boolean('Contrato generado por una adenda', default=False, copy=False)
    realizado = fields.Boolean(string=u'Realizado?', compute='_get_realizado', store=False)

    show_cargar_parametrica = fields.Boolean('Mostrar cargar paramétrica', compute = '_compute_show_cargar_parametrica')

    @api.one
    @api.constrains('factura_mensual','cantidad_mensual')
    def _check_facturacion_mensual(self):
        if self.factura_mensual and self.cantidad_mensual == 0:
            raise  ValidationError(_('Si el contrato tiene facturación mensual, no puede definirse la Cantidad mensual con monto en 0!'))

    @api.one
    def _compute_show_cargar_parametrica(self):
        if self.env['grp.parametrica.historica'].search_count(
                [('contrato_proveedor_id.contrato_general_id', '=', self.id)]):
            self.show_cargar_parametrica = False
        else:
            self.show_cargar_parametrica = True


    @api.onchange('factura_mensual')
    def onchange_factura_mensual(self):
        if self.factura_mensual:
            self._compute_cantidad_mensual()
            self._compute_estimado_mensual()

    @api.onchange('cantidad_mensual')
    def onchange_cantidad_mensual(self):
        if self.cantidad_mensual:
            self._compute_estimado_mensual()

    @api.onchange('precio')
    def onchange_precio(self):
        self.precio_ajustado = self.precio

    @api.one
    @api.constrains('fecha_fin','fecha_inicio')
    def _check_dates(self):
        if self.fecha_fin < self.fecha_inicio:
            raise ValidationError(u'Le fecha de fin debe ser mayor que la fecha de inicio')

    def contract_finalization(self, cr, uid, ids=None, context=None):
        ids = self.search(cr, uid, [('contrato_general_id', '=', False)])
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state == 'vigente' and rec.fecha_fin and fields.Date.from_string(rec.fecha_fin) <= fields.Date.from_string(fields.Date.today()) and rec.nro_renovacion >= rec.cantidad_renovaciones:
                to_finalize = True
                for contrato_particular_id in rec.contrato_particular_ids:
                    if contrato_particular_id.monto_facturar != 0:
                        to_finalize = False
                        break
                if to_finalize:
                    rec.action_end_cascade()
                else:
                    _model, group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                               'grp_contrato_proveedores',
                                                                                               'group_grp_contrato_proveedores')

                    users = self.pool.get('res.users').search(cr, uid, [('groups_id', 'in', group_id),('operating_unit_ids','in',rec.operating_unit_id.id)])
                    if users:
                        partner_ids = [user.partner_id.id for user in
                                       self.pool.get('res.users').browse(cr, uid, users, context)]
                    else:
                        partner_ids = []
                    msg = _(u"El contrato: %s ha llegado a su fecha de fin, no tiene renovaciones pendientes, pero tiene aún saldo.") % (rec.nro_interno)
                    self.pool.get('mail.thread').message_post(cr, uid, rec.id,
                                                              subject=u'Alerta de finalización de contrato',
                                                              subtype='mt_comment', body=msg,
                                                              partner_ids=partner_ids, context=context)

    def alert_renovacion_contrato(self, cr, uid, ids=None, context=None):
        ids = self.search(cr, uid, [('contrato_general_id', '=', False)])
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.prorroga and rec.fecha_fin == datetime.now().strftime(
                    '%Y-%m-%d') and rec.cantidad_renovaciones > rec.contador_renovaciones:
                users = []
                _model_1, group_id_1 = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                           'grp_seguridad',
                                                                                           'grp_compras_apg_Jefe_de_compras_2')
                _model_2, group_id_2 = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                           'grp_contrato_proveedores',
                                                                                           'group_grp_contrato_proveedores')

                users += self.pool.get('res.users').search(cr, uid, [('groups_id', 'in', group_id_1)])

                users_2_ids = self.pool.get('res.users').search(cr, uid, [('groups_id', 'in', group_id_2)])
                for user in self.pool.get('res.users').browse(cr, uid, users_2_ids, context):
                    if user.id not in users and rec.operating_unit_id.id in user.operating_unit_ids.ids:
                        users.append(user.id)
                partner_ids = []
                if users:
                    partner_ids = [user.partner_id.id for user in
                                   self.pool.get('res.users').browse(cr, uid, users, context)]
                msg = _(u"El contrato: %s tiene una renovación pendiente.") % (rec.nro_interno)
                self.pool.get('mail.thread').message_post(cr, uid, rec.id,
                                                          subject=u'Renovación del contrato',
                                                          subtype='mt_comment', body=msg,
                                                          partner_ids=partner_ids, context=context)


    @api.multi
    def write(self, values):

        result = super(GrpContratoProveedores, self).write(values)
        if values.get("fecha_base_ajuste") or values.get("fecha_fin") or values.get("parametrica_periodicidad_id"):
            self.update_parametrica_planificada()
        # TODO: K SPRINT 12 GAP 67 actualizar datos de los contratos de condiciones especificas
        vals_particulares = {}
        for rec in self:
            if not rec.contrato_general_id:
                if values.get("proveedor", False):
                    vals_particulares['proveedor'] = values.get("proveedor", False)
                if values.get("nro_contrato", False):
                    vals_particulares['nro_contrato'] = values.get("nro_contrato", False)
                if values.get("pedido_compra", False):
                    vals_particulares['pedido_compra'] = values.get("pedido_compra", False)
                if values.get("tipo_contrato_id", False):
                    vals_particulares['tipo_contrato_id'] = values.get("tipo_contrato_id", False)
                if values.get("nro_cuenta", False):
                    vals_particulares['nro_cuenta'] = values.get("nro_cuenta", False)
                if values.get("fecha_celebracion", False):
                    vals_particulares['fecha_celebracion'] = values.get("fecha_celebracion", False)
                if values.get("operating_unit_id", False):
                    vals_particulares['operating_unit_id'] = values.get("operating_unit_id", False)
                if len(vals_particulares) > 1:
                    particular_ids = self.search([('contrato_general_id', '=', rec.id)])
                    particular_ids.write(vals_particulares)
        return result

    @api.one
    def _compute_cantidad_pendiente(self):
        for rec in self:
            if rec.contrato_general_id:
                purchase_order_ids = self.env["purchase.order"].search([('contrato_id','=',rec.contrato_general_id.id),
                                                                    ('partner_id','=',rec.nro_line_adj_id.proveedor_cot_id.id),
                                                                    ('currency_oc','=',rec.nro_line_adj_id.currency.id)])
                invoice_line_ids = self.env['account.invoice.line'].search([('orden_compra_linea_id.order_id','in',purchase_order_ids.ids),
                                                                            ('product_id.grp_sice_cod','=',rec.codigo_articulo),
                                                                            ('invoice_id.state', 'in',['open', 'sice','intervened', 'prioritized','forced', 'paid'])
                                                                            ])
            else:
                purchase_order_ids = self.env["purchase.order"].search([('contrato_id', '=', rec.id)])
                invoice_line_ids = self.env['account.invoice.line'].search(
                    [('orden_compra_linea_id.order_id', 'in', purchase_order_ids.ids),
                     ('invoice_id.state', 'in', ['open', 'sice','intervened', 'prioritized', 'forced', 'paid'])
                     ])
            total_facturado = sum(map(lambda x: x.quantity, invoice_line_ids))
            rec.cantidad_pendiente = rec.cantidad - total_facturado



    @api.one
    @api.depends('parametrica_historica_ids', 'parametrica_historica_ids.porcentaje',
                 'parametrica_historica_ids.precio_ajustado', 'parametrica_historica_ids.importe')
    def _compute_summary_fields(self):
        if self.parametrica_historica_ids:
            self.porcentaje_avg = sum(self.parametrica_historica_ids.mapped('porcentaje')) / len(
                self.parametrica_historica_ids)
            self.precio_ajustado_avg = sum(self.parametrica_historica_ids.mapped('precio_ajustado')) / len(
                self.parametrica_historica_ids)
            self.importe_total = sum(self.parametrica_historica_ids.mapped('importe'))

    # TODO verificar bien si el calculo de los meses es entre la fecha inicial y final del contrato general
    # TODO verificar bien si la cantidad total es el campo cantidad
    @api.one
    def _compute_cantidad_mensual(self):
        if self.contrato_general_id.fecha_inicio and self.contrato_general_id.fecha_fin:
            ini = datetime.strptime(self.contrato_general_id.fecha_inicio, "%Y-%m-%d")
            end = datetime.strptime(self.contrato_general_id.fecha_fin, "%Y-%m-%d")
            meses = 0
            ini += relativedelta(months=1)
            while ini < end:
                ini += relativedelta(months=1)
                meses += 1
            if meses:
                self.cantidad_mensual = self.cantidad / meses

    @api.one
    def _compute_estimado_mensual(self):
        self.estimado_mensual = self.cantidad_mensual * self.precio_ajustado

    @api.one
    @api.depends('cantidad', 'precio', 'parametrica_historica_ids')
    def _compute_total_ajustado(self):
        self.total_ajustado = self.cantidad * self.precio + sum(self.parametrica_historica_ids.mapped('importe'))

    @api.one
    @api.depends('orden_compra_ids')
    def _compute_total_oc(self):
        total_oc = 0.0
        if self.orden_compra_ids:
            for rec in self.orden_compra_ids.mapped(lambda x: x.order_line).filtered(lambda x: x.cotizaciones_linea_id.id == self.nro_line_adj_id.id and x.order_id.state in ['confirmed']):
                total_oc += rec.price_unit * rec.product_qty
        self.total_oc = total_oc

    @api.one
    @api.depends('invoice_ids','invoice_line_ids')
    def _compute_total_factura(self):
        total_factura = 0.0
        if not self.contrato_general_id.exists():
            orden_linea_ids = self.orden_compra_ids.mapped(lambda x: x.order_line).filtered(
                lambda x: x.cotizaciones_linea_id.id == self.nro_line_adj_id.id)
            for rec in self.invoice_ids.mapped(lambda x: x.invoice_line).filtered(
                    lambda x: x.orden_compra_linea_id.id in orden_linea_ids.ids and x.invoice_id.state in ['open', 'intervened','sice', 'prioritized', 'paid']):
                total_factura += rec.price_unit * rec.quantity
        elif self.invoice_line_ids:
            total_factura = sum([x.importe_imp_incl for x in self.invoice_line_ids.filtered(lambda x: x.invoice_id.state in ['open', 'intervened','sice', 'prioritized', 'paid'])])
        self.total_factura = total_factura

    @api.multi
    @api.depends('convenio','total_ajustado', 'total_factura', 'finalizado_parcial', 'total_obligado')
    def _compute_monto_facturar(self):
        for rec in self:
            if rec.convenio:
                _monto_facturar = rec.total_ajustado - rec.total_obligado
            elif not rec.convenio and not rec.finalizado_parcial:
                _monto_facturar = rec.total_ajustado - rec.total_factura
            else:
                _monto_facturar = 0
            rec.monto_facturar = _monto_facturar


    @api.one
    @api.depends('afectaciones_ids')
    def _compute_monto_afectado(self):
        if self.afectaciones_ids:
            self.monto_afectado = sum(map(lambda x: x.importe, self.afectaciones_ids.mapped(lambda x: x.llpapg_ids)))

    @api.one
    @api.depends('afectaciones_ids')
    def _compute_total_comprometido(self):
        compromiso_obj = self.env['grp.compromiso']
        total_comprometido = 0.0
        if self.afectaciones_ids:
            compromisos = compromiso_obj.search([('afectacion_id', 'in', self.afectaciones_ids.ids), ('state', '=', 'comprometido')])
            total_comprometido = sum(map(lambda x: x.importe, compromisos.mapped(lambda x: x.llpapg_ids)))
        self.total_comprometido = total_comprometido

    @api.one
    @api.depends('afectaciones_ids')
    def _compute_total_obligado(self):
        invoice_obj = self.env['account.invoice']
        total_obligado = 0.0
        if self.afectaciones_ids:
            invoice = invoice_obj.search([('afectacion_id', 'in', self.afectaciones_ids.ids), ('doc_type', '=', 'obligacion_invoice'), ('state', '=', 'open')])
            total_obligado = sum(map(lambda x: x.importe, invoice.mapped(lambda x: x.llpapg_ids)))
        self.total_obligado = total_obligado

    @api.one
    def do_not_show_warning(self):
        self.write({'show_warning':False, 'renovacion_alert':False})

    @api.multi
    def action_confirm(self):
        for rec in self:
            # INés_20180910: Incidencia id=2851. Contratos - Crear control en el campo Fecha Base Ajuste
            if rec.contrato_general_id and rec.fecha_base_ajuste and (rec.fecha_base_ajuste < rec.contrato_general_id.fecha_inicio or rec.fecha_base_ajuste > rec.contrato_general_id.fecha_fin):
                raise exceptions.ValidationError(
                    u'La fecha base de ajuste, en pestaña Paramétrica genérica, está fuera del rango de vigencia del contrato general.')
            # End INés_20180910: Incidencia id=2851. Contratos - Crear control en el campo Fecha Base Ajuste
            if not rec.secuencia and not rec.contrato_original_id:
                if rec.contrato_general_id:
                    if rec.contrato_general_id.state != 'vigente':
                        raise exceptions.ValidationError(_(
                            u'No se puede confirmar un contrato de condiciones particulares si el contrato de condiciones generales no está vigente.'))
                    anio = datetime.strptime(rec.contrato_general_id.fecha_resolucion, "%Y-%m-%d").date().year
                    self._cr.execute("""select max(cp.secuencia) from
                                                grp_contrato_proveedores cp WHERE EXTRACT(YEAR FROM cp.fecha_resolucion) = %s AND cp.contrato_general_id = %s""" % (
                        anio, rec.contrato_general_id.id))
                    maxima = self._cr.fetchone()[0]
                    if not maxima:
                        maxima = 0
                    final = str(maxima + 1)
                    nro_interno = rec.contrato_general_id.nro_interno + "-" + final
                else:
                    anio = datetime.strptime(rec.fecha_resolucion, "%Y-%m-%d").date().year
                    usuario = self.env.user
                    company = usuario.company_id
                    self._cr.execute("""select max(cp.secuencia) from
                                    grp_contrato_proveedores cp WHERE EXTRACT(YEAR FROM cp.fecha_resolucion) = %s
                                    AND cp.id not in (SELECT id FROM grp_contrato_proveedores where contrato_general_id > 0)""" % (
                    anio))
                    maxima = self._cr.fetchone()[0]
                    if not maxima:
                        maxima = 0
                    # 005-Inicio
                    final = str(maxima + 1)

                    nro_interno = "Contratos-" + company.inciso + "-" + str(anio) + "-" + final.zfill(5)
                # 005-Fin

                self.write({'state': 'vigente', 'secuencia': maxima + 1,
                            'nro_interno': nro_interno, 'se_valido': True})
            else:
                self.write({'state': 'vigente', 'se_valido': True})
        return True

    @api.multi
    def action_end(self):
        for rec in self:
            if not rec.contrato_general_id and self.search_count([('contrato_general_id', '=', rec.id), ('state', 'not in', ['end', 'cancel'])]):
                raise exceptions.ValidationError(_(u'Debe finalizar o cerrar los contratos de condiciones particulares asociados a este contrato.'))
            self.env['grp.acciones.contrato'].create({'contrato_id': rec.id,
                                                          'se_copio': False,
                                                          'se_registro': False,
                                                          'tipo': 'Finalización',})
        return self.write({'state': 'end'})

    # RAGU: finalizacion en cascada, exclusivo para generales
    @api.multi
    def action_end_cascade(self):
        for rec in self.filtered(lambda x: not x.contrato_general_id):
            rec.contrato_particular_ids.action_end()
            rec.action_end()

    @api.multi
    def _check_gral_contracts_finalization(self):
        for rec in self:
            if rec.contrato_particular_ids.filtered(lambda x: x.state not in ['end', 'cancel', 'draft']):
                raise ValidationError(u"No se puede eliminar un Contrato si tiene Contratos particulares asociados no 'Finalizados', 'Cancelados' o en 'Borrador'!")
            return True

    @api.multi
    def action_cancel(self):
        self._check_gral_contracts_finalization()
        return self.write({'state': 'cancel'})

    @api.multi
    def action_draft(self):
        return self.write({'state': 'draft', 'se_valido': False})

    @api.multi
    def action_partial_end(self):
        # TODO optimizar este codigo buscar de q otra forma puedo obtener las facturas de una oc
        for rec in self:
            ordenes_compra_ids = rec.orden_compra_ids.ids
            facturas = self.env["account.invoice"].search([('orden_compra_id', 'in', ordenes_compra_ids),
                                                           ('state', 'not in', ['open', 'intervened', 'prioritized',
                                                                                'paid', 'forced', 'cancel_sice',
                                                                                'cancel_siif', 'cancel'])])
            if facturas:
                raise exceptions.ValidationError(
                    _(
                        u'No puede finalizar parcialmente el contrato porque no se han registrado todas las facturas del contrato.'))

            rec.write({'finalizado_parcial_ids': [(0, 0, {'total_finalizado': rec.monto_facturar})]})
        return self.write({'finalizado_parcial': True, 'state': 'end'})

    @api.multi
    def button_renovacion(self):
        adj_obj = self.env['grp.cotizaciones']
        for rec in self:
            adj_ids = adj_obj.search([('nro_pedido_original_id', '=', rec.pedido_compra.id), ('ampliacion', '=', True),
                                      ('contrato_generado', '!=', True)])
            if adj_ids.mapped(lambda x: x.sice_page_aceptadas).filtered(lambda x: x.contrato_generado != True and x.proveedor_cot_id.id == rec.proveedor.id) or rec.convenio:
                context = dict(self._context)
                mod_obj = self.env['ir.model.data']
                res = mod_obj.get_object_reference('grp_contrato_proveedores', 'grp_crear_renovacion_wizard_view')
                models = 'grp.crear.renovacion.wizard'
                res_id = res and res[1] or False
                ctx = context.copy()
                ctx.update({'adjudicacion_ids': not rec.convenio and adj_ids.ids or [], 'default_contrato_id': rec.id,})
                return {
                    'name': "Renovación/ampliación de contratos",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': models,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': ctx,
                }
            else:
                rec.write({'show_warning':True, 'renovacion_alert':True})
                context = dict(self._context)
                mod_obj = self.env['ir.model.data']
                res = mod_obj.get_object_reference('grp_contrato_proveedores', 'view_contract_proveedores_form')
                models = 'grp.contrato.proveedores'
                res_id = res and res[1] or False
                ctx = context.copy()
                return {
                    'name': "Contrato de condiciones generales",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': models,
                    'res_id': rec.id,
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'context': ctx,
                }
        return True

    @api.multi
    def update_parametrica_planificada(self):
        for rec in self:
            rec.parametrica_planificada_ids.unlink()
            if rec.parametrica_periodicidad_id:
                fecha_fin = rec.contrato_general_id.fecha_fin if rec.contrato_general_id.id != False else rec.fecha_fin  # se asume que la fecha_fin del contrato particular es la del general
                fecha_inicio = rec.fecha_base_ajuste if rec.fecha_base_ajuste else False
                parametrica_planificadas = []
                if fecha_inicio:
                    rango_fecha = rec.parametrica_periodicidad_id.get_period_limits_from_date(rec.fecha_base_ajuste)
                    iterador_fecha = str(fields.Date.from_string(rango_fecha[1]))
                    while fecha_fin >= iterador_fecha and fecha_inicio <= iterador_fecha:
                        parametrica_planificadas.append((0, 0, {'fecha': rango_fecha[1], 'ejecutado': False}))
                        rango_fecha = rec.parametrica_periodicidad_id.get_period_limits_from_date(iterador_fecha)
                        iterador_fecha = str(fields.Date.from_string(rango_fecha[1]))
                    rec.write({
                        'parametrica_planificada_ids': parametrica_planificadas
                    })

    @api.multi
    def action_cargarparametrica(self):
        for rec in self:
            rec.contrato_particular_ids.write({
                'parametrica_formula_id': rec.parametrica_formula_id.id,
                'parametrica_periodicidad_id': rec.parametrica_periodicidad_id.id,
                'fecha_base_ajuste': rec.fecha_base_ajuste,
            })

    @api.multi
    def action_calcularparametricas(self):
        ParametricaFormula = self.env['contracts_pro.formula']
        dict_write = {}
        for rec in self:
            parametrica_planificada_ids = rec.parametrica_planificada_ids.filtered(
                lambda x: (x.fecha <= fields.Date.today() and not x.ejecutado))

            if parametrica_planificada_ids:
                proxima_parametrica_planificada_ids = rec.parametrica_planificada_ids.filtered(
                    lambda x: (x.fecha > fields.Date.today() and not x.ejecutado))

                porcentaje = round(
                    ParametricaFormula.get_value(rec.parametrica_formula_id.id, parametrica_planificada_ids[-1].fecha,
                                                 context=self._context), 4)
                valor_afectado = round(rec.precio_ajustado * (1 + porcentaje),2)
                variacion = rec.cantidad_pendiente * (valor_afectado - rec.precio_ajustado)
                importe_ajuste = round(rec.precio_ajustado * (1 + porcentaje), 2)
                parametrica_planificada_ids[-1].write({'ejecutado': True})

                dict_write.update({
                    'precio_ajustado': importe_ajuste,
                    'ultima_actualizacion': parametrica_planificada_ids[-1].fecha,
                    'parametrica_historica_ids': [(0, 0, {
                        'fecha_planificada_ejecutada': parametrica_planificada_ids[-1].fecha,
                        'fecha': fields.Date.today(),
                        'porcentaje': porcentaje,
                        'importe': variacion,
                        'precio_ajustado': importe_ajuste
                    })]
                })

                if proxima_parametrica_planificada_ids:
                    dict_write['proxima_actualizacion'] = proxima_parametrica_planificada_ids[-1].fecha

            rec.write(dict_write)

    @api.multi
    def action_recalcularparametrica(self):
        self.ensure_one()
        executed_param_ids = self.parametrica_planificada_ids.filtered(
            lambda x: (x.ejecutado))
        if len(executed_param_ids) >= 1:
            last_executed_param_id = executed_param_ids[0]
            if len(executed_param_ids) >= 2:
                origin_executed_param_id = executed_param_ids[1]
                historica_origen_id = self.parametrica_historica_ids.filtered(lambda x: (x.fecha_planificada_ejecutada == origin_executed_param_id.fecha))[0]
                dict_write = {
                    'precio_ajustado': historica_origen_id.precio_ajustado,
                    'ultima_actualizacion': origin_executed_param_id.fecha,
                    'proxima_actualizacion': last_executed_param_id.fecha,
                }
                self.parametrica_historica_ids.filtered(
                    lambda x: (x.fecha_planificada_ejecutada == last_executed_param_id.fecha)).unlink()
            else:
                dict_write = {
                    'precio_ajustado': self.precio,
                    'ultima_actualizacion': False,
                    'proxima_actualizacion': last_executed_param_id.fecha,
                }
                self.parametrica_historica_ids.unlink()
            last_executed_param_id.write({'ejecutado': False})
            self.write(dict_write)

    @api.model
    def create(self, vals):
        moneda_obj = self.env['grp.monedas.contrato']
        contrato_id = super(GrpContratoProveedores, self).create(vals)

        if contrato_id.contrato_general_id:
            moneda_ids = moneda_obj.search([('contrato_id', '=', contrato_id.contrato_general_id.id),
                                            ('moneda', '=', contrato_id.nro_line_adj_id.currency.name)])
            if moneda_ids:
                monto_inicial = moneda_ids[0].monto_inicial + (contrato_id.cantidad * contrato_id.precio)
                moneda_ids[0].write({
                    'monto_inicial': monto_inicial,
                })
            else:
                moneda_obj.create({'contrato_id': contrato_id.contrato_general_id.id,
                                   'moneda': contrato_id.nro_line_adj_id.currency.name,
                                   'monto_inicial': contrato_id.cantidad * contrato_id.precio
                                   })

            if contrato_id.operating_unit_id.id and contrato_id.operating_unit_id.id != contrato_id.contrato_general_id.operating_unit_id.id:
                contrato_id.write({'operating_unit_id': contrato_id.contrato_general_id.operating_unit_id.id})


        ir_model_data = self.env['ir.model.data']
        _model, group_id = ir_model_data.get_object_reference('grp_seguridad',
                                                              'grp_compras_apg_Ordenador_del_gasto')
        users = self.env['res.users'].search([('groups_id', 'in', group_id),('operating_unit_ids','in',contrato_id.operating_unit_id.id)])

        if users:
            contrato_id.message_subscribe_users(user_ids=users.ids)

        return contrato_id

    @api.model
    def alert_vencimiento_compra_directa(self):
        _is_alert_date = fields.Date.from_string(fields.Date.today()) + timedelta(days=int(60))
        contratos = self.search([('tipo_compra.idTipoCompra', '=', 'CD'), ('fecha_fin', '=', _is_alert_date)])
        # if self.tipo_compra.idTipoCompra == 'CD' and _is_alert_date == fields.Date.from_string(self.fecha_fin):
        web_base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        for contrato in contratos:
            body = u'''
                El Contrato: <a href="%(web)s/web#id=%(id)s&view_type=form&model=grp.contrato.poveedores">%(nro_interno)s<a/> correspondiente a la compra %(compra)s se vencerá dentro de 2 meses.''' \
                   % {'web': web_base_url,
                      'id': contrato.id,
                      'nro_interno': contrato.nro_interno,
                      'compra': contrato.pedido_compra.name,
                      }

            contrato.sent_alert_mail('Alerta vencimiento de contrato de compra directa', contrato.write_uid.email, body)
            # TODO: el from no deberia ser quien modifica el contrato, enviar admin o algo similar


    @api.model
    def alert_vencimiento_tipo_licitaciones(self):
        _is_alert_date = fields.Date.from_string(fields.Date.today()) + timedelta(days=int(120))
        contratos = self.search([('tipo_compra.idTipoCompra', 'in', ['LA','LP']), ('fecha_fin', '=', _is_alert_date)])
        # if (self.tipo_compra.idTipoCompra == 'LA' or self.tipo_compra.idTipoCompra == 'LP') and \
        #                 _is_alert_date == fields.Date.from_string(self.fecha_fin):
        web_base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        for contrato in contratos:
            body = u'''
                   El Contrato: <a href="%(web)s/web#id=%(id)s&view_type=form&model=grp.contrato.poveedores">%(nro_interno)s<a/> correspondiente a la compra %(compra)s se vencerá dentro de 4 meses.''' \
                   % {'web': web_base_url,
                      'id': contrato.id,
                      'nro_interno': contrato.nro_interno,
                      'compra': contrato.pedido_compra.name,
                      }

            contrato.sent_alert_mail('Alerta vencimiento de contrato del tipo licitaciones', contrato.write_uid.email, body)


    def sent_alert_mail(self, _subject, _from, _body):
        Mail = self.pool['mail.mail']
        partner_ids = [partner.id for partner in self.message_follower_ids]
        vals = {
            'subject': _subject,
            'body_html': '<pre>%s</pre>' % _body,
            'recipient_ids': [(6, 0, partner_ids)],
            'email_from': _from
        }
        mail_id = self.env['mail.mail'].create(vals).id
        Mail.send(self._cr, self._uid, [mail_id], context=self._context)

    @api.constrains('give_amount_total', 'cession_ids')
    def _check_amount_total(self):
        for rec in self:
            if rec.give_amount_total < sum(map(lambda x: x.give_amount, rec.cession_ids)) and rec.cession_type == 'amout_cession':
                raise exceptions.ValidationError(
                    _(u'La suma de montos cedidos ingresados en la grilla de cesiones es superior al importe total cedido en pesos.'))

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(u"El contrato no está en 'Borrador' por lo que no puede ser eliminado!")
            if not self.env.user.has_group('grp_contrato_proveedores.group_grp_contrato_proveedores'):
                raise ValidationError(u"El contrato no puede ser eliminado si no está asignado al grupo GRP - Contrato Proveedores!")
            if rec.contrato_particular_ids:
                raise ValidationError(u"No se puede eliminar un Contrato si tiene Contratos particulares asociados!")
            if rec.contrato_general_id and rec.contrato_general_id.state not in ['draft', 'cancel']:
                raise ValidationError(u"No se puede eliminar un Contrato particular si el Contrato General asociado no está en los estados: 'Borrador','Cancelado'!")

        return super(GrpContratoProveedores, self).unlink()



class GrpHistorialFinalizadoParcial(models.Model):
    _name = 'grp.historial.finalizado.parcial'

    contrato_id = fields.Many2one("grp.contrato.proveedores", string=u"Nº Contrato")
    fecha = fields.Date(string=u"Fecha", default=lambda *a: fields.Date.today())
    total_finalizado = fields.Float(string=u"Total finalizado")


class GrpTipoResolucion(models.Model):
    _name = 'grp.tipo.resolucion'
    _description = "Alta de tipo de resolucion"

    name = fields.Char(
        string=u"Tipo de resolución",
        required=True,
        size=50
    )


class GrpParametricaPlanificada(models.Model):
    _name = 'grp.parametrica.planificada'
    _description = "Parametrica planificada"
    _order = 'fecha DESC'

    contrato_proveedor_id = fields.Many2one('grp.contrato.proveedores', string=u"Contrato de proveedor", required=True, ondelete='cascade')
    fecha = fields.Date('Fecha planificada', required=True)
    ejecutado = fields.Boolean('Realizado', default=False)


class GrpParametricaHistorica(models.Model):
    _name = 'grp.parametrica.historica'
    _description = "Parametrica historica"

    contrato_proveedor_id = fields.Many2one('grp.contrato.proveedores', string=u"Contrato de proveedor", required=True, ondelete='cascade')
    fecha_planificada_ejecutada = fields.Date('Fecha planficada', required=True)
    fecha = fields.Date('Fecha', required=True)
    porcentaje = fields.Float('Porcentaje', required=True,digits=(16,4))
    precio_ajustado = fields.Float('Precio ajustado', required=True)
    importe = fields.Float('Importe del ajuste', required=True)

class GrpMonedasContrato(models.Model):
    _name = 'grp.monedas.contrato'

    contrato_id = fields.Many2one("grp.contrato.proveedores", string=u"Contrato")
    moneda = fields.Char(string=u"Moneda")
    monto_inicial = fields.Float(string='Monto contrato inicial', digits_compute=dp.get_precision('Account'))
    monto_ajustado = fields.Float(string='Monto contrato ajustado', compute='_compute_monto_ajustado',
                                  digits_compute=dp.get_precision('Account'), store=True)

    # TODO: K SPRINT 13 GAP 452
    monto_ejecutar_actual = fields.Float(string='Monto a ejecutar ejercicio actual',
                                         digits_compute=dp.get_precision('Account'))
    listo = fields.Boolean(u"Listo para procesar", default=False)
    fecha_procesamiento = fields.Datetime(string=u'Último procesamiento', default=fields.Datetime.now())

    # TODO: K SPRINT 12 GAP 67
    @api.one
    @api.depends('contrato_id.contrato_particular_ids.precio_ajustado', 'contrato_id.contrato_particular_ids.cantidad')
    def _compute_monto_ajustado(self):
        self.monto_ajustado = sum(map(lambda m: m.cantidad * m.precio_ajustado,
                                        self.contrato_id.contrato_particular_ids.filtered(
                                        lambda x: x.moneda.name == self.moneda)))


class GrpAccionesContrato(models.Model):
    _name = 'grp.acciones.contrato'
    _order = 'id desc'

    contrato_id = fields.Many2one("grp.contrato.proveedores", string=u"Contrato")
    link = fields.Many2one("grp.contrato.proveedores", string=u"Link")
    tipo = fields.Char(string=u"Tipo", size=20)
    se_copio = fields.Boolean(string=u"Se hizo copia?",default=False)
    se_registro = fields.Boolean(string=u"Se hizo registro nuevo?",default=False)
    fecha = fields.Date(string=u"Fecha", default=lambda *a: fields.Date.today())
    user_id = fields.Many2one('res.users', string='Usuario', default=lambda self: self.env.user)
    descripcion = fields.Text(string=u"Descripción detallada")

class GrpCessionContrato(models.Model):
    _name = 'grp.cession.contrato'

    contract_id = fields.Many2one("grp.contrato.proveedores", string=u'Contrato')
    partner_id = fields.Many2one("res.partner", string=u'Proveedor')
    date = fields.Date(string=u'Fecha cesión')
    give_amount = fields.Float(string=u'Importe cedido en pesos')
    cession_type = fields.Selection(selection=[('amout_cession', u'Cesión de importes'),
                                               ('total_cession', u'Cesión de totalidad del contrato')],
                                    string=u'Tipo de cesión', related='contract_id.cession_type', readonly=True)
    monto_ajustado_contrato = fields.Float(string='Monto ajustado del contrato',
                                           compute='_compute_monto_ajustado_contrato') # TODO: K VARIANZA GRP

    invoice_cession_ids = fields.One2many('grp.cesion.embargo', 'contract_cesion_id',
                                             string='Cesiones facturas')
    saldo_ceder = fields.Float(string='Total saldo a ceder', compute='_compute_saldo_ceder')

    @api.depends('invoice_cession_ids')
    def _compute_saldo_ceder(self):
        for rec in self:
            rec.saldo_ceder = rec.give_amount
            if rec.invoice_cession_ids:
                for inv_cesion in rec.invoice_cession_ids:
                    if inv_cesion.invoice_id.state == 'paid':
                        rec.saldo_ceder = rec.saldo_ceder - inv_cesion.monto_cedido_embargado


    @api.multi
    def _compute_saldo_ceder_moneda(self, moneda):
        for rec in self:
            rec.saldo_ceder_moneda = 0
            if rec.contract_id.monedas_ids:
                contracto_moneda = rec.contract_id.monedas_ids.filtered(lambda x: x.moneda == str(moneda.id))
                if contracto_moneda:
                    monto_ajustado = contracto_moneda.monto_ajustado
                    cesiones = rec.invoice_cession_ids.filtered(lambda x: x.invoice_id.state == 'paid'
                                                                          and x.invoice_id.currency_id.id == int(contracto_moneda.moneda))
                    monto_cedido_en_moneda = 0
                    for cesion in cesiones:
                        if cesion.invoice_id.currency_id.type_ref_base == 'smaller':
                            monto_cedido_en_moneda += cesion.monto_cedido_embargado * moneda.rate
                        elif cesion.invoice_id.currency_id.type_ref_base == 'bigger':
                            monto_cedido_en_moneda += cesion.monto_cedido_embargado / moneda.rate

                    return monto_ajustado - monto_cedido_en_moneda

        return True

    @api.depends('contract_id')
    def _compute_monto_ajustado_contrato(self):
        for rec in self:
            rec.monto_ajustado_contrato = sum(rec.contract_id.monedas_ids.mapped('monto_ajustado'))

    @api.onchange('contract_id', 'cession_type')
    def onchange_give_amount(self):
        if self.cession_type == 'total_cession':
            self.give_amount = self.monto_ajustado_contrato


class GrpProveedoresHabilitadosContrato(models.Model):
    _name = 'grp.proveedores.habilitados.contrato'

    contrato_id = fields.Many2one("grp.contrato.proveedores", string=u'Contrato')
    control_proveedores = fields.Boolean(string='Control de proveedores habilitados', related='contrato_id.control_proveedores', readonly=True)
    proveedor = fields.Many2one("res.partner", string=u"Proveedor")
    monto_mensual = fields.Float(string='Monto mensual')
    fecha_inactivo = fields.Date(string=u"Fecha inactivo desde")

class GrpControlProveedoresContrato(models.Model):
    _name = 'grp.control.proveedores.contrato'

    contrato_id = fields.Many2one("grp.contrato.proveedores", string=u'Contrato')
    invoice_id = fields.Many2one("account.invoice", string=u'Factura')
    proveedor = fields.Many2one("res.partner", related='invoice_id.partner_id', string=u"Proveedor", readonly=True)
    mes = fields.Char(string=u"Mes de devengamiento")
    monto_mensual = fields.Float(string='Monto mensual pactado')
    monto_facturado = fields.Float(string='Monto facturado', related='invoice_id.amount_total', readonly=True)
    motivo = fields.Char(string=u"Motivo desvío")

class GrpRetenciones(models.Model):
    _name = 'grp.retenciones'

    contrato_id = fields.Many2one('grp.contrato.proveedores', string=u'Contrato', required=True)
    producto_id = fields.Many2one('product.product', domain=[('retencion_ok', '=', True)], string=u'Producto')
    cuenta_id = fields.Many2one('account.account', string=u'Cuenta', required=True)
    descripcion = fields.Char(string=u"Descripción", size=30)
    importe_pesos = fields.Float(string='Importe pesos', required=True)
    retenciones_factura_ids = fields.One2many('account.global.retention.line', 'retencion_id',
                                              string=u'Retenciones manuales factura')
    retencion_factura_id = fields.Many2one('account.global.retention.line', string=u'Retencion manual factura',
                                           compute='_compute_retencion_factura_id', store=True)

    # RAGU: saldo a retener es un compute que esta pendiente a los cambios en las lineas de la factura
    saldo_retener = fields.Float(string='Saldo a retener', compute='_compute_saldo_retener')

    @api.one
    def _compute_saldo_retener(self):
        self.saldo_retener = self.importe_pesos - sum(map(lambda c: c.amount_ret_pesos, self.retenciones_factura_ids.filtered(lambda x: x.retencion_id.id == self.id and x.invoice_id.state not in ['draft', 'proforma', 'proforma2', 'sice', 'cancel_sice', 'in_approved', 'approved', 'in_auth', 'authorized', 'cancel'])))

    @api.onchange('producto_id')
    def onchange_producto_id(self):
        if self.producto_id and self.producto_id.property_account_expense:
            self.cuenta_id = self.producto_id.property_account_expense
        else:
            self.cuenta_id = False

    @api.one
    @api.constrains('importe_pesos')
    def _check_importe_pesos(self):
        if self.importe_pesos <= 0:
            raise ValidationError(u'El Importe pesos debe ser mayor a cero.')

    @api.multi
    @api.depends('retenciones_factura_ids')
    def _compute_retencion_factura_id(self):
        for record in self:
            if record.retenciones_factura_ids:
                record.retencion_factura_id = record.retenciones_factura_ids[0]


class GrpHistorialContratos(models.Model):
    _name = 'grp.historial.contratos'
    _inherit = 'grp.contrato.proveedores'

    link = fields.Many2one(comodel_name='grp.contrato.proveedores', string=u"Link", readonly=True)
    fecha_modificacion = fields.Date(string=u'Fecha de modificación', readonly=True)


class GrpContratoProveedoresIncidentes(models.Model):
    _name = 'grp.contrato.proveedores.incidente'
    _description = "Reporte de incidentes para contrator particulares"

    contrato_proveedor_id = fields.Many2one('grp.contrato.proveedores', required=True, ondelete='cascade', domain="[('contrato_general_id','!=',False)]")
    fecha = fields.Date('Fecha', required=True)
    name = fields.Char('Incidente', required=True, size=100)
