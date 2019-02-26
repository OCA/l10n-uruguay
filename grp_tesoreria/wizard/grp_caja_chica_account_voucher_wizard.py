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


# TODO: SPRING 10 GAP 474 C
class grpCajaChicaAccountVoucherWizard(models.TransientModel):
    _name = "grp.caja.chica.account.voucher.wizard"

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(grpCajaChicaAccountVoucherWizard, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                                            context=context,
                                                                            toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        if self._context is not None and 'default_caja_chica_id' in self._context:
            caja_id = self._context['default_caja_chica_id']
            caja = self.env['grp.caja.chica.tesoreria'].search([('id', '=', caja_id)])
            account_vouchers = self.env['account.voucher'].search([('state', '=', 'confirm'),
                                                                   ('id', 'not in',
                                                                    caja.transaction_ids.mapped('voucher_id').ids),
                                                                   ('journal_id.caja_chica_t', '=', True),
                                                                   ('journal_id.operating_unit_id', 'in',
                                                                    caja.box_id.operating_unit_ids.ids)
                                                                   ])
            if self.env.user.company_id.box_refund_in_selection == 'out_box':
                account_vouchers += self.env['account.voucher'].search([('state', '=', 'posted'),
                                                                        ('id', 'not in',
                                                                         caja.transaction_ids.mapped('voucher_id').ids),
                                                                        ('journal_id.type', '=', 'sale'),
                                                                        ('operating_unit_id', 'in',
                                                                         caja.box_id.operating_unit_ids.ids),
                                                                        '|', ('rendicion_viaticos_id', '!=', False),
                                                                        ('rendicion_anticipos_id', '!=', False)
                                                                        ])
            for field in res['fields']:
                if field == 'account_voucher_ids':
                    res['fields'][field]['domain'] = [
                        ('id', 'in', account_vouchers.filtered(lambda x: x.currency_id.id == caja.currency.id).ids)]
            res['arch'] = etree.tostring(doc)
        return res

    payment_date = fields.Date('Fecha de pago', default=lambda *a: fields.Date.today(), required=True)
    entry_date = fields.Date('Fecha de asiento', default=lambda *a: fields.Date.today(), required=True)
    account_voucher_ids = fields.Many2many('account.voucher', string=u'Pago a proveedores')
    caja_chica_id = fields.Many2one('grp.caja.chica.tesoreria', string='Caja chica', ondelete='cascade')

    @api.onchange('payment_date')
    def _onchange_payment_date(self):
        self.entry_date = self.payment_date

    @api.multi
    def transfer_account_voucher(self):
        self.ensure_one()
        vouchers = self.mapped('account_voucher_ids')
        out_voucher_ids = vouchers.filtered(lambda x: not x.rendicion_viaticos_id and not x.rendicion_anticipos_id)
        in_voucher_ids = vouchers.filtered(lambda x: x.rendicion_viaticos_id or x.rendicion_anticipos_id)

        vouchers.with_context({'in_cashbox': True}).proforma_voucher()
        in_voucher_ids.write(
            {'date': self.payment_date, 'entry_date': self.entry_date, 'in_cashbox': True, 'state': 'pagado'})
        out_voucher_ids.write({'date': self.payment_date, 'entry_date': self.entry_date})

        new_trasactions = [(0, 0, {'voucher_id': voucher.id, 'ref': self.is_vale_viatico(voucher),
                                   'account_move_id': voucher.move_id.id,
                                   'date': self.payment_date, 'entry_date': self.entry_date,
                                   'partner_id': voucher.partner_id.id,
                                   'amount': voucher.amount * -1}) for voucher in out_voucher_ids]
        new_trasactions.extend([(0, 0, {'voucher_id': voucher.id, 'ref': self.is_vale_viatico(voucher),
                                        'account_move_id': voucher.move_id.id,
                                        'date': self.payment_date, 'entry_date': self.entry_date,
                                        'partner_id': voucher.partner_id.id,
                                        'amount': voucher.amount}) for voucher in in_voucher_ids])

        self.caja_chica_id.write({'transaction_ids': new_trasactions})
        return True

    # TODO: C SPRING 12 GAP_301
    # RAGU: Seteando valores de ref para las lineas de la caja chica
    def is_vale_viatico(self, voucher):
        _vale_rec_name = False
        if voucher.rendicion_viaticos_id:
            _vale_rec_name = u'%s' % (voucher.rendicion_viaticos_id.name_get()[0][1])
        elif voucher.solicitud_viatico_id:
            _vale_rec_name = u'%s' % (voucher.solicitud_viatico_id.name_get()[0][1])
        elif voucher.rendicion_anticipos_id:
            _vale_rec_name = u'%s' % (voucher.rendicion_anticipos_id.name_get()[0][1])
        elif voucher.solicitud_anticipos_id:
            _vale_rec_name = u'%s' % (voucher.solicitud_anticipos_id.name_get()[0][1])

        if not _vale_rec_name:
            vale = self.env['grp.vale.caja'].search(
                [('aprobacion_pago_id', '=', voucher.invoice_id.id)]) if voucher.invoice_id else False
            if vale:
                vale.write({'state': 'pagado'})
                _vale_rec_name = u'Vale(%s)' % (vale.number)
            s = set()
            for line_dr_id in voucher.line_dr_ids.filtered(lambda x: x.reconcile):
                if line_dr_id.move_line_id.invoice.supplier_invoice_number:
                    s.add(line_dr_id.move_line_id.invoice.supplier_invoice_number)
            s = list(s)
            if s:
                _vale_rec_name = u'Factura(%s)' % (', '.join(s))

        if not _vale_rec_name:
            _vale_rec_name = voucher.nro_documento and voucher.nro_documento.find(
                ', ') == -1 and voucher.nro_documento or voucher.number
        return _vale_rec_name
