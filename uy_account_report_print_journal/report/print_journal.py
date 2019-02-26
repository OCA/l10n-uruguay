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

from openerp.addons.account_financial_report_webkit.report.webkit_parser_header_fix \
    import HeaderFooterTextWebKitParser
from openerp.addons.account_financial_report_webkit.report.print_journal \
    import PrintJournalWebkit
from openerp.tools.translate import _

class PrintJournalWebkitExt(PrintJournalWebkit):

    def set_context(self, objects, data, ids, report_type=None):
        result = super(PrintJournalWebkitExt, self).set_context(objects, data, ids, report_type=report_type)
        gb_journal_period = data['form']['gb_journal_period']
        gb_period = data['form']['gb_period']
        order_period = data['form']['order_period']
        self.localcontext.update({
            'gb_journal_period': gb_journal_period,
            'gb_period': gb_period,
            'get_line_reference': self.get_line_reference,
        })

        moves = self.localcontext['moves']
        new_moves = {}
        if gb_journal_period:
            for key,value in moves.items():
                if value:
                    new_moves[key] = value
            self.localcontext.update({'moves': new_moves})
        else:
            account_period_obj = self.pool.get('account.period')
            start_period = self.get_start_period_br(data)
            stop_period = self.get_end_period_br(data)
            period_ids = account_period_obj.build_ctx_periods(self.cursor,
                                                              self.uid,
                                                              start_period.id,
                                                              stop_period.id)
            if gb_period:
                # Sort periods by date start
                period_ids = account_period_obj.search(self.cursor, self.uid, [('id','in',period_ids)], order=("date_start " + order_period))
                objects = account_period_obj.browse(self.cursor, self.uid, period_ids)

                move_ids = [ m.id for k,v in moves.items() for m in v]
                domain_arg = [('id','in',move_ids)]
                move_obj = self.pool.get('account.move')
                for period in objects:
                    new_move_ids = move_obj.search(self.cursor, self.uid, domain_arg + [('period_id', '=', period.id)], order="date")
                    if new_move_ids:
                        new_moves[period.id] = move_obj.browse(self.cursor, self.uid, new_move_ids)
                        # Sort account move line by date and account
                        for move in new_moves[period.id]:
                            move.line_id.sorted(key=lambda a: (a.date, a.account_id.code))
            else:
                if period_ids:
                    # send only one object, does'nt matter what
                    objects = account_period_obj.browse(self.cursor, self.uid, period_ids[0])
                    for period in list(objects):
                        all_moves = None
                        for val in moves.values():
                            if not all_moves:
                                all_moves = val
                            else:
                                all_moves |= val
                        all_moves.sorted(key=lambda a: a.date)
                        new_moves[period.id] = all_moves

            self.localcontext.update({'moves': new_moves})
            return super(PrintJournalWebkit, self).set_context(objects, data, ids, report_type=report_type)

        return result

    def get_line_reference(self, line):
        # TODO: Create a computed field in account.move.line ??
        ref_line = False
        move_id = line.move_id and line.move_id.id or -1
        invoice_obj = self.pool.get('account.invoice')
        invoice_ids = invoice_obj.search(self.cursor, self.uid, [('move_id','=',move_id)])
        invoice = invoice_ids and invoice_obj.browse(self.cursor, self.uid, invoice_ids[0]) or False
        if invoice: # Check for invoice
            if invoice.type == 'out_invoice':
                ref_line = _("Customer invoice")+ " " + (invoice.number or '')
            elif invoice.type == 'out_refund':
                ref_line = _("Customer refund")+ " " + (invoice.number or '')
            elif invoice.type == 'in_invoice':
                ref_line = _("Supplier invoice")+ " " + (invoice.supplier_invoice_number or (invoice.number or ''))
            elif invoice.type == 'in_refund':
                ref_line = _("Supplier refund")+ " " + (invoice.supplier_invoice_number or (invoice.number or ''))
        if not ref_line: # check for voucher
            voucher_obj = self.pool.get('account.voucher')
            voucher_ids = voucher_obj.search(self.cursor, self.uid, [('move_id','=',move_id)])
            voucher = voucher_ids and voucher_obj.browse(self.cursor, self.uid, voucher_ids[0]) or False
            if voucher:
                if voucher.journal_id.type in ['bank','cash'] and voucher.type=='receipt':
                    ref_line = "Pago Cliente %s" % (voucher.number or voucher.reference)
                if voucher.journal_id.type in ['bank','cash'] and voucher.type=='payment':
                    ref_line = "Pago Proveedor %s" % (voucher.number or voucher.reference)
                if voucher.journal_id.type in ['sale','sale_refund'] and voucher.type=='sale':
                    ref_line = "Recibo de venta %s" % (voucher.number or voucher.reference)
                if voucher.journal_id.type in ['purchase','purchase_refund'] and voucher.type=='purchase':
                    ref_line = "Recibo de compra %s" % (voucher.number or voucher.reference)
        if not ref_line: # check for origin of POS orders
            try:
                if hasattr(line, 'pos_order_ids_char'): # addon uy_account_report_general_ledger is installed
                    pos_order_obj = self.pool.get('pos.order')
                    ref_pos_ids = line.pos_order_ids_char
                    if ref_pos_ids:
                        pos_nbrs = []
                        po_ids = ref_pos_ids.split(",")
                        for ref_order in pos_order_obj.read(self.cursor, self.uid, [int(x) for x in po_ids], ['pos_reference']):
                            if ref_order['pos_reference']:
                                arr = ref_order['pos_reference'].split(" ")
                                nbr = len(arr)>=2 and arr[1] or False
                                if nbr:
                                    pos_nbrs.append(nbr)
                        if pos_nbrs:
                            pos_nbrs.reverse()
                            ref_line = "%s" % ((len(pos_nbrs)==1 and _('POS Order') or _('POS Orders')) + ' ' + ', '.join(pos_nbrs))
                    else:
                        if line.name and line.name.find(":") != -1:
                            n = line.name.split(":")[0]
                            if n:
                                po_ids = pos_order_obj.search(self.cursor, self.uid, [('name','=',n)])
                                if po_ids:
                                    ref_order = pos_order_obj.read(self.cursor, self.uid, po_ids[0], ['pos_reference'])['pos_reference']
                                    ref_line = "%s" % (ref_order and (_('POS') + ' ' + ref_order +  (line.statement_id and ' (Pago)' or '')) or '')
            except: #ignore
                pass

        if not ref_line:
            ref_line = line.ref or ''

        return ref_line


HeaderFooterTextWebKitParser(
    'report.account.account_report_print_journal_webkit_ext',
    'account.journal.period',
    'addons/uy_account_report_print_journal/report/account_report_print_journal.mako',
    parser=PrintJournalWebkitExt)
