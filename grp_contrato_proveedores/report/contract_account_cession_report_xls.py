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

import xlwt
from datetime import datetime
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from openerp.tools.translate import _
from openerp.report import report_sxw
from openerp.exceptions import ValidationError
from openerp.osv import osv
import openerp
import logging
_logger = logging.getLogger(__name__)

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
# TODO: M SPRING 12 GAP 79
class contract_account_cession_xls_parser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(contract_account_cession_xls_parser, self).__init__(cr, uid, name,
                                                         context=context)
        contract_obj = self.pool.get('grp.contrato.proveedores')
        number = ''
        contract_ids = False
        self.context = context
        if 'active_ids' in context:
            contract_ids = context['active_ids']
            # number = contract_obj.browse(cr, uid, contract_ids[0], self.context).nro_interno

        fecha_reporte = self.formatLang(
            str(datetime.today()), date_time=True)

        self.localcontext.update({
            'datetime': datetime,
            'contract_id': contract_ids,
            'contract_number':self.contract_number,
            'fecha_reporte':fecha_reporte,
            'cessions':self.get_cessions,
            'monedas':self.get_monedas,
            'pay_invoice':self.get_pay_invoice,
            'other_invoice':self.get_other_invoice,
            'cesion_invoice':self.get_cesion_invoice,
            'type_cession':self.get_type_cession,
            'total_amount':self.get_total_amount,
            'calcular_saldo_ceder':self.get_calculo_saldo_ceder,
            'ValidationError':ValidationError
        })

    def contract_number(self, contract_id):
        return self.pool.get('grp.contrato.proveedores').browse(self.cr, self.uid, contract_id, self.context).nro_interno


    def get_cessions(self, contract_id):
        cession = self.pool.get('grp.contrato.proveedores').browse(
            self.cr, self.uid, contract_id, self.context).cession_ids
        return cession

    def get_monedas(self, contract_id):
        monedas = self.pool.get('grp.contrato.proveedores').browse(
            self.cr, self.uid, contract_id, self.context).monedas_ids
        return monedas

    def get_pay_invoice(self, contract_id,cesion):
        # contract_cessions_ids = []
        invoices = []
        # contract_cessions = self.pool.get('grp.contrato.proveedores').browse(
        #     self.cr, self.uid, contract_id, self.context).cession_ids
        # if contract_cessions:
        #     contract_cessions_ids = contract_cessions.ids
        contract_invoices = self.pool.get('account.invoice').search(
            self.cr, self.uid, [('contrato_id','=',contract_id)])#,('state','=','paid')
        for contract_invoice in self.pool.get('account.invoice').browse(self.cr, self.uid,contract_invoices, self.context):
            if contract_invoice.filtered(lambda x: x.cesion_ids):
                if contract_invoice.mapped(lambda x: x.cesion_ids).filtered(lambda x: x.contract_cesion_id.id == cesion.id):
                    invoices.append(contract_invoice)
        return invoices

    def get_other_invoice(self, contract_id,cesion):
        invoices = []
        contract_invoices = self.pool.get('account.invoice').search(
            self.cr, self.uid, [('contrato_id','=',contract_id)])#,('state','in',['open','intervened','prioritized'])
        for contract_invoice in self.pool.get('account.invoice').browse(self.cr, self.uid,contract_invoices, self.context):
            if contract_invoice.filtered(lambda x: x.cesion_ids):
                if contract_invoice.mapped(lambda x: x.cesion_ids).filtered(lambda x: x.contract_cesion_id.id == cesion.id):
                    invoices.append(contract_invoice)
        return invoices

    def get_cesion_invoice(self, invoice,cesion):
        cesion_invoice = False
        if invoice.cesion_ids:
            cesion_invoice = invoice.mapped(lambda x: x.cesion_ids).filtered(lambda x: x.contract_cesion_id.id == cesion.id)
        return cesion_invoice

    def get_type_cession(self, contract_id):
        type = self.pool.get('grp.contrato.proveedores').browse(
            self.cr, self.uid, contract_id, self.context).cession_type
        return type

    def get_total_amount(self, cesions):
        amount_total = sum(
                    map(lambda x: x.give_amount, cesions))
        return amount_total

    def get_calculo_saldo_ceder(self, moneda, invoices, cesion):
        invoice_obj = self.pool.get('account.invoice')
        calcular_monto_cedido = 0
        currency = self.pool.get('res.currency').browse(self.cr, self.uid,int(moneda.moneda), self.context)
        for invoice in invoices:
            if invoice.currency_id.id == int(moneda.moneda):
                cesion_invoice = self.get_cesion_invoice(invoice, cesion)
                monto_cedido_en_moneda = 0
                if invoice.currency_id.type_ref_base == 'smaller' and cesion_invoice:
                    monto_cedido_en_moneda = cesion_invoice.monto_cedido_embargado * currency.rate
                elif invoice.currency_id.type_ref_base == 'bigger' and cesion_invoice:
                    monto_cedido_en_moneda = cesion_invoice.monto_cedido_embargado / currency.rate
                calcular_monto_cedido += monto_cedido_en_moneda
        return calcular_monto_cedido




class contract_account_cession_xls(report_xls):
    column_sizes = [x[1] for x in _column_sizes]

    def __init__(self, name, table, rml=False, parser=False, header=True,
                 store=False):
        super(contract_account_cession_xls, self).__init__(
            name, table, rml, parser, header, store)

        # Cell Styles
        _xs = self.xls_styles
        # header



    def generate_xls_report(self, _p, _xs, data, objects, wb):
        for contrato_id in _p['contract_id']:
            report_name = _("Cuenta corriente de cesiones"+'-'+str(contrato_id))
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
            cell_style = xlwt.easyxf(_xs['xls_title']+_xs['center'])
            c_specs = [
                ('espacio', 2, 2, 'text', None),
                ('report_name', 4, 2, 'text', _('Cuenta corriente de cesiones')),
            ]
            # row_data = self.xls_row_template(c_specs, ['report_name'])
            # row_pos = self.xls_write_row(
            #     ws, row_pos, row_data, row_style=cell_style)

            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cell_style)

            row_pos += 1


            # ------HEADER------#
            cabezal_cell_format = _xs['bold'] + _xs['fill_blue'] + _xs['borders_all']
            cell_format = _xs['borders_all']
            cell_style = xlwt.easyxf(cell_format)
            cell_style_left = xlwt.easyxf(cell_format + _xs['left'])
            cabezal_cell_style_lef = xlwt.easyxf(cabezal_cell_format + _xs['left'])
            header_data ={'cabezal_1':u'Fecha reporte:','cabezal_2':u'Número contrato:'}
            for key, value in header_data.items():
                if key == 'cabezal_1':
                    fecha_reporte = _p['fecha_reporte']
                    c_specs = [
                        (key, 2, 0, 'text', value),
                        (key+'_value', 2, 0, 'text', fecha_reporte),
                    ]
                else:
                    number = _p['contract_number'](contrato_id)
                    c_specs = [
                        (key, 2, 0, 'text', value),
                        (key + '_value', 3, 0, 'text', number),
                    ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cell_style_left)

            row_pos += 2

            cessions = _p['cessions'](contrato_id)
            total_amount = _p['total_amount'](cessions)
            for cesion in cessions:
                cesion_data = {'cesion_1': u'Fecha cesión:', 'cesion_2': u'Proveedor:','cesion_3':u'Tipo cesión'}
                for key, value in cesion_data.items():
                    if key == 'cesion_1':
                        inf = cesion.date
                        # inf = _p['format_date'](cesion.date)
                    elif key == 'cesion_2':
                        inf = str(cesion.partner_id.name)
                    else:
                        if cesion.cession_type == 'amout_cession':
                            inf = u'Cesión de importes'
                        else:
                            inf = u'Cesión de totalidad del contrato'
                    c_specs = [
                        (key, 2, 0, 'text', value),
                        (key+'_value', 3, 0, 'text', inf),
                    ]
                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cell_style_left)

                if cesion.cession_type == 'amout_cession':
                    c_specs = [
                        ('cession_type', 3, 0, 'text', _('Importe cedido en pesos:')),
                        ('cession_type' + '_value', 2, 0, 'text', total_amount),
                    ]
                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cell_style_left)
                else:
                    cell_format = _xs['bold'] + _xs['fill_blue'] + _xs['borders_all']
                    row_pos += 1
                    c_specs = [
                        ('moneda', 2, 0, 'text', _('Moneda')),
                        ('monto_ajustado', 3, 0, 'text', _('Monto contrato ajustado')),
                    ]
                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                    monedas = _p['monedas'](contrato_id)
                    for moneda in monedas:
                        c_specs = [
                            ('moneda', 2, 0, 'text', moneda.moneda),
                            ('monto_ajustado', 3, 0, 'text', moneda.monto_ajustado),
                        ]
                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cell_style_left)

                row_pos += 2

                # Title
                cell_style = xlwt.easyxf(_xs['xls_title'] + _xs['left'])
                c_specs = [
                    ('report_name', 4, 2, 'text', _('Facturas pagas')),
                ]
                row_data = self.xls_row_template(c_specs, ['report_name'])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cell_style)

                c_specs = [
                    ('invoice_date', 2, 0, 'text', _('Fecha factura')),
                    ('invoice_nro', 2, 0, 'text', _('Nro. factura')),
                    ('invoice_moneda', 2, 0, 'text', _('Moneda factura')),
                    ('invoice_amount', 3, 0, 'text', _('Monto cedido en factura')),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                invoices = _p['pay_invoice'](contrato_id, cesion)
                monto_total = 0
                for invoice in invoices:
                    cesion_invoice = _p['cesion_invoice'](invoice, cesion)
                    if cesion_invoice:
                        monto_total += cesion_invoice.monto_cedido_embargado
                    c_specs = [
                        ('invoice_date', 2, 0, 'text', invoice.date_invoice),
                        ('invoice_nro', 2, 0, 'text', invoice.supplier_invoice_number),
                        ('invoice_moneda', 2, 0, 'text', invoice.currency_id.name),
                        ('invoice_amount', 3, 0, 'text', cesion_invoice and cesion_invoice.monto_cedido_embargado or False),
                    ]
                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cell_style_left)

                c_specs = [
                    ('espacio_1', 4, 0, 'text', None),
                    ('total_monto_cedido', 3, 0, 'text', _('Monto total cedido y pago:')),
                    ('total_monto_cedido_value', 2, 0, 'text', monto_total),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cell_style_left)

                if cesion.cession_type == 'amout_cession':
                    c_specs = [
                        ('espacio_2', 4, 0, 'text', None),
                        ('total_saldo_ceder', 3, 0, 'text', _('Saldo a ceder:')),
                        ('total_saldo_ceder_value', 2, 0, 'text', total_amount - monto_total),
                    ]
                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cell_style_left)

                else:

                    row_pos += 1
                    c_specs = [
                        ('espacio_3', 4, 0, 'text', None,None,cell_style_left),
                        ('moneda', 2, 0, 'text', _('Moneda'),None,cabezal_cell_style_lef),
                        ('monto_ajustado', 3, 0, 'text', _('Saldo a ceder'),None,cabezal_cell_style_lef),
                    ]

                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data)#row_style=cabezal_cell_style_lef

                    monedas = _p['monedas'](contrato_id)
                    for moneda in monedas:
                        saldo_ceder = _p['calcular_saldo_ceder'](moneda, invoices, cesion)
                        c_specs = [
                            ('espacio_4', 4, 0, 'text', None),
                            ('moneda', 2, 0, 'text', moneda.moneda),
                            ('monto_ajustado', 3, 0, 'text', moneda.monto_ajustado - saldo_ceder),
                        ]
                        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                        row_pos = self.xls_write_row(
                            ws, row_pos, row_data, row_style=cell_style_left)

                row_pos += 2

                # Title
                cell_style = xlwt.easyxf(_xs['xls_title'] + _xs['left'])
                c_specs = [
                    ('report_name', 4, 2, 'text', _('Facturas ingresadas')),
                ]
                row_data = self.xls_row_template(c_specs, ['report_name'])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cell_style)

                c_specs = [
                    ('invoice_date', 2, 0, 'text', _('Fecha factura')),
                    ('invoice_nro', 2, 0, 'text', _('Nro. factura')),
                    ('invoice_moneda', 2, 0, 'text', _('Moneda factura')),
                    ('invoice_amount', 3, 0, 'text', _('Monto cedido en factura')),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cabezal_cell_style_lef)

                invoices = _p['other_invoice'](contrato_id, cesion)
                other_monto_total = 0
                for invoice in invoices:
                    cesion_invoice = _p['cesion_invoice'](invoice, cesion)
                    if cesion_invoice:
                        other_monto_total += cesion_invoice.monto_cedido_embargado
                    c_specs = [
                        ('invoice_date', 2, 0, 'text', invoice.date_invoice),
                        ('invoice_nro', 2, 0, 'text', invoice.supplier_invoice_number),
                        ('invoice_moneda', 2, 0, 'text', invoice.currency_id.name),
                        ('invoice_amount', 3, 0, 'text', cesion_invoice and cesion_invoice.monto_cedido_embargado or False),
                    ]
                    row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                    row_pos = self.xls_write_row(
                        ws, row_pos, row_data, row_style=cell_style_left)

                c_specs = [
                    ('espacio_5', 4, 0, 'text', None),
                    ('total_monto_cedido', 3, 0, 'text', _('Monto total ingresado en facturas:')),
                    ('total_monto_cedido_value', 2, 0, 'text', other_monto_total),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cell_style_left)

                row_pos += 2




contract_account_cession_xls('report.contract.account.cession.xls', 'grp.contrato.proveedores',
                    parser=contract_account_cession_xls_parser)
