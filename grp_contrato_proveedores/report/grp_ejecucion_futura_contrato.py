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

import time
from datetime import datetime
from openerp.report import report_sxw
from openerp import SUPERUSER_ID
from openerp.osv import osv

import logging
_logger = logging.getLogger(__name__)
# TODO: K SPRING 13 GAP 452
class grp_ejecucion_futura_contrato(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(grp_ejecucion_futura_contrato, self).__init__(cr, uid, name, context=context)

        fecha_reporte = self.formatLang(
            str(datetime.today()), date=True)

        self.localcontext.update({
            'time': time,
            'get_lines': self._get_lines,
            'get_code': self._get_code,
            'fecha_reporte':fecha_reporte,
        })

    # TODO: K SPRING 13 GAP 452
    def _get_code(self, data):
        return data['code']

    # TODO: K SPRING 13 GAP 452
    def _get_lines(self, data):
        lines = []
        contrato_obj = self.pool.get('grp.contrato.proveedores')
        estimado_ejecutar_obj = self.pool.get('grp.estimado.ejecutar.contrato')
        line_aux = {}
        if data['estimado_ejecutar_ids']:
            estimado_ejecutar = estimado_ejecutar_obj.browse(self.cr, self.uid,data['estimado_ejecutar_ids'])
            contrato_list = []
            for rec in estimado_ejecutar:
                contrato = rec.contrato_id
                if not contrato.id in contrato_list:
                    vals ={
                        'nro_interno':contrato.nro_interno,
                        'proveedor':contrato.proveedor.name,
                        'nro_pedido_c':contrato.pedido_compra.name,
                        'fecha_inicio':contrato.fecha_inicio,
                        'fecha_fin':contrato.fecha_fin,
                        'cantidad_renovaciones':contrato.cantidad_renovaciones,
                        'contador_renovaciones':contrato.contador_renovaciones,
                    }
                    monedas = []
                    vals_moneda = {
                        'moneda':rec.moneda,
                        'monto_ajustado':rec.monto_ajustado,
                        'saldo_pendiente':rec.monto_facturar,
                        'monto_ejecutar_actual':data['monedas'][str(rec.id)]['monto_ejecutar_actual'],
                        'monto_ejecutar_futuro':data['monedas'][str(rec.id)]['monto_ejecutar_futuro'],
                        'tipo_cambio':data['monedas'][str(rec.id)]['tipo_cambio'],
                        'total_ejecutar':data['monedas'][str(rec.id)]['total_ejecutar'],
                    }
                    monedas.append(vals_moneda)
                    vals['monedas'] = monedas
                    apgs = []
                    for apg in contrato.pedido_compra.apg_ids:
                        if apg.fiscalyear_siif_id.date_start > apg.pc_id.date_start and apg.state not in ('afectado', 'desafectado', 'anulada'):
                            vals_apg = {
                                'nro_apg':apg.name,
                                'fiscalyear_siif_id':apg.fiscalyear_siif_id.name,
                                'currency_id':apg.moneda.name,
                                'monto_divisa':apg.monto_divisa,
                            }
                            apgs.append(vals_apg)
                    vals['apg'] = apgs
                    line_aux[str(contrato.id)] = vals
                    contrato_list.append(contrato.id)
                else:
                    vals_moneda = {
                        'moneda':rec.moneda,
                        'monto_ajustado':rec.monto_ajustado,
                        'saldo_pendiente':rec.monto_facturar,
                        'monto_ejecutar_actual':data['monedas'][str(rec.id)]['monto_ejecutar_actual'],
                        'monto_ejecutar_futuro':data['monedas'][str(rec.id)]['monto_ejecutar_futuro'],
                        'tipo_cambio':data['monedas'][str(rec.id)]['tipo_cambio'],
                        'total_ejecutar':data['monedas'][str(rec.id)]['total_ejecutar'],
                    }
                    line_aux[str(contrato.id)]['monedas'].append(vals_moneda)
            if len(line_aux)>0:
                lines = [line_aux[key] for key in line_aux]
        return lines

class report_grp_resumen_ejecucion_contrato(osv.AbstractModel):
    _name = 'report.grp_contrato_proveedores.report_ejecucion_futura_contrato'
    _inherit = 'report.abstract_report'
    _template = 'grp_contrato_proveedores.report_ejecucion_futura_contrato'
    _wrapped_report_class = grp_ejecucion_futura_contrato

# report_sxw.report_sxw('report.account.inv.daily.registered', 'account.invoice', 'addons/grp_compras_estatales/report/account_inv_daily_register.rml', parser=account_daily_registered, header=False)
