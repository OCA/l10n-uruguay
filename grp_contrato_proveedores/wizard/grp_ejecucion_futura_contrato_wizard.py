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
import openerp.addons.decimal_precision as dp
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

# TODO: K SPRING 13 GAP 452
class GrpEjecucionFuturaContratoWizard(models.TransientModel):
    _name = 'grp.ejecucion.futura.contrato.wizard'

    # TODO: K SPRING 13 GAP 452
    @api.model
    def _default_lineas(self):
        estimado_ejecutar_obj = self.env["grp.estimado.ejecutar.contrato"]
        estimado_ejecutar_ids = estimado_ejecutar_obj.search([])
        monedas = []
        vals_monedas = []
        moneda = self.env.user.company_id.currency_id
        for contrato in estimado_ejecutar_ids:
            if contrato.listo and not contrato.moneda in monedas and contrato.moneda != moneda.name:
                vals_monedas.append([0, False, {'moneda': contrato.moneda}])
                monedas.append(contrato.moneda)
        return vals_monedas

    linea_ids = fields.One2many("grp.ejecucion.futura.contrato.linea.wizard", "ejecucion_futura_id",
                                default=lambda self:self._default_lineas(), string=u"Lineas")
    estimado_ejecutar_ids = fields.One2many("grp.estimado.ejecutar.contrato", compute='_compute_estimado_ejecutar_ids',
                                            string=u"Estimado a ejecutar")

    # TODO: K SPRING 12 GAP 205
    @api.one
    def _compute_estimado_ejecutar_ids(self):
        estimado_ejecutar_obj = self.env["grp.estimado.ejecutar.contrato"]
        self.estimado_ejecutar_ids = estimado_ejecutar_obj.search([('listo', '=', True)])

    # TODO: K SPRING 12 GAP 205
    def get_monedas(self, cr, uid, records, code, context=None):
        monedas = {}
        moneda_obj = self.pool.get('grp.monedas.contrato')
        registro_obj = self.pool.get('grp.registro.ejecucion.futura.contrato')
        for rec in records:
            cambio_moneda = {}
            for linea in rec.linea_ids:
                cambio_moneda[linea.moneda] = linea.monto
            if rec.estimado_ejecutar_ids:
                for estimado_ejecutar in rec.estimado_ejecutar_ids:
                    tipo_cambio = 0.0
                    total_ejecutar = estimado_ejecutar.monto_ejecutar_futuro
                    if cambio_moneda.has_key(estimado_ejecutar.moneda):
                        tipo_cambio = cambio_moneda[estimado_ejecutar.moneda]
                        total_ejecutar = estimado_ejecutar.monto_ejecutar_futuro * tipo_cambio
                    monedas[str(estimado_ejecutar.id)] = {'monto_ejecutar_actual': estimado_ejecutar.monto_ejecutar_actual,
                                                          'monto_ejecutar_futuro': estimado_ejecutar.monto_ejecutar_futuro,
                                                          'tipo_cambio': tipo_cambio,
                                                          'total_ejecutar' : total_ejecutar}
                    registro_obj.create(cr, uid, {'id_ejecucion': code,
                                                  'contrato_id': estimado_ejecutar.contrato_id.id,
                                                  'moneda': estimado_ejecutar.moneda,
                                                  'monto_ajustado': estimado_ejecutar.monto_ajustado,
                                                  'monto_facturar': estimado_ejecutar.monto_facturar,
                                                  'monto_ejecutar_actual': estimado_ejecutar.monto_ejecutar_actual,
                                                  'monto_ejecutar_futuro': estimado_ejecutar.monto_ejecutar_futuro,
                                                  'tipo_cambio': tipo_cambio,
                                                  'monto_ejecutar_fut_pesos' : total_ejecutar})
                    moneda_obj.write(cr, uid, estimado_ejecutar.id, {'monto_ejecutar_actual': 0.00,
                                                                     'listo': False,
                                                                     'fecha_procesamiento': (datetime.now()).strftime('%Y-%m-%d %H:%M:%S')})

        return monedas

    # TODO: K SPRING 13 GAP 452
    def procesar_datos(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}

        data = self.read(cr, uid, ids)[0]

        obj_sequence = self.pool.get('ir.sequence')
        data['code'] = obj_sequence.next_by_code(cr, uid, 'sec.ejecucion.futura.contrato', context)

        datas = {
             'ids': [],
             'model': 'grp.contrato.proveedores',
             'form': data
            }
        records = self.browse(cr, uid, ids)
        data['monedas'] = self.get_monedas(cr, uid, records, data['code'], context)
        return self.pool['report'].get_action(cr, uid, [], 'grp_contrato_proveedores.report_ejecucion_futura_contrato', data=datas, context=context)

    # TODO: K SPRING 13 GAP 452
    def procesar_datos_xls(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}

        data = self.read(cr, uid, ids)[0]

        obj_sequence = self.pool.get('ir.sequence')
        data['code'] = obj_sequence.next_by_code(cr, uid, 'sec.ejecucion.futura.contrato', context)

        datas = {
             'ids': [],
             'model': 'grp.contrato.proveedores',
             'form': data
            }

        records = self.browse(cr, uid, ids)
        data['monedas'] = self.get_monedas(cr, uid, records, data['code'], context)

        return {'type': 'ir.actions.report.xml',
                    'report_name': 'grp_contrato_proveedores.grp_ejecucion_futura_contrato_xls',
                    'datas': datas}


class GrpEjecucionFuturaContratoLineaWizard(models.TransientModel):
    _name = 'grp.ejecucion.futura.contrato.linea.wizard'

    ejecucion_futura_id = fields.Many2one('grp.ejecucion.futura.contrato.wizard', 'Ejecucion futura')
    moneda = fields.Char(string="Moneda")
    monto = fields.Float(string='Tipo de cambio', digits_compute=dp.get_precision('Account'))




