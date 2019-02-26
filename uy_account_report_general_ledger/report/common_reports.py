# -*- encoding: utf-8 -*-
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

from openerp.addons.account_financial_report_webkit.report.common_reports \
    import CommonReportHeaderWebkit


def change_get_move_line_datas():

    def _get_move_line_datas(self, move_line_ids,
                             order='l.date ASC, per.date_start ASC, \
                                 per.date_stop ASC, m.name ASC'):
        # Possible bang if move_line_ids is too long
        # We can not slice here as we have to do the sort.
        # If slice has to be done it means that we have to reorder in python
        # after all is finished. That quite crapy...
        # We have a defective desing here (mea culpa) that should be fixed
        #
        # TODO improve that by making a better domain or if not possible
        # by using python sort
        if not move_line_ids:
            return []
        if not isinstance(move_line_ids, list):
            move_line_ids = [move_line_ids]
        monster = """
SELECT l.id AS id,
            l.date AS ldate,
            j.code AS jcode ,
            j.type AS jtype,
            l.currency_id,
            l.account_id,
            l.amount_currency,
            l.ref AS lref,
            l.name AS lname,
            COALESCE(l.debit, 0.0) - COALESCE(l.credit, 0.0) AS balance,
            l.debit,
            l.credit,
            COALESCE(l.curr_debit, 0.0) - COALESCE(l.curr_credit, 0.0) AS curr_balance,
            l.curr_debit,
            l.curr_credit,
            l.period_id AS lperiod_id,
            per.code as period_code,
            per.special AS peropen,
            l.partner_id AS lpartner_id,
            p.name AS partner_name,
            m.name AS move_name,
            COALESCE(partialrec.name, fullrec.name, '') AS rec_name,
            COALESCE(partialrec.id, fullrec.id, NULL) AS rec_id,
            m.id AS move_id,
            c.name AS currency_code,
            i.id AS invoice_id,
            i.type AS invoice_type,
            i.number AS invoice_number,
            l.date_maturity
FROM account_move_line l
    JOIN account_move m on (l.move_id=m.id)
    LEFT JOIN res_currency c on (l.currency_id=c.id)
    LEFT JOIN account_move_reconcile partialrec
        on (l.reconcile_partial_id = partialrec.id)
    LEFT JOIN account_move_reconcile fullrec on (l.reconcile_id = fullrec.id)
    LEFT JOIN res_partner p on (l.partner_id=p.id)
    LEFT JOIN account_invoice i on (m.id =i.move_id)
    LEFT JOIN account_period per on (per.id=l.period_id)
    JOIN account_journal j on (l.journal_id=j.id)
    WHERE l.id in %s"""
        monster += (" ORDER BY %s" % (order,))
        try:
            self.cursor.execute(monster, (tuple(move_line_ids),))
            res = self.cursor.dictfetchall()
        except Exception:
            self.cursor.rollback()
            raise
        return res or []

    setattr(CommonReportHeaderWebkit, '_get_move_line_datas', _get_move_line_datas)


change_get_move_line_datas()
