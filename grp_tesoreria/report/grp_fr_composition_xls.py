# -*- coding: utf-8 -*-
# © 2017 Quanam (ATEL SA., Uruguay)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

# try:
from openerp.addons.report_xls.report_xls import report_xls
from openerp import fields, _, api

from openerp.report import report_sxw
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
import xlwt
import math


class GrpFRCompositionXls(report_xls):
    def __init__(self, name, table, rml=False, parser=False, header=True,
                 store=False):
        super(GrpFRCompositionXls, self).__init__(
            name, table, rml, parser, header, store)

        _xs = self.xls_styles
        self.title_center_style = xlwt.easyxf(_xs['xls_title'] + _xs['center'] + _xs['underline'])
        self.bold_left_style = xlwt.easyxf(_xs['left'] + _xs['bold'])
        self.bold_right_style = xlwt.easyxf(_xs['right'] + _xs['bold'])
        self.normal_date_style = xlwt.easyxf(_xs['left'], num_format_str=report_xls.date_format)
        self.normal_number_style = xlwt.easyxf(_xs['right'], num_format_str=report_xls.decimal_format)
        self.bold_number_style = xlwt.easyxf(_xs['right'] + _xs['bold'], num_format_str=report_xls.decimal_format)

        self.summary_number_style = xlwt.easyxf(_xs['right'] + _xs['bold'] + _xs['fill_grey'],
                                                num_format_str=report_xls.decimal_format)
        self.summary_style = xlwt.easyxf(_xs['right'] + _xs['bold'] + _xs['fill_grey'])

        self.subtitle_style = xlwt.easyxf(_xs['left'] + _xs['bold'] + _xs['fill_grey'])
        self.subtitle_center_style = xlwt.easyxf(_xs['center'] + _xs['bold'] + _xs['fill_blue'])

    def global_initializations(self, wb, _p, xlwt, _xs, objects, data):
        return True

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        env = api.Environment(self.cr, _p['user'].id, {})
        objects.ensure_one()
        wizard = objects[0]
        report_name = "Composición de Fondo Rotatorio"
        ws = wb.add_sheet(report_name)
        ws.panes_frozen = True
        ws.remove_splits = True
        ws.portrait = 1  # Landscape
        ws.fit_width_to_pages = 1
        ws.fit_num_pages = 1
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

        # summary = {}
        row_pos = self._header_section(wizard, ws, _p, row_pos, _xs)
        row_pos += 3

        operating_unit_ids = env['operating.unit']
        combinations = []
        if wizard.operating_unit_id:
            combinations.append({'operating_unit':wizard.operating_unit_id.id,
                                 'operating_unit_name': wizard.operating_unit_id.name_get()[0][1],
                                 'fondo_rotatorio_siif':wizard.fr_siif_id.id,
                                 'fondo_rotatorio_name': wizard.fr_siif_id and wizard.fr_siif_id.name_get()[0][1] or ''})
        else:
            operating_unit_ids += env['operating.unit'].search([])
            for operating_unit_id in operating_unit_ids:
                fr_siif_id = env['fondo.rotatorio.siif'].search([('fiscal_year', '=', wizard.fiscal_year_id.id),
                                                    ('inciso', '=', wizard.inciso_id.id),
                                                    ('ue.ue', '=', operating_unit_id.code)], limit=1)
                combinations.append({'operating_unit': operating_unit_id.id,
                                     'operating_unit_name':operating_unit_id.name_get()[0][1],
                                     'fondo_rotatorio_siif': fr_siif_id.id,
                                     'fondo_rotatorio_name': fr_siif_id and fr_siif_id.name_get()[0][1] or ''})


        for combination in [a for a in combinations if a['operating_unit'] and a['fondo_rotatorio_siif']]:
            row_pos += 2
            c_specs = [
                ('report_name', 7, 2, 'text', _(u'UE: %s, Número de FR: %s' % (combination['operating_unit_name'], combination['fondo_rotatorio_name']))),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.title_center_style)

            row_pos = self._availability_section(wizard, ws, _p, row_pos, _xs, combination) + 1

            row_pos = self._repositions_section(wizard, ws, _p, row_pos, _xs, combination) + 1

        self.global_initializations(wb, _p, xlwt, _xs, objects, data)

    def _format_time(self, time):
        hour = str(int(math.floor(time)))
        if len(hour) == 1:
            hour = '0' + hour
        minuts = str(int(round((time % 1) * 60)))
        if len(minuts) == 1:
            minuts = '0' + minuts
        return '%s:%s' % (hour, minuts)

    def _header_section(self, wizard, ws, _p, row_pos, _xs):
        c_specs = [
            ('report_name', 7, 2, 'text', _(u'COMPOSICIÓN DE FONDO ROTATORIO')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.title_center_style)

        row_pos += 3

        c_specs = [
            ('date', 1, 2, 'text', _(u'Fecha')),
            ('inciso', 2, 2, 'text', _(u'Inciso')),
            ('ou', 2, 2, 'text', _(u'Unidad Ejecutora')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.title_center_style)

        c_specs = [
            ('date', 1, 2, 'date', fields.Date.from_string(wizard.date), None, self.normal_date_style),
            ('inciso', 2, 2, 'text', wizard.inciso_id and wizard.inciso_id.name_get()[0][1] or ''),
            ('ou', 2, 2, 'text', wizard.operating_unit_id and wizard.operating_unit_id.name_get()[0][1] or ''),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data)

        return row_pos

    # DISPONIBILIDADES
    def _availability_section(self, wizard, ws, _p, row_pos, _xs, _combination):
        c_specs = [
            ('report_name', 7, 2, 'text', _(u'Disponibilidades')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.subtitle_center_style)

        row_pos += 1

        row_pos = self._cashbox_section(wizard, ws, _p, row_pos, _xs, _combination)
        row_pos += 1
        row_pos = self._bank_statement_section(wizard, ws, _p, row_pos, _xs, _combination)
        return row_pos

    def get_bank_statement(self, user, _operating_unit, _fondo_rotatorio_siif):
        env = api.Environment(self.cr, user, {})
        journal_obj = env['account.journal']
        bank_statement_obj = env['account.bank.statement']
        args = [('operating_unit_id', '=', _operating_unit),
                ('fondo_rotatorio_siif', '=', _fondo_rotatorio_siif)]
        dict_byfr = {}
        for journal_id in journal_obj.search(args):
            bank_statement_id = bank_statement_obj.search([('journal_id', '=', journal_id.id), ('state', '!=', 'draft')],
                                                order='date DESC', limit=1)
            if bank_statement_id:
                dict_byfr.setdefault(bank_statement_id.journal_id.fondo_rotatorio_siif,{'data':[]})
                dict_byfr[bank_statement_id.journal_id.fondo_rotatorio_siif]['data'].append({'journal_id':journal_id, 'bank_statement_id':bank_statement_id})
        return dict_byfr

    def get_cashbox(self, user, _operating_unit, _fondo_rotatorio_siif):
        env = api.Environment(self.cr, user, {})
        cashbox_obj = env['grp.caja']
        cajachica_obj = env['grp.caja.chica.tesoreria']
        args = [('caja_chica_t','=',True),('journal_id.operating_unit_id','=',_operating_unit),('journal_id.fondo_rotatorio_siif','=',_fondo_rotatorio_siif)]
        cashbox_ids = cashbox_obj.search(args)

        dict_byfr = {}
        for cashbox_id in cashbox_ids:
            cajachica_id = cajachica_obj.search([('box_id','=',cashbox_id.id),('state','!=','draft')], order='date DESC', limit=1)
            if cajachica_id:
                dict_byfr.setdefault(cashbox_id.journal_id.fondo_rotatorio_siif,{'data':[]})
                dict_byfr[cashbox_id.journal_id.fondo_rotatorio_siif]['data'].append({'cashbox_id':cashbox_id, 'cajachica_id':cajachica_id})
        return dict_byfr


    def _cashbox_section(self, wizard, ws, _p, row_pos, _xs,_combination):
        caja_state = {'draft': u'Borrador', 'open': u'Abierto/a', 'end': u'Cerrado', 'check': u'Revisado'}
        c_specs = [
            ('report_name', 7, 2, 'text', _('Saldo de cuentas de caja de efectivo')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.subtitle_style)

        items = self.get_cashbox(_p['user'].id, _combination['operating_unit'],_combination['fondo_rotatorio_siif'])

        for key, data in items.items():
            c_specs = [
                ('box', 2, 2, 'text', _(u'Caja')),
                ('cashbox_nro', 2, 2, 'text', _(u'Caja No.')),
                ('state', 1, 2, 'text', _(u'Estado')),
                ('total', 1, 2, 'text', _(u'Total')),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)


            for cashbox_item in data['data']:
                if cashbox_item['cajachica_id']:
                    _total = cashbox_item['cajachica_id'].state == 'open' and cashbox_item['cajachica_id'].balance_end or cashbox_item['cajachica_id'].balance_end_real
                else:
                    _total = 0
                c_specs = [
                    ('box', 2, 2, 'text', cashbox_item['cashbox_id'].name_get()[0][1]),
                    ('cashbox_nro', 2, 2, 'text', cashbox_item['cajachica_id'] and cashbox_item['cajachica_id'].name),
                    ('state', 1, 2, 'text', cashbox_item['cajachica_id'] and caja_state.get(cashbox_item['cajachica_id'].state)),
                    ('total', 1, 2, 'number', _total, None, self.normal_number_style),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(ws, row_pos, row_data)

            row_pos += 1

        return row_pos

    def _bank_statement_section(self, wizard, ws, _p, row_pos, _xs,_combination):
        caja_state = {'draft': u'Borrador', 'open': u'Abierto/a', 'end': u'Cerrado', 'check': u'Revisado'}
        c_specs = [
            ('report_name', 7, 2, 'text', _('Saldo de cuentas de caja chica')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.subtitle_style)

        items = self.get_bank_statement(_p['user'].id, _combination['operating_unit'],_combination['fondo_rotatorio_siif'])

        for key, data in items.items():
            c_specs = [
                ('journal', 2, 2, 'text', _(u'Diario')),
                ('bs_nro', 2, 2, 'text', _(u'Registro de caja.')),
                ('state', 1, 2, 'text', _(u'Estado')),
                ('total', 1, 2, 'text', _(u'Total')),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)


            for cashbox_item in data['data']:
                if cashbox_item['bank_statement_id']:
                    _total = cashbox_item['bank_statement_id'].state == 'open' and cashbox_item['bank_statement_id'].balance_end or cashbox_item['bank_statement_id'].balance_end_real
                else:
                    _total = 0
                c_specs = [
                    ('journal', 2, 2, 'text', cashbox_item['journal_id'].name_get()[0][1]),
                    ('bs_nro', 2, 2, 'text', cashbox_item['bank_statement_id'] and cashbox_item['bank_statement_id'].name),
                    ('state', 1, 2, 'text', cashbox_item['bank_statement_id'] and caja_state.get(cashbox_item['bank_statement_id'].state)),
                    ('total', 1, 2, 'number', _total, None, self.normal_number_style),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(ws, row_pos, row_data)

            row_pos += 1

        return row_pos

    # REPOSICIONES
    def _repositions_section(self, wizard, ws, _p, row_pos, _xs, _combination):
        c_specs = [
            ('report_name', 7, 2, 'text', _(u'Reposiciones')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.subtitle_center_style)

        row_pos += 1

        row_pos = self._voucher_reposition_unincluded_section(wizard, ws, _p, row_pos, _xs, _combination)
        row_pos = self._3en1_nosiif_section(wizard, ws, _p, row_pos, _xs, _combination)
        row_pos = self._3en1_tgn_section(wizard, ws, _p, row_pos, _xs, _combination)
        return row_pos

    def get_voucher_reposition_unincluded(self, user, _operating_unit, _fondo_rotatorio_siif):
        env = api.Environment(self.cr, user, {})
        agrupador_fr_obj = env['grp.agrupar.fondo.rotarios']

        agrupador_fr_ids = agrupador_fr_obj.search([('operating_unit_id', '=', _operating_unit),
                ('journal_id.fondo_rotatorio_siif', '=', _fondo_rotatorio_siif)], order='tipo_documento')

        agrupador_fr_byfr = {}
        for agrupador_fr_id in agrupador_fr_ids:
            agrupador_fr_byfr.setdefault(agrupador_fr_id.tipo_documento,[])
            agrupador_fr_byfr[agrupador_fr_id.tipo_documento].append(agrupador_fr_id)
        return agrupador_fr_byfr

    def _voucher_reposition_unincluded_section(self, wizard, ws, _p, row_pos, _xs, _combination):
        voucher_reposition_type = {'account_invoice_fr': u'Facturas de fondo rotatorio',
                                   'account_invoice_refund_fr': u'Nota de Crédito fondo rotatorio',
                                   'hr_expense_anticipo': u'Rendición de anticipo',
                                   'hr_expense': u'Rendición de viático',
                                   'hr_expense_v': u'Vales',
                                   'bank_statement': u'Líneas de Registros de caja',
                                   'caja_chica': u'Líneas de Caja efectivo',
                                   'hr_expense_a': u'Abonos'}
        c_specs = [
            ('report_name', 7, 2, 'text', _('Comprobantes no incluidos en reposición')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.subtitle_style)

        data = self.get_voucher_reposition_unincluded(_p['user'].id, _combination['operating_unit'],
                                 _combination['fondo_rotatorio_siif'])


        for tipo_documento, tipo_documento_data in data.items():
            c_specs = [
                ('title', 2, 2, 'text', _(u'Tipo de documento')),
                ('doct_type', 2, 2, 'text', voucher_reposition_type.get(tipo_documento)),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

            c_specs = [
                ('partner', 3, 2, 'text', _(u'Proveedor')),
                ('date', 1, 2, 'text', _(u'Fecha')),
                ('nro_doc', 1, 2, 'text', _(u'N° documento')),
                ('total', 1, 2, 'text', _(u'Total')),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

            row_start = row_pos
            for data in tipo_documento_data:
                c_specs = [
                    ('partner', 3, 2, 'text', data.proveedor),
                    ('date', 1, 2, 'text', data.fecha_factura),
                    ('nro_doc', 1, 2, 'text', data.n_documento),
                    ('total', 1, 2, 'number', data.total, None, self.normal_number_style),
                ]
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(ws, row_pos, row_data)

            stotal_summary = 'SUM(' + rowcol_to_cell(row_start, 5) + ':' + rowcol_to_cell(row_pos - 1, 5) + ')'
            c_specs = [
                ('partner', 3, 2, 'text', ''),
                ('date', 1, 2, 'text', ''),
                ('nro_doc', 1, 2, 'text', ''),
                ('total', 1, 2, 'number', None, stotal_summary, self.bold_number_style),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)

        return row_pos


    # 3 en 1 no obligados en SIIF
    def get_3en1(self, user, _operating_unit, _fondo_rotatorio_siif, _states):
        env = api.Environment(self.cr, user, {})
        fr_obj = env['grp.fondo.rotatorio']

        return fr_obj.search([('operating_unit_id', '=', _operating_unit),
                              ('siif_nro_fondo_rot','=',_fondo_rotatorio_siif),
                              ('state','in', _states)])


    def _3en1_nosiif_section(self, wizard, ws, _p, row_pos, _xs, _combination):
        _3en1_states_dict = {'draft': u'Borrador',
                           'confirmado': u'Confirmado',
                           'obligado': u'Obligado',
                           'intervenido': u'Intervenido',
                           'priorizado': u'Priorizado',
                           'anulado_siif': u'Anulado SIIF',
                           'cancelado': u'Cancelado',
                           'pagado': u'Pagado'}


        c_specs = [
            ('report_name', 7, 2, 'text', _('3 en 1 no obligados en SIIF')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.subtitle_style)

        c_specs = [
            ('3en1', 2, 2, 'text', _('3en1')),
            ('amount', 1, 2, 'text', _('Importe')),
            ('amount2', 1, 2, 'text', _('Importe a cobrar')),
            ('state', 1, 2, 'text', _('Estado')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

        data = self.get_3en1(_p['user'].id, _combination['operating_unit'],
                                 _combination['fondo_rotatorio_siif'], ['draft','confirmado','anulado_siif'])

        for item in data:
            c_specs = [
                ('3en1', 3, 2, 'text', item.name),
                ('amount', 1, 2, 'number', item.total_reponer, None, self.normal_number_style),
                ('amount2', 1, 2, 'number', item.liquido_pagable, None, self.normal_number_style),
                ('state', 1, 2, 'text', _3en1_states_dict.get(item.state)),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)
        return row_pos


    def _3en1_tgn_section(self, wizard, ws, _p, row_pos, _xs, _combination):
        _3en1_states_dict = {'draft': u'Borrador',
                           'confirmado': u'Confirmado',
                           'obligado': u'Obligado',
                           'intervenido': u'Intervenido',
                           'priorizado': u'Priorizado',
                           'anulado_siif': u'Anulado SIIF',
                           'cancelado': u'Cancelado',
                           'pagado': u'Pagado'}


        c_specs = [
            ('report_name', 7, 2, 'text', _(u'Reposiciones no pagas por TGN')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.subtitle_style)

        c_specs = [
            ('3en1', 2, 2, 'text', _(u'3en1')),
            ('afectation', 1, 2, 'text', _(u'Afectación')),
            ('compromise', 1, 2, 'text', _(u'Compromiso')),
            ('obligation', 1, 2, 'text', _(u'Obligación')),
            ('amount', 1, 2, 'text', _(u'Importe')),
            ('amount2', 1, 2, 'text', _(u'Importe a cobrar')),
            ('state', 1, 2, 'text', _(u'Estado')),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(ws, row_pos, row_data, row_style=self.bold_left_style)

        data = self.get_3en1(_p['user'].id, _combination['operating_unit'],
                                 _combination['fondo_rotatorio_siif'], ['obligado','intervenido','priorizado'])

        for item in data:
            c_specs = [
                ('3en1', 2, 2, 'text', item.name),
                ('afectation', 1, 2, 'number', item.nro_afectacion, None, self.normal_number_style),
                ('compromise', 1, 2, 'number', item.nro_compromiso, None, self.normal_number_style),
                ('obligation', 1, 2, 'number', item.nro_obligacion, None, self.normal_number_style),
                ('amount', 1, 2, 'number', item.total_reponer, None, self.normal_number_style),
                ('amount2', 1, 2, 'number', item.liquido_pagable, None, self.normal_number_style),
                ('state', 1, 2, 'text', _3en1_states_dict.get(item.state)),
            ]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(ws, row_pos, row_data)
        return row_pos


GrpFRCompositionXls(
    'report.grp_tesoreria.report_grp_fr_composition_xls',
    'grp.fr.composition.wizard', parser=report_sxw.rml_parse
)
