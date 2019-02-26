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

from openerp import models, fields, api, exceptions

_logger = logging.getLogger(__name__)

# TODO: K SPRING 15
class GrpRemesaWizard(models.TransientModel):
    _name = "grp.remesa.wizard"

    caja_ids = fields.Many2many('grp.caja.recaudadora.tesoreria', 'remesa_caja_rel',
                                domain=[('state', '=', 'checked'),
                                        ('caja_principal', '=', True)], string=u'Cajas')

    # TODO: K SPRING 15
    @api.multi
    def cargar_lineas(self):
        details_ids = []
        check_ids = []
        remesa = self.env['grp.remesa'].browse(self._context.get('active_id'))
        sequence = remesa.sequence
        if self.caja_ids:
            for caja in self.caja_ids:
                if sequence == '/':
                    sequence = caja.name
                details_line = caja.voucher_details_ids.filtered(
                    lambda x: x.entrega_tesoreria is True and x.siff_ticket is False and x.preparar_remesa is False)
                if details_line:
                    for line in details_line:
                        details_ids.append([0, 0, {'origin_line_id': line.id,
                                                   'voucher_id': line.voucher_id.id,
                                                   'origin_voucher_id': line.voucher_id.id,
                                                   'invoice_id': line.invoice_id.id,
                                                   'product_id': line.product_id.id,
                                                   'type': 'box_details',
                                                   'price_subtotal': line.price_subtotal,
                                                   'amount': line.amount,
                                                   'box_id': caja.box_id.id,
                                                   'name': caja.name,
                                                   'plus_amount': line.plus_amount,
                                                   'shipment': True}])
                        line.write({'preparar_remesa': True})
                        caja._get_preparar_remesa()
                        checks = caja.check_ids.filtered(
                            lambda x: x.voucher_id == line.voucher_id and x.invoice_id == line.invoice_id)
                        for check in checks:
                            if check.id not in check_ids:
                                check.copy({'origin_line_id': check.id, 'remesa_id': remesa.id,
                                            'caja_recaudadora_id': False})
                                check_ids.append(check.id)
                    details_line.write({'siff_ticket': True})

                valores_custodia_line = caja.valores_custodia_ids.filtered(
                    lambda x: x.entrega_tesoreria is True and x.siff_ticket is False)
                if valores_custodia_line:
                    for line in valores_custodia_line:
                        line.copy(
                            {'origin_line_id': line.id, 'remesa_id': remesa.id, 'caja_recaudadora_id': False,
                             'box_id': caja.box_id.id, 'name': caja.name, 'shipment': True})
                        checks = caja.check_ids.filtered(
                            lambda x: x.valor_custodia_id == line.valor_custodia_id)
                        for check in checks:
                            if check.id not in check_ids:
                                check.copy(
                                    {'origin_line_id': check.id, 'remesa_id': remesa.id,
                                     'caja_recaudadora_id': False})
                                check_ids.append(check.id)
                    valores_custodia_line.write({'siff_ticket': True})
            vals ={'box_details_ids': details_ids}
            if sequence != remesa.sequence:
                vals['sequence'] = sequence
            remesa.write(vals)
            # data = remesa._update_remesa()
            # remesa.write(data)

        else:
            raise exceptions.ValidationError(u"Debe seleccionar al menos una caja.")
        return True
