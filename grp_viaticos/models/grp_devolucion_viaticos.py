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

import logging

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError

_logger = logging.getLogger(__name__)

# TODO: SPRING 11 GAP 28 L

class GrpDevolucionViaticos(models.Model):
    _inherit = 'account.voucher'

    rendicion_viaticos_id = fields.Many2one('hr.expense.expense', string=u'Rendición de viáticos', readonly=True,
                                            states={'draft': [('readonly', False)]})

    def _get_nro_documento(self):
        documentos = super(GrpDevolucionViaticos, self)._get_nro_documento()
        if self.rendicion_viaticos_id:
            documentos.append(u'Devolución de viático %s' % (self.name_get()[0][1]))
        return documentos

    @api.multi
    def cancel_voucher(self):
        rviatico_obj = self.env['hr.expense.expense']
        for rec in self:
            sviaticos_ids = rec.line_ids.filtered(lambda x: x.origin_voucher_id.solicitud_viatico_id and x.amount != 0 and not x.origin_voucher_id.rendicion_viaticos_id).mapped('origin_voucher_id.solicitud_viatico_id')
            if rviatico_obj.search_count([('solicitud_viatico_id', 'in', sviaticos_ids.ids),
                                          ('state', 'not in', ['cancelado', 'cancelled'])]):
                raise ValidationError(_(u"No se pueden cancelar pagos de Solicitudes de Viáticos si tienen asociada una Rendición de Viáticos!"))
            sviaticos_ids.suspend_security().write({'adelanto_pagado':False})
            rec.line_ids.filtered(lambda x: x.origin_voucher_id.rendicion_viaticos_id and x.amount != 0).mapped('origin_voucher_id.rendicion_viaticos_id').suspend_security().write({'state':'autorizado'})
        return super(GrpDevolucionViaticos, self).cancel_voucher()

    @api.onchange('rendicion_viaticos_id')
    def _onchange_rendicion_viaticos_id(self):
        self.operating_unit_id = self.rendicion_viaticos_id.operating_unit_id.id



class GrpDevolucionViaticosLine(models.Model):
    _inherit = 'account.voucher.line'

    product_id = fields.Many2one('product.product', string=u'Producto', required=False)
