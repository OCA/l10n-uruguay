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


# TODO: M SPRING 12 GAP 77
class GrpInvoiceContractCessionWizard(models.TransientModel):
    _name = "grp.invoice.contract.cession.wizard"

    @api.model
    def default_get(self, fields):
        res = super(GrpInvoiceContractCessionWizard, self).default_get(fields)
        cession_ids = []
        contrato = self.env['grp.contrato.proveedores']
        if 'default_contract_id' in self._context and 'default_invoice_id' in self._context:
            contract_id = self._context['default_contract_id']
            invoice_id = self._context['default_invoice_id']
            if contrato.browse(contract_id).cession_ids:
                for cesion in contrato.browse(contract_id).cession_ids:
                    if not self.env['grp.cesion.embargo'].search([('contract_cesion_id','=',cesion.id),('invoice_id','=',invoice_id)]):
                        cession_ids.append([0, 0, {'partner_id': cesion.partner_id.id,
                                                   'contract_cesion_id': cesion.id,
                                                   'date': cesion.date,
                                                   'give_amount': cesion.give_amount,
                                                   'saldo_ceder': cesion.saldo_ceder,
                                                   'cession_type': cesion.cession_type}])

            res['line_ids'] = cession_ids
        return res

    line_ids = fields.One2many('grp.invoice.contract.cession.line.wizard','wizard_id', string=u'Lineas')
    contract_id = fields.Many2one('grp.contrato.proveedores', string='Contrato')
    invoice_id = fields.Many2one('account.invoice', string='Factura')

    @api.multi
    def import_contract_cessions(self):
        cession_ids = []
        if self.line_ids and self.line_ids.filtered(lambda x: x.select):
            for line in self.line_ids.filtered(lambda x: x.select):
                cession_ids.append([0, 0, {'tipo_ces_emb': 'C',
                                           'cesion_partner_id': line.partner_id.id,
                                           'contract_cesion_id': line.contract_cesion_id.id,
                                           'cesion_rupe_cta_bnc_id': False,
                                           'monto_cedido_embargado': line.contract_cesion_id.saldo_ceder}])
            self.invoice_id.write({'cesion_ids': cession_ids})
        else:
            raise exceptions.ValidationError(u"Debe seleccionar al menos una cesion.")
        return True

# TODO: M SPRING 12 GAP 77
class GrpCesionEmbargo(models.Model):
    _inherit = 'grp.cesion.embargo'

    contract_cesion_id = fields.Many2one('grp.cession.contrato', string='Contrato cesion')

# TODO: M SPRING 12 GAP 77
class GrpInvoiceContractCessionLineWizard(models.TransientModel):
    _name = "grp.invoice.contract.cession.line.wizard"

    wizard_id = fields.Many2one('grp.invoice.contract.cession.wizard', string='Wizard')
    contract_cesion_id = fields.Many2one('grp.cession.contrato', string='Contrato cesion')
    partner_id = fields.Many2one("res.partner", string=u'Proveedor')
    date = fields.Date(string=u'Fecha cesión')
    give_amount = fields.Float(string=u'Importe cedido en pesos')
    cession_type = fields.Selection(selection=[('amout_cession', u'Cesión de importes'),
                                               ('total_cession', u'Cesión de totalidad del contrato')],
                                    string=u'Tipo de cesión')
    saldo_ceder = fields.Float(string='Total saldo a ceder')
    select = fields.Boolean(u'Seleccionar', default=False)



