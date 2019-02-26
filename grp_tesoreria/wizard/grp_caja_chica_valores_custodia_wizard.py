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

from openerp import models, fields, api
from lxml import etree
from openerp.exceptions import ValidationError

_logger = logging.getLogger(__name__)


# TODO: SPRING 10 GAP 474 C
class grpCajaChicaValoresCustodiaWizard(models.TransientModel):
    _name = "grp.caja_chica.valores_custodia.wizard"

    def _get_valores_custodia(self, exclude_vc_ids):
        return self.env['grp.valores_custodia'].search([('state', '=', 'entrega_autorizada'),
                                                 ('id', 'not in', exclude_vc_ids),
                                                 ('tipo_id.efectivo', '=', True),
                                                 ('readonly', '=', False)])

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(grpCajaChicaValoresCustodiaWizard, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                                             context=context,
                                                                             toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        if self._context is not None and 'default_caja_chica_id' in self._context:
            caja_id = self._context['default_caja_chica_id']
            caja = self.env['grp.caja.chica.tesoreria'].search([('id', '=', caja_id)])
            valores_custodia = self._get_valores_custodia(caja.transaction_ids.mapped('custody_id').ids)
            for node in doc.xpath("//field[@name='valores_custodia_ids']"):
                node.set('domain', "[('id','in'," + str(valores_custodia.ids) + ")]")
            for field in res['fields']:
                if field == 'valores_custodia_ids':
                    res['fields'][field]['domain'] = [
                        ('id', 'in', valores_custodia.ids)]
            res['arch'] = etree.tostring(doc)
        return res

    valores_custodia_ids = fields.Many2many('grp.valores_custodia', 'grp_caja_chicha_valores_custodia_wizard_rel',
                                            'custody_id', 'wizard_id', string=u'Valores en custodia en efectivo')
    caja_chica_id = fields.Many2one('grp.caja.chica.tesoreria', string='Caja chica', ondelete='cascade')

    @api.multi
    def transfer_account_voucher(self):
        valores_custodia = self.mapped('valores_custodia_ids')

        self.caja_chica_id.write({'transaction_ids': [(0, 0, {'custody_id': obj.id, 'ref': 'Valor en custodia',
                                                              'date': obj.fecha_entregado, 'partner_id': obj.partner_id.id,
                                                              'amount': obj.monto}) for obj in valores_custodia]})
        return True
