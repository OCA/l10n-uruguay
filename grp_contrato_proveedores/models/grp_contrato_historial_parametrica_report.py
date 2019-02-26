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

from openerp import api, exceptions, fields, models
from openerp import tools
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta


# TODO: C SPRING 12 GAP_306
class GrpContratoHistorialParametricaReport(models.Model):
    _name = 'grp.contrato.historial.parametrica.report'
    _auto = False
    _description = 'Historial de ajustes'

    # PARAMETRICA
    fecha = fields.Date('Fecha', required=True)
    porcentaje = fields.Float('Porcentaje', required=True)
    precio_ajustado_parametrica = fields.Float('Precio ajustado', required=True)
    importe = fields.Float('Importe del ajuste', required=True)

    # CONTRATO
    nro_interno = fields.Char(string=u"Nro. Interno")
    secuencia = fields.Integer(string=u"Secuencia")
    proveedor = fields.Many2one(string=u"Proveedor", comodel_name="res.partner")
    tipo_resolucion = fields.Many2one(comodel_name="grp.tipo.resolucion",string=u"Tipo Resolución")
    fecha_resolucion = fields.Date(string=u"Fecha Resolución")
    fecha_inicio = fields.Date(string=u"Fecha inicio")
    fecha_fin = fields.Date(string=u"Fecha final")
    nro_contrato = fields.Char(string=u"Nro. Resolución", size=20)
    moneda = fields.Many2one(string=u"Moneda",comodel_name="res.currency")
    monto_resolucion = fields.Char(string=u"Monto resolución",size=12)
    prorroga = fields.Boolean(string=u"Prórroga")
    state = fields.Selection(
        selection=[
            ('draft', u'Borrador'),
            ('vigente', u'Vigente'),
            ('end', u'Finalizado'),
            ('cancel', u'Cancelado'),
        ], string=u"Estado", required=True, readonly=True, default='draft')
    tipo_prorroga = fields.Selection(selection=[('automatico', u'Automático'), ('manual', u'Manual')],
                                     string=u"Tipo prórroga")
    renovacion = fields.Char(string=u"Renovación", size=60)
    plazo = fields.Char(string=u"Plazo", size=60)
    note = fields.Text(string=u"Notas", size=250)
    pedido_compra = fields.Many2one(comodel_name="grp.pedido.compra", string=u"Pedido de compra")
    tipo_compra = fields.Many2one("sicec.tipo.compra",
                                  string=u"Tipo de compra")
    description = fields.Text(string=u"Concepto", size=250, store=True)
    periodo_oc = fields.Char(string=u"Período OC", size=40)
    se_valido = fields.Boolean(string=u"Se valido", default=False)
    cession_type = fields.Selection(
        selection=[
            ('amout_cession', u'Cesión de importes'),
            ('total_cession', u'Cesión de totalidad del contrato')],
        string=u"Tipo de cesión", readonly=True,
        states={'draft': [('readonly', False)], 'vigente': [('readonly', False)]}
    )

    operating_unit_id = fields.Many2one('operating.unit', string='Unidad ejecutora', required=False)
    department_id = fields.Many2one('hr.department', string=u'Unidad responsable')
    nro_adj_id = fields.Many2one('grp.cotizaciones', string=u'Nro. de Adjudicación')
    tipo_contrato_id = fields.Many2one('grp.tipo.contrato', string=u'Tipo de contrato')
    nro_cuenta = fields.Char(string=u"Nº Cuenta/Obra", size=15)
    fecha_celebracion = fields.Date(string=u"Fecha celebración")
    # monedas_ids = fields.One2many("grp.monedas.contrato", "contrato_id", string=u"Monedas")
    # acciones_ids = fields.One2many("grp.acciones.contrato", "contrato_id", string=u"Acciones")

    # Datos de los contratos de condiciones particulares
    contrato_general_id = fields.Many2one('grp.contrato.proveedores', string=u'Contrato de condiciones generales')
    # contrato_particular_ids = fields.One2many('grp.contrato.proveedores', 'contrato_general_id',
    #                                           string=u'Contratos particulares')
    nro_line_adj_id = fields.Many2one('grp.cotizaciones.lineas.aceptadas', string=u'Línea de adjudicación')
    codigo_articulo = fields.Integer(string='Producto')
    cantidad = fields.Float(string='Cantidad')
    currency = fields.Many2one('res.currency', string='Moneda')
    precio_ajustado = fields.Float(string='Precio unitario ajustado')

    give_amount_total = fields.Float(string=u'Importe total cedido en pesos', readonly=True,
                                     states={'draft': [('readonly', False)], 'vigente': [('readonly', False)]})

    factura_mensual = fields.Boolean(string=u"Factura mensual", default=False, readonly=True,
                                     states={'draft': [('readonly', False)]})
    cantidad_mensual = fields.Integer(string=u"Cantidad mensual", size=4, compute='_compute_cantidad_mensual')
    estimado_mensual = fields.Float(string=u"Monto estimado mensual", compute='_compute_estimado_mensual')

    finalizado_parcial = fields.Boolean(string='Finalizado parcial')

    contrato_original_id = fields.Many2one('grp.contrato.proveedores', string=u'Contrato original')
    nro_renovacion = fields.Integer(string='Nro de renovación')
    renovacion_alert = fields.Boolean(u"Mostar alerta de renovación", default=False)

    cantidad_renovaciones = fields.Integer(string='Cantidad de renovaciones')
    contador_renovaciones = fields.Integer(string='Contador de renovaciones')

    convenio = fields.Boolean(string='Convenio', default=lambda self: self._default_convenio())

    control_proveedores = fields.Boolean(string='Control de proveedores habilitados')

    parametrica_formula_id = fields.Many2one('contracts_pro.formula', 'Fórmula paramétrica')
    parametrica_periodicidad_id = fields.Many2one('contracts_pro.period', 'Periodicidad del ajuste')
    fecha_base_ajuste = fields.Date('Fecha base de ajuste', required=False)
    ultima_actualizacion = fields.Date('Última actualización', copy=False)
    proxima_actualizacion = fields.Date('Próxima actualización', copy=False)
    cantidad_pendiente = fields.Float(string='Cantidad pendiente', compute='_compute_cantidad_pendiente')

    @api.one
    @api.depends('cantidad', 'contrato_general_id.fecha_inicio', 'contrato_general_id.fecha_fin')
    def _compute_cantidad_mensual(self):
        if self.contrato_general_id.fecha_inicio and self.contrato_general_id.fecha_fin:
            ini = datetime.strptime(self.contrato_general_id.fecha_inicio, "%Y-%m-%d")
            end = datetime.strptime(self.contrato_general_id.fecha_fin, "%Y-%m-%d")
            meses = (
            relativedelta(years=end.year, months=end.month, days=end.day) - relativedelta(years=ini.year, months=ini.month,
                                                                                          days=ini.day)).months
            if meses:
                self.cantidad_mensual = self.cantidad / meses

    @api.one
    @api.depends('cantidad_mensual', 'precio_ajustado')
    def _compute_estimado_mensual(self):
        self.estimado_mensual = self.cantidad_mensual * self.precio_ajustado

    @api.one
    @api.depends('afectaciones_ids')
    def _compute_total_obligado(self):
        invoice_obj = self.env['account.invoice']
        total_obligado = 0.0
        if self.afectaciones_ids:
            invoice = invoice_obj.search([('afectacion_id', 'in', self.afectaciones_ids.ids), ('doc_type', '=', 'obligacion_invoice'), ('state', '=', 'open')])
            total_obligado = sum(map(lambda x: x.importe, invoice.mapped(lambda x: x.llpapg_ids)))
        self.total_obligado = total_obligado

    # TODO: R SPRING 12 GAP 443
    @api.one
    def _compute_cantidad_pendiente(self):
        for rec in self:
            invoice_line_ids = self.env['account.invoice.line'].search([('invoice_id.orden_compra_id','in',rec.nro_adj_id.purchase_order_ids.ids),('invoice_id.state','in',['open','intervened','prioritized','forced','paid'])])
            total_facturado = sum(map(lambda x: x.quantity, invoice_line_ids))
            rec.cantidad_pendiente = rec.cantidad - total_facturado

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_contrato_historial_parametrica_report')
        cr.execute("""
            CREATE OR replace VIEW grp_contrato_historial_parametrica_report AS (
                SELECT 
                    main_view.*, 
                    pedido_compra_view.tipo_compra,  
                    pedido_compra_view.description
                FROM
                    (SELECT
                        contrato.nro_interno,
                        contrato.secuencia,
                        contrato.proveedor,
                        contrato.tipo_resolucion,
                        contrato.fecha_resolucion,
                        contrato.fecha_inicio,
                        contrato.fecha_fin,
                        contrato.nro_contrato,
                        contrato.moneda,
                        contrato.monto_resolucion,
                        contrato.prorroga,
                        contrato.state,
                        contrato.tipo_prorroga,
                        contrato.renovacion,
                        contrato.plazo,
                        contrato.note,
                        contrato.pedido_compra,
                        contrato.periodo_oc,
                        contrato.cession_type,
                        contrato.operating_unit_id,
                        contrato.department_id,
                        contrato.nro_adj_id,
                        contrato.tipo_contrato_id,
                        contrato.nro_cuenta,
                        contrato.fecha_celebracion,
                        contrato.contrato_general_id,
                        contrato.nro_line_adj_id,
                        contrato.codigo_articulo,
                        contrato.currency,
                        contrato.precio_ajustado,
                        contrato.give_amount_total,
                        contrato.factura_mensual,
                        contrato.cantidad,
                        contrato.finalizado_parcial,
                        contrato.contrato_original_id,
                        contrato.nro_renovacion,
                        contrato.renovacion_alert,
                        contrato.cantidad_renovaciones,
                        contrato.contador_renovaciones,
                        contrato.convenio,
                        contrato.control_proveedores,
                        contrato.parametrica_formula_id,
                        contrato.parametrica_periodicidad_id,
                        contrato.fecha_base_ajuste,
                        contrato.ultima_actualizacion,
                        contrato.proxima_actualizacion,
                        parametrica.fecha as fecha,
                        parametrica.porcentaje as porcentaje,
                        parametrica.precio_ajustado as precio_ajustado_parametrica,
                        parametrica.importe as importe,
                        parametrica.id as id
                    FROM grp_parametrica_historica parametrica
                    INNER JOIN grp_contrato_proveedores contrato ON contrato.id = parametrica.contrato_proveedor_id
                    WHERE contrato.contrato_general_id is not null) AS main_view 
                LEFT JOIN
                    (SELECT * FROM grp_pedido_compra) AS pedido_compra_view ON main_view.pedido_compra = pedido_compra_view.id
            )
        """)
