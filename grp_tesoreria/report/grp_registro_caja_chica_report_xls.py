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
from openerp.tools.translate import _

_column_sizes = [
    ('moneda', 12),
    ('producto', 12)
]

import logging
_logger = logging.getLogger(__name__)
# TODO: M SPRING 14 GAP 473
class grp_registro_caja_chica_xls_parser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(grp_registro_caja_chica_xls_parser, self).__init__(cr, uid, name,
                                                         context=context)

        caja_ids = False
        self.context = context
        if 'active_ids' in context:
            caja_ids = context['active_ids']

        self.localcontext.update({
            'datetime': datetime,
            'caja_ids': caja_ids,
            'account_bank_statement':self.get_account_bank_statement,
            'lines': self.get_lines,
            # 'monedas':self.get_monedas,
            # 'pay_invoice':self.get_pay_invoice,
            # 'other_invoice':self.get_other_invoice,
            # 'cesion_invoice':self.get_cesion_invoice,
            # 'type_cession':self.get_type_cession,
            # 'total_amount':self.get_total_amount,
            # 'calcular_saldo_ceder':self.get_calculo_saldo_ceder,
            # 'ValidationError':ValidationError
        })

    def get_account_bank_statement(self, caja_ids):
        return self.pool.get('account.bank.statement').browse(
            self.cr, self.uid, caja_ids, self.context)

    def get_lines(self, caja_ids):
        lines = []
        for rec in self.pool.get('account.bank.statement').browse(self.cr, self.uid, caja_ids, self.context):
            odg_ids = rec.line_ids.sorted(key=lambda a: a.concepto_id.odg_id).mapped(lambda x: x.concepto_id.odg_id)
            if odg_ids:
                odg_ids = list(set(odg_ids))
                for odg_id in odg_ids:
                    concepto_lines = []
                    if odg_id:
                        concepto_ids = rec.line_ids.filtered(lambda x: x.concepto_id.odg_id == odg_id).mapped\
                                                            (lambda x: x.concepto_id)
                    else:
                        concepto_ids = rec.line_ids.filtered(lambda x: x.concepto_id.odg_id == False)
                    if odg_id:
                        for concepto_id in concepto_ids:
                            if not concepto_id.poner_dinero:
                                concepto_lines.append([{'concepto': line.concepto_id.name, 'comunicacion': line.name,
                                                        'referencia': line.ref, 'importe': line.amount,
                                                        'rubro': line.concepto_id.odg_id
                                                       }for line in rec.line_ids.filtered(lambda x: x.concepto_id.id == concepto_id.id
                                                                                      and x.concepto_id.odg_id == odg_id)])
                    else:
                        for concepto_id in concepto_ids:
                            if not concepto_id.concepto_id.poner_dinero:
                                concepto_lines.append([{'concepto': line.concepto_id.name, 'comunicacion': line.name,
                                                        'referencia': line.ref, 'importe': line.amount,
                                                        'rubro': line.concepto_id.odg_id
                                                       }for line in rec.line_ids.filtered(lambda x: x.concepto_id.id == concepto_id.concepto_id.id
                                                                                      and x.concepto_id.odg_id == odg_id)])
                    lines.append(concepto_lines)
            else:
                concepto_lines = []
                concepto_ids = rec.line_ids.mapped(lambda x: x.concepto_id)
                for concepto_id in concepto_ids:
                    if not concepto_id.concepto_id.poner_dinero:
                        concepto_lines.append([{'concepto': line.concepto_id.name, 'comunicacion': line.name,
                                                'referencia': line.ref, 'importe': line.amount,
                                                'rubro': line.concepto_id.odg_id
                                                } for line in
                                               rec.line_ids.filtered(lambda x: x.concepto_id.id == concepto_id.concepto_id.id)])
                lines.append(concepto_lines)
        return lines

class grp_registro_caja_chica_xls(report_xls):
    column_sizes = [x[1] for x in _column_sizes]

    def __init__(self, name, table, rml=False, parser=False, header=True,
                 store=False):
        super(grp_registro_caja_chica_xls, self).__init__(
            name, table, rml, parser, header, store)

        # Cell Styles
        _xs = self.xls_styles
        # header

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        for caja_id in _p['caja_ids']:
            report_name = _("Registro Caja"+'-'+str((_p['account_bank_statement'](caja_id).name).replace('/','-')))
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
                ('report_name', 4, 2, 'text', _('Planilla de Caja Chica')),
            ]

            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cell_style)

            row_pos += 1

            # # ------HEADER------#
            cabezal_cell_format = _xs['bold'] + _xs['borders_all']
            cell_format = _xs['borders_all']
            cell_style = xlwt.easyxf(cell_format)
            cell_style_left = xlwt.easyxf(cell_format + _xs['left'])
            cell_style_left_bold = xlwt.easyxf(cell_format + _xs['left'] + _xs['bold'])
            cabezal_cell_style_lef = xlwt.easyxf(cabezal_cell_format + _xs['center'])

            c_specs = [
                ('Dependencia', 2, 0, 'text', 'Dependencia:'),
                # ('espacio', 2, 0, 'text', None),
                ('Dependencia'+'_value', 2, 0, 'text', _p['account_bank_statement'](caja_id).journal_id.name),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=cell_style_left_bold)
            fecha_reporte = _p['account_bank_statement'](caja_id).date
            anio = datetime.strptime(fecha_reporte, "%Y-%m-%d").date().year
            mes = datetime.strptime(fecha_reporte, "%Y-%m-%d").date().month

            c_specs = [
                ('Mes', 2, 0, 'text', 'Mes:'),
                ('Mes'+'_value', 2, 0, 'text', str(mes) + '/' + str(anio)),
                ('espacio', 2, 0, 'text', None),
                ('N de Planillado', 2, 0, 'text', 'Nº de Planillado:'),
                ('N de Planillado' + '_value', 2, 0, 'text', _p['account_bank_statement'](caja_id).name),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=cell_style_left_bold)

            lines = _p['lines'](caja_id)
            flag = False
            total = 0
            for opg in lines:
                total_opg = 0
                for concepto in opg:
                    total_concepto = 0
                    for line in concepto:
                        total_concepto += abs(line['importe'])
                        total += (-line['importe'])
                        if not flag:
                            cell_format =_xs['borders_all']
                            cell_style_left = xlwt.easyxf(cell_format + _xs['left'])
                            row_pos += 1
                            c_specs = [
                                ('concepto', 2, 0, 'text', _('Concepto')),
                                # ('odg', 2, 0, 'text', _('ODG')),
                                ('comunicacion', 2, 0, 'text', _(u'Descripcion')),
                                ('referencia', 2, 0, 'text', _('Referencia')),
                                ('importe', 2, 0, 'text', _(u'Importe $')),
                                ('rubro', 2, 0, 'text', _(u'Rubro')),
                            ]
                            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                            row_pos = self.xls_write_row(
                                ws, row_pos, row_data, row_style=cabezal_cell_style_lef)
                            flag = True

                        c_specs = [
                            ('concepto', 2, 0, 'text', line['concepto']),
                            # ('odg', 2, 0, 'text', line['rubro']),
                            ('comunicacion', 2, 0, 'text', line['comunicacion']),
                            ('referencia', 2, 0, 'text', line['referencia']),
                            ('importe', 2, 0, 'text', -line['importe']),
                            ('rubro', 2, 0, 'text', line['rubro']),
                        ]
                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cell_style_left)

                    c_specs = [
                        ('espacio', 4, 0, 'text', None),
                        ('comunicacion', 2, 0, 'text', 'Total por concepto'),
                        ('referencia', 2, 0, 'text', total_concepto)
                    ]
                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cabezal_cell_style_lef)
                    total_opg += total_concepto
                    row_pos += 1
                c_specs = [
                    ('espacio', 4, 0, 'text', None),
                    ('comunicacion', 2, 0, 'text', 'Total por Rubro'),
                    ('referencia', 2, 0, 'text', total_opg)
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cabezal_cell_style_lef)
                row_pos += 1

            cabezal_cell_format_total = xlwt.easyxf(_xs['bold'] +_xs['center'])
            c_specs = [
                ('espacio', 4, 0, 'text', None),
                ('comunicacion', 2, 0, 'text', 'TOTAL GENERAL:'),
                ('referencia', 2, 0, 'text', total)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cabezal_cell_format_total)
            row_pos += 1
            row_pos += 1

            cabezal_cell_format_line = xlwt.easyxf(_xs['center'])
            c_specs = [
                ('linea1', 2, 0, 'text', '__________________________'),
                ('espacio', 6, 0, 'text', None),
                ('linea2', 2, 0, 'text', '__________________________')
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cabezal_cell_format_line)

            c_specs = [
                ('linea1', 2, 0, 'text', 'Firma Responsable'),
                ('espacio', 6, 0, 'text', None),
                ('linea2', 2, 0, 'text', 'Revisado por:')
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cabezal_cell_format_line)
            row_pos += 1


grp_registro_caja_chica_xls('report.grp_tesoreria.grp_registro_caja_chica_xls', 'account.bank.statement',
                    parser=grp_registro_caja_chica_xls_parser)
