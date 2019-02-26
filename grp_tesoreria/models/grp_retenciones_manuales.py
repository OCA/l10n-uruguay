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
from datetime import datetime

from openerp import fields, exceptions
from openerp import models, api
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

_ESTADO = [
    ('draft', 'Borrador'),
    ('validado', 'Validado'),
    ('aprobacion_pago', 'Aprobación de Pago'),
    ('cerrado', 'Cerrado'),
    ('cancelado', 'Cancelado'),
]

_TIPO_SELECT = [
    ('mvd', u'Montevideo'),
    ('ext', u'Exterior'),
]


class GrpRetencionesManuales(models.Model):
    _name = 'grp.retenciones.manuales'
    _inherit = ['mail.thread']
    _description = 'Retenciones manuales'

    @api.model
    def _domain_invoice_ids(self):
        select_nro_afectacion = [('id', 'in', [])]
        self.env.cr.execute("""select min(inv.id), inv.nro_afectacion from account_invoice inv
                                inner join presupuesto_concepto con on (inv.siif_concepto_gasto = con.id)
                                where con.concepto = '1' and con.descripcion = 'Remuneraciones'
                                and inv.state= 'prioritized' and (inv.ret_sueldo= False or inv.ret_sueldo is null)
                                group by inv.nro_afectacion""")
        if self.env.cr.rowcount > 0:
            ids = self.env.cr.fetchall()
            select_nro_afectacion = [('id', 'in', [x[0] for x in ids if x])]
        return select_nro_afectacion

    @api.model
    def _get_moneda_base(self):
        res = self.env['res.users'].read([self._uid], ['company_id'])
        if res and res[0]['company_id']:
            company_id = res[0]['company_id'][0]
        else:
            return self.env['res.currency']
        res = self.env['res.company'].read([company_id], ['currency_id'])
        if res and res[0]['currency_id']:
            currency_id = res[0]['currency_id'][0]
        else:
            return self.env['res.currency']
        return currency_id

    # TODO: SPRING 10 GAP 274.275 K
    @api.model
    def _get_company_id(self):
        res = self.env['res.users'].browse(self._uid)
        if res and res.company_id:
            return res.company_id
        return self.env['res.company']

    # TODO: SPRING 10 GAP 274.275 K
    @api.model
    def _get_journal_id(self):
        res = self.env['account.journal'].search([('habilitaciones', '=', True)], limit=1)
        if res:
            return res
        return self.env['account.journal']

    # TODO: SPRING 10 GAP 274.275 K
    @api.model
    def _get_divisa(self):
        res = self.env['res.currency'].search([('name', '=', 'UYU')], limit=1)
        if res:
            return res
        return self.env['res.currency']

    # TODO: SPRING 10 GAP 274.275 K
    @api.model
    def _default_fecha_asiento(self):
        return self.fecha and self.fecha or False

    # Definicion de campos
    name = fields.Char(
        string=u"Nª retención",
        select="1"
    )
    moneda_base = fields.Many2one(
        comodel_name="res.currency",
        string=u"Moneda base",
        default='_get_moneda_base'
    )
    create_uid = fields.Many2one(
        comodel_name="res.users",
        string=u"Usuario"
    )
    company_id = fields.Many2one('res.company', string='Company', readonly=False, related=False,
                                 default=lambda self: self.env['res.company']._company_default_get(
                                     'grp.retenciones.manuales'))
    afectation_nro = fields.Integer(u'Nro afectación', required=True)
    afectation_id = fields.Many2one('account.invoice', string=u'Nro. Afectación',
                                    domain=lambda self: self._domain_invoice_ids())
    afectation_account_id = fields.Many2one('account.account', string=u'Cuenta de la afectación',
                                            related='afectation_id.account_id', readonly=True)
    residual = fields.Float(string=u'Saldo de obligación', related='afectation_id.residual', store=True, readonly=True)
    tipo = fields.Selection(
        selection=_TIPO_SELECT,
        string=u"Tipo"
    )
    fecha = fields.Date(string=u"Fecha Creación", required=False, default=datetime.now())
    period_id = fields.Many2one('account.period', string=u'Período', required=False)
    journal_id = fields.Many2one('account.journal', string=u'Diario', required=True,
                                 domain="[('habilitaciones','=', True)]", default=_get_journal_id)
    default_debit_account_id = fields.Many2one('account.account', string=u'Cuenta Contable',
                                               related='journal_id.default_debit_account_id', readonly=True)
    obligacion = fields.Many2one(
        comodel_name='account.invoice',
        string=u'Obligación'
    )
    total_estimado = fields.Float(compute='_compute_total_estimado', string=u'Total en pesos', readonly=True)
    lineas_retenciones_manuales_ids = fields.One2many(
        comodel_name='grp.lineas.retenciones.manuales',
        inverse_name='retencion_manual_id',
        string=u'Lineas de retenciones manuales'
    )
    lineas_retenciones_resumen_ids = fields.One2many(
        comodel_name='grp.lineas.retenciones.manuales.resumen',
        inverse_name='retencion_manual_id',
        string=u'Lineas de resumen de retenciones manuales'
    )
    state = fields.Selection(selection=_ESTADO, string=u'Estado', default='draft')
    divisa = fields.Many2one(
        comodel_name='res.currency',
        string=u'Divisa',
        default=lambda self: self._get_divisa()
    )
    divisa_name = fields.Char(
        string=u'Nombre divisa',
        default="UYU"
    )
    fecha_tc = fields.Date(
        string=u'Fecha TC'
    )
    valor_tc = fields.Float(
        string=u'Valor TC'
    )
    descripcion = fields.Char(
        string=u'Descripción',
        size=80,
        select="1"
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string=u'Asiento'
    )
    resumen_cargado = fields.Boolean(
        string=u'Resumen cargado',
        default=False,
    )
    boton_modificar = fields.Boolean(
        string=u'Boton modificar presionado',
        default=False
    )
    secuencial = fields.Char(
        string=u'Secuencial'
    )
    move_ids = fields.One2many(comodel_name='account.move', compute='_compute_move_ids', string=u'Asientos contables')

    # TODO: SPRING 10 GAP 274.275 K
    fecha_asiento = fields.Date(string=u"Fecha de Asiento",
                                default=lambda self: self._default_fecha_asiento())

    show_error_message = fields.Boolean(u'Mostrar mensaje de error', compute='_compute_show_error_message')

    operating_unit_id = fields.Many2one('operating.unit', string='UE', required=True)

    _defaults = {
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid,
                                                                                                       'grp.retenciones.manuales',
                                                                                                       context=context),
    }

    @api.multi
    @api.depends('journal_id', 'afectation_id', 'state')
    def _compute_show_error_message(self):
        for rec in self:
            rec.show_error_message = rec.journal_id and rec.afectation_id and rec.journal_id.default_debit_account_id.id != rec.afectation_id.account_id.id and rec.state not in [
                'draft', 'cerrado']

    # TODO: SPRING 10 GAP 274.275 K
    @api.multi
    @api.depends('lineas_retenciones_manuales_ids')
    def _compute_total_estimado(self):
        for retencion in self:
            total = 0
            for linea in retencion.lineas_retenciones_manuales_ids:
                total += linea.importe
            retencion.total_estimado = total

    @api.multi
    def _compute_move_ids(self):
        for rec in self:
            rec.move_ids = rec.lineas_retenciones_resumen_ids.filtered(lambda x: x.move_id).mapped('move_id').ids

    @api.onchange('afectation_nro', 'operating_unit_id')
    def onchange_afectation_nro(self):
        if self.operating_unit_id:
            self.env.cr.execute("""select min(inv.id), inv.nro_afectacion from account_invoice inv
                                                inner join presupuesto_concepto con on (inv.siif_concepto_gasto = con.id)
                                                where con.concepto = '1' and con.descripcion = 'Remuneraciones'
                                                and inv.state in ('prioritized','open') and inv.nro_afectacion = %s and (inv.ret_sueldo= False or inv.ret_sueldo is null) and inv.operating_unit_id = %s
                                                group by inv.nro_afectacion""" % (
            self.afectation_nro, self.operating_unit_id.id))
            _ids = [x[0] for x in self.env.cr.fetchall() if x]
        else:
            _ids = []
        afectation_domain = [('id', 'in', _ids)]
        self.afectation_id = False
        return {
            'domain': {
                'afectation_id': afectation_domain,
            }
        }

    # TODO: SPRING 10 GAP 274.275 K
    @api.onchange('lineas_retenciones_manuales_ids')
    def onchange_lineas_retenciones_manuales_ids(self):
        if self._context.get('eliminar_lineas_retenciones_manuales_ids'):
            lineas_a_eliminar_ids = self._context.get('eliminar_lineas_retenciones_manuales_ids')
            lineas_a_eliminar = self.env['grp.lineas.retenciones.manuales'].browse(lineas_a_eliminar_ids)

            resumen_2reverse = lineas_a_eliminar.mapped('resumen_id')
            resumen_2reverse.cancelar_linea()

            if self.lineas_retenciones_manuales_ids:
                self.lineas_retenciones_manuales_ids -= lineas_a_eliminar

    @api.onchange('fecha_asiento')
    def onchange_fecha_asiento(self):
        period_id = False
        if self.fecha_asiento:
            period_ids = self.env['account.period'].find(self.fecha_asiento)
            period_id = period_ids and period_ids[0].id or False
        self.period_id = period_id

    @api.onchange('divisa')
    def onchange_divisa(self):
        divisa_name = ''
        if self.divisa:
            divisa_obj = self.divisa
            if isinstance(divisa_obj, list) and divisa_obj:
                divisa_obj = divisa_obj[0]
            divisa_name = divisa_obj.name
        self.divisa_name = divisa_name

    @api.onchange('fecha_tc', 'divisa', 'company_id')
    def onchange_fecha_tc(self):
        rate = 0.0
        if self.fecha_tc and self.divisa and self.company_id:
            self._cr.execute("""SELECT rate FROM res_currency_rate WHERE
                                    currency_id = %s AND name <= %s
                                    ORDER BY name desc LIMIT 1""",
                             (self.divisa.id, self.fecha_tc))
            if self._cr.rowcount:
                rate = self._cr.fetchone()[0]
            else:
                raise exceptions.ValidationError(_(u"No currency rate associated"
                                                   u" for currency %d for the given date" % self.fecha_tc))
            _logger.info("Divisa rate: %s", rate)
        self.valor_tc = rate

    @api.model
    def create(self, vals):
        if vals.get('fecha', False) and vals['fecha']:
            anio = datetime.strptime(vals['fecha'], "%Y-%m-%d").date().year
            mes = datetime.strptime(vals['fecha'], "%Y-%m-%d").date().month
            fiscal_year_id = self.env['account.fiscalyear'].search([('code', '=', anio)], limit=1)
            if fiscal_year_id:
                vals['secuencial'] = self.env['ir.sequence'].with_context({'fiscalyear_id': fiscal_year_id.id}).get(
                    'sec.grp.retenciones.manuales')
                vals['name'] = str(mes) + '-' + str(anio) + '-' + vals['secuencial']
            else:
                raise ValueError(_(u'No se ha identificado un año fiscal adecuado!'))

        return super(GrpRetencionesManuales, self).create(vals)

    # al guardar se modifica el numero de retencion con los datos que se hayan modificado.
    @api.multi
    def write(self, vals):
        for self_obj in self:
            if (vals.get('fecha', False) and vals['fecha']) or (vals.get('tipo', False) and vals['tipo']):
                if vals.get('fecha', False) and vals['fecha']:
                    _fecha = vals['fecha']
                else:
                    _fecha = self_obj.fecha
            else:
                _fecha = self_obj.fecha
            anio = datetime.strptime(_fecha, "%Y-%m-%d").date().year
            mes = datetime.strptime(_fecha, "%Y-%m-%d").date().month
            seq = self_obj.secuencial
            if seq:
                vals['name'] = str(mes) + '-' + str(anio) + '-' + seq
            else:
                vals['name'] = str(mes) + '-' + str(anio)
        return super(GrpRetencionesManuales, self).write(vals)

    @api.multi
    def copy(self, default=None):
        default = default or {}
        default.update({
            'lineas_retenciones_resumen_ids': False,
        })
        return super(GrpRetencionesManuales, self).copy()

    @api.multi
    def action_validado(self):
        if self.filtered(lambda x: x.afectation_id.state != 'prioritized'):
            raise exceptions.ValidationError(
                _(u"No se pueden validar Retenciones si la Afectación no está 'Priorizada'!"))
        for retencion in self:
            if len(retencion.lineas_retenciones_resumen_ids) > 0:
                for linea_resumen in retencion.lineas_retenciones_resumen_ids:
                    retencion.create_move(linea_resumen)
                self.write({'state': 'validado', 'resumen_cargado': False})
            else:
                raise exceptions.ValidationError(_(u'Error, para validar'
                                                   u' la retención manual primero debe crear líneas'))
        return True

    # TODO: SPRING 10 GAP 274.275 K
    @api.one
    def create_move(self, linea_resumen):
        if not self.default_debit_account_id:
            raise exceptions.ValidationError(_(u'Error, de configuración:'
                                               u'El diario seleccionado no tiene asociada una Cuenta deudora!'))
        account_move_obj = self.env['account.move']
        account_move_line_obj = self.env['account.move.line']

        if not self.journal_id.sequence_id.active:
            raise exceptions.ValidationError(_(u'Error, de configuración:'
                                               u' Por favor activa la secuencia en el diario seleccionado.'))
        c = dict(self._context)
        c.update({'fiscalyear_id': self.period_id.fiscalyear_id.id})
        name = self.pool.get('ir.sequence').next_by_id(self._cr, self._uid, self.journal_id.sequence_id.id, context=c)

        account_move_id = account_move_obj.create({
            'name': name,
            'journal_id': self.journal_id.id,
            'period_id': self.period_id.id,
            'company_id': self.company_id.id,
            'partner_id': linea_resumen.empresa.id or False,
            'ref': self.name,
            'date': self.fecha_asiento,
            'operating_unit_id': linea_resumen.operating_unit_id.id
        })
        currency_resumen_id = False
        amount_currency_resumen = False
        total_estimado_resumen = 0
        for linea in linea_resumen.linea_ids:
            total_estimado_resumen += linea.importe
            amount_currency = False
            currency_id = False
            if linea.retencion_manual_id.divisa:
                currency = self.env['res.currency'].browse(linea.retencion_manual_id.divisa.id)
                if currency.name != 'UYU':
                    currency_id = linea.retencion_manual_id.divisa.id
                    amount_currency = (linea.importe * -1)
                    if not currency_resumen_id:
                        currency_resumen_id = linea.retencion_manual_id.divisa.id
                    amount_currency_resumen += amount_currency
                else:
                    currency_id = False
                    amount_currency = False
            account_move_line_obj.create({
                'move_id': account_move_id.id,
                'name': self.name + '-' + linea.name,
                'partner_id': linea.empresa.id or False,
                'amount_currency': amount_currency,
                'currency_id': currency_id,
                'account_id': linea.account_control_ids.id,
                'credit': linea.importe,
                'debit': False,
            })
        move_line_toreconcile = account_move_line_obj.create({
            'move_id': account_move_id.id,
            'name': self.name,
            'amount_currency': amount_currency_resumen,
            'currency_id': currency_resumen_id,
            'account_id': self.default_debit_account_id.id,
            'debit': total_estimado_resumen,
            'credit': False,
            'partner_id': self.afectation_id.partner_id.id,
        })
        linea_resumen.write({'move_id': account_move_id.id})

        # CONCILIAR ASIENTOS
        period_id = self.env['account.period'].find(fields.Date.today()).id
        lines2reconcile = account_move_line_obj.browse()
        # apunte de la factura contra el cual conciliar
        lines2reconcile += self.afectation_id.move_id.line_id.filtered(
            lambda x: x.account_id.id == self.afectation_id.account_id.id)
        # apunte de la habilitacion a conciliar
        lines2reconcile += move_line_toreconcile
        lines2reconcile.reconcile_partial('manual', writeoff_journal_id=self.journal_id.id,
                                          writeoff_period_id=period_id)

        return True

    def crear_extorno(self, reversal_period_id):
        account_move_line_obj = self.env['account.move.line']
        period_id = self.env['account.period'].find(fields.Date.today()).id
        for lineas_retenciones_resumen_id in self.lineas_retenciones_resumen_ids.filtered(lambda x: not x.cancelado):
            # ROMPER CONCILIACIONES EXISTENTES
            move_lines = lineas_retenciones_resumen_id.move_id.line_id.filtered(
                lambda x: x.reconcile_id.id or x.reconcile_partial_id)
            account_move_line_obj._remove_move_reconcile(move_ids=move_lines.ids)
            # CREAR EXTORNO
            reversal_move_ids = lineas_retenciones_resumen_id.move_id.create_reversals(
                fields.Date.today(),
                reversal_period_id=reversal_period_id,
            )
            # CONCILIANDO EXTORNO CON HABILITACION
            lines2reconcile = move_lines + account_move_line_obj.search(
                [('move_id', 'in', reversal_move_ids)]).filtered(
                lambda x: x.account_id.id == self.default_debit_account_id.id)
            if lines2reconcile:
                lines2reconcile.reconcile_partial('manual', writeoff_journal_id=self.journal_id.id,
                                                  writeoff_period_id=period_id)
        return True

    @api.multi
    def action_modificar(self):
        reversal_period_id = self.env['account.period'].find(fields.Date.today()).id
        for rec in self:
            rec.crear_extorno(reversal_period_id)
        self.write({'state': 'draft', 'boton_modificar': True})
        return True

    # TODO: SPRING 10 GAP 274.275 K
    @api.multi
    def action_aprobar_pago(self):
        self.write({'state': 'aprobacion_pago'})
        return True

    # # TODO: SPRING 10 GAP 274.275 K
    # @api.multi
    # def action_cancelar(self):
    #     for retencion in self:
    #         if len(retencion.lineas_retenciones_manuales_ids.filtered(
    #                 lambda x: x.pagado != True and x.cheque_emitido != True)) > 0:
    #             lineas = retencion.lineas_retenciones_manuales_ids.filtered(
    #                 lambda x: x.pagado != True and x.cheque_emitido != True)
    #             retencion.lineas_retenciones_resumen_ids.filtered(
    #                 lambda x: x.id in lineas.mapped(lambda x: x.resumen_id)._ids).write({'cancelado': True})
    #             retencionaction_can.action_cerrar()
    #         else:
    #             raise exceptions.ValidationError(_(u'Error, para cancelar'
    #                                                u' la retención manual primero debe crear líneas'))
    #     return True

    # Nueva implementación del cancelar
    @api.multi
    def action_cancelar(self):
        for retencion in self:
            if len(retencion.lineas_retenciones_resumen_ids.filtered(
                    lambda x: x.pagado is False and x.cheque_emitido is False)) > 0:
                resumen_ids = retencion.lineas_retenciones_resumen_ids.filtered(
                    lambda x: x.pagado is False and x.cheque_emitido is False)
                for resumen_id in resumen_ids:
                    resumen_id.cancel_summary_line()
            else:
                raise exceptions.ValidationError(_(u'Error, para cancelar'
                                                   u' la retención manual primero debe crear líneas'))
        self.write({'state': 'cancelado'})
        return True

    @api.multi
    def action_cerrar(self):
        self.write({'state': 'cerrado'})
        return True

    @api.multi
    def action_change2validado(self):
        if self.lineas_retenciones_resumen_ids.filtered(
                lambda x: x.cheque_emitido is True or x.pagado is True or x.cancelado is True):
            raise exceptions.ValidationError(_(u'Error, no se puede cambiar del estado Aprobación de pago con líneas '
                                               u'de la pestaña Resumen que tengan seleccionados algunos de los checks '
                                               u'En Proceso, Pagado, Cancelado'))
        self.write({'state': 'validado'})
        return True

    @api.multi
    def cambiar_estado_cron_habilitaciones(self):
        habilitaciones_ids = self.search([('state', '=', 'validado')])
        cantidad = 0
        if len(habilitaciones_ids) > 0:
            for habilitacion in habilitaciones_ids:
                for linea in habilitacion.lineas_retenciones_manuales_ids:
                    if linea.pagado:
                        cantidad += 1
                if cantidad == len(habilitacion.lineas_retenciones_manuales_ids):
                    self.browse([habilitacion.id]).write({'state': 'cerrado'})
                else:
                    cantidad = 0
        return True

    # TODO: SPRING 10 GAP 274.275 K
    @api.multi
    def cargar_resumen(self):
        for rec in self:
            if rec.lineas_retenciones_resumen_ids:
                lista_lineas = []
                for line in rec.lineas_retenciones_resumen_ids:
                    if not line.cheque_emitido:
                        lista_lineas.append(line.id)
                if lista_lineas:
                    self.env['grp.lineas.retenciones.manuales.resumen'].browse(lista_lineas).unlink()
            query = """
                    select id, retencion_manual_id, account_control_ids,
                    empresa, beneficiario, importe, importe_moneda_base, operating_unit_id
                    from grp_lineas_retenciones_manuales
                    where retencion_manual_id = %s and not cheque_emitido
                    """

            query_groupby = """
                    select empresa, sum(importe) as importe,
                    sum(importe_moneda_base) as importe_moneda_base, retencion_manual_id,
                    account_control_ids,
                    beneficiario, operating_unit_id
                    from grp_lineas_retenciones_manuales
                    where retencion_manual_id = %s and not cheque_emitido
                    group by empresa,retencion_manual_id,
                    account_control_ids,
                    beneficiario, operating_unit_id
                    """
            self._cr.execute(query_groupby, [rec.id])
            res_query_groupby = self._cr.dictfetchall()
            self._cr.execute(query, [rec.id])
            res_query = self._cr.dictfetchall()
            for line_group in res_query_groupby:
                if line_group.get('empresa') and line_group['empresa'] and line_group.get(
                        'operating_unit_id') and line_group['operating_unit_id']:
                    if line_group.get('beneficiario') and line_group['beneficiario']:
                        # no se agrega la linea agrupada
                        for line in res_query:
                            if (line_group['account_control_ids'] == line['account_control_ids']) \
                                    and (line_group['empresa'] == line['empresa']) \
                                    and (line_group['operating_unit_id'] == line['operating_unit_id']) \
                                    and (line_group['beneficiario'] == line['beneficiario']):
                                empresa = ''
                                if line.get('empresa', False) and line['empresa']:
                                    empresa = self.env['res.partner'].browse(line['empresa']).name
                                resumen = {
                                    'account_control_ids': line['account_control_ids'],
                                    'retencion_manual_id': line['retencion_manual_id'],
                                    'operating_unit_id': line['operating_unit_id'],
                                    'empresa': line.get('empresa', ''),
                                    'beneficiario': line.get('beneficiario', ''),
                                    'importe': line['importe'],
                                    'importe_moneda_base': line['importe_moneda_base'],
                                    'referencia': line.get('beneficiario', False) and line[
                                        'beneficiario'] or empresa,
                                    'linea_ids': [(6, 0, [line['id']])],
                                }
                                _logger.info("Antes de crear")
                                self.env['grp.lineas.retenciones.manuales.resumen'].create(resumen)
                    else:
                        _logger.info("ENTRA A FOR LINE RES QUERY")
                        if line_group.get('empresa') and line_group['empresa']:
                            empresa = self.env['res.partner'].browse(line_group['empresa']).name
                        else:
                            empresa = ''
                        resumen = {
                            'account_control_ids': line_group['account_control_ids'],
                            'retencion_manual_id': line_group['retencion_manual_id'],
                            'operating_unit_id': line_group['operating_unit_id'],
                            'empresa': line_group.get('empresa', ''),
                            'beneficiario': line_group.get('beneficiario', ''),
                            'importe': line_group['importe'],
                            'importe_moneda_base': line_group['importe_moneda_base'],
                            'referencia': line_group.get('beneficiario', False) and line_group[
                                'beneficiario'] or empresa,
                        }
                        lines_resumen = []
                        for line in res_query:
                            if (line_group['account_control_ids'] == line['account_control_ids']) \
                                    and (line_group['empresa'] == line['empresa']) \
                                    and (line_group['operating_unit_id'] == line['operating_unit_id']) \
                                    and (line_group['beneficiario'] == line['beneficiario']):
                                lines_resumen.append(line['id'])
                        if lines_resumen:
                            resumen.update({'linea_ids': [(6, 0, lines_resumen)]})
                        _logger.info("Antes de crear")
                        self.env['grp.lineas.retenciones.manuales.resumen'].create(resumen)

                else:
                    # no se agrega la linea agrupada
                    for line in res_query:
                        if (line_group['account_control_ids'] == line['account_control_ids']) \
                                and (line_group['empresa'] == line['empresa']) \
                                and (line_group['beneficiario'] == line['beneficiario']):
                            empresa = ''
                            if line.get('empresa', False) and line['empresa']:
                                empresa = self.env['res.partner'].browse(line['empresa']).name
                            resumen = {
                                'account_control_ids': line['account_control_ids'],
                                'retencion_manual_id': line['retencion_manual_id'],
                                'empresa': line.get('empresa', ''),
                                'beneficiario': line.get('beneficiario', ''),
                                'importe': line['importe'],
                                'referencia': line.get('beneficiario', False) and line['beneficiario'] or empresa,
                                'linea_ids': [(6, 0, [line['id']])],
                            }
                            _logger.info("Antes de crear")
                            self.env['grp.lineas.retenciones.manuales.resumen'].create(resumen)
            self.env['grp.retenciones.manuales'].browse([rec.id]).write({'resumen_cargado': True})
        return True

    # TODO: SPRING 10 GAP 274.275 K
    @api.multi
    def eliminar_lineas(self, lineas):
        if lineas:
            context = dict(self._context)
            mod_obj = self.env['ir.model.data']
            res = mod_obj.get_object_reference('grp_tesoreria',
                                               'grp_confirmacion_elemina_ret_manuales_wizard_view')
            models = 'grp.confirmacion.eleminar.ret.manuales.wizard'
            res_id = res and res[1] or False
            ctx = context.copy()
            ctx.update({'eliminar_lineas_retenciones_manuales_ids': lineas._ids})
            return {
                'name': "Elimina retenciones manuales",
                'view_mode': 'form',
                'view_id': res_id,
                'view_type': 'form',
                'res_model': models,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': ctx,
            }
        return True

    # TODO: SPRING 10 GAP 274.275 K
    @api.multi
    def cargar_lineas(self):
        for rec in self:
            if rec.lineas_retenciones_manuales_ids:
                rec.lineas_retenciones_manuales_ids.unlink()
            if len(rec.nro_afectacion_ids) > 0:
                invoice_obj = self.env['account.invoice']
                invoice_ids = []
                for invoice_ret in invoice_obj.search(
                        [('nro_afectacion_fnc', 'in',
                          rec.nro_afectacion_ids.mapped(lambda x: x.nro_afectacion_fnc))]).mapped(
                    lambda y: y.invoice_ret_global_line_ids):
                    if not invoice_ret.group_id and not invoice_ret.creditor_id:
                        linea = {
                            'empresa': invoice_ret.invoice_id.partner_id.id,
                            # invoice_ret.prov_retencion_no_siif.id,
                            'product_id': invoice_ret.product_id.id,
                            'invoice_ret_global_line_id': invoice_ret.id,
                            # 'nro_afectacion': invoice_ret.invoice_id.nro_afectacion_fnc,
                            'importe': invoice_ret.amount_ret_pesos,
                            'retencion_manual_id': rec.id,
                            'operating_unit_id': invoice_ret.invoice_id.operating_unit_id.id,
                        }
                        res_id = self.env['grp.lineas.retenciones.manuales'].create(linea)
                        if invoice_ret.invoice_id.id not in invoice_ids:
                            invoice_ids.append(invoice_ret.invoice_id.id)
                if len(invoice_ids) > 0:
                    for invoice in invoice_obj.browse(invoice_ids):
                        invoice.write({'ret_sueldo': True})

        # return super(grp_retenciones_manuales, self).browse(self._ids).write(vals)
        return True


class GrpLineasRetencionesManuales(models.Model):
    _name = 'grp.lineas.retenciones.manuales'
    _description = 'Lineas de retenciones manuales'

    _GRUPO_FUNCIONARIO = [
        ('secret', u'Secretaría'),
        ('serv_ext_mvdeo', u'Servicios Exterior en Montevideo'),
        ('serv_ext_ext', u'Servicio Exterior en Exterior'),
        ('adsc', u'Adscriptos'),
        ('cont_temp', u'Contratados Temporales'),
        ('exc', u'Excedentes'),
        ('subs', u'Subsidios'),
        ('adm_ases_ext', u'Administrativos y Asesores en Exterior'),
    ]

    @api.depends('retencion_manual_id', 'importe')
    def _calcular_importe_base(self):
        result = {}
        for rec in self:
            if rec.retencion_manual_id.company_id:
                company_currency = rec.retencion_manual_id.company_id.currency_id.id
                current_currency = rec.retencion_manual_id.divisa.id
                ctx = self._context.copy()
                ctx.update({'date': rec.retencion_manual_id.fecha})
                if company_currency != current_currency:
                    # MVARELA 22/04/2016 actualizo los rate type y los paso por contexto para el compute
                    # date = rec.retencion_manual_id.fecha or time.strftime('%Y-%m-%d')
                    # rate_type_from_id = False
                    # self._cr.execute("""SELECT currency_rate_type_id FROM res_currency_rate WHERE currency_id = %s
                    #  AND name <= %s AND company_id = %s
                    #   ORDER BY name desc LIMIT 1""", (current_currency, date, rec.retencion_manual_id.company_id.id))
                    # if self._cr.rowcount:
                    #     rate_type_from_id = self._cr.fetchone()[0]
                    # rate_type_to_id = False
                    # self._cr.execute("""SELECT currency_rate_type_id
                    # FROM res_currency_rate
                    # WHERE currency_id = %s AND name <= %s AND company_id = %s
                    # ORDER BY name desc LIMIT 1""", (company_currency, date, rec.retencion_manual_id.company_id.id))
                    # if self._cr.rowcount:
                    #     rate_type_to_id = self._cr.fetchone()[0]
                    # ctx.update({'currency_rate_type_from': rate_type_from_id, 'currency_rate_type_to': rate_type_to_id})
                    # _logger.info("contexto: %s", ctx)
                    # amount = currency_obj.compute(current_currency, company_currency, rec.importe, context=ctx)
                    amount = rec.importe * rec.retencion_manual_id.valor_tc
                else:
                    amount = rec.importe
                rec.importe_moneda_base = amount
            else:
                rec.importe_moneda_base = 0.0
        return result

    @api.model
    def create(self, vals):
        if not vals.get('empresa', False) and not vals.get('beneficiario', False):
            raise exceptions.ValidationError(_(u'Debe cargar un valor en al menos uno de estos campos: '
                                               u'Proveedor/Funcionario, o Beneficiario.'))
        return super(GrpLineasRetencionesManuales, self).create(vals)

    @api.multi
    @api.depends('retencion_manual_id')
    def _get_boton_modificar(self):
        for rec in self:
            rec.boton_modificar = rec.retencion_manual_id.boton_modificar

    @api.depends('retencion_manual_id')
    def _get_estado_editable(self):
        res = {}
        for rec in self:
            rec.estado_editable = (rec.retencion_manual_id.state not in ['draft'])
        return res

    retencion_manual_id = fields.Many2one(
        comodel_name='grp.retenciones.manuales',
        string=u'Retencion manual id',
    )
    empresa = fields.Many2one(
        comodel_name='res.partner',
        string=u'Proveedor/Funcionario'
    )
    divisa_name = fields.Char(
        string=u'Nombre divisa'
    )
    importe = fields.Float(
        string=u'Importe',
        required=True
    )
    importe_moneda_base = fields.Float(
        compute='_calcular_importe_base',
        string=u'Total en pesos',
        store=True
    )
    pagado = fields.Boolean(
        string=u'Pagado',
        default=False
    )
    beneficiario = fields.Char(
        string=u'Beneficiario',
        size=50
    )
    # TODO: SPRING 10 GAP 274.275 K cambio del campo a entero
    # nro_afectacion = fields.Integer(
    #     string=u'Nro. Afectación'
    # )
    afectation_id = fields.Many2one('account.invoice', string=u'Nro. Afectación',
                                    related='retencion_manual_id.afectation_id', readonly=True, store=True)
    afectation_nro = fields.Integer(string=u'Nro. Afectación',
                                    related='retencion_manual_id.afectation_id.nro_afectacion', readonly=True,
                                    store=True)
    grupo_funcionario = fields.Selection(
        selection=_GRUPO_FUNCIONARIO,
        string=u'Grupo Funcionario'
    )
    cheque_emitido = fields.Boolean(
        string=u'Cheque emitido'
    )
    resumen_id = fields.Many2one(
        comodel_name='grp.lineas.retenciones.manuales.resumen',
    )
    boton_modificar = fields.Boolean(
        compute='_get_boton_modificar',
        string=u'Boton modificar presionado'
    )
    # TODO: SPRING 10 GAP 274.275 K
    estado_editable = fields.Boolean(
        compute='_get_estado_editable',
        string=u"Estado editable"
    )

    # TODO: SPRING 10 GAP 274.275 K
    name = fields.Char(string=u"Nombre asiento")
    operating_unit_id = fields.Many2one('operating.unit', string='UE',
                                        related='retencion_manual_id.afectation_id.operating_unit_id', readonly=True)
    invoice_ret_global_line_id = fields.Many2one('account.global.retention.line',
                                                 string='Invoice Global Retention Lines')
    product_id = fields.Many2one('product.product', string='Producto',
                                 domain="[('retencion_ok','=',True),('property_account_expense.type','=','payable')]")
    account_control_ids = fields.Many2one('account.account', string=u'Cuenta', readonly=True,
                                          related='product_id.property_account_expense', store=True)
    retencion_state = fields.Selection(selection=_ESTADO, string=u'Estado', related='retencion_manual_id.state')

    # fin definicion de campos

    # TODO: SPRING 10 GAP 274.275 K
    @api.model
    def create(self, vals):
        name = '1'
        lines = self.search([('retencion_manual_id', '=', vals['retencion_manual_id'])], order='name desc', limit=1)
        if lines:
            name = str(int(lines.name) + 1)
        vals['name'] = name
        return super(GrpLineasRetencionesManuales, self).create(vals)

    # TODO: SPRING 10 GAP 274.275 K
    @api.multi
    def eliminar_linea(self):
        if self:
            context = dict(self._context)
            mod_obj = self.env['ir.model.data']
            res = mod_obj.get_object_reference('grp_tesoreria',
                                               'grp_confirmacion_elemina_ret_manuales_wizard_view')
            models = 'grp.confirmacion.eleminar.ret.manuales.wizard'
            res_id = res and res[1] or False
            ctx = context.copy()
            ctx.update({'eliminar_lineas_retenciones_manuales_ids': self._ids})
            return {
                'name': "Elimina retenciones manuales",
                'view_mode': 'form',
                'view_id': res_id,
                'view_type': 'form',
                'res_model': models,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': ctx,
            }
        return True


class GrpLineasRetencionesManualesResumen(models.Model):
    _name = 'grp.lineas.retenciones.manuales.resumen'
    _rec_name = 'referencia'

    @api.multi
    @api.depends('retencion_manual_id')
    def _get_boton_modificar(self):
        for rec in self:
            rec.boton_modificar = rec.retencion_manual_id.boton_modificar

    @api.depends('cheque_emitido')
    def _get_cheque_emitido(self):
        for rec in self:
            rec.cheque_emitido_copy = rec.cheque_emitido

    @api.depends('retencion_manual_id')
    def _get_estado_editable(self):
        for rec in self:
            rec.estado_editable = (rec.retencion_manual_id.state not in ['draft'])

    retencion_manual_id = fields.Many2one(
        comodel_name='grp.retenciones.manuales',
        string=u'Retención manual'
    )
    account_control_ids = fields.Many2one('account.account', string=u'Cuenta')
    empresa = fields.Many2one(
        comodel_name='res.partner',
        string=u'Proveedor/Funcionario'
    )
    beneficiario = fields.Char(
        string=u'Beneficiario',
        size=50
    )
    importe = fields.Float(
        string=u'Importe',
    )
    importe_moneda_base = fields.Float(
        string=u'Total en pesos',
    )
    pagado = fields.Boolean(string=u'Pagado', compute='_compute_pagado')
    referencia = fields.Char(
        string=u'Referencia'
    )
    cheque_emitido = fields.Boolean(
        string=u'Cheque emitido', compute='_compute_cheque_emitido'
    )
    cheque_emitido_copy = fields.Boolean(
        string=u'Cheque emitido copia',
        compute='_get_cheque_emitido'
    )
    linea_ids = fields.One2many(
        comodel_name='grp.lineas.retenciones.manuales',
        inverse_name='resumen_id'
    )
    boton_modificar = fields.Boolean(
        compute='_get_boton_modificar',
        string=u'Boton modificar presionado'
    )
    estado_editable = fields.Boolean(
        compute='_get_estado_editable',
        string=u"Estado editable"
    )
    # TODO: SPRING 10 GAP 274.275 K
    no_recibo = fields.Char('Nro. Recibo', size=10)
    operating_unit_id = fields.Many2one('operating.unit', string='UE')
    cancelado = fields.Boolean(string=u'Cancelado', default=False)
    move_id = fields.Many2one('account.move', string=u'Asiento')
    state = fields.Selection(selection=_ESTADO, string=u'Estado', related='retencion_manual_id.state', readonly=True)

    @api.multi
    def _compute_cheque_emitido(self):
        for rec in self:
            voucher_line_id = self.env['account.voucher.line'].search(
                [('move_line_id.move_id.id', '=', rec.move_id.id)], limit=1)
            rec.cheque_emitido = True if voucher_line_id and voucher_line_id.voucher_id.state != 'cancel' else False

    @api.multi
    def _compute_pagado(self):
        for rec in self:
            voucher_line_id = self.env['account.voucher.line'].search(
                [('move_line_id.move_id.id', '=', rec.move_id.id)], limit=1)
            rec.pagado = True if voucher_line_id and voucher_line_id.voucher_id.state == 'posted' else False

    @api.multi
    def write(self, values):
        res = super(GrpLineasRetencionesManualesResumen, self).write(values)
        retenciones_manuales_cerrar = []
        for rec in self:
            if not self.search_count(
                    [('retencion_manual_id', '=', rec.retencion_manual_id.id), ('pagado', '=', False)]):
                retenciones_manuales_cerrar.append(rec.retencion_manual_id.id)
        if retenciones_manuales_cerrar:
            self.env['grp.retenciones.manuales'].search(
                [('id', 'in', list(set(retenciones_manuales_cerrar)))]).action_cerrar()
        return res

    def crear_extorno_retenciones(self, period_id):
        return self.move_id.create_reversals(fields.Date.today(), reversal_period_id=period_id)

    def romper_conciliacion(self):
        move_lines = self.move_id.line_id.filtered(lambda x: x.reconcile_id.id or x.reconcile_partial_id)
        self.env['account.move.line']._remove_move_reconcile(move_ids=move_lines.ids)

    def conciliar_asientos(self, reversal_move_ids, period_id):
        for move_line_id in self.move_id.line_id:
            lines2rec = move_line_id + self.env['account.move.line'].search(
                [('move_id', 'in', reversal_move_ids)]).filtered(
                lambda x: x.account_id.id == move_line_id.account_id.id)
            lines2rec.reconcile(type='manual', writeoff_journal_id=self.retencion_manual_id.journal_id.id,
                                writeoff_period_id=period_id)

    def cancel_summary_line(self):
        period_id = self.env['account.period'].find(fields.Date.today()).id
        self.romper_conciliacion()
        reversal_move_ids = self.crear_extorno_retenciones(period_id)
        self.conciliar_asientos(reversal_move_ids, period_id)
        self.write({'cancelado': True})

    @api.multi
    def cancelar_linea(self):
        for rec in self:
            if rec.pagado is False and rec.cheque_emitido is False:
                rec.cancel_summary_line()
            else:
                raise exceptions.ValidationError(
                    _(u'Error, No puede cancelar una línea con check Pagado o En Proceso marcado'))
        return True


class GrpNroAfectacionRetencionesManuales(models.Model):
    _name = 'grp.nro.afectacion.retenciones.manuales'

    retencion_manual_id = fields.Many2one('grp.retenciones.manuales', string=u'Retencion manual id')
