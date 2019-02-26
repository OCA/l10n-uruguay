# -*- coding: utf-8 -*-
# © 2017 Quanam (ATEL SA., Uruguay)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# try:
from openerp.addons.report_xls.report_xls import report_xls
from openerp import fields,_, api

from openerp.report import report_sxw
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
import xlwt
import math


class GrpCashboxRegisterXls(report_xls):
    def __init__(self, name, table, rml=False, parser=False, header=True,
                 store=False):
        super(GrpCashboxRegisterXls, self).__init__(
            name, table, rml, parser, header, store)

        _xs = self.xls_styles
        self.title_center_style = xlwt.easyxf(_xs['xls_title'] + _xs['center'] + _xs['underline'])
        self.bold_left_style = xlwt.easyxf(_xs['left'] + _xs['bold'])
        self.bold_right_style = xlwt.easyxf(_xs['right'] + _xs['bold'])
        self.normal_date_style = xlwt.easyxf(_xs['left'], num_format_str=report_xls.date_format)
        self.normal_number_style = xlwt.easyxf(_xs['right'], num_format_str=report_xls.decimal_format)

        self.summary_number_style = xlwt.easyxf(_xs['right'] + _xs['bold'] + _xs['fill_grey'],
                                                num_format_str=report_xls.decimal_format)
        self.summary_style = xlwt.easyxf(_xs['right'] + _xs['bold'] + _xs['fill_grey'])

        self.subtitle_style = xlwt.easyxf(_xs['left'] + _xs['bold'] + _xs['fill_grey'])
        self.subtitle_center_style = xlwt.easyxf(_xs['center'] + _xs['bold'] + _xs['fill_blue'])


    def global_initializations(self, wb, _p, xlwt, _xs, objects, data):
        return True

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        objects.ensure_one()
        execution = objects[0]
        report_name = "Arqueo de Caja Tesorería"
        ws = wb.add_sheet(report_name)
        ws.panes_frozen = True
        ws.remove_splits = True
        ws.portrait = 1  # Landscape
        ws.fit_width_to_pages = 1
        row_pos = 1
        # set print header/footer
        ws.header_str = self.xls_headers['standard']
        ws.footer_str = self.xls_footers['standard']

        # EMPTY ROW TO DEFINE SIZES
        c_specs = [('empty%s' % i, 1, 18, 'text', None)
                   for i in range(0, 8)]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, set_column_size=True)

        summary = {}
        row_pos = self._header_section(execution, ws, _p, row_pos, _xs)
        row_pos += 3
        row_pos, summary['cash_summary'] = self._cash_section(execution, ws, _p, row_pos, _xs)
        row_pos += 3
        row_pos, summary['check_summary'] = self._receipt_docs_section(execution, ws, _p, row_pos, _xs)
        row_pos += 3
        row_pos,summary['payment_summary'] = self._payment_docs_section(execution, ws, _p, row_pos, _xs)
        row_pos += 3

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 5, 2, 'text', u'OTROS DECARGOS PENDIENTES', None, self.subtitle_center_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)
        row_pos += 1
        row_pos = self._pendent_voucher_section(execution, ws, _p, row_pos, _xs)
        row_pos += 1
        row_pos,summary['third_section'] = self._third_section(execution, ws, _p, row_pos, _xs)

        row_pos += 1
        row_pos,summary['valores_custodia'] = self._valores_custodia_section(execution, ws, _p, row_pos, _xs)

        row_pos += 1
        row_pos,summary['other_section'] = self._other_section(execution, ws, _p, row_pos, _xs)

        row_pos += 3
        row_pos = self._summary_section(execution, ws, _p, row_pos, _xs, summary)

        self.global_initializations(wb, _p, xlwt, _xs, objects, data)

    def _format_time(self, time):
        hour = str(int(math.floor(time)))
        if len(hour) == 1:
            hour = '0' + hour
        minuts = str(int(round((time % 1) * 60)))
        if len(minuts) == 1:
            minuts = '0' + minuts
        return '%s:%s' % (hour, minuts)

    def _header_section(self, o, ws, _p, row_pos, _xs):
        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('report_name', 5, 2, 'text', _('ARQUEO DE CAJA DE TESORERÍA')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.title_center_style)

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 1, 2, 'text', u'Nombre Arqueo', None, self.bold_right_style),
            ('value', 4, 2, 'text', _(o.cashbox_register_id.name_get()[0][1])),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 1, 2, 'text', u'Fecha Arqueo', None, self.bold_right_style),
            ('value', 4, 2, 'date', fields.Date.from_string(o.date),None,self.normal_date_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos =  self.xls_write_row(ws, row_pos, row_data)

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 1, 2, 'text', u'Hora inicio', None, self.bold_right_style),
            ('value', 4, 2, 'text', self._format_time(o.hour_start)),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 1, 2, 'text', u'Hora fin', None, self.bold_right_style),
            ('value', 4, 2, 'text', self._format_time(o.hour_end)),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        row_pos += 1

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 1, 2, 'text', u'Presentes:'),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data,row_style=self.bold_left_style)

        for title in o.title_ids:
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('title', 3, 2, 'text', title.name),
                ('value', 3, 2, 'text', title.operating_unit),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

        return row_pos

    def _cash_section(self, o, ws, _p, row_pos, _xs):
        currencies_summary = []

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 5, 2, 'text', u'EFECTIVO EN CAJA', None, self.subtitle_center_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        row_pos += 1

        for composition in o.composition_ids:
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('title', 5, 2, 'text', composition.currency_id and composition.currency_id.name_get()[0][1] or
                 _p['company'].currency_id.name_get()[0][1], None, self.subtitle_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('uom', 2, 2, 'text', u'Unidad de medida'),
                ('nro', 2, 2, 'text', u'Nro unidades'),
                ('stotal', 1, 2, 'text', u'Subtotal al cierre')
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

            row_start = row_pos
            for monetary_line in composition.composition_id.monetaryline_ids:
                c_specs = [
                    ('espacio', 2, 2, 'text', None),
                    ('uom', 2, 2, 'number', monetary_line.pieces, None, self.normal_number_style),
                    ('nro', 2, 2, 'number', monetary_line.number, None, self.normal_number_style),
                    ('stotal', 1, 2, 'number', None, rowcol_to_cell(row_pos, 2) + '*' + rowcol_to_cell(row_pos, 4), self.normal_number_style)
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(ws, row_pos, row_data)

            if row_start == row_pos:
                c_specs = [
                    ('espacio', 2, 2, 'text', None),
                    ('uom', 2, 2, 'number', 0, None, self.normal_number_style),
                    ('nro', 2, 2, 'number', 0, None, self.normal_number_style),
                    ('stotal', 1, 2, 'number', None, rowcol_to_cell(row_pos, 2) + '*' + rowcol_to_cell(row_pos, 4),
                     self.normal_number_style)
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(ws, row_pos, row_data)

            stotal_summary = 'SUM(' + rowcol_to_cell(row_start, 6) + ':' + rowcol_to_cell(row_pos - 1, 6) + ')'

            currencies_summary.append({
                'currency_name': 'Total %s' % (composition.currency_id and composition.currency_id.name_get()[0][1] or _p['company'].currency_id.name_get()[0][1]),
                'stotal_summary': 'SUM(' + rowcol_to_cell(row_start, 6) + ':' + rowcol_to_cell(row_pos - 1, 6) + ')'
            })
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('nro', 4, 2, 'text', 'Total', None, self.summary_style),
                ('stotal', 1, 2, 'number', None, stotal_summary, self.summary_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

        row_pos += 1
        currencies_summary_toreturn_dict = {'UYU': 0, 'USD': 0}

        for currency_summary in currencies_summary:
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency_name', 4, 2, 'text', currency_summary['currency_name'], None, self.summary_style),
                ('stotal', 1, 2, 'number', None, currency_summary['stotal_summary'], self.summary_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            if 'UYU' in currency_summary['currency_name']:
                currencies_summary_toreturn_dict['UYU'] = currency_summary['stotal_summary']
            elif 'USD' in currency_summary['currency_name']:
                currencies_summary_toreturn_dict['USD'] = currency_summary['stotal_summary']

        return row_pos, currencies_summary_toreturn_dict

    def _get_receipt_docs_items(self, execution, _p):
        env = api.Environment(self.cr, _p['user'].id, {})
        CajaRecaudadora = env['grp.caja.recaudadora.tesoreria']
        CajaRecaudadoraLine = env['grp.caja.recaudadora.tesoreria.line']
        cajas_recaudadoras_currency = {}

        hour_end = self._format_time(execution.hour_end).split(':')
        execution_date = fields.Datetime.from_string(execution.date).replace(hour=int(hour_end[0]),minute=int(hour_end[1]))

        for cashbox_id in execution.caja_recaudadora_ids:
            last_cashbox = CajaRecaudadora.search([('box_id', '=', cashbox_id.id),
                                                   ('state', 'in', ['close', 'checked']),
                                                   ('closing_date', '<=', str(execution_date))], limit=1,
                                                  order='closing_date DESC')
            for voucher_detail_id in last_cashbox.voucher_details_ids.filtered(
                    lambda x: x.payment_method == 'check'):
                _available = False
                if not voucher_detail_id.shipment and not voucher_detail_id.entrega_tesoreria:
                    _available = True
                else:
                    # BOLETO SIIF
                    if voucher_detail_id.shipment and not voucher_detail_id.caja_recaudadora_id.box_id.caja_principal:
                        if not CajaRecaudadoraLine.search_count([('siif_reference_id', '=', voucher_detail_id.id),
                                                                 ('remesa_id.state', '=', 'collection_send')]):
                            _available = True
                    # REMESA
                    # if voucher_detail_id.entrega_tesoreria and not voucher_detail_id.caja_recaudadora_id.box_id.caja_principal:
                    if voucher_detail_id.entrega_tesoreria:
                        if not CajaRecaudadoraLine.search_count([('origin_line_id', '=', voucher_detail_id.id),
                                                                 ('remesa_id.state', '=', 'collection_send')]):
                            _available = True
                if _available:
                    cajas_recaudadoras_currency.setdefault(voucher_detail_id.currency_id.name_get()[0][1],{'lines':[],'total_amount':0})
                    cajas_recaudadoras_currency[voucher_detail_id.currency_id.name_get()[0][1]]['lines'].append(
                        {'caja_config_id': cashbox_id,'type': type,'caja_recaudadora_line_id': voucher_detail_id}
                    )
                    cajas_recaudadoras_currency[voucher_detail_id.currency_id.name_get()[0][1]]['total_amount'] += voucher_detail_id.amount
        return cajas_recaudadoras_currency

    def _receipt_docs_section(self, o, ws, _p, row_pos, _xs):
        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 5, 2, 'text', u'DOCUMENTOS AL COBRO', None, self.subtitle_center_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)
        row_pos += 1
        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 5, 2, 'text', u'Detalles de cheque', None, self.subtitle_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)
        row_pos += 1

        currencies_summary = []
        lines = self._get_receipt_docs_items(o, _p)
        for currency, data in lines.items():
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency', 5, 2, 'text', currency, None, self.subtitle_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('bank', 2, 2, 'text', u'Banco', None),
                ('serie', 1, 2, 'text', u'Serie', None),
                ('check', 1, 2, 'text', u'Nro. Cheque', None),
                ('amount', 1, 2, 'text', u'Monto', None),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

            row_start = row_pos
            for currency_line in data['lines']:
                c_specs = [
                    ('espacio', 2, 2, 'text', None),
                    ('bank', 2, 2, 'text', currency_line['caja_recaudadora_line_id'].voucher_id.bank_id and
                     currency_line['caja_recaudadora_line_id'].voucher_id.bank_id.name_get()[0][1] or '', None),
                    ('serie', 1, 2, 'text', currency_line['caja_recaudadora_line_id'].voucher_id.receipt_serial, None),
                    ('check', 1, 2, 'text', currency_line['caja_recaudadora_line_id'].receipt_check, None),
                    ('amount', 1, 2, 'number', currency_line['caja_recaudadora_line_id'].amount, None,
                     self.normal_number_style),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(ws, row_pos, row_data)
            stotal_summary = 'SUM(' + rowcol_to_cell(row_start, 6) + ':' + rowcol_to_cell(row_pos - 1, 6) + ')'

            currencies_summary.append({
                'name': currency,
                'currency_name': 'Total %s' % (currency),
                'stotal_summary': stotal_summary
            })

            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('total', 4, 2, 'text', 'Total', None, self.summary_style),
                ('stotal', 1, 2, 'number', None, stotal_summary, self.summary_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

        row_pos += 1
        currencies_summary_toreturn_dict = {'UYU': 0, 'USD': 0}
        for currency_summary in currencies_summary:
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency_name', 4, 2, 'text', currency_summary['currency_name'], None, self.summary_style),
                ('stotal', 1, 2, 'number', None, currency_summary['stotal_summary'], self.summary_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            if 'UYU' in currency_summary['currency_name']:
                currencies_summary_toreturn_dict['UYU'] = currency_summary['stotal_summary']
            elif 'USD' in currency_summary['currency_name']:
                currencies_summary_toreturn_dict['USD'] = currency_summary['stotal_summary']
        return row_pos, currencies_summary_toreturn_dict


    def _get_payment_docs_items(self, execution, _p):
        env = api.Environment(self.cr, _p['user'].id, {})
        CajaRecaudadora = env['grp.caja.recaudadora.tesoreria']
        check_lines = env['grp.caja.recaudadora.tesoreria.line']

        hour_end = self._format_time(execution.hour_end).split(':')
        execution_date = fields.Datetime.from_string(execution.date).replace(hour=int(hour_end[0]),
                                                                             minute=int(hour_end[1]))

        for cashbox_id in execution.caja_cheque_ids:
            last_cashbox = CajaRecaudadora.search([('box_id', '=', cashbox_id.id),
                                                   ('state', 'in', ['close', 'checked']),
                                                   ('closing_date', '<=', str(execution_date))], limit=1,
                                                  order='closing_date DESC')
            check_lines += last_cashbox.closing_check_details_ids
        return check_lines

    def _payment_docs_section(self, o, ws, _p, row_pos, _xs):
        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 5, 2, 'text', u'DOCUMENTOS AL PAGO', None, self.subtitle_center_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)
        row_pos += 1

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('check_number', 1, 2, 'text', u'Nro. Cheque', None, self.bold_left_style),
            ('bank', 1, 2, 'text', u'Nro. Banco', None, self.bold_left_style),
            ('provider', 2, 2, 'text', u'Proveedor', None, self.bold_left_style),
            ('amount', 1, 2, 'text', u'Importe', None, self.bold_left_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        row_start = row_pos
        for line in self._get_payment_docs_items(o,_p):
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('check_number', 1, 2, 'text', line.receipt_check, None),
                ('bank', 1, 2, 'text', line.bank_id and line.bank_id.name_get()[0][1] or '', None),
                ('provider', 2, 2, 'text', line.partner_id and line.partner_id.name_get()[0][1] or '', None),
                ('amount', 1, 2, 'number', line.check_amount, None, self.normal_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

        if row_start == row_pos:
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('check_number', 1, 2, 'text', '', None),
                ('bank', 1, 2, 'text', '', None),
                ('provider', 2, 2, 'text', '', None),
                ('amount', 1, 2, 'number', 0, None, self.normal_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

        stotal_summary = 'SUM(' + rowcol_to_cell(row_start, 6) + ':' + rowcol_to_cell(row_pos - 1, 6) + ')'

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('summary', 4, 2, 'text', u'Total', None, self.summary_style),
            ('stotal', 1, 2, 'number', None, stotal_summary or None, self.summary_number_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        return row_pos,{'UYU': stotal_summary, 'USD': 0}

    def _pendent_voucher_section(self, o, ws, _p, row_pos, _xs):
        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 5, 2, 'text', u'COMPROBANTES PENDIENTES DE DECARGO', None, self.subtitle_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)
        row_pos += 1

        return row_pos


    def _third_cash_section(self, o, ws, _p, row_pos, _xs):
        currencies_summary = []

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 5, 2, 'text', u'FONDOS DE TERCEROS', None, self.subtitle_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)
        row_pos += 1

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 5, 2, 'text', u'Detalles de efectivo', None, self.subtitle_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        for composition in o.composition_ids:
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('title', 5, 2, 'text', composition.currency_id and composition.currency_id.name_get()[0][1] or
                 _p['company'].currency_id.name_get()[0][1], None, self.subtitle_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('uom', 2, 2, 'text', u'Unidad de medida'),
                ('nro', 2, 2, 'text', u'Nro unidades'),
                ('stotal', 1, 2, 'text', u'Subtotal al cierre')
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

            row_start = row_pos
            for monetary_line in composition.composition_id.fterceros_monetaryline_ids:
                c_specs = [
                    ('espacio', 2, 2, 'text', None),
                    ('uom', 2, 2, 'number', monetary_line.pieces, None, self.normal_number_style),
                    ('nro', 2, 2, 'number', monetary_line.number, None, self.normal_number_style),
                    ('stotal', 1, 2, 'number', None, rowcol_to_cell(row_pos, 2) + '*' + rowcol_to_cell(row_pos, 4),
                     self.normal_number_style)
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(ws, row_pos, row_data)
            if not composition.composition_id.fterceros_monetaryline_ids:
                c_specs = [
                    ('espacio', 2, 2, 'text', None),
                    ('uom', 2, 2, 'number', 0, None, self.normal_number_style),
                    ('nro', 2, 2, 'number', 0, None, self.normal_number_style),
                    ('stotal', 1, 2, 'number', None, rowcol_to_cell(row_pos, 2) + '*' + rowcol_to_cell(row_pos, 4),
                     self.normal_number_style)
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(ws, row_pos, row_data)

            stotal_summary = 'SUM(' + rowcol_to_cell(row_start, 6) + ':' + rowcol_to_cell(row_pos - 1, 6) + ')'

            currencies_summary.append({
                'currency_name': 'Total %s' % (composition.currency_id and composition.currency_id.name_get()[0][1] or
                                               _p['company'].currency_id.name_get()[0][1]),
                'stotal_summary': 'SUM(' + rowcol_to_cell(row_start, 6) + ':' + rowcol_to_cell(row_pos - 1, 6) + ')'
            })
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('nro', 4, 2, 'text', 'Total', None, self.summary_style),
                ('stotal', 1, 2, 'number', None, stotal_summary, self.summary_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

        row_pos += 1
        currencies_summary_toreturn_dict = {'UYU': 0, 'USD': 0}

        for currency_summary in currencies_summary:
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency_name', 4, 2, 'text', currency_summary['currency_name'], None, self.summary_style),
                ('stotal', 1, 2, 'number', None, currency_summary['stotal_summary'], self.summary_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            if 'UYU' in currency_summary['currency_name']:
                currencies_summary_toreturn_dict['UYU'] = currency_summary['stotal_summary']
            elif 'USD' in currency_summary['currency_name']:
                currencies_summary_toreturn_dict['USD'] = currency_summary['stotal_summary']

        return row_pos, currencies_summary_toreturn_dict, currencies_summary

    def _get_third_check_section_items(self, execution, _p):
        env = api.Environment(self.cr, _p['user'].id, {})
        CajaRecaudadora = env['grp.caja.recaudadora.tesoreria']
        CajaRecaudadoraLine = env['grp.caja.recaudadora.tesoreria.line']
        currency = {}

        hour_end = self._format_time(execution.hour_end).split(':')
        execution_date = fields.Datetime.from_string(execution.date).replace(hour=int(hour_end[0]),
                                                                             minute=int(hour_end[1]))

        for cashbox_id in execution.caja_fondo_terceros_ids:
            last_cashbox = CajaRecaudadora.search([('box_id', '=', cashbox_id.id),
                                                   ('state', 'in', ['close', 'checked']),
                                                   ('closing_date', '<=', str(execution_date))], limit=1,
                                                  order='closing_date DESC')
            for voucher_detail_id in last_cashbox.voucher_details_ids.filtered(
                    lambda x: x.payment_method == 'check'):
                _available = False
                if not voucher_detail_id.shipment and not voucher_detail_id.entrega_tesoreria:
                    _available = True
                else:
                    if voucher_detail_id.shipment and not voucher_detail_id.caja_recaudadora_id.box_id.caja_principal:
                        if not CajaRecaudadoraLine.search_count([('siif_reference_id', '=', voucher_detail_id.id), (
                                'boleto_siif_id.state', '!=', u'collection_send')]):
                            _available = True
                    if voucher_detail_id.entrega_tesoreria and not voucher_detail_id.caja_recaudadora_id.box_id.caja_principal:
                        if not CajaRecaudadoraLine.search_count([('origin_line_id', '=', voucher_detail_id.id),
                                                                 ('remesa_id.state', '=', 'collection_send')]):
                            _available = True
                if _available:
                    currency.setdefault(voucher_detail_id.currency_id.name_get()[0][1],
                                                           {'lines': [], 'total_amount': 0})
                    currency[voucher_detail_id.currency_id.name_get()[0][1]]['lines'].append(
                        {'caja_recaudadora_line_id': voucher_detail_id}
                    )
                    currency[voucher_detail_id.currency_id.name_get()[0][1]][
                        'total_amount'] += voucher_detail_id.amount
        return currency

    def _third_check_section(self, o, ws, _p, row_pos, _xs):
        row_pos += 1
        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 5, 2, 'text', u'Detalles de cheque', None, self.subtitle_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        currencies_summary = []
        lines = self._get_third_check_section_items(o, _p)
        for currency, data in lines.items():
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency', 5, 2, 'text', currency, None, self.subtitle_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('bank', 2, 2, 'text', u'Banco', None),
                ('serie', 1, 2, 'text', u'Serie', None),
                ('check', 1, 2, 'text', u'Nro. Cheque', None),
                ('amount', 1, 2, 'text', u'Monto', None),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

            row_start = row_pos
            for currency_line in data['lines']:
                c_specs = [
                    ('espacio', 2, 2, 'text', None),
                    ('bank', 2, 2, 'text', currency_line['caja_recaudadora_line_id'].voucher_id.bank_id and
                     currency_line['caja_recaudadora_line_id'].voucher_id.bank_id.name_get()[0][1] or '', None),
                    ('serie', 1, 2, 'text', currency_line['caja_recaudadora_line_id'].voucher_id.receipt_serial, None),
                    ('check', 1, 2, 'text', currency_line['caja_recaudadora_line_id'].receipt_check, None),
                    ('amount', 1, 2, 'number', currency_line['caja_recaudadora_line_id'].amount, None,
                     self.normal_number_style),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(ws, row_pos, row_data)
            if row_start == row_pos:
                c_specs = [
                    ('espacio', 2, 2, 'text', None),
                    ('bank', 2, 2, 'text', '', None),
                    ('serie', 1, 2, 'text', '', None),
                    ('check', 1, 2, 'text', '', None),
                    ('amount', 1, 2, 'number', 0, None,self.normal_number_style),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(ws, row_pos, row_data)
            stotal_summary = 'SUM(' + rowcol_to_cell(row_start, 6) + ':' + rowcol_to_cell(row_pos - 1, 6) + ')'

            currencies_summary.append({
                'currency_name': 'Total %s' % (currency),
                'stotal_summary': stotal_summary
            })

            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('total', 4, 2, 'text', 'Total', None, self.summary_style),
                ('stotal', 1, 2, 'number', None, stotal_summary, self.summary_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

        row_pos += 1
        currencies_summary_toreturn_dict = {'UYU': 0, 'USD': 0}
        for currency_summary in currencies_summary:
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency_name', 4, 2, 'text', currency_summary['currency_name'], None, self.summary_style),
                ('stotal', 1, 2, 'number', None, currency_summary['stotal_summary'], self.summary_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            if 'UYU' in currency_summary['currency_name']:
                currencies_summary_toreturn_dict['UYU'] = currency_summary['stotal_summary']
            elif 'USD' in currency_summary['currency_name']:
                currencies_summary_toreturn_dict['USD'] = currency_summary['stotal_summary']
        return row_pos, currencies_summary_toreturn_dict, currencies_summary

    def _third_section(self, o, ws, _p, row_pos, _xs):
        row_pos,ca_currencies_summary_toreturn_dict,ca_currencies_summary = self._third_cash_section(o, ws, _p, row_pos, _xs)
        row_pos,ch_currencies_summary_toreturn_dict,ch_currencies_summary = self._third_check_section(o, ws, _p, row_pos, _xs)

        third_currencies = {}
        for key, value in ca_currencies_summary_toreturn_dict.items():
            third_currencies.setdefault(key, {'cash':[],'check':[]})
            if isinstance(value, str):
                third_currencies[key]['cash'].append(value)
        for key, value in ch_currencies_summary_toreturn_dict.items():
            third_currencies.setdefault(key, {'cash':[],'check':[]})
            if isinstance(value, str):
                third_currencies[key]['check'].append(value)

        row_pos += 1
        for key, values in third_currencies.items():
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency', 5, 2, 'text', key, None, self.subtitle_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            row_start = row_pos
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency', 4, 2, 'text', u'Efectivo', None),
                ('stotal', 1, 2, 'number', None,values['cash'] and '+'.join(values['cash']) or None, self.normal_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency', 4, 2, 'text', u'Cheque', None),
                ('stotal', 1, 2, 'number', None, values['check'] and '+'.join(values['check']) or None,
                 self.normal_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency', 4, 2, 'text', u'Total Fondo terceros', None),
                ('stotal', 1, 2, 'number', None, 'SUM(' + rowcol_to_cell(row_start, 6) + ':' + rowcol_to_cell(row_pos - 1, 6) + ')',
                 self.normal_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

        return row_pos,third_currencies

    def _get_other_items(self, execution, _p):
        env = api.Environment(self.cr, _p['user'].id, {})
        CajaPagadora = env['grp.caja.pagadora.tesoreria']
        cajas_currency = {}

        hour_end = self._format_time(execution.hour_end).split(':')
        execution_date = fields.Datetime.from_string(execution.date).replace(hour=int(hour_end[0]),
                                                                             minute=int(hour_end[1]))

        for cashbox_id in execution.caja_otras_ids:
            last_cashbox = CajaPagadora.search([('box_id', '=', cashbox_id.id),
                                                   ('state', 'in', ['close', 'checked']),
                                                   ('closing_date', '<=', str(execution_date))], limit=1,
                                                  order='closing_date DESC')
            currency_name = last_cashbox.journal_id.currency and last_cashbox.journal_id.currency.name_get()[0][1] or \
                            _p['company'].currency_id.name_get()[0][1]
            for check_line_id in last_cashbox.check_line_ids:
                cajas_currency.setdefault(currency_name,{'lines':[],'total_amount':0})
                cajas_currency[currency_name]['lines'].append({
                    'line_id': check_line_id,
                })
                cajas_currency[currency_name]['total_amount'] += check_line_id.amount
        return cajas_currency

    def _other_section(self, o, ws, _p, row_pos, _xs):
        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 5, 2, 'text', u'OTROS VALORES', None, self.subtitle_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)
        row_pos += 1

        currencies_summary = []
        for key, data in self._get_other_items(o, _p).items():
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency', 5, 2, 'text', key, None, self.subtitle_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('cashbox', 1, 2, 'text', u'Caja', None),
                ('concept', 1, 2, 'text', u'Concepto', None),
                ('partner', 2, 2, 'text', u'Proveedor', None),
                ('amount', 1, 2, 'text', u'Importe', None)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

            row_start = row_pos
            for currency_line in data['lines']:
                c_specs = [
                    ('espacio', 2, 2, 'text', None),
                    ('cashbox', 1, 2, 'text', currency_line['line_id'].payment_box_id.box_id.name_get()[0][1], None),
                    ('concept', 1, 2, 'text', '', None),
                    ('partner', 2, 2, 'text', currency_line['line_id'].partner_id.name_get()[0][1], None),
                    ('amount', 1, 2, 'number', currency_line['line_id'].amount, None, self.normal_number_style)
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(ws, row_pos, row_data)
            stotal_summary = 'SUM(' + rowcol_to_cell(row_start, 6) + ':' + rowcol_to_cell(row_pos - 1, 6) + ')'

            currencies_summary.append({
                'name': key,
                'currency_name': 'Total %s' % (key),
                'stotal_summary': stotal_summary
            })

            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('total', 4, 2, 'text', 'Total', None, self.summary_style),
                ('stotal', 1, 2, 'number', None, stotal_summary, self.summary_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

        row_pos += 1
        currencies_summary_toreturn_dict = {'UYU': 0, 'USD': 0}
        for currency_summary in currencies_summary:
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency_name', 4, 2, 'text', currency_summary['currency_name'], None, self.summary_style),
                ('stotal', 1, 2, 'number', None, currency_summary['stotal_summary'], self.summary_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            if 'UYU' in currency_summary['currency_name']:
                currencies_summary_toreturn_dict['UYU'] = currency_summary['stotal_summary']
            elif 'USD' in currency_summary['currency_name']:
                currencies_summary_toreturn_dict['USD'] = currency_summary['stotal_summary']

        return row_pos, currencies_summary_toreturn_dict

    def _get_valores_custodia_items(self, execution, _p):
        env = api.Environment(self.cr, _p['user'].id, {})
        return env['grp.valores_custodia'].search([('state','in',['recibido','vencido','entrega_autorizada'])], order='currency_id')

    def _valores_custodia_section(self, o, ws, _p, row_pos, _xs):
        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 5, 2, 'text', u'VALORES EN GARANTÍA', None, self.subtitle_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        currencies_summary = {}

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('date', 1, 2, 'text', u'Fecha ingreso', None),
            ('garanty', 1, 2, 'text', u'Garantía', None),
            ('vto_date', 1, 2, 'text', u'Fecha Vto.', None),
            ('partner', 1, 2, 'text', u'Empresa', None),
            ('currency', 1, 2, 'text', u'Moneda', None),
            ('amount', 1, 2, 'text', u'Monto', None),
            ('licit', 1, 2, 'text', u'Licitación', None),
            ('bank', 1, 2, 'text', u'Banco', None)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

        for data in self._get_valores_custodia_items(o, _p):
            data_currency =  data.currency_id or _p['user'].company_id.currency_id
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('date', 1, 2, 'text',data.fecha_recepcion or '', None),
                ('garanty', 1, 2, 'text', data.tipo_id.name_get()[0][1], None),
                ('vto_date', 1, 2, 'text', data.fecha_vencimiento, None),
                ('partner', 1, 2, 'text', data.partner_id and data.partner_id.name_get()[0][1] or '', None),
                ('currency', 1, 2, 'text', data_currency.name_get()[0][1], None),
                ('amount', 1, 2, 'number', data.monto, None, self.normal_number_style),
                ('licit', 1, 2, 'text', data.nro_licitacion and data.nro_licitacion.name_get()[0][1] or '', None),
                ('bank', 1, 2, 'text', data.bank_id and data.bank_id.name_get()[0][1] or '', None)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            currencies_summary.setdefault(data_currency.name_get()[0][1], {'amount': 0})
            currencies_summary[data_currency.name_get()[0][1]]['amount'] += data.monto

        row_pos += 1
        currencies_summary_toreturn_dict = {'UYU': 0, 'USD': 0}
        for key,data in currencies_summary.items():
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('currency_name', 7, 2, 'text', key, None, self.summary_style),
                ('stotal', 1, 2, 'number', data['amount'],None, self.summary_number_style)
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

            if 'UYU' in key:
                currencies_summary_toreturn_dict['UYU'] = data['amount']
            elif 'USD' in data['amount']:
                currencies_summary_toreturn_dict['USD'] = data['amount']

        return row_pos, currencies_summary_toreturn_dict

    def _summary_section(self, o, ws, _p, row_pos, _xs, summary):
        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('title', 7, 2, 'text', u'EFECTIVO, DOCUMENTOS AL COBRO, DOCUMENTOS AL PAGO Y COMPROBANTES PENDIENTES DE DESCARGOS', None, self.subtitle_center_style)
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)
        row_pos += 1

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('nral', 3, 2, 'text', u'Numeral', None),
            ('uyu', 1, 2, 'text', u'Total UYU', None),
            ('usd', 1, 2, 'text', u'Total USD', None),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('nral', 3, 2, 'text', u'Efectivo en Caja', None),
            ('uyu', 1, 2, 'number', None, summary['cash_summary']['UYU'] or None, self.normal_number_style),
            ('usd', 1, 2, 'number', None, summary['cash_summary']['USD'] or None,  self.normal_number_style),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('nral', 3, 2, 'text', u'Documentos al cobro', None),
            ('uyu', 1, 2, 'number', None, summary['check_summary']['UYU'] or None, self.normal_number_style),
            ('usd', 1, 2, 'number', None, summary['check_summary']['USD'] or None, self.normal_number_style),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('nral', 3, 2, 'text', u'Comprobantes pendientes de descargo', None),
            ('uyu', 1, 2, 'number', 0, None, self.normal_number_style),
            ('usd', 1, 2, 'number', 0, None, self.normal_number_style),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('nral', 3, 2, 'text', u'Documentos de pago', None),
            ('uyu', 1, 2, 'number', 0, summary['payment_summary']['UYU'] or None, self.normal_number_style),
            ('usd', 1, 2, 'number', 0, None, self.normal_number_style),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('nral', 3, 2, 'text', u'Fondo de terceros', None),
            ('uyu', 1, 2, 'number', 0, '+'.join(summary['third_section']['UYU']['cash'] + summary['third_section']['UYU']['check']) or None, self.normal_number_style),
            ('usd', 1, 2, 'number', 0, '+'.join(summary['third_section']['USD']['cash'] + summary['third_section']['USD']['check']) or None, self.normal_number_style),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('nral', 3, 2, 'text', u'Fondos de garantía', None),
            ('uyu', 1, 2, 'number', summary['valores_custodia']['UYU'] or None, None, self.normal_number_style),
            ('usd', 1, 2, 'number', summary['valores_custodia']['USD'] or None, None, self.normal_number_style),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        c_specs = [
            ('espacio', 2, 2, 'text', None),
            ('nral', 3, 2, 'text', u'Otros Valores', None),
            ('uyu', 1, 2, 'number', 0, summary['other_section']['UYU'] or None, self.normal_number_style),
            ('usd', 1, 2, 'number', 0, summary['other_section']['USD'] or None, self.normal_number_style),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        return row_pos



GrpCashboxRegisterXls(
    'report.grp_tesoreria.report_grp_cashbox_register_xls',
    'grp.cashbox.register.execution', parser=report_sxw.rml_parse
)