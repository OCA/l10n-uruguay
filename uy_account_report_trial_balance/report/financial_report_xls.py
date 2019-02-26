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

from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.uy_account_report_trial_balance.report.trial_balance import TrialBalanceWebkitExt
from openerp.tools.translate import _
from utils import compute_amounts_in_currency
from openerp.addons.account_financial_report_webkit.report.common_reports \
    import CommonReportHeaderWebkit
from openerp import pooler


class financial_report_xls(report_xls):
    column_sizes = [12, 40, 17, 17, 17, 17, 17, 17, 17, 17, 17]

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        context = {'lang': (_p.get('lang') or 'en_US')}

        ws = wb.add_sheet(_("Financial report"))
        ws.panes_frozen = True
        ws.remove_splits = True
        ws.portrait = 0  # Landscape
        ws.fit_width_to_pages = 1
        row_pos = 0

        # set print header/footer
        ws.header_str = self.xls_headers['standard']
        ws.footer_str = self.xls_footers['standard']

        # Title
        cell_style = xlwt.easyxf(_xs['xls_title'])
        report_name = ' - '.join([data['form']['account_report_id'][1].upper(),
                                 _p.company.partner_id.name,
                                 _p.company.currency_id.name])
        c_specs = [
            ('report_name', 1, 0, 'text', report_name),
        ]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=cell_style)

        # write empty row to define column sizes
        c_sizes = self.column_sizes
        c_specs = [('empty%s' % i, 1, c_sizes[i], 'text', None)
                   for i in range(0, len(c_sizes))]
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, set_column_size=True)

        # Alternative Currency
        base_currency_id = _p.company.currency_id.id
        currency_obj = self.pool.get('res.currency')
        alt_curr_ids = currency_obj.search(self.cr, self.uid, [('alt_currency','=',True)])
        alt_curr_id = alt_curr_ids and alt_curr_ids[0] or False
        display_curr_columns = data.get('form',{}).get('display_curr_columns', False) and \
                                (alt_curr_id and base_currency_id != alt_curr_id or False) or False
        ## Alternative currency rate options
        context.update({
            'curr_rate_option': data.get('form',{}).get('curr_rate_option', False),
            'curr_rate_date': data.get('form',{}).get('curr_rate_date', False),
            'curr_rate': data.get('form',{}).get('curr_rate', False),
        })

        # Header Table
        cell_format = _xs['bold'] + _xs['fill_blue'] + _xs['borders_all']
        cell_style = xlwt.easyxf(cell_format)
        cell_style_center = xlwt.easyxf(cell_format + _xs['center'])
        c_specs = [
            ('fy', 1, 0, 'text', _('Fiscal Year')),
            ('df', 1, 0, 'text', _p.filter_form(data) ==
             'filter_date' and _('Dates Filter') or _('Periods Filter')),
            ('tm', 2, 0, 'text', _('Target Moves'), None, cell_style_center),
            ('coa', 1, 0, 'text', _('Chart of Account'),
             None, cell_style_center),
        ]
        if display_curr_columns:
            c_specs += [('altc', 1, 0, 'text', _('Alt. Currency'))]
            c_specs += [('altcro', 2, 0, 'text', _('Alt. Curr. Rate Option'))]

        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=cell_style)

        cell_format = _xs['borders_all'] + _xs['wrap'] + _xs['top']
        cell_style = xlwt.easyxf(cell_format)
        cell_style_center = xlwt.easyxf(cell_format + _xs['center'])
        c_specs = [('fy', 1, 0, 'text', _p.fiscalyear.name if _p.fiscalyear else '-')]
        df = _('From') + ': '
        if _p.filter_form(data) == 'filter_date':
            df += _p.start_date if _p.start_date else u''
        else:
            df += _p.start_period.name if _p.start_period else u''
        df += ' ' + _('\nTo') + ': '
        if _p.filter_form(data) == 'filter_date':
            df += _p.stop_date if _p.stop_date else u''
        else:
            df += _p.stop_period.name if _p.stop_period else u''
        c_specs += [
            ('df', 1, 0, 'text', df),
            ('tm', 2, 0, 'text', _p.display_target_move(
                data), None, cell_style_center),
            ('coa', 1, 0, 'text', _p.chart_account.name,
             None, cell_style_center),
        ]
        if display_curr_columns:
            c_specs += [('altc', 1, 0, 'text', currency_obj.read(self.cr, self.uid, alt_curr_id, ['name'])['name'] )]
            rate_option = _("Transaction Date")
            if data.get('form',{}).get('curr_rate_option', False)=='set_date':
                rate_option = _("Custom Date: ") + data.get('form',{}).get('curr_rate_date', '')
            elif data.get('form',{}).get('curr_rate_option', False)=='set_curr_rate':
                rate_option = _("Currency Rate: ") + str(data.get('form',{}).get('curr_rate', 0.0))
            c_specs += [('altcro', 2, 0, 'text', rate_option )]

        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=cell_style)

        # comparison header table
        if _p.comparison_mode in ('single', 'multiple'):
            row_pos += 1
            cell_format_ct = _xs['bold'] + \
                _xs['fill_blue'] + _xs['borders_all']
            cell_style_ct = xlwt.easyxf(cell_format_ct)
            c_specs = [('ct', 8, 0, 'text', _('Comparisons'))]
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=cell_style_ct)
            cell_style_center = xlwt.easyxf(cell_format)
            for index, params in enumerate(_p.comp_params):
                c_specs = [
                    ('c', 3, 0, 'text', _('Comparison') + str(index + 1) +
                     ' (C' + str(index + 1) + ')')]
                if params['comparison_filter'] == 'filter_date':
                    c_specs += [('f', 3, 0, 'text', _('Dates Filter') + ': ' +
                                 _p.formatLang(
                                     params['start'], date=True) + ' - ' +
                                 _p.formatLang(params['stop'], date=True))]
                elif params['comparison_filter'] == 'filter_period':
                    c_specs += [('f', 3, 0, 'text', _('Periods Filter') +
                                 ': ' + params['start'].name + ' - ' +
                                 params['stop'].name)]
                else:
                    c_specs += [('f', 3, 0, 'text', _('Fiscal Year') +
                                 ': ' + params['fiscalyear'].name)]
                row_data = self.xls_row_template(
                    c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cell_style_center)
        ##
        row_pos += 1

        # Column Header Row
        cell_format = _xs['bold'] + _xs['fill_blue'] + \
            _xs['borders_all'] + _xs['wrap'] + _xs['top']
        cell_style = xlwt.easyxf(cell_format)
        cell_style_right = xlwt.easyxf(cell_format + _xs['right'])
        cell_style_center = xlwt.easyxf(cell_format + _xs['center'])

        c_specs = [
            ('code', 1, 0, 'text', _('Code')),
            ('account', 1, 0, 'text', _('Name')),
        ]
        if _p.comparison_mode == 'no_comparison':
            c_specs += [
                ('debit', 1, 0, 'text', _('Debit'), None, cell_style_right),
                ('credit', 1, 0, 'text', _('Credit'), None, cell_style_right),
            ]
        c_specs += [('balance', 1, 0, 'text', _('Balance'), None, cell_style_right)]

        if display_curr_columns:
            if _p.comparison_mode == 'no_comparison':
                c_specs += [
                    ('curr_debit', 1, 0, 'text', _('Curr. Debit'), None, cell_style_right),
                    ('curr_credit', 1, 0, 'text', _('Curr. Credit'), None, cell_style_right),
                ]
            c_specs += [('curr_balance', 1, 0, 'text', _('Curr. Balance'), None, cell_style_right)]

        if _p.comparison_mode in ('single', 'multiple'):
            for index in range(_p.nb_comparison):
                if _p.comp_params[index]['comparison_filter'] == 'filter_year' \
                        and _p.comp_params[index].get('fiscalyear', False):
                    c_specs += [('balance_%s' % index, 1, 0, 'text',
                                 _('Balance %s') %
                                 _p.comp_params[index]['fiscalyear'].name,
                                 None, cell_style_right)]
                else:
                    c_specs += [('balance_%s' % index, 1, 0, 'text',
                                 _('Balance C%s') % (index + 1), None,
                                 cell_style_right)]
            if display_curr_columns:
                for index in range(_p.nb_comparison):
                    if _p.comp_params[index]['comparison_filter'] == 'filter_year' \
                            and _p.comp_params[index].get('fiscalyear', False):
                        c_specs += [('curr_balance_%s' % index, 1, 0, 'text', _('Curr. Balance %s') %
                                    _p.comp_params[index]['fiscalyear'].name, None, cell_style_right)]
                    else:
                        c_specs += [('curr_balance_%s' % index, 1, 0, 'text', _('Curr. Balance C%s') %
                                    (index + 1), None, cell_style_right)]

        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=cell_style)
        ws.set_horz_split_pos(row_pos)

        # cell styles for account data
        view_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        view_cell_style = xlwt.easyxf(view_cell_format)
        view_cell_style_center = xlwt.easyxf(view_cell_format + _xs['center'])
        view_cell_style_decimal = xlwt.easyxf(
            view_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)
        view_cell_style_pct = xlwt.easyxf(
            view_cell_format + _xs['center'], num_format_str='0')
        regular_cell_format = _xs['borders_all']
        regular_cell_style = xlwt.easyxf(regular_cell_format)
        regular_cell_style_center = xlwt.easyxf(
            regular_cell_format + _xs['center'])
        regular_cell_style_decimal = xlwt.easyxf(
            regular_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)
        regular_cell_style_pct = xlwt.easyxf(
            regular_cell_format + _xs['center'], num_format_str='0')

        if display_curr_columns:
            account_obj = self.pool.get('account.account')
            c_report = CommonReportHeaderWebkit()
            c_report.pool = pooler.get_pool(self.cr.dbname)
            c_report.cr = self.cr
            c_report.cursor = self.cr
            c_report.uid = self.uid

            main_filter = c_report._get_form_param('filter', data, default='filter_no')
            target_move = c_report._get_form_param('target_move', data, default='all')
            start_date = c_report._get_form_param('date_from', data)
            stop_date = c_report._get_form_param('date_to', data)
            start_period = c_report.get_start_period_br(data)
            stop_period = c_report.get_end_period_br(data)
            if main_filter == 'filter_no':
                fiscalyear = c_report.get_fiscalyear_br(data)
                start_period = c_report.get_first_fiscalyear_period(fiscalyear)
                stop_period = c_report.get_last_fiscalyear_period(fiscalyear)
            if main_filter == 'filter_date':
                start = start_date
                stop = stop_date
            else:
                start = start_period
                stop = stop_period

            curr_values_by_account = {}

        for a in self.get_lines(data):
            if a['level'] != 0:
                if not a.get('level') > 3:
                    cell_style = view_cell_style
                    cell_style_center = view_cell_style_center
                    cell_style_decimal = view_cell_style_decimal
                    cell_style_pct = view_cell_style_pct
                else:
                    cell_style = regular_cell_style
                    cell_style_center = regular_cell_style_center
                    cell_style_decimal = regular_cell_style_decimal
                    cell_style_pct = regular_cell_style_pct

                c_specs = [
                    ('code', 1, 0, 'text', a.get('code',u'')),
                    ('account', 1, 0, 'text', ("  " * (a['level'] - 1)) + a['name']),
                ]
                if _p.comparison_mode == 'no_comparison':
                    c_specs += [
                        ('debit', 1, 0, 'number', a.get('debit', 0.0),
                         None, cell_style_decimal),
                        ('credit', 1, 0, 'number', a.get('credit', 0.0),
                         None, cell_style_decimal),
                    ]
                c_specs += [('balance', 1, 0, 'number', a.get('balance', 0.0),
                             None, cell_style_decimal)]
                if display_curr_columns:
                    cumul_curr_balance = None
                    if _p.comparison_mode == 'no_comparison':
                        if a.get('type')=='report':
                            if a.get('account_ids', False):
                                cumul_curr_debit = 0.0
                                cumul_curr_credit = 0.0
                                analized_account_ids = []
                                for account_id in a.get('account_ids'):
                                    if account_id in analized_account_ids:
                                        continue
                                    curr_debit = 0.0
                                    curr_credit = 0.0
                                    lines = []
                                    children_and_consolidated = account_obj._get_children_and_consol(self.cr, self.uid, account_id)
                                    for acc_id in children_and_consolidated:
                                        analized_account_ids.append(acc_id)
                                        move_line_ids = c_report.get_move_lines_ids(
                                            acc_id, main_filter, start, stop, target_move)
                                        if move_line_ids:
                                            lines += c_report._get_move_line_datas(move_line_ids)
                                    for line in lines:
                                        curr_debit += (line.get('debit', 0.0) and line.get('currency_id', False)==alt_curr_id) and (line.get('amount_currency') < 0 and -line.get('amount_currency') or (line.get('amount_currency') or 0.0)) or \
                                                             compute_amounts_in_currency(self, self.cr, self.uid, line.get('debit', 0.0), base_currency_id, alt_curr_id, date=line.get('ldate', False), context=context)
                                        curr_credit += (line.get('credit', 0.0) and line.get('currency_id', False)==alt_curr_id) and (line.get('amount_currency') < 0 and -line.get('amount_currency') or (line.get('amount_currency') or 0.0)) or \
                                                              compute_amounts_in_currency(self, self.cr, self.uid, line.get('credit', 0.0), base_currency_id, alt_curr_id, date=line.get('ldate', False), context=context)

                                    curr_values_by_account[account_id] = { 'curr_debit': curr_debit, 'curr_credit': curr_credit }
                                    cumul_curr_debit += curr_debit
                                    cumul_curr_credit += curr_credit
                            else:
                                cumul_curr_debit = compute_amounts_in_currency(self, self.cr, self.uid, a.get('debit', 0.0), base_currency_id, alt_curr_id, context=context)
                                cumul_curr_credit = compute_amounts_in_currency(self, self.cr, self.uid, a.get('credit', 0.0), base_currency_id, alt_curr_id, context=context)

                        if a.get('type')=='account':
                            if a['account_id'] in curr_values_by_account:
                                cumul_curr_debit = curr_values_by_account.get(a['account_id']).get('curr_debit', 0.0)
                                cumul_curr_credit = curr_values_by_account.get(a['account_id']).get('curr_credit', 0.0)
                            else:
                                cumul_curr_debit = 0.0
                                cumul_curr_credit = 0.0
                                children_and_consolidated = account_obj._get_children_and_consol(self.cr, self.uid, a['account_id'])
                                lines = []
                                for acc_id in children_and_consolidated:
                                    move_line_ids = c_report.get_move_lines_ids(
                                        acc_id, main_filter, start, stop, target_move)
                                    if move_line_ids:
                                        lines += c_report._get_move_line_datas(move_line_ids)
                                for line in lines:
                                    cumul_curr_debit += (line.get('debit', 0.0) and line.get('currency_id', False)==alt_curr_id) and (line.get('amount_currency') < 0 and -line.get('amount_currency') or (line.get('amount_currency') or 0.0)) or \
                                                         compute_amounts_in_currency(self, self.cr, self.uid, line.get('debit', 0.0), base_currency_id, alt_curr_id, date=line.get('ldate', False), context=context)
                                    cumul_curr_credit += (line.get('credit', 0.0) and line.get('currency_id', False)==alt_curr_id) and (line.get('amount_currency') < 0 and -line.get('amount_currency') or (line.get('amount_currency') or 0.0)) or \
                                                          compute_amounts_in_currency(self, self.cr, self.uid, line.get('credit', 0.0), base_currency_id, alt_curr_id, date=line.get('ldate', False), context=context)

                        cumul_curr_balance = (cumul_curr_debit - cumul_curr_credit) * a.get('sign')
                        c_specs += [
                            ('curr_debit', 1, 0, 'number', cumul_curr_debit,
                             None, cell_style_decimal),
                            ('curr_credit', 1, 0, 'number', cumul_curr_credit,
                             None, cell_style_decimal),
                        ]
                    c_specs += [('curr_balance', 1, 0, 'number', cumul_curr_balance or \
                                compute_amounts_in_currency(self, self.cr, self.uid, a.get('balance', 0.0), base_currency_id, alt_curr_id, context=context),
                                 None, cell_style_decimal)]
                if _p.comparison_mode in ('single', 'multiple'):
                    _c = []
                    for index in range(_p.nb_comparison):
                        if 'comp%s_balance'%(index) in a and index not in _c:
                            c_specs += [('balance_%s' % index, 1, 0, 'number',
                                    a['comp%s_balance'%(index)] or 0.0, None, cell_style_decimal)]
                            _c.append(index)
                        elif 'comp%s_balance'%(index+1) in a and index+1 not in _c:
                            c_specs += [('balance_%s' % index, 1, 0, 'number',
                                    a['comp%s_balance'%(index+1)] or 0.0, None, cell_style_decimal)]
                            _c.append(index+1)
                        elif 'comp%s_balance'%(index+2) in a and index+2 not in _c:
                            c_specs += [('balance_%s' % index, 1, 0, 'number',
                                    a['comp%s_balance'%(index+2)] or 0.0, None, cell_style_decimal)]
                            _c.append(index+2)
                    if display_curr_columns:
                        _c = []
                        for index in range(_p.nb_comparison):
                            if 'comp%s_balance'%(index) in a and index not in _c:
                                c_specs += [('curr_balance_%s' % index, 1, 0, 'number',
                                            compute_amounts_in_currency(self, self.cr, self.uid, a['comp%s_balance'%(index)] or 0.0, base_currency_id, alt_curr_id, context=context),
                                            None, cell_style_decimal)]
                                _c.append(index)
                            elif 'comp%s_balance'%(index+1) in a and index+1 not in _c:
                                c_specs += [('curr_balance_%s' % index, 1, 0, 'number',
                                            compute_amounts_in_currency(self, self.cr, self.uid, a['comp%s_balance'%(index+1)] or 0.0, base_currency_id, alt_curr_id, context=context),
                                            None, cell_style_decimal)]
                                _c.append(index+1)
                            elif 'comp%s_balance'%(index+2) in a and index+2 not in _c:
                                c_specs += [('curr_balance_%s' % index, 1, 0, 'number',
                                            compute_amounts_in_currency(self, self.cr, self.uid, a['comp%s_balance'%(index+2)] or 0.0, base_currency_id, alt_curr_id, context=context),
                                            None, cell_style_decimal)]
                                _c.append(index+2)
                row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
                row_pos = self.xls_write_row(
                    ws, row_pos, row_data, row_style=cell_style)

    def get_lines(self, data):
        lines = []
        account_obj = self.pool.get('account.account')
        currency_obj = self.pool.get('res.currency')
        ids2 = self.pool.get('account.financial.report')._get_children_by_order(self.cr, self.uid, [data['form']['account_report_id'][0]], context=data['form']['used_context'])
        for report in self.pool.get('account.financial.report').browse(self.cr, self.uid, ids2, context=data['form']['used_context']):
            vals = {
                'name': report.name,
                'balance': report.balance * report.sign or 0.0,
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type =='sum' and 'view' or False, #used to underline the financial report balances
                'sign': report.sign,
                'account_ids': [],
                #'account_ids': [ a.id for a in report.child_account_ids ],
            }
            vals['debit'] = report.debit
            vals['credit'] = report.credit

            index = 0
            while index < data['form'].get('max_comparison', 0):
                if data['form']['comp%s_filter'%(index)] in ('filter_year','filter_date','filter_period'):
                    comparison_context = self._build_comparison_context(data, index)
                    vals['comp%s_balance'%(index)] = self.pool.get('account.financial.report').browse(self.cr, self.uid, report.id, context=comparison_context).balance * report.sign or 0.0
                index += 1
            lines.append(vals)

            account_ids = []
            if report.display_detail == 'no_detail':
                #the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue
            if report.type == 'accounts' and report.account_ids:
                account_ids = account_obj._get_children_and_consol(self.cr, self.uid, [x.id for x in report.account_ids])
            elif report.type == 'account_type' and report.account_type_ids:
                account_ids = account_obj.search(self.cr, self.uid, [('user_type','in', [x.id for x in report.account_type_ids])])

            if account_ids:
                for account in account_obj.browse(self.cr, self.uid, account_ids, context=data['form']['used_context']):
                    #if there are accounts to display, we add them to the lines with a level equals to their level in
                    #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
                    #financial reports for Assets, liabilities...)
                    if report.display_detail == 'detail_flat' and account.type == 'view':
                        continue
                    flag = False
                    vals = {
                        'code': account.code,
                        'name': account.name,
                        'balance':  account.balance != 0 and account.balance * report.sign or account.balance,
                        'type': 'account',
                        'level': report.display_detail == 'detail_with_hierarchy' and min(account.level + 1,6) or 6, #account.level + 1
                        'account_type': account.type,
                        'account_id': account.id,
                        'sign': report.sign,
                    }

                    vals['debit'] = account.debit
                    vals['credit'] = account.credit
                    if not currency_obj.is_zero(self.cr, self.uid, account.company_id.currency_id, vals['balance']):
                        flag = True

                    index = 0
                    while index < data['form'].get('max_comparison', 0):
                        if data['form']['comp%s_filter'%(index)] in ('filter_year','filter_date','filter_period'):
                            comparison_context = self._build_comparison_context(data, index)
                            vals['comp%s_balance'%(index)] = self.pool.get('account.financial.report').browse(self.cr, self.uid, report.id, context=comparison_context).balance * report.sign or 0.0
                            #if not currency_obj.is_zero(self.cr, self.uid, account.company_id.currency_id, vals['comp%s_balance'%(index)]):
                                #flag = True
                        index += 1

                    if flag:
                        # update account_ids of parent reports
                        lines.reverse()
                        report_level = 6
                        for line in lines:
                            if line['type'] == 'report' and line['level'] < report_level:
                                line['account_ids'].append(account.id)
                                report_level = line['level']
                        lines.reverse()
                        ###
                        lines.append(vals)
        return lines

    def _build_comparison_context(self, data, index, context=None):
        if context is None:
            context = {}
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        if data['form']['comp%s_filter'%(index)] == 'filter_year':
            result['fiscalyear'] = 'comp%s_fiscalyear_id'%(index) in data['form'] and data['form']['comp%s_fiscalyear_id'%(index)] or False
        elif data['form']['comp%s_filter'%(index)] == 'filter_date':
            result['date_from'] = data['form']['comp%s_date_from'%(index)]
            result['date_to'] = data['form']['comp%s_date_to'%(index)]
        elif data['form']['comp%s_filter'%(index)] == 'filter_period':
            result['period_from'] = data['form']['comp%s_period_from'%(index)]
            result['period_to'] = data['form']['comp%s_period_to'%(index)]
        return result

financial_report_xls('report.account.account_financial_report_xls',
                  'account.account',
                  parser=TrialBalanceWebkitExt)
