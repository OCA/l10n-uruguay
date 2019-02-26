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
from lxml import etree

_logger = logging.getLogger(__name__)


# TODO: SPRING 11 GAP 292 M
class grpCajaRecaudadoraBoletoSiifValoresCustodiaWizard(models.TransientModel):
    _name = "grp.caja.recaudadora.boleto.siif.valores.custodia.wizard"

    @api.model
    def default_get(self, fields):
        res = super(grpCajaRecaudadoraBoletoSiifValoresCustodiaWizard, self).default_get(fields)
        line_ids = []
        for valore_custodia in self.env['grp.valores_custodia'].search(
                [('tipo_id.transferencia', '=', True), ('boleto_siif', '=', False), ('state', '=', 'recibido')]):
            line_ids.append([0, 0, {'valor_custodia_id': valore_custodia.id,
                                   'partner_id': valore_custodia.partner_id.id,
                                   'fecha_recepcion': valore_custodia.fecha_recepcion,
                                   'name': valore_custodia.name,
                                   'monto': valore_custodia.monto}])

        res['line_ids'] = line_ids
        return res

    line_ids = fields.One2many('grp.caja.recaudadora.boleto.siif.custodia.line.wizard', 'wizard_id', string=u'Lineas')
    boleto_siif_id = fields.Many2one('grp.caja.recaudadora.tesoreria.boleto.siif', string='Boleto SIIF')

    @api.multi
    def transfer_account_voucher(self):

        valor_custodia_line = self.env['grp.caja.recaudadora.tesoreria.line.valor.custodia']
        if self.line_ids and self.line_ids.filtered(lambda x: x.select):
            for line in self.line_ids.filtered(lambda x: x.select):
                valor_custodia_line.create({
                    'valor_custodia_id': line.valor_custodia_id.id,
                    'boleto_siif_id': self.boleto_siif_id.id,
                    'shipment': True
                })

                line.valor_custodia_id.write({'boleto_siif': True})
            data = self.boleto_siif_id._update_remesa()
            self.boleto_siif_id.write(data)
        else:
            raise exceptions.ValidationError(u"Debe seleccionar al menos una linea.")
        return True

    class grpCajaRecaudadoraBoletoSiifCustodiaLineWizard(models.TransientModel):
        _name = "grp.caja.recaudadora.boleto.siif.custodia.line.wizard"

        wizard_id = fields.Many2one('grp.caja.recaudadora.boleto.siif.valores.custodia.wizard', string='Wizard')
        valor_custodia_id = fields.Many2one('grp.valores_custodia', 'VC', help='Valor en custodia')
        partner_id = fields.Many2one('res.partner', string=u'Cliente', related='valor_custodia_id.partner_id', readonly=True)
        # operating_unit_id = fields.Many2one('operating.unit', u'Unidad ejecutora', related='valor_custodia_id.operating_unit_id')
        fecha_recepcion = fields.Date(u'Fecha de cobro', related='valor_custodia_id.fecha_recepcion', readonly=True)
        name = fields.Char(u'N°', related='valor_custodia_id.name', readonly=True)
        monto = fields.Float(string=u'Importe cobrado', related='valor_custodia_id.monto', readonly=True)
        select = fields.Boolean(u'Seleccionar', default=False)

