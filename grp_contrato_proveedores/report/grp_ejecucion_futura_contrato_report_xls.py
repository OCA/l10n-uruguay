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
import xlwt
from datetime import datetime
from openerp.report import report_sxw
from openerp.addons.report_xls.report_xls import report_xls
from .grp_ejecucion_futura_contrato import grp_ejecucion_futura_contrato
from openerp.tools.translate import _

_column_sizes = [
    ('date', 12),
    ('period', 12),
    ('move', 20),
    ('journal', 12),
    ('account_code', 12),
    ('partner', 30),
    ('ref', 30),
    ('label', 45),
    ('counterpart', 30),
    ('debit', 15),
    ('credit', 15),
    ('cumul_bal', 15),
    ('curr_bal', 15),
    ('curr_code', 7),
]

import logging
_logger = logging.getLogger(__name__)
# TODO: K SPRING 13 GAP 452
class grp_ejecucion_futura_contrato_xls(report_xls):
    column_sizes = [x[1] for x in _column_sizes]

    def __init__(self, name, table, rml=False, parser=False, header=True,
                 store=False):
        super(grp_ejecucion_futura_contrato_xls, self).__init__(
            name, table, rml, parser, header, store)

        # Cell Styles
        _xs = self.xls_styles
        # header



    def generate_xls_report(self, _p, _xs, data, objects, wb):
        for contrato_id in _p['get_lines'](data['form']):
            report_name = _("Ejecucion futura"+'-'+str(contrato_id['nro_interno']))
            ws = wb.add_sheet(report_name[:31])
            ws.panes_frozen = True
            ws.remove_splits = True
            ws.portrait = 1  # Landscape
            ws.fit_width_to_pages = 1
            row_pos = 1

            # set print header/footer
            ws.header_str = self.xls_headers['standard']
            ws.footer_str = self.xls_footers['standard']

            # Title
            cell_style = xlwt.easyxf(_xs['xls_title']+_xs['center']+_xs['underline'])
            c_specs = [
                ('espacio', 3, 2, 'text', None),
                ('report_name', 4, 2, 'text', _('Ejecución futura de contratos')),
            ]

            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cell_style)

            cell_style_right = xlwt.easyxf(_xs['right'])
            c_specs = [
                ('espacio', 8, 2, 'text', None),
                ('report_name', 2, 2, 'text', _p['fecha_reporte']),
            ]

            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cell_style_right)

            c_specs = [
                ('espacio', 8, 2, 'text', None),
                ('report_name', 2, 2, 'text', _p['get_code'](data['form'])),
            ]

            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cell_style_right)

            row_pos += 1


            # ------HEADER------#
            cabezal_cell_format = _xs['bold'] + _xs['borders_all']
            cell_format = _xs['borders_all']
            cell_style = xlwt.easyxf(cell_format)
            cell_style_left = xlwt.easyxf(cell_format + _xs['left'])
            cabezal_cell_style_lef = xlwt.easyxf(cabezal_cell_format + _xs['left'])
            header_data =[contrato_id['nro_interno'],contrato_id['nro_pedido_c'],contrato_id['proveedor'],
                          contrato_id['fecha_inicio'],contrato_id['fecha_fin'],contrato_id['cantidad_renovaciones'],
                          contrato_id['contador_renovaciones']]
            for value in header_data:
                c_specs = [
                    (value, 2, 0, 'text', value),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cell_style_left)

            cell_format =_xs['borders_all']
            cell_style_left = xlwt.easyxf(cell_format + _xs['left'])
            row_pos += 1
            c_specs = [
                ('moneda', 2, 0, 'text', _('Moneda')),
                ('monto_ajustado', 2, 0, 'text', _('Monto contrato ajustado')),
                ('saldo_pendiente', 2, 0, 'text', _('Saldo pendiente')),
                ('monto_ejecutar_actual', 2, 0, 'text', _('Monto a ejecutar ej. actual')),
                ('monto_ejecutar_futuro', 2, 0, 'text', _('Monto a ejecutar ej futuros')),
                ('tipo_cambio', 2, 0, 'text', _('Tipo de cambio')),
                ('total_ejecutar', 2, 0, 'text', _('Monto a ejecutar ej. futuros (pesos)')),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

            monedas = contrato_id['monedas']
            total_ejecutar_f = 0
            for moneda in monedas:
                total_ejecutar_f += moneda['total_ejecutar']
                c_specs = [
                    ('moneda', 2, 0, 'text', moneda['moneda']),
                    ('monto_ajustado', 2, 0, 'text', moneda['monto_ajustado']),
                    ('saldo_pendiente', 2, 0, 'text', moneda['saldo_pendiente']),
                    ('monto_ejecutar_actual', 2, 0, 'text', moneda['monto_ejecutar_actual']),
                    ('monto_ejecutar_futuro', 2, 0, 'text', moneda['monto_ejecutar_futuro']),
                    ('tipo_cambio', 2, 0, 'text', moneda['tipo_cambio']),
                    ('total_ejecutar', 2, 0, 'text', moneda['total_ejecutar']),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cell_style_left)
            c_specs = [
                    ('espacio', 12, 0, 'text', None),
                    ('total_ejecutar_f', 2, 0, 'text', total_ejecutar_f),
                ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cell_style_left)

            row_pos += 1
            cell_detalle_style = xlwt.easyxf(cell_format + _xs['left'] + _xs['underline'])
            c_specs = [
                ('detalles', 11, 0, 'text', _('APG futuras')),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cell_detalle_style)
            c_specs = [
                ('nro_apg', 2, 0, 'text', _('Nro APG')),
                ('fiscalyear_siif_id', 2, 0, 'text', _('Año fiscal')),
                ('currency_id', 2, 0, 'text', _('Precio Moneda')),
                ('monto_divisa', 2, 0, 'text', _('Monto original')),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

            apgs = contrato_id['apg']
            for apg in apgs:
                c_specs = [
                    ('nro_apg', 2, 0, 'text', apg['nro_apg']),
                    ('fiscalyear_siif_id', 2, 0, 'text', apg['fiscalyear_siif_id']),
                    ('currency_id', 2, 0, 'text', apg['currency_id']),
                    ('monto_divisa', 2, 0, 'text', apg['monto_divisa']),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cell_style_left)

grp_ejecucion_futura_contrato_xls('report.grp_contrato_proveedores.grp_ejecucion_futura_contrato_xls', 'grp.contrato.proveedores',
                    parser=grp_ejecucion_futura_contrato)
