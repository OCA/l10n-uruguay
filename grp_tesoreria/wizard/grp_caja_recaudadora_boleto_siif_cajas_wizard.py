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


class grpCajaRecaudadoraBoletoSiifCajasWizard(models.TransientModel):
    _name = "grp.caja.recaudadora.boleto.siif.cajas.wizard"

    caja_ids = fields.Many2many('grp.caja.recaudadora.tesoreria', 'boleto_siif_caja_rel', domain=[('state', '=', 'checked'), ('caja_principal', '=', False)], string=u'Cajas')

    @api.multi
    def cargar_lineas(self):
        details_ids = []
        boleto_siif = self.env['grp.caja.recaudadora.tesoreria.boleto.siif'].browse(self._context.get('active_id'))
        if self.caja_ids:
            for caja in self.caja_ids:
                details_line = caja.voucher_details_ids.filtered(lambda x: x.shipment is True and x.siff_ticket is False)
                for line in details_line:
                    details_ids.append([0, 0, {'voucher_id': line.voucher_id.id,
                                               'invoice_id': line.invoice_id.id,
                                               'type': 'box_details',
                                               'product_id': line.product_id.id,
                                               'price_subtotal': line.price_subtotal,
                                               'siif_reference_id':line.id,
                                               'amount': line.amount,
                                               'shipment': True
                                               }])
                details_line.write({'siff_ticket': True})

            boleto_siif.write({'voucher_details_ids': details_ids})
            data = boleto_siif._update_remesa()
            boleto_siif.write(data)

        else:
            raise exceptions.ValidationError(u"Debe seleccionar al menos una caja.")
        return True
