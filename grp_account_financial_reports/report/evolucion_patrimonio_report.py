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


from openerp import models, fields, api
from openerp.addons.report_xls.report_xls import report_xls
from openerp.report import report_sxw
import time
from xlwt import *

COLUMN_TYPES = {
    'capital': 'Capital',
    'comp': 'Aportes y Comprom. a Capital',
    'adjust': 'Ajustes al patrimonio',
    'reserve': 'Reservas',
    'result': 'Resultados acumulados',
    'int': u'Interés Minoritario'
}


class evolucion_patrimonio_conf(models.Model):
    _name = 'evolucion.patrimonio.conf'
    _order = 'sequence'

    @api.model
    def create(self, vals):
        if vals.get('type', '') == 'sum':
            vals['account_ids'] = False
        return super(evolucion_patrimonio_conf, self).create(vals)

    @api.multi
    def write(self, vals):
        if vals.get('type', '') == 'sum':
            vals['account_ids'] = [(5, 0, 0)]
        return super(evolucion_patrimonio_conf, self).write(vals)

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        if self.parent_id:
            self.section = self.parent_id.section

    # columns
    name = fields.Char(u'Rubro', size=50, required=True)
    section = fields.Selection([
        (1, 'SALDOS INICIALES'),
        # ('subtotal_si','SUBTOTAL (SI)'),
        (2, 'MODIFICACION AL SALDO INICIAL'),
        # ('saldos_iniciales_modif','SALDOS INICIALES MODIFICADOS'),
        (4, 'AUMENTO DEL APORTE DE PROPIETARIOS'),
        (5, 'DISTRIBUCION DE UTILIDADES'),
        (6, 'DISTRIB. DE UTIL. ANTICIPADAS'),
        (7, 'REEXPRESIONES CONTABLES'),
        (8, 'RESULTADO DEL EJERCICIO'),
        # ('subtotal','SUBTOTAL'),
        (10, 'SALDOS FINALES')
        # ('total_saldos_finales','TOTAL SALDOS FINALES')
    ], string=u'Sección', required=True)
    type = fields.Selection([
        ('sum', 'Vista'),
        ('accounts', 'Cuentas')
    ], 'Tipo', default="accounts", required=True)
    parent_id = fields.Many2one('evolucion.patrimonio.conf', 'Padre', domain=[('type', '=', 'sum')])
    sequence = fields.Integer('Sequence')
    sign = fields.Selection([(-1, 'Invertir signo del saldo'),
                             (1, 'Preservar signo del saldo')],
                            string='Signo en informes', default=1,
                            help=u'Para cuentas que tipicamente tienen más débito que crédito y que desea imprimir con importes negativos en sus informes, debería revertir el signo en el balance;p.e: cuenta de gasto. La misma aplica para cuentas que tipicamente tienen más crédito que débito y que desea imprimir con importes positivos en sus informes. p.e: cuenta de ingresos.')

    line_ids = fields.One2many('evolucion.patrimonio.conf.line', 'epp_id', string=u'Cuentas')


class evolucion_patrimonio_conf_line(models.Model):
    _name = 'evolucion.patrimonio.conf.line'

    epp_id = fields.Many2one('evolucion.patrimonio.conf', 'EPP', required=True)
    account_id = fields.Many2one('account.account', 'Cuenta', required=True, domain=[('type', '!=', 'view')],
                                 copy=False)
    headers = fields.Selection([
        ('capital', 'Capital'),
        ('comp', 'Aportes y Comprom. a Capital'),
        ('adjust', 'Ajustes al patrimonio'),
        ('reserve', 'Reservas'),
        ('result', 'Resultados acumulados'),
        ('int', u'Interés Minoritario')], string="Columnas", copy=False)
    amount_option = fields.Selection([
        ('initial_balance', 'Saldo contable al inicio del ejercicio'),
        ('balance', 'Movimientos'),
        ('close_balance', 'Saldo contable al cierre del ejercicio')
    ], string=u"Forma de cálculo de importe",
        default='initial_balance', required=True)


class report_evolucion_patrimonio(models.AbstractModel):
    _name = 'report.report_evolucion_patrimonio'

    # 1- Saldo Inicial
    @api.model
    def get_initial_amount(self, id, data, conf, data_record):
        if conf.type == 'sum':
            return True
        else:
            use_context = data['form']['used_context']
            use_context1 = dict(data['form']['used_context'])
            fiscalyear_id = data['form']['fiscalyear_id']
            fiscal_year = self.env['account.fiscalyear'].search([('id', '=', fiscalyear_id)])
            fiscal_year_prev = self.env['account.fiscalyear'].search([('date_start', '<', fiscal_year.date_start)],
                                                                     limit=1, order='date_start DESC')
            use_context1.update({
                'fiscalyear': fiscalyear_id,
                'periods': fiscal_year.period_ids.ids
            })
            # if fiscal_year_prev:
            #     fiscalyear_id = fiscal_year_prev.id
            use_context.update({
                'fiscalyear': fiscalyear_id
            })
            column_int = float(0)
            MoveLine = self.env['account.move.line']
            for key in COLUMN_TYPES.keys():
                _sum = 0
                for acc_line in conf.with_context(use_context).line_ids.filtered(lambda x: x.headers == key):
                    if acc_line.amount_option == 'initial_balance':
                        move_line_id = MoveLine.search([('account_id', '=', acc_line.account_id.id),
                                                        ('period_id.fiscalyear_id', '=', fiscalyear_id),
                                                        ('period_id.special', '=', True)], order='date ASC', limit=1)
                        _sum += move_line_id.debit - move_line_id.credit
                        # _sum += acc_line.with_context(use_context).account_id.initial_balance
                    elif acc_line.amount_option == 'balance':
                        _sum += acc_line.with_context(use_context1).account_id.balance
                    else:
                        move_line_id = MoveLine.search([('account_id', '=', acc_line.account_id.id),
                                                        ('period_id.fiscalyear_id', '=', fiscalyear_id),
                                                        ('period_id.special', '=', True)], order='date ASC', limit=1)
                        _sum += (move_line_id.debit - move_line_id.credit) + acc_line.with_context(
                            use_context1).account_id.balance
                _sum *= conf.sign
                data_record[key] = _sum
                column_int += _sum
            data_record['int'] = column_int

            return True

    # 2- MODIF. AL SALDO INICIAL
    @api.model
    def get_modif_amount(self, id, data, conf, data_record):
        if conf.type == 'sum':
            return True
        else:
            use_context = data['form']['used_context']
            use_context1 = dict(data['form']['used_context'])
            fiscalyear_id = data['form']['fiscalyear_id']
            use_context.update({
                # 'all_fiscalyear': True,
                'fiscalyear': fiscalyear_id
            })
            fiscal_year = self.env['account.fiscalyear'].search([('id', '=', fiscalyear_id)])
            use_context1.update({
                'fiscalyear': fiscalyear_id,
                'periods': fiscal_year.period_ids.ids
            })
            # fiscal_year_prev = self.env['account.fiscalyear'].search([('date_start', '<', fiscal_year.date_start)],
            #                                                          limit=1, order='date_start DESC')
            # if fiscal_year_prev:
            #     fiscalyear_id = fiscal_year_prev.id
            use_context.update({
                'fiscalyear': fiscalyear_id
            })

            column_int = float(0)
            MoveLine = self.env['account.move.line']
            for key in COLUMN_TYPES.keys():
                _sum = 0
                for acc_line in conf.with_context(use_context).line_ids.filtered(lambda x: x.headers == key):
                    if acc_line.amount_option == 'initial_balance':
                        move_line_id = MoveLine.search([('account_id', '=', acc_line.account_id.id),
                                                        ('period_id.fiscalyear_id', '=', fiscalyear_id),
                                                        ('period_id.special', '=', True)], order='date ASC', limit=1)
                        _sum += move_line_id.debit - move_line_id.credit
                    elif acc_line.amount_option == 'balance':
                        _sum += acc_line.with_context(use_context1).account_id.balance
                    else:
                        move_line_id = MoveLine.search([('account_id', '=', acc_line.account_id.id),
                                                        ('period_id.fiscalyear_id', '=', fiscalyear_id),
                                                        ('period_id.special', '=', True)], order='date ASC', limit=1)
                        _sum += (move_line_id.debit - move_line_id.credit) + acc_line.with_context(
                            use_context1).account_id.balance
                _sum *= conf.sign
                data_record[key] = _sum
                column_int += _sum
            data_record['int'] = column_int
            return True

    # 4-AUMENTO DEL APORTE DE PROPIETARIO
    @api.model
    def get_increase_owner_amount(self, id, data, conf, data_record):
        # Es el mismo procedimiento, se pone en otra función por si hay cambios futuros
        return self.get_modif_amount(id, data, conf, data_record)

    # 5-DISTRIBUCION DE UTILIDADES
    @api.model
    def get_distribution_utilities(self, id, data, conf, data_record):
        # Es el mismo procedimiento, se pone en otra función por si hay cambios futuros
        return self.get_modif_amount(id, data, conf, data_record)

    # 6-DISTRIB. DE UTIL. ANTICIPADAS
    @api.model
    def get_distribution_ant(self, id, data, conf, data_record):
        # Es el mismo procedimiento, se pone en otra función por si hay cambios futuros
        return self.get_modif_amount(id, data, conf, data_record)

    # 7-REEXPRESIONES CONTABLES
    @api.model
    def get_account_exp(self, id, data, conf, data_record):
        # Es el mismo procedimiento, se pone en otra función por si hay cambios futuros
        return self.get_modif_amount(id, data, conf, data_record)

    # 8-RESULTADOS DEL EJERCICIO
    @api.model
    def get_year_results(self, id, data, conf, data_record):
        # Es el mismo procedimiento, se pone en otra función por si hay cambios futuros
        return self.get_modif_amount(id, data, conf, data_record)

    # 10-SALDOS FINALES
    @api.model
    def get_final_amount(self, id, data, conf, data_record):
        # Es el mismo procedimiento, se pone en otra función por si hay cambios futuros
        return self.get_modif_amount(id, data, conf, data_record)

    @api.model
    def clean_zero(self, values):
        for t in values:
            if isinstance(t, (list,)):
                for index in range(len(t)):
                    if isinstance(t[index], (dict,)):
                        for key, value in t[index].items():
                            if t[index][key] == 0:
                                t[index][key] = ''
            if isinstance(t, (dict,)):
                for key, value in t.items():
                    if t[key] == 0:
                        t[key] = ''
        return values

    @api.model
    def get_lines(self, data, show_zero=False):
        self._cr.execute("""
            SELECT
                c.id,
                c.section,
                c.type,
                c.parent_id,
                c1.sequence AS parent_sequence,
                c1.name AS parent_name,
                c.id AS child_id,
                c.sequence AS child_sequence,
                c.name AS child_name,
                c.sign AS sign
            FROM evolucion_patrimonio_conf c
            LEFT JOIN evolucion_patrimonio_conf c1 ON (c.parent_id = c1.id)
            GROUP BY
                c.id,
                c.section,
                c.type,
                c.parent_id,
                c1.sequence,
                c1.name,
                c.id,
                c.sequence,
                c.name,
                c.sign
            HAVING
            c.parent_id IS NOT NULL OR c.type = 'accounts'
            ORDER BY c1.sequence, c.sequence;
        """)
        res = self._cr.dictfetchall()
        list_initial_balance = []
        list_subtotal = {'capital': 0, 'comp': 0, 'adjust': 0, 'reserve': 0, 'result': 0, 'int': 0}
        list_modif_initial_balance = {'capital': 0, 'comp': 0, 'adjust': 0, 'reserve': 0, 'result': 0, 'int': 0}
        list_subtotal2 = {'capital': 0, 'comp': 0, 'adjust': 0, 'reserve': 0, 'result': 0, 'int': 0}
        list_subtotal3 = {'capital': 0, 'comp': 0, 'adjust': 0, 'reserve': 0, 'result': 0, 'int': 0}
        list_increase_owner = []
        list_increase_owner_total = {'capital': 0, 'comp': 0, 'adjust': 0, 'reserve': 0, 'result': 0, 'int': 0}
        list_distribution_utilities = []
        list_distribution_utilities_total = {'capital': 0, 'comp': 0, 'adjust': 0, 'reserve': 0, 'result': 0, 'int': 0}
        list_distribution_ant = {'capital': 0, 'comp': 0, 'adjust': 0, 'reserve': 0, 'result': 0, 'int': 0}
        list_account_exp = {'capital': 0, 'comp': 0, 'adjust': 0, 'reserve': 0, 'result': 0, 'int': 0}
        list_year_results = {'capital': 0, 'comp': 0, 'adjust': 0, 'reserve': 0, 'result': 0, 'int': 0}
        list_final_amount = []
        list_final_amount_total = {'capital': 0, 'comp': 0, 'adjust': 0, 'reserve': 0, 'result': 0, 'int': 0}

        for c in res:
            conf = self.env['evolucion.patrimonio.conf'].search([('id', '=', c['id'])])
            data_record = {
                'name': c['child_name'],
                'capital': '',
                'comp': '',
                'adjust': '',
                'reserve': '',
                'result': '',
                'int': '',
                'id_conf': c['id'],
                'parent_id': c['parent_id'],
                'type': c['type'],
                'margin': 5
            }
            # 1- Saldo Inicial
            if c['section'] == 1:
                if c.get('parent_id', False):
                    _found = False
                    data_record_parent = data_record.copy()
                    for ok in list_initial_balance:
                        if ok['parent_id'] == c['parent_id']:
                            _found = True
                            break
                    if not _found:
                        data_record_parent['name'] = c['parent_name'].upper()
                        # data_record_parent['margin'] += 5
                        list_initial_balance.append(data_record_parent)
                    # if c.get('parent_id', False):
                    data_record['margin'] = data_record_parent['margin'] + 15
                    data_record['name'] = c['child_name']

                if c.get('type', False) == 'sum':  # or not c.get('parent_id', False):
                    data_record['name'] = c['child_name'].upper()
                # amount = self.get_initial_amount(c['id'], data, conf, data_record)
                self.get_initial_amount(c['id'], data, conf, data_record)
                list_initial_balance.append(data_record)
                # TOTALES
                for key in COLUMN_TYPES.keys():
                    if key in list_modif_initial_balance:
                        list_subtotal[key] += data_record[key]
                # if c['column'] in list_subtotal:
                #     list_subtotal[c['column']] += amount
            # 2- MODIF. AL SALDO INICIAL
            if c['section'] == 2:
                self.get_modif_amount(c['id'], data, conf, data_record)
                for key in COLUMN_TYPES.keys():
                    if key in list_modif_initial_balance:
                        list_modif_initial_balance[key] += data_record[key]
                # if c['column'] in list_modif_initial_balance:
                #     list_modif_initial_balance[c['column']] += amount
            # 4-AUMENTO DEL APORTE DE PROPIETARIO
            if c['section'] == 4:
                if c.get('parent_id', False):
                    _found = False
                    data_record_parent = data_record.copy()
                    for ok in list_increase_owner:
                        if ok['parent_id'] == c['parent_id']:
                            _found = True
                            break
                    if not _found:
                        data_record_parent['name'] = c['parent_name'].upper()
                        # data_record_parent['margin'] += 5
                        list_increase_owner.append(data_record_parent)
                    # if c.get('parent_id', False):
                    data_record['margin'] = data_record_parent['margin'] + 15
                    data_record['name'] = c['child_name']
                if c.get('type', False) == 'sum':  # or not c.get('parent_id', False):
                    data_record['name'] = c['child_name'].upper()
                self.get_increase_owner_amount(c['id'], data, conf, data_record)
                # data_record[c['column']] = amount
                list_increase_owner.append(data_record)
                # TOTALES
                for key in COLUMN_TYPES.keys():
                    if key in list_modif_initial_balance:
                        list_increase_owner_total[key] += data_record[key]
                # if c['column'] in list_increase_owner_total:
                #     list_increase_owner_total[c['column']] += amount
            # 5-DISTRIBUCION DE UTILIDADES
            if c['section'] == 5:
                if c.get('parent_id', False):
                    _found = False
                    data_record_parent = data_record.copy()
                    for ok in list_distribution_utilities:
                        if ok['parent_id'] == c['parent_id']:
                            _found = True
                            break
                    if not _found:
                        data_record_parent['name'] = c['parent_name'].upper()
                        # data_record_parent['margin'] += 5
                        list_distribution_utilities.append(data_record_parent)
                    # if c.get('parent_id', False):
                    data_record['margin'] = data_record_parent['margin'] + 15
                    data_record['name'] = c['child_name']

                if c.get('type', False) == 'sum':  # or not c.get('parent_id', False):
                    data_record['name'] = c['child_name'].upper()
                self.get_distribution_utilities(c['id'], data, conf, data_record)
                # data_record[c['column']] = amount
                list_distribution_utilities.append(data_record)
                for key in COLUMN_TYPES.keys():
                    if key in list_distribution_utilities_total:
                        list_distribution_utilities_total[key] += data_record[key]
                # if c['column'] in list_distribution_utilities_total:
                #     list_distribution_utilities_total[c['column']] += amount
            # 6-DISTRIB. DE UTIL. ANTICIPADAS
            if c['section'] == 6:
                data_record_copy = dict(data_record)
                self.get_distribution_ant(c['id'], data, conf, data_record_copy)
                for key in COLUMN_TYPES.keys():
                    if key in list_distribution_ant:
                        list_distribution_ant[key] += data_record_copy[key]
                # if c['column'] in list_distribution_ant:
                #     list_distribution_ant[c['column']] += amount
            # 7-REEXPRESIONES CONTABLES
            if c['section'] == 7:
                data_record_copy = dict(data_record)
                self.get_account_exp(c['id'], data, conf, data_record_copy)
                for key in COLUMN_TYPES.keys():
                    if key in list_account_exp:
                        list_account_exp[key] += data_record_copy[key]
                # if c['column'] in list_account_exp:
                #     list_account_exp[c['column']] += amount
            # 8-RESULTADOS DEL EJERCICIO
            if c['section'] == 8:
                data_record_copy = dict(data_record)
                self.get_year_results(c['id'], data, conf, data_record_copy)
                for key in COLUMN_TYPES.keys():
                    if key in list_year_results:
                        list_year_results[key] += data_record_copy[key]
                # if c['column'] in list_year_results:
                #     list_year_results[c['column']] += amount
            # 10-SALDOS FINALES
            if c['section'] == 10:
                data_record_parent = data_record.copy()
                if c.get('parent_id', False):
                    _found = False
                    # data_record_parent = data_record.copy()
                    for ok in list_final_amount:
                        if ok['parent_id'] == c['parent_id']:
                            _found = True
                            break
                    if not _found:
                        data_record_parent['name'] = c['parent_name'].upper()
                        # data_record_parent['margin'] += 5
                        list_final_amount.append(data_record_parent)
                    # if c.get('parent_id', False):
                    data_record['margin'] = data_record_parent['margin'] + 15
                    data_record['name'] = c['child_name']
                # self.get_final_amount(c['id'], data, conf, data_record_parent)
                self.get_final_amount(c['id'], data, conf, data_record)
                # data_record[c['column']] = amount
                list_final_amount.append(data_record)
                for key in COLUMN_TYPES.keys():
                    if key in list_final_amount_total:
                        list_final_amount_total[key] += data_record[key]
                # if c['column'] in list_final_amount_total:
                #     list_final_amount_total[c['column']] += amount
        # TOTALES
        # 3-SALDOS INIC. MODIFICADOS
        for key, value in list_subtotal.items():
            list_subtotal2[key] += value
        for key, value in list_modif_initial_balance.items():
            list_subtotal2[key] += value
        # SUBTOTAL SEMIFINAL (4, 5, 6, 7, 8)
        for key, value in list_increase_owner_total.items():
            list_subtotal3[key] += value
        for key, value in list_distribution_utilities_total.items():
            list_subtotal3[key] += value
        for key, value in list_distribution_ant.items():
            list_subtotal3[key] += value
        for key, value in list_account_exp.items():
            list_subtotal3[key] += value
        for key, value in list_year_results.items():
            list_subtotal3[key] += value
        _r = (
            # 1- Saldo Inicial
            list_initial_balance,
            # 2- MODIF. AL SALDO INICIAL
            list_subtotal,
            # 3-SALDOS INIC. MODIFICADOS
            list_modif_initial_balance,
            # SUBTOTAL
            list_subtotal2,
            # 4-AUMENTO DEL APORTE DE PROPIETARIO
            list_increase_owner,
            # 5-DISTRIBUCION DE UTILIDADES
            list_distribution_utilities,
            # 6-DISTRIB. DE UTIL. ANTICIPADAS
            list_distribution_ant,
            # 7-REEXPRESIONES CONTABLES
            list_account_exp,
            # 8-RESULTADOS DEL EJERCICIO
            list_year_results,
            # SUBTOTAL
            list_subtotal3,
            # 10-SALDOS FINALES
            list_final_amount,
            # TOTAL SALDOS FINALES
            list_final_amount_total
        )
        if not show_zero:
            return self.clean_zero(_r)
        return _r

    @api.multi
    def render_html(self, data):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('report_evolucion_patrimonio')
        _rows = self.env[report.model].browse(data['form']['wzd_ids'])
        docargs = {
            'doc_ids': _rows.ids,
            'doc_model': report.model,
            'docs': _rows,
            # Customs
            'lines': self.get_lines(data)
        }
        return report_obj.render('grp_account_financial_reports.report_evolucion_patrimonio', docargs)


class report_evolucion_patrimonio_parser_xls(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context=None):
        super(report_evolucion_patrimonio_parser_xls, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'cr': self.cr,
            'uid': self.uid,
            'pool': self.pool
        })


report_sxw.report_sxw('report.report_evolucion_patrimonio_xls', 'evolucion.patrimonio.wzd',
                      parser=report_evolucion_patrimonio_parser_xls, header=False, register=False)

FONT_SIZE = 8


class report_evolucion_patrimonio_xls(report_xls):
    def pixel2with(self, pixel):
        # *** Approximation ****
        return int(round((pixel - 0.446) / 0.0272, 0))

    def width2pixels(self, width):
        # *** Approximation ****
        return int(round(width * 0.0272 + 0.446, 0))

    def font_size(self, size):
        # 10/200 = size/x
        return size * 20

    def print_blank(self, ws, r1, r2, c1, c2, left=1, right=1, top=1, bottom=1, font_size=8):
        """ Print Blank Row"""
        borders1 = Borders()
        borders1.left = left
        borders1.right = right
        borders1.top = top
        borders1.bottom = bottom
        fnt1 = Font()
        fnt1.height = self.font_size(font_size)
        style1 = XFStyle()
        style1.borders = borders1
        style1.font = fnt1
        ws.write_merge(r1, r2, c1, c2, '', style1)

    def print_title(self, ws, parser, row, data):
        fnt_title = Font()
        fnt_title.bold = True
        fnt_title.height = self.font_size(FONT_SIZE + 8)
        al_title = Alignment()
        al_title.horz = Alignment.HORZ_LEFT
        al_title.vert = Alignment.VERT_CENTER
        al_title.wrap = Alignment.WRAP_AT_RIGHT
        style_title = XFStyle()
        style_title.font = fnt_title
        style_title.alignment = al_title
        row = 0
        ws.write_merge(row, 1, 0, 6, "ESTADO DE EVOLUCION DEL PATRIMONIO", style=style_title)
        return row + 2

    def print_title2(self, ws, parser, row, data):
        fnt_title2 = Font()
        fnt_title2.height = self.font_size(FONT_SIZE + 4)
        al_title2 = Alignment()
        al_title2.horz = Alignment.HORZ_LEFT
        al_title2.vert = Alignment.VERT_CENTER
        al_title2.wrap = Alignment.WRAP_AT_RIGHT
        style_title2 = XFStyle()
        style_title2.font = fnt_title2
        style_title2.alignment = al_title2
        ws.write(row, 0, u"DENOMINACIÓN DE LA EMPRESA:", style=style_title2)
        wzd_obj = parser.pool.get('evolucion.patrimonio.wzd').browse(parser.cr, parser.uid, data['form']['wzd_ids'][0])
        ws.write_merge(row, row, 1, 4, wzd_obj.company_id.name, style=style_title2)
        ws.write(row, 5, "Ejercicio: ", style=style_title2)
        ws.write(row, 6, wzd_obj.fiscalyear_id.name, style=style_title2)
        return row + 2

    def print_header(self, ws, parser, row, data):
        fnt_header = Font()
        fnt_header.height = self.font_size(FONT_SIZE + 4)
        al_header = Alignment()
        al_header.horz = Alignment.HORZ_CENTER
        al_header.vert = Alignment.VERT_CENTER
        al_header.wrap = Alignment.WRAP_AT_RIGHT
        borders_header = Borders()
        borders_header.left = 1
        borders_header.right = 1
        borders_header.top = 1
        borders_header.bottom = 1
        style_header = XFStyle()
        style_header.font = fnt_header
        style_header.alignment = al_header
        style_header.borders = borders_header
        ws.write(row, 0, "CONCEPTO", style=style_header)
        ws.write(row, 1, "CAPITAL", style=style_header)
        ws.write(row, 2, "APORTES Y COMPROM. A CAPITALIZ.", style=style_header)
        ws.write(row, 3, "AJUSTES AL PATRIMON.", style=style_header)
        ws.write(row, 4, "RESERVAS", style=style_header)
        ws.write(row, 5, "RESULT. ACUMUL.", style=style_header)
        ws.write(row, 6, "PATRIMONIO TOTAL", style=style_header)
        return row + 1

    # 1-SALDOS INICIALES
    def print_initial_amount(self, ws, line, parser, row, data):
        fnt_initial = Font()
        fnt_initial.bold = True
        fnt_initial.height = self.font_size(FONT_SIZE)
        al_initial = Alignment()
        al_initial.horz = Alignment.HORZ_LEFT
        al_initial.vert = Alignment.VERT_CENTER
        al_initial.wrap = Alignment.WRAP_AT_RIGHT
        borders_initial = Borders()
        borders_initial.left = 1
        borders_initial.right = 1
        borders_initial.top = 1
        borders_initial.bottom = 1
        style_initial = XFStyle()
        style_initial.font = fnt_initial
        style_initial.alignment = al_initial
        style_initial.borders = borders_initial
        ws.write(row, 0, "1-SALDOS INICIALES", style=style_initial)
        ws.write(row, 1, "", style=style_initial)
        ws.write(row, 2, "", style=style_initial)
        ws.write(row, 3, "", style=style_initial)
        ws.write(row, 4, "", style=style_initial)
        ws.write(row, 5, "", style=style_initial)
        ws.write(row, 6, "", style=style_initial)

        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        for l in line:
            row += 1
            ws.write(row, 0, " " * ((l['margin'] - 10) if l['margin'] > 5 else l['margin']) + l['name'],
                     style=style_line)
            ws.write(row, 1, l['capital'], style=style_line_value)
            ws.write(row, 2, l['comp'], style=style_line_value)
            ws.write(row, 3, l['adjust'], style=style_line_value)
            ws.write(row, 4, l['reserve'], style=style_line_value)
            ws.write(row, 5, l['result'], style=style_line_value)
            ws.write(row, 6, l['int'], style=style_line_value)
        return row + 1

    # SUBTOTAL
    def print_subtotal_initial(self, ws, line, parser, row, data):
        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        ws.write(row, 0, "SUBTOTAL", style=style_line)
        ws.write(row, 1, line['capital'], style=style_line_value)
        ws.write(row, 2, line['comp'], style=style_line_value)
        ws.write(row, 3, line['adjust'], style=style_line_value)
        ws.write(row, 4, line['reserve'], style=style_line_value)
        ws.write(row, 5, line['result'], style=style_line_value)
        ws.write(row, 6, line['int'], style=style_line_value)
        return row + 1

    # 2- MODIF. AL SALDO INICIAL
    def print_modif_amount(self, ws, line, parser, row, data):
        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        ws.write(row, 0, "2-MODIF. AL SALDO INICIAL", style=style_line)
        ws.write(row, 1, line['capital'], style=style_line_value)
        ws.write(row, 2, line['comp'], style=style_line_value)
        ws.write(row, 3, line['adjust'], style=style_line_value)
        ws.write(row, 4, line['reserve'], style=style_line_value)
        ws.write(row, 5, line['result'], style=style_line_value)
        ws.write(row, 6, line['int'], style=style_line_value)
        return row + 1

    # 3-SALDOS INIC. MODIFICADOS
    def print_modif_amount_initial(self, ws, line, parser, row, data):
        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        ws.write(row, 0, "3-SALDOS INIC. MODIFICADOS", style=style_line)
        ws.write(row, 1, line['capital'], style=style_line_value)
        ws.write(row, 2, line['comp'], style=style_line_value)
        ws.write(row, 3, line['adjust'], style=style_line_value)
        ws.write(row, 4, line['reserve'], style=style_line_value)
        ws.write(row, 5, line['result'], style=style_line_value)
        ws.write(row, 6, line['int'], style=style_line_value)
        return row + 1

    # 4-AUMENTO DEL APORTE DE PROPIETARIO
    def print_increase_owner_amount(self, ws, line, parser, row, data):
        fnt_initial = Font()
        fnt_initial.bold = True
        fnt_initial.height = self.font_size(FONT_SIZE)
        al_initial = Alignment()
        al_initial.horz = Alignment.HORZ_LEFT
        al_initial.vert = Alignment.VERT_CENTER
        al_initial.wrap = Alignment.WRAP_AT_RIGHT
        borders_initial = Borders()
        borders_initial.left = 1
        borders_initial.right = 1
        borders_initial.top = 1
        borders_initial.bottom = 1
        style_initial = XFStyle()
        style_initial.font = fnt_initial
        style_initial.alignment = al_initial
        style_initial.borders = borders_initial
        ws.write(row, 0, "4-AUMENTO DEL APORTE DE PROPIETARIO", style=style_initial)
        ws.write(row, 1, "", style=style_initial)
        ws.write(row, 2, "", style=style_initial)
        ws.write(row, 3, "", style=style_initial)
        ws.write(row, 4, "", style=style_initial)
        ws.write(row, 5, "", style=style_initial)
        ws.write(row, 6, "", style=style_initial)

        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        for l in line:
            row += 1
            ws.write(row, 0, " " * ((l['margin'] - 10) if l['margin'] > 5 else l['margin']) + l['name'],
                     style=style_line)
            ws.write(row, 1, l['capital'], style=style_line_value)
            ws.write(row, 2, l['comp'], style=style_line_value)
            ws.write(row, 3, l['adjust'], style=style_line_value)
            ws.write(row, 4, l['reserve'], style=style_line_value)
            ws.write(row, 5, l['result'], style=style_line_value)
            ws.write(row, 6, l['int'], style=style_line_value)
        return row + 1

    # 5-DISTRIBUCION DE UTILIDADES
    def print_distribution_utilities(self, ws, line, parser, row, data):
        fnt_initial = Font()
        fnt_initial.bold = True
        fnt_initial.height = self.font_size(FONT_SIZE)
        al_initial = Alignment()
        al_initial.horz = Alignment.HORZ_LEFT
        al_initial.vert = Alignment.VERT_CENTER
        al_initial.wrap = Alignment.WRAP_AT_RIGHT
        borders_initial = Borders()
        borders_initial.left = 1
        borders_initial.right = 1
        borders_initial.top = 1
        borders_initial.bottom = 1
        style_initial = XFStyle()
        style_initial.font = fnt_initial
        style_initial.alignment = al_initial
        style_initial.borders = borders_initial
        ws.write(row, 0, "5-DISTRIBUCION DE UTILIDADES", style=style_initial)
        ws.write(row, 1, "", style=style_initial)
        ws.write(row, 2, "", style=style_initial)
        ws.write(row, 3, "", style=style_initial)
        ws.write(row, 4, "", style=style_initial)
        ws.write(row, 5, "", style=style_initial)
        ws.write(row, 6, "", style=style_initial)

        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        for l in line:
            row += 1
            ws.write(row, 0, " " * ((l['margin'] - 10) if l['margin'] > 5 else l['margin']) + l['name'],
                     style=style_line)
            ws.write(row, 1, l['capital'], style=style_line_value)
            ws.write(row, 2, l['comp'], style=style_line_value)
            ws.write(row, 3, l['adjust'], style=style_line_value)
            ws.write(row, 4, l['reserve'], style=style_line_value)
            ws.write(row, 5, l['result'], style=style_line_value)
            ws.write(row, 6, l['int'], style=style_line_value)
        return row + 1

    # 6-DISTRIB. DE UTIL. ANTICIPADAS
    def print_distribution_ant(self, ws, line, parser, row, data):
        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        fnt_line.bold = True
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        ws.write(row, 0, "6-DISTRIB. DE UTIL. ANTICIPADAS", style=style_line)
        ws.write(row, 1, line['capital'], style=style_line_value)
        ws.write(row, 2, line['comp'], style=style_line_value)
        ws.write(row, 3, line['adjust'], style=style_line_value)
        ws.write(row, 4, line['reserve'], style=style_line_value)
        ws.write(row, 5, line['result'], style=style_line_value)
        ws.write(row, 6, line['int'], style=style_line_value)
        return row + 1

    # 7-REEXPRESIONES CONTABLES
    def print_account_exp(self, ws, line, parser, row, data):
        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        fnt_line.bold = True
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        ws.write(row, 0, "7-REEXPRESIONES CONTABLES", style=style_line)
        ws.write(row, 1, line['capital'], style=style_line_value)
        ws.write(row, 2, line['comp'], style=style_line_value)
        ws.write(row, 3, line['adjust'], style=style_line_value)
        ws.write(row, 4, line['reserve'], style=style_line_value)
        ws.write(row, 5, line['result'], style=style_line_value)
        ws.write(row, 6, line['int'], style=style_line_value)
        return row + 1

    # 8-RESULTADOS DEL EJERCICIO
    def print_year_results(self, ws, line, parser, row, data):
        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        fnt_line.bold = True
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        ws.write(row, 0, "8-RESULTADOS DEL EJERCICIO", style=style_line)
        ws.write(row, 1, line['capital'], style=style_line_value)
        ws.write(row, 2, line['comp'], style=style_line_value)
        ws.write(row, 3, line['adjust'], style=style_line_value)
        ws.write(row, 4, line['reserve'], style=style_line_value)
        ws.write(row, 5, line['result'], style=style_line_value)
        ws.write(row, 6, line['int'], style=style_line_value)
        return row + 1

    # 9-.............................. (Es necesario?)
    def print_line_extra(self, ws, parser, row, data):
        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        ws.write(row, 0, "9-..............................", style=style_line)
        ws.write(row, 1, "", style=style_line_value)
        ws.write(row, 2, "", style=style_line_value)
        ws.write(row, 3, "", style=style_line_value)
        ws.write(row, 4, "", style=style_line_value)
        ws.write(row, 5, "", style=style_line_value)
        ws.write(row, 6, "", style=style_line_value)
        return row + 1

    # SUBTOTAL
    def print_subtotal(self, ws, line, parser, row, data):
        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        ws.write(row, 0, "SUBTOTAL (4 a 9)", style=style_line)
        ws.write(row, 1, line['capital'], style=style_line_value)
        ws.write(row, 2, line['comp'], style=style_line_value)
        ws.write(row, 3, line['adjust'], style=style_line_value)
        ws.write(row, 4, line['reserve'], style=style_line_value)
        ws.write(row, 5, line['result'], style=style_line_value)
        ws.write(row, 6, line['int'], style=style_line_value)
        return row + 1

    # 10-SALDOS FINALES
    def print_final_amount(self, ws, line, parser, row, data):
        fnt_initial = Font()
        fnt_initial.bold = True
        fnt_initial.height = self.font_size(FONT_SIZE)
        al_initial = Alignment()
        al_initial.horz = Alignment.HORZ_LEFT
        al_initial.vert = Alignment.VERT_CENTER
        al_initial.wrap = Alignment.WRAP_AT_RIGHT
        borders_initial = Borders()
        borders_initial.left = 1
        borders_initial.right = 1
        borders_initial.top = 1
        borders_initial.bottom = 1
        style_initial = XFStyle()
        style_initial.font = fnt_initial
        style_initial.alignment = al_initial
        style_initial.borders = borders_initial
        ws.write(row, 0, "10-SALDOS FINALES", style=style_initial)
        ws.write(row, 1, "", style=style_initial)
        ws.write(row, 2, "", style=style_initial)
        ws.write(row, 3, "", style=style_initial)
        ws.write(row, 4, "", style=style_initial)
        ws.write(row, 5, "", style=style_initial)
        ws.write(row, 6, "", style=style_initial)

        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        for l in line:
            row += 1
            ws.write(row, 0, " " * ((l['margin'] - 10) if l['margin'] > 5 else l['margin']) + l['name'],
                     style=style_line)
            ws.write(row, 1, l['capital'], style=style_line_value)
            ws.write(row, 2, l['comp'], style=style_line_value)
            ws.write(row, 3, l['adjust'], style=style_line_value)
            ws.write(row, 4, l['reserve'], style=style_line_value)
            ws.write(row, 5, l['result'], style=style_line_value)
            ws.write(row, 6, l['int'], style=style_line_value)
        return row + 1

    # TOTAL SALDOS FINALES
    def print_total_amount(self, ws, line, parser, row, data):
        fnt_line = Font()
        fnt_line.height = self.font_size(FONT_SIZE)
        al_line = Alignment()
        al_line.horz = Alignment.HORZ_LEFT
        al_line.vert = Alignment.VERT_CENTER
        al_line.wrap = Alignment.WRAP_AT_RIGHT
        borders_line = Borders()
        borders_line.left = 1
        borders_line.right = 1
        borders_line.top = 1
        borders_line.bottom = 1
        style_line = XFStyle()
        style_line.font = fnt_line
        style_line.alignment = al_line
        style_line.borders = borders_line

        fnt_line_value = Font()
        fnt_line_value.height = self.font_size(FONT_SIZE)
        al_line_value = Alignment()
        al_line_value.horz = Alignment.HORZ_CENTER
        al_line_value.vert = Alignment.VERT_CENTER
        al_line_value.wrap = Alignment.WRAP_AT_RIGHT
        borders_line_value = Borders()
        borders_line_value.left = 1
        borders_line_value.right = 1
        borders_line_value.top = 1
        borders_line_value.bottom = 1
        style_line_value = XFStyle()
        style_line_value.font = fnt_line_value
        style_line_value.alignment = al_line_value
        style_line_value.borders = borders_line_value

        ws.write(row, 0, "TOTAL SALDOS FINALES", style=style_line)
        ws.write(row, 1, line['capital'], style=style_line_value)
        ws.write(row, 2, line['comp'], style=style_line_value)
        ws.write(row, 3, line['adjust'], style=style_line_value)
        ws.write(row, 4, line['reserve'], style=style_line_value)
        ws.write(row, 5, line['result'], style=style_line_value)
        ws.write(row, 6, line['int'], style=style_line_value)
        return row + 1

    def generate_xls_report(self, parser, xls_styles, data, objects, wb):
        ws = wb.add_sheet("Informe")
        ws.col(0).width = self.pixel2with(350)  # Concepto
        ws.col(1).width = self.pixel2with(120)  # Capital
        ws.col(2).width = self.pixel2with(120)  # Aportes
        ws.col(3).width = self.pixel2with(120)  # Ajustes
        ws.col(4).width = self.pixel2with(120)  # Reservas
        ws.col(5).width = self.pixel2with(120)  # Resultados
        ws.col(6).width = self.pixel2with(120)  # Patrimonio

        row = 0
        row = self.print_title(ws, parser, row, data)
        row = self.print_title2(ws, parser, row, data)
        row = self.print_header(ws, parser, row, data)

        pdf_parser = parser.pool.get(
            'report.report_evolucion_patrimonio')  # report_evolucion_patrimonio(parser.pool, parser.cr)
        lines = pdf_parser.get_lines(parser.cr, parser.uid, data, context={})
        # 1-SALDOS INICIALES
        row = self.print_initial_amount(ws, lines[0], parser, row, data)
        # SUBTOTAL
        row = self.print_subtotal_initial(ws, lines[1], parser, row, data)
        # 2- MODIF. AL SALDO INICIAL
        row = self.print_modif_amount(ws, lines[2], parser, row, data)
        # 3-SALDOS INIC. MODIFICADOS
        row = self.print_modif_amount_initial(ws, lines[3], parser, row, data)
        # 4-AUMENTO DEL APORTE DE PROPIETARIO
        row = self.print_increase_owner_amount(ws, lines[4], parser, row, data)
        # 5-DISTRIBUCION DE UTILIDADES
        row = self.print_distribution_utilities(ws, lines[5], parser, row, data)
        # 6-DISTRIB. DE UTIL. ANTICIPADAS
        row = self.print_distribution_ant(ws, lines[6], parser, row, data)
        # 7-REEXPRESIONES CONTABLES
        row = self.print_account_exp(ws, lines[7], parser, row, data)
        # 8-RESULTADOS DEL EJERCICIO
        row = self.print_year_results(ws, lines[8], parser, row, data)
        # 9-.............................. (Es necesario?)
        row = self.print_line_extra(ws, parser, row, data)
        # SUBTOTAL
        row = self.print_subtotal(ws, lines[9], parser, row, data)
        # 10-SALDOS FINALES
        row = self.print_final_amount(ws, lines[10], parser, row, data)
        # TOTAL SALDOS FINALES
        row = self.print_total_amount(ws, lines[11], parser, row, data)


report_evolucion_patrimonio_xls('report.report_evolucion_patrimonio_xls', 'evolucion.patrimonio.wzd',
                                parser=report_evolucion_patrimonio_parser_xls)
