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

from openerp import models, fields, api, _
from datetime import datetime, date


class grp_account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'



    # TODO SPRING 5 GAP 46
    def asset_create(self, cr, uid, lines, context=None):
        context = context or {}
        asset_obj = self.pool.get('account.asset.asset')
        asset_asset_obj = self.pool.get('asset.asset')
        if lines and not asset_obj.search(cr,uid, [('invoice_id','=',lines[0].invoice_id.id)]):
            tipo = 'doc_type' in context and context.get('doc_type', False)
            if lines[0].invoice_id.doc_type in ['3en1_invoice','invoice'] or tipo:
                total_cost = sum(map(lambda x: x.quantity * x.price_unit, filter(lambda l: l.asset_category_id, lines)))
                expenses_list = map(lambda x: x.quantity * x.price_unit, filter(lambda l: l.active_expense, lines))
                for line in lines:
                    if line.asset_category_id:
                        quant = line.quantity
                        while quant > 0:
                            vals = {
                                'name': line.name,
                                'code': line.invoice_id.number or False,
                                'category_id': line.asset_category_id.id,
                                'period_id': line.invoice_id.period_id.id,
                                'partner_id': line.invoice_id.partner_id.id,
                                'company_id': line.invoice_id.company_id.id,
                                'currency_id': line.invoice_id.currency_id.id,
                                'purchase_date': line.invoice_id.date_invoice,
                                'invoice_id': line.invoice_id.id,
                                'unidades_originales': line.quantity,
                                # ECHAVIANO, corrigiendo error de creacion de activo desde factura
                                'purchase_value_date': self.get_fecha_depreciacion(line.invoice_id.date_invoice),
                            }
                            # 002- Inicio inc - 536
                            iva_include = False
                            for tax in line.invoice_line_tax_id:
                                # si es iva incluido
                                if tax.price_include:
                                    iva_include = True
                            current_cost = iva_include and line.quantity * line.price_unit or line.price_subtotal
                            percent = current_cost / float(total_cost)
                            expense_distrb = sum(map(lambda x: (x*percent) / line.quantity, expenses_list))
                            vals.update({'purchase_value': expense_distrb + line.price_unit})
                            # 002- Fin inc - 536
                            changed_vals = asset_obj.onchange_category_id(cr, uid, [], vals['category_id'], context=context)
                            vals.update(changed_vals['value'])
                            asset_id = asset_obj.create(cr, uid, vals, context=context)
                            if line.asset_category_id.is_asset_mro:
                                asset_asset_obj.create(cr, uid, {'name':vals['name']}, context=context)
                            if line.asset_category_id.open_asset:
                                asset_obj.validate(cr, uid, [asset_id], context=context)
                            quant -=1
        return True
