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
class grp_resumen_ejecucion_contrato(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(grp_resumen_ejecucion_contrato, self).__init__(cr, uid, name, context=context)

        fecha_reporte = self.formatLang(
            str(datetime.today()), date=True)

        self.localcontext.update({
            'time': time,
            'get_lines': self._get_lines,
            'fecha_reporte':fecha_reporte,
        })

    # TODO: K SPRING 13 GAP 452
    def _get_lines(self, data):
        lines = []
        contrato_obj = self.pool.get('grp.contrato.proveedores')

        search_list = [('contrato_general_id','=', False),('state','=','vigente')]
        if data['fecha_inicio']:
            search_list.append(('fecha_inicio','>=',data['fecha_inicio']))
        if data['fecha_fin']:
            search_list.append(('fecha_fin','>=',data['fecha_fin']))
        if data['proveedor']:
            search_list.append(('proveedor','>=',data['proveedor'][0]))
        if data['contrato_id']:
            search_list.append(('id','>=',data['contrato_id'][0]))


        for contrato in contrato_obj.browse(self.cr,self.uid,contrato_obj.search(self.cr, self.uid, search_list)):
            vals ={
                'nro_interno':contrato.nro_interno,
                'proveedor':contrato.proveedor.name,
                'fecha_inicio':contrato.fecha_inicio,
                'fecha_fin':contrato.fecha_fin,
            }
            monedas = []
            for moneda in contrato.monedas_ids:
                vals_moneda = {
                    'moneda':moneda.moneda,
                    'monto_ajustado':moneda.monto_ajustado,
                }
                contrato_particulares_moneda_ids = contrato_obj.search(self.cr, self.uid, [('contrato_general_id','=',contrato.id),
                                                                                    ('currency.name','=',moneda.moneda)])
                saldo_pendiente = sum([elem.monto_facturar for elem in contrato_obj.browse(self.cr,self.uid,contrato_particulares_moneda_ids)])
                vals_moneda['saldo_pendiente'] = saldo_pendiente
                monedas.append(vals_moneda)
            vals['monedas'] = monedas
            contratos_particulares = []
            contrato_particulares_ids = contrato_obj.search(self.cr, self.uid, [('contrato_general_id','=',contrato.id),('state','=','vigente')])
            for particulares in contrato_obj.browse(self.cr,self.uid,contrato_particulares_ids):
                vals_particulares = {
                    'codigo_articulo':particulares.codigo_articulo,
                    'cantidad':particulares.cantidad,
                    'precio_ajustado':particulares.precio_ajustado,
                    'total_ajustado':particulares.total_ajustado,
                    'ultima_actualizacion':particulares.ultima_actualizacion,
                }
                contratos_particulares.append(vals_particulares)
            vals['contratos_particulares'] = contratos_particulares
            lines.append(vals)

        return lines

class report_grp_resumen_ejecucion_contrato(osv.AbstractModel):
    _name = 'report.grp_contrato_proveedores.report_resumen_ejecucion_contrato'
    _inherit = 'report.abstract_report'
    _template = 'grp_contrato_proveedores.report_resumen_ejecucion_contrato'
    _wrapped_report_class = grp_resumen_ejecucion_contrato

# report_sxw.report_sxw('report.account.inv.daily.registered', 'account.invoice', 'addons/grp_compras_estatales/report/account_inv_daily_register.rml', parser=account_daily_registered, header=False)