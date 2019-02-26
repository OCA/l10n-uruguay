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

# TODO: SPRING 11 GAP 28 L
class GrpAprobacionPagos(models.Model):
    _inherit = 'account.invoice'

    doc_type = fields.Selection(
        selection_add=[('adelanto_viatico', u'Adelanto de viáticos')])
    doc_type_computed = fields.Char(string=u"Tipo Documento", compute="_compute_doc_type", store=True)

    @api.depends('doc_type', 'type')
    def _compute_doc_type(self):
        voucher_obj = self.env['account.voucher']
        for rec in self:
            if rec.doc_type != 'invoice':
                dict_types = dict(self.fields_get(allfields=['doc_type'])['doc_type']['selection'])
                dict_types.update({'vales_caja': u'Vales de caja'})
                if rec.doc_type == 'adelanto_viatico':
                    voucher_id = voucher_obj.search([('invoice_id', '=', rec.id)], limit=1)
                    if voucher_id.rendicion_viaticos_id:
                        rec.doc_type_computed = u'Rendición de viáticos'
                    elif voucher_id.solicitud_viatico_id:
                        rec.doc_type_computed = u'Solicitud de viáticos'
                    else:
                        rec.doc_type_computed = u'Adelanto de viáticos'
                else:
                    rec.doc_type_computed = dict_types.get(rec.doc_type, rec.doc_type)
            else:
                if rec.type == 'out_refund':
                    rec.doc_type_computed = "Nota de crédito de cliente"
                elif rec.type == 'in_refund':
                    rec.doc_type_computed = "Nota de crédito de proveedor"
                elif rec.type == 'out_invoice':
                    rec.doc_type_computed = "Factura de cliente"
                elif rec.type == 'in_invoice':
                    rec.doc_type_computed = "Factura de proveedor"

    @api.one
    def _compute_related_document(self):
        voucher_obj = self.env['account.voucher']
        voucher_id = voucher_obj.search([('invoice_id', '=', self.id)], limit=1)
        if voucher_id:
            self.related_document = voucher_id._get_related_document()['related_document']
            self.related_document2 = voucher_id._get_related_document()['related_document2']
        else:
            super(GrpAprobacionPagos, self)._compute_related_document()

    @api.multi
    def action_link_related_document(self):
        self.ensure_one()
        voucher_id = self.env['account.voucher'].search([('invoice_id', '=', self.id)], limit=1)
        if voucher_id:
            _related_info_dict = voucher_id._get_related_document()
            if _related_info_dict['related_model'] and _related_info_dict['related_id']:
                dict_toreturn = {
                    'type': 'ir.actions.act_window',
                    'res_model': _related_info_dict['related_model'],
                    'display_name': 'Documento relacionado',
                    'view_type': 'form',
                    'name': 'Documento relacionado',
                    'target': 'current',
                    'view_mode': 'form',
                    'res_id': _related_info_dict['related_id']
                }

                if _related_info_dict.get('view_id') and _related_info_dict['view_id']:
                    res = self.env['ir.model.data'].get_object_reference(_related_info_dict['module_name'],
                                                                         _related_info_dict['view_id'])
                    res_id = res and res[1] or False
                    dict_toreturn.update({
                        'view_id': res_id
                    })
                return dict_toreturn
            else:
                return super(GrpAprobacionPagos, self).action_link_related_document()
        else:
            return super(GrpAprobacionPagos, self).action_link_related_document()
