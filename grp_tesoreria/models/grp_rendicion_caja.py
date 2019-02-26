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

from openerp import models, fields, api, exceptions
from openerp.tools.translate import _
from openerp.exceptions import ValidationError
from datetime import *
from dateutil.relativedelta import relativedelta
import time
from lxml import etree


# TODO: M SPRING 13 GAP 281

class GrpRendicionCaja(models.Model):
    _name = 'grp.rendicion.caja'
    _rec_name = 'period_id'

    period_id = fields.Many2one('account.period',string=u'Período', readonly=True, states={'draft': [('readonly', False)]})
    period_date_start = fields.Date(related="period_id.date_start", store=True)
    period_date_stop = fields.Date(related="period_id.date_stop", store=True)
    # TODO: eliminar campo many2one
    #caja_recaudadora_id = fields.Many2one('grp.caja.recaudadora.tesoreria', string='Caja',
    #                                      domain=[('caja_principal', '=', True)])
    caja_recaudadora_ids = fields.Many2many('grp.caja.recaudadora.tesoreria', string='Cajas (principal)',
                                            domain="[('caja_principal', '=', True),('state','=','checked'),('open_date','>=',period_date_start),('open_date','<=',period_date_stop)]",
                                            readonly=True, states={'draft': [('readonly', False)]})
    caja_recaudadora_siif_ids = fields.Many2many("grp.caja.recaudadora.tesoreria.boleto.siif",
                                                 relation="grp_rendicion_caja_boleto_siif_rel", column1='grp_rendicion_caja_id', column2='boleto_siif_id',
                                                 string="Cajas (no principal)",
                                                 domain="[('state', '=', 'collection_send'),('open_date','>=',period_date_start),('open_date','<=',period_date_stop)]",
                                                 readonly=True, states={'draft': [('readonly', False)]})
    remesa_ids = fields.Many2many("grp.remesa", string="Depósito", domain="[('state', '=', 'collection_send'),('open_date','>=',period_date_start),('open_date','<=',period_date_stop)]",
                                  readonly=True, states={'draft': [('readonly', False)]})
    user_uid = fields.Many2one('res.users', 'Responsable', readonly=True, default=lambda self: self._uid)
    balance_inicial = fields.Float(string='Saldo inicial', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', u'Borrador'),
                            ('to_be_reviewed', u'Listo para revisión'),
                            ('done', u'Finalizado')], u'Estado', default='draft', readonly=True)
    cargos_ids = fields.One2many('grp.rendicion.caja.line', 'rendicion_caja_id', u'Cargos',
                                 domain=[('type', '=', 'cargos')])

    descargos_ids = fields.One2many('grp.rendicion.caja.line', 'rendicion_caja_id', u'Descargos',
                                 domain=[('type', '=', 'descargos')])

    ajustes_ids = fields.One2many('grp.rendicion.caja.line', 'rendicion_caja_id', u'Ajustes',
                                    domain=[('type', '=', 'ajuste')], readonly=True, states={'draft': [('readonly', False)]})
    balance_final_recaudacion = fields.Float(string=u"Recaudación", compute='_compute_balance_final')
    balance_final_fondos_terceros = fields.Float(string="Fondos de terceros", compute='_compute_balance_final')
    balance_final_pagos = fields.Float(string="Pagos", compute='_compute_balance_final')
    balance_final_fondos_garantia = fields.Float(string=u"Fondos de garantía", compute='_compute_balance_final')
    balance_final = fields.Float(compute='_compute_balance_final', string=u'Saldo final')

    resumen_ids = fields.One2many('grp.rendicion.caja.line.resumen', 'rendicion_caja_id', u'Resumen', readonly=True, states={'draft': [('readonly', False)]})

    balance_final_resumen = fields.Float(compute='_compute_balance_final_resumen', string=u'Saldo final resumen')

    mes_anterior_ids = fields.One2many('grp.rendicion.caja.line.siif', 'rendicion_caja_id', u'Pendientes mes anterior',
                                        domain=[('tipo', '=', 'mes_anterior')], readonly=True, states={'draft': [('readonly', False)]})
    recaudacion_ids = fields.One2many('grp.rendicion.caja.line.siif', 'rendicion_caja_id', u'Recaudación',
                                      domain=[('tipo', '=', 'recaudacion')], readonly=True, states={'draft': [('readonly', False)]})
    mes_siguiente_ids = fields.One2many('grp.rendicion.caja.line.siif', 'rendicion_caja_id', u'Mes siguiente',
                                      domain=[('tipo', '=', 'mes_siguiente')], readonly=True, states={'draft': [('readonly', False)]})
    rendicion_ids = fields.One2many('grp.rendicion.caja.line.siif', 'rendicion_caja_id', u'Rendición',
                                        domain=[('tipo', '=', 'rendicion')], readonly=True, states={'draft': [('readonly', False)]})

    balance_final_pendiente = fields.Float(string="Pendientes", compute='_compute_balance_final_general')
    balance_final_cargos = fields.Float(string="Cargos", compute='_compute_balance_final_general')
    balance_final_descargos = fields.Float(string=u"Descargos", compute='_compute_balance_final_general')
    balance_final_general = fields.Float(compute='_compute_balance_final_general', string=u'Saldo final')

    @api.one
    @api.constrains('period_id')
    def _check_lines(self):
        for line in self.cargos_ids:
            if line.date > self.period_id.date_stop or line.date < self.period_id.date_start:
                raise ValidationError(
                    _(u"La fecha no es válida. Se encuentra fuera del rango del período seleccionado!"))

    @api.multi
    @api.depends('cargos_ids','descargos_ids','ajustes_ids')
    def _compute_balance_final(self):
        for rec in self:
            rec.balance_final_recaudacion = 0.0
            rec.balance_final_fondos_terceros = 0.0
            rec.balance_final_pagos = 0.0
            rec.balance_final_fondos_garantia = 0.0
            rec.balance_final = 0.0
            if rec.cargos_ids or rec.descargos_ids or rec.ajustes_ids:
                rec.balance_final_recaudacion = self._get_total('recaudacion',rec.cargos_ids,rec.descargos_ids,rec.ajustes_ids)
                rec.balance_final_fondos_terceros = self._get_total('fondos_terceros',rec.cargos_ids,rec.descargos_ids,rec.ajustes_ids)
                rec.balance_final_pagos = self._get_total('pagos',rec.cargos_ids,rec.descargos_ids,rec.ajustes_ids)
                rec.balance_final_fondos_garantia = self._get_total('fondos_garantia',rec.cargos_ids,rec.descargos_ids,rec.ajustes_ids)
                rec.balance_final = rec.balance_inicial + rec.balance_final_recaudacion + rec.balance_final_fondos_terceros + \
                                    rec.balance_final_pagos + rec.balance_final_fondos_garantia

    @api.multi
    @api.depends('resumen_ids')
    def _compute_balance_final_resumen(self):
        for rec in self:
            rec.balance_final_resumen = 0.0
            if rec.resumen_ids:
                rec.balance_final_resumen = rec.balance_inicial + sum(map(lambda x: x.cargos, rec.resumen_ids)) - sum(map(lambda x: x.descargos, rec.resumen_ids))

    @api.multi
    @api.depends('mes_anterior_ids', 'recaudacion_ids', 'mes_siguiente_ids', 'rendicion_ids')
    def _compute_balance_final_general(self):
        for rec in self:
            rec.balance_final_pendiente = 0.0
            rec.balance_final_cargos = 0.0
            rec.balance_final_descargos = 0.0
            rec.balance_final_general = 0.0
            if rec.mes_anterior_ids or rec.recaudacion_ids or rec.mes_siguiente_ids or rec.rendicion_ids:
                rec.balance_final_pendiente = sum(map(lambda x: x.pendiente, rec.mes_anterior_ids))
                rec.balance_final_cargos = sum(map(lambda x: x.cargos, rec.mes_siguiente_ids)) + \
                                           sum(map(lambda x: x.cargos, rec.rendicion_ids))
                rec.balance_final_descargos = sum(map(lambda x: x.descargos, rec.recaudacion_ids)) + \
                                           sum(map(lambda x: x.descargos, rec.rendicion_ids))
                rec.balance_final_general = rec.balance_final_pendiente + rec.balance_final_cargos - \
                                    rec.balance_final_descargos

    @api.onchange('period_id')
    def _onchange_period_id(self):
        if self.period_id:
            self.caja_recaudadora_ids = False
            self.cargos_ids = False
            self.descargos_ids = False
            if self.caja_recaudadora_ids and self.period_id:
                rendicion_anterior = self.get_rendicion_periodo_anterior()
                if rendicion_anterior:
                    self.balance_inicial = rendicion_anterior.balance_final

    @api.onchange('caja_recaudadora_ids', 'caja_recaudadora_siif_ids', 'remesa_ids')
    def _onchange_cajas(self):
        if self.period_id and (self.caja_recaudadora_ids or self.caja_recaudadora_siif_ids or self.remesa_ids):
            self.cargos_ids = self._get_cargos_ids() or False
            self.descargos_ids = self._get_descargos_ids() or False
            rendicion_anterior = self.get_rendicion_periodo_anterior()
            if rendicion_anterior:
                self.balance_inicial = rendicion_anterior.balance_final

    # TODO: Se decidio utilizar un sql_constraints en vez de un constrains
    #_sql_constraints = [
    #    ('caja_period_uniq', 'unique (caja_recaudadora_id, period_id)', u'Solo debe existir un registro por caja y periodo.')
    #]
    @api.one
    @api.constrains('period_id','caja_recaudadora_ids')
    def _check_unicity(self):
        if self.period_id and self.caja_recaudadora_ids and \
           self.search_count([('id','!=',self.id),('period_id','=',self.period_id.id),('caja_recaudadora_ids','in',self.caja_recaudadora_ids.ids)]):
            raise ValidationError(u'Solo debe existir un registro por caja y período.')

    @api.multi
    def unlink(self):
        for row in self:
            if row.state not in ('draft'):
                raise ValidationError(u'No puede eliminar una rendición en un estado diferente a Borrador.')
        return super(GrpRendicionCaja, self).unlink()

    def _get_recaudacion_cajas_siif(self, fecha):
        recaudacion = 0
        for boleto_siif in self.caja_recaudadora_siif_ids.filtered(lambda x:x.date == fecha):
            recaudacion += abs(sum(boleto_siif.total_shipment_ids.mapped('amount')))
        return recaudacion

    def _get_recaudacion_remesa_ids(self, fecha):
        recaudacion = 0
        for remesa in self.remesa_ids.filtered(lambda x:x.date == fecha):
            recaudacion += abs(sum(remesa.total_shipment_ids.mapped('amount')))
        return recaudacion

    def _get_cargos_ids(self):
        cargos_ids = [(5,)]
        details = self.caja_recaudadora_ids.mapped('voucher_details_ids').filtered(
                                                lambda x: x.date >= self.period_id.date_start
                                                and x.date <= self.period_id.date_stop)
        valores_custodia = self.caja_recaudadora_ids.mapped('valores_custodia_ids').filtered(
                                                lambda x: x.fecha_recepcion >= self.period_id.date_start
                                                and x.fecha_recepcion <= self.period_id.date_stop)
        transactions = self.caja_recaudadora_ids.mapped('transaction_ids').filtered(
                                                lambda x: x.date >= self.period_id.date_start
                                                and x.date <= self.period_id.date_stop)

        if details or valores_custodia or transactions or self.caja_recaudadora_siif_ids:
            fechas = sorted(list(set(details.mapped('date')) | set(
                valores_custodia.mapped('fecha_recepcion')) | set(
                transactions.mapped('date')) | set(self.caja_recaudadora_siif_ids.mapped('date'))))
            for fecha in fechas:
                recaudacion = self.details_filter(details, 'recaudacion',
                                                  fecha) + self.transactions_filter(
                    transactions, 'recaudacion', fecha)
                # Recaudacion de boletos_siif (Cajas no principal)
                recaudacion += self._get_recaudacion_cajas_siif(fecha)

                fondos_terceros = self.details_filter(details, 'fondos_terceros', fecha) + self.transactions_filter(
                                                                            transactions, 'fondos_terceros', fecha)
                pagos = self.details_filter(details, 'pagos', fecha) + self.transactions_filter(transactions, 'pagos', fecha)

                fondos_garantia = self.valores_custodia_filter(valores_custodia, 'fondos_garantia', fecha)

                if recaudacion or fondos_terceros or pagos or fondos_garantia:
                    values = {
                        'date': fecha,
                        'recaudacion': abs(recaudacion) or 0,
                        'fondos_terceros': abs(fondos_terceros) or 0,
                        'pagos': abs(pagos) or 0,
                        'fondos_garantia': abs(fondos_garantia) or 0,
                        'type': 'cargos',
                    }
                    cargos_ids.append((0, 0, values))
        return cargos_ids


    def _get_descargos_ids(self):
        descargos_ids = [(5,)]
        details = self.caja_recaudadora_ids.mapped('voucher_details_ids').filtered(
                        lambda x: x.entrega_caja and (x.fecha_entrega >= self.period_id.date_start
                        and x.fecha_entrega <= self.period_id.date_stop))

        transactions = self.caja_recaudadora_ids.mapped('transaction_ids').filtered(
                        lambda x: x.date >= self.period_id.date_start
                        and x.date <= self.period_id.date_stop)

        remesas = self.caja_recaudadora_ids.filtered(
                        lambda x: x.remittance_date and x.remittance_date >= self.period_id.date_start
                        and x.remittance_date <= self.period_id.date_stop).mapped('total_shipment_ids')

        if details or transactions or remesas or self.caja_recaudadora_siif_ids or self.remesa_ids:
            fechas = sorted(list(set(details.mapped('fecha_entrega'))
                                 | set(transactions.mapped('date'))
                                 | set(remesas.mapped('caja_recaudadora_id').mapped('remittance_date'))
                                 | set(self.caja_recaudadora_siif_ids.mapped('date'))
                                 | set(self.remesa_ids.mapped('date'))
                                 ))

            for fecha in fechas:
                recaudacion = self.descargos_details_filter(details,
                                                            'recaudacion',
                                                            fecha) + self.descargos_transactions_filter(
                    transactions, 'recaudacion',
                    fecha) + self.descargos_remesas_filter(remesas,
                                                           'recaudacion', fecha)
                # Recaudacion de boletos_siif (Cajas no principal)
                recaudacion += self._get_recaudacion_cajas_siif(fecha)
                # Recaudacion de remesas
                recaudacion += self._get_recaudacion_remesa_ids(fecha)

                fondos_terceros = self.descargos_details_filter(details, 'fondos_terceros', fecha) + self.descargos_transactions_filter(
                    transactions, 'fondos_terceros', fecha) + self.descargos_remesas_filter(remesas, 'fondos_terceros', fecha)
                pagos = self.descargos_details_filter(details, 'pagos', fecha) + self.descargos_transactions_filter(
                    transactions, 'pagos', fecha) + self.descargos_remesas_filter(remesas, 'pagos', fecha)
                fondos_garantia = self.descargos_remesas_filter(remesas, 'fondos_garantia', fecha)

                if recaudacion or fondos_terceros or pagos or fondos_garantia:
                    values = {
                        'date': fecha,
                        'recaudacion': abs(recaudacion) or 0,
                        'fondos_terceros': abs(fondos_terceros) or 0,
                        'pagos': abs(pagos) or 0,
                        'fondos_garantia': abs(fondos_garantia) or 0,
                        'type': 'descargos',
                    }
                    descargos_ids.append([0, 0, values])
        return descargos_ids

    @api.multi
    def btn_review(self):
        values = {'state': 'to_be_reviewed'}
        rendicion = self.env['grp.tipo.rendicion']
        resumen_ids = [(5,)]
        for rec in self:
            if rec.cargos_ids or rec.descargos_ids or rec.ajustes_ids:
                tipos_rendicion = rendicion.search([])
                for tipo in tipos_rendicion:
                    val = self._get_resumen(tipo,tipo.type,rec.cargos_ids,rec.descargos_ids,rec.ajustes_ids)
                    if val:
                        resumen_ids.append([0, 0, val])
                values['resumen_ids'] = resumen_ids
                _data_siif = self._get_data_siif(resumen_ids)
                values['mes_anterior_ids'] = _data_siif['mes_anterior_ids']
                values['recaudacion_ids'] = _data_siif['recaudacion_ids']
                values['mes_siguiente_ids'] = _data_siif['mes_siguiente_ids']
                values['rendicion_ids'] = _data_siif['rendicion_ids']
            rec.write(values)
        return True

    @api.multi
    def btn_cancel(self):
        return self.write({'state': 'draft'})

    @api.multi
    def btn_done(self):
        return self.write({'state': 'done'})

    @api.multi
    def btn_refresh(self):
        self.ensure_one()
        self.write({'cargos_ids': self._get_cargos_ids(),'descargos_ids': self._get_descargos_ids()})

    #TODO: Filtros para cargos
    def details_filter(self, details, type, fecha):
        return sum(map(lambda x: x.weight_amount, details.filtered(lambda x: x.date == fecha
                                and not x.apertura_recibo
                                and self.get_rendicion(type, product = x.product_id))))

    def transactions_filter(self, transactions, type, fecha):
        return sum(map(lambda x: x.amount, transactions.filtered(lambda x: x.date == fecha
                                    and self.get_rendicion(type, concept=x.concept_id)
                                    and x.amount > 0)))

    def valores_custodia_filter(self, valores_custodia, type, fecha):
        return sum(map(lambda x: x.monto, valores_custodia.filtered(lambda x: x.fecha_recepcion == fecha
                                    and self.get_rendicion(type, product = x.product_id)
                                    and not x.apertura_recibo and not x.remove_transaction)))

    # TODO: Filtros para descargos
    def descargos_details_filter(self, details, type, fecha):
        return sum(map(lambda x: x.weight_amount, details.filtered(lambda x: x.fecha_entrega == fecha
                                and self.get_rendicion(type, product = x.product_id))))

    def descargos_transactions_filter(self, transactions, type, fecha):
        return sum(map(lambda x: x.amount, transactions.filtered(lambda x: x.date == fecha
                                    and self.get_rendicion(type, concept = x.concept_id)
                                    and x.amount < 0)))

    def descargos_remesas_filter(self, remesas, type, fecha):
        return sum(map(lambda x: x.amount, remesas.filtered(lambda x: x.caja_recaudadora_id.remittance_date == fecha
                                    and self.get_rendicion(type, product = x.product_id))))

    def get_rendicion(self, type, product=False, concept=False):
            rendicion = self.env['grp.tipo.rendicion']
            if product:
                return rendicion.search_count([('product_ids','=',product.id),('type','=',type)])

            if concept:
                return rendicion.search_count([('concept_ids','=',concept.id),('type','=',type)])

    def _get_total(self, type, cargos, descargos, ajustes):
        total = 0
        if type == 'recaudacion':
            total = sum(map(lambda x: x.recaudacion, cargos)) - sum(map(lambda x: x.recaudacion, descargos)) + \
                    sum(map(lambda x: x.recaudacion, ajustes))
        if type == 'fondos_terceros':
            total = sum(map(lambda x: x.fondos_terceros, cargos)) - sum(map(lambda x: x.fondos_terceros, descargos)) + \
                    sum(map(lambda x: x.fondos_terceros, ajustes))

        if type == 'pagos':
            total = sum(map(lambda x: x.pagos, cargos)) - sum(map(lambda x: x.pagos, descargos)) + \
                    sum(map(lambda x: x.pagos, ajustes))
        if type == 'fondos_garantia':
            total = sum(map(lambda x: x.fondos_garantia, cargos)) - sum(map(lambda x: x.fondos_garantia, descargos)) + \
                    sum(map(lambda x: x.fondos_garantia, ajustes))
        return total

    def _get_resumen(self, tipo_rendicion,concepto, cargos, descargos, ajustes):
        cargos = sum(map(lambda x: x[concepto], cargos)) + \
                 sum(map(lambda x: x[concepto], ajustes.filtered(lambda x: x[concepto] > 0)))

        descargos = sum(map(lambda x: x[concepto], descargos)) + \
                    sum(map(lambda x: x[concepto], ajustes.filtered(lambda x: x[concepto] < 0)))
        if cargos or descargos:
            return {'tipo_rendicion_id': tipo_rendicion.id,'cargos': cargos,'descargos': descargos}
        else:
            return False

    def _get_data_siif(self, resumen_ids):
        values = {}
        mes_anterior_ids = [(5,)]
        recaudacion_ids = [(5,)]
        mes_siguiente_ids = [(5,)]
        rendicion_ids = [(5,)]
        rendicion_anterior = self.get_rendicion_periodo_anterior()
        for resumen in resumen_ids:
            if resumen[0] == 0:
                if rendicion_anterior:
                    mes_anterior = rendicion_anterior.mes_siguiente_ids.filtered(
                                                        lambda x: x.tipo_rendicion_id.id == resumen[2]['tipo_rendicion_id'])
                    val_mes_anterior = {'tipo_rendicion_id': resumen[2]['tipo_rendicion_id'],
                                       'code': self.get_tipo_rendicion(resumen[2]['tipo_rendicion_id']).code,
                                       'pendiente':mes_anterior.mes_siguiente,
                                       'tipo': 'mes_anterior'}
                    mes_anterior_ids.append([0, 0, val_mes_anterior])
                descargos = resumen[2]['descargos']
                pendiente = 0
                val_recaudacion = {'tipo_rendicion_id': resumen[2]['tipo_rendicion_id'],
                                   'descargos': descargos,
                                   'pendiente': 0,
                                   'recaudacion': descargos - pendiente,
                                   'tipo': 'recaudacion'}
                recaudacion_ids.append([0, 0, val_recaudacion])

                cargos = resumen[2]['cargos']
                val_mes_siguiente = {'tipo_rendicion_id': resumen[2]['tipo_rendicion_id'],
                                     'cargos': cargos,
                                     'recaudacion': val_recaudacion['recaudacion'],
                                     'mes_siguiente': cargos + val_recaudacion['recaudacion'],
                                     'tipo': 'mes_siguiente'}
                mes_siguiente_ids.append([0, 0, val_mes_siguiente])

                val_rendicion = {'tipo_rendicion_id': resumen[2]['tipo_rendicion_id'],
                                 'code': self.get_tipo_rendicion(resumen[2]['tipo_rendicion_id']).code,
                                 'cargos': 0,
                                 'descargos': 0,
                                 'tipo': 'rendicion'}
                rendicion_ids.append([0, 0, val_rendicion])

        values['mes_anterior_ids'] = mes_anterior_ids
        values['recaudacion_ids'] = recaudacion_ids
        values['mes_siguiente_ids'] = mes_siguiente_ids
        values['rendicion_ids'] = rendicion_ids
        return values

    def get_tipo_rendicion(self, tipo_rendicion_id):
        return self.env['grp.tipo.rendicion'].search([('id','=',tipo_rendicion_id)])

    def get_rendicion_periodo_anterior(self):
        periodo_anterior = self._get_periodo_anterior()
        rendicion_anterior = False
        if periodo_anterior:
            #rendicion_anterior = self.search(
            #    [('caja_recaudadora_id', '=', self.caja_recaudadora_id.id), ('period_id', '=', periodo_anterior.id)], limit=1)
            for rendicion in self.search([('period_id', '=', periodo_anterior.id)]):
                if self.caja_recaudadora_ids.ids in rendicion.caja_recaudadora_ids.ids:
                    rendicion_anterior = rendicion
                    break
        return rendicion_anterior


    def _get_periodo_anterior(self):
        date_start = datetime.strptime(self.period_date_start, "%Y-%m-%d")
        date_stop_anterior = (date_start - relativedelta(days=1)).strftime("%Y-%m-%d")
        periodo_anterior = self.env['account.period'].search(
            [('date_start', '<=', date_stop_anterior), ('date_stop', '>=', date_stop_anterior)], limit=1, order='date_start DESC')
        return periodo_anterior



class GrpRendicionCajaLine(models.Model):
    _name = 'grp.rendicion.caja.line'

    rendicion_caja_id = fields.Many2one('grp.rendicion.caja', u'Rendición de caja')
    date = fields.Date(u'Fecha', required=True)
    recaudacion = fields.Float(string=u'Recaudación')
    fondos_terceros = fields.Float(string=u'Fdos. de 3ros')
    pagos = fields.Float(string=u'Pagos')
    fondos_garantia = fields.Float(string=u'Fdos. Gtías')
    type = fields.Selection([('cargos', 'Cargos'),
                             ('descargos', 'Descargos'),
                             ('ajuste','Ajuste')], string='Tipo', default='ajuste')

    period_id = fields.Many2one('account.period', string=u'Período', related='rendicion_caja_id.period_id', store=True, readonly=True)
    #caja_recaudadora_id = fields.Many2one('grp.caja.recaudadora.tesoreria', string='Caja',
    #                                      related='rendicion_caja_id.caja_recaudadora_id', readonly=True)
    caja_recaudadora_ids = fields.Many2many('grp.caja.recaudadora.tesoreria', string='Cajas',
                                          related='rendicion_caja_id.caja_recaudadora_ids', readonly=True)
    user_uid = fields.Many2one('res.users', 'Responsable', related='rendicion_caja_id.user_uid', readonly=True)
    balance_inicial = fields.Float(string=u'Saldo inicial',related='rendicion_caja_id.balance_inicial', readonly=True)

    @api.one
    @api.constrains('date', 'period_id','type')
    def _check_date(self):
        if self.type=='ajuste' and self.period_id and self.date and (self.date > self.period_id.date_stop or self.date < self.period_id.date_start):
            raise ValidationError(_("La fecha no es válida. Se encuentra fuera del rango del período seleccionado!"))


class GrpRendicionCajaLineResumen(models.Model):
    _name = 'grp.rendicion.caja.line.resumen'

    rendicion_caja_id = fields.Many2one('grp.rendicion.caja', 'Rendición de caja', ondelete='cascade')
    tipo_rendicion_id = fields.Many2one('grp.tipo.rendicion', 'Tipo de rendición')
    type = fields.Selection([('recaudacion',u'Recaudación'),
                             ('fondos_terceros',u'Fondos de terceros'),
                             ('pagos',u'Pagos'),
                             ('fondos_garantia',u'Fondos de garantía')], string=u'Tipo', related='tipo_rendicion_id.type', readonly=True)
    code = fields.Char(string=u'Código', related='tipo_rendicion_id.code', readonly=True)
    cargos = fields.Float(string=u'Cargos')
    descargos = fields.Float(string=u'Descargos')
    saldo_final = fields.Float(string=u'Saldo_final')


class GrpRendicionCajaLineSiif(models.Model):
    _name = 'grp.rendicion.caja.line.siif'

    rendicion_caja_id = fields.Many2one('grp.rendicion.caja', 'Rendición de caja')
    tipo_rendicion_id = fields.Many2one('grp.tipo.rendicion', 'Concepto')
    code = fields.Char(string=u'Código')
    doc = fields.Char(string=u'Documento')
    pendiente = fields.Float(string=u'Pendiente')
    recaudacion = fields.Float(string=u'Recaudación')
    mes_siguiente = fields.Float(string=u'Mes siguiente')
    cargos = fields.Float(string=u'Cargos')
    descargos = fields.Float(string=u'Descargos')
    tipo = fields.Selection([('mes_anterior', u'Mes anterior'),
                             ('recaudacion', u'Recaudación'),
                             ('mes_siguiente', u'Mes siguiente'),
                             ('rendicion', u'Rendición')], string=u'Tipo')




