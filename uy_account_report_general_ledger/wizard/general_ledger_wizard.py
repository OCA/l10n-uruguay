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

from openerp.osv import fields, orm
from openerp.tools.translate import _
import time

class general_ledger_webkit_wizard(orm.TransientModel):
    _inherit = 'general.ledger.webkit'

    _columns = {
        'filter_partner_ids': fields.many2many('res.partner', 'general_ledger_webkit_res_partner_rel', 'gen_ledger_wzd_id', 'partner_id', 'Filter by Partners'),
        'filter_operating_unit_ids': fields.many2many('operating.unit', 'general_ledger_webkit_operating_unit_rel', 'gen_ledger_wzd_id', 'operating_unit_id', string='Operating Units', required=False),
        # Secundary currency rate options
        'display_curr_columns': fields.boolean('Display columns secundary currency'),
        'curr_rate_option': fields.selection([ ('trans_date', 'Tipo de cambio según fecha de la transacción'),
                                               ('set_date', 'Tipo de cambio según una fecha dada'),
                                               ('set_curr_rate', 'Otro tipo de cambio')], 'Opciones de tipo de cambio', required=True),
        'curr_rate_date': fields.date('Fecha'),
        'curr_rate': fields.float('Tipo de cambio'),
    }

    _defaults = {
        'centralize': False,
        'target_move': 'all',
        'amount_currency': False,
        'display_curr_columns': True,
        'curr_rate_option': 'trans_date',
        'curr_rate_date': time.strftime("%Y-%m-%d")
    }

    def pre_print_report(self, cr, uid, ids, data, context=None):
        data = super(general_ledger_webkit_wizard, self).pre_print_report(
            cr, uid, ids, data, context)
        vals = self.read(cr, uid, ids,
                         ['display_curr_columns','curr_rate_option','curr_rate_date','curr_rate' ],
                         context=context)[0]
        row = self.browse(cr, uid, ids[0])
        filter_partner_ids = []
        filter_partner_names = []
        for partner in row.filter_partner_ids:
            filter_partner_ids.append(partner.id)
            filter_partner_names.append(partner.name)
        vals['filter_partner_ids'] = filter_partner_ids
        vals['filter_partner_names'] = filter_partner_names
        filter_operating_unit_ids = []
        filter_operating_unit_names = []
        for ou in row.filter_operating_unit_ids:
            filter_operating_unit_ids.append(ou.id)
            filter_operating_unit_names.append(ou.name)
        vals['filter_operating_unit_ids'] = filter_operating_unit_ids
        vals['filter_operating_unit_names'] = filter_operating_unit_names
        data['form'].update(vals)
        return data

    def _print_report(self, cr, uid, ids, data, context=None):
        context = context or {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        if context.get('xls_export'):
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'account.account_report_general_ledger_xls_ext',
                    'datas': data}
        else:
            return {'type': 'ir.actions.report.xml',
                    'report_name': 'account.account_report_general_ledger_webkit_ext',
                    'datas': data}
