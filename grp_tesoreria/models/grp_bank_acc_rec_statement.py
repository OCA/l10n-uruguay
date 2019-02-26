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

from openerp import models, fields, exceptions
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp import models, api

import logging
_logger = logging.getLogger(__name__)

class BankAccRecStatementLineTesoreriaInh(models.Model):
    _inherit = 'bank.acc.rec.statement.line'

    deleted = fields.Boolean(
        string=u'Linea eliminada',
        default=False
    )

    # MVARELA 19/02/2016 : Error al intentar borrar linea sin asiento
    @api.multi
    def unlink(self):
        account_move_line_obj = self.env['account.move.line']
        move_line_ids = []
        for statement_line in self:
            if not statement_line.deleted and statement_line.move_line_id:
                otros_statements_ids = self.search([('move_line_id', '=', statement_line.move_line_id.id),
                                                    ('deleted', '=', False),
                                                    ('id', '!=', statement_line.id)])
                if len(otros_statements_ids) == 0:
                    move_line_ids.append(statement_line.move_line_id.id)

        if move_line_ids:
            # Reset field values in move lines to be added later
            account_move_line_obj.browse(move_line_ids).write({
                'draft_assigned_to_statement': False,
                'cleared_bank_account': False,
                'bank_acc_rec_statement_id': False,
            })
        return super(BankAccRecStatementLineTesoreriaInh, self).unlink()

    @api.model
    def create(self, vals):
        account_move_line_obj = self.env['account.move.line']
        # Prevent manually adding new statement line.
        # This would allow only onchange method to pre-populate statement lines based on the filter rules.
        if not vals.get('move_line_id', False):
            raise exceptions.ValidationError(_(u"You cannot add any new bank statement"
                                               u" line manually as of this revision!"))
        #MVARELA 10/11/2016: Las eliminadas no se marcan como asignadas a un extracto
        if not vals.get('deleted', False):
            account_move_line_obj.browse([vals['move_line_id']]).write({'draft_assigned_to_statement': True})
        return super(BankAccRecStatementLineTesoreriaInh, self).create(vals)


class BankAccRecStatementTesoreriaInh(models.Model):
    _inherit = 'bank.acc.rec.statement'

    @api.constrains('journal_id')
    def check_statement(self):
        for rec in self:
            statements = self.search([('journal_id', '=', rec.journal_id.id), ('id', '<>', rec.id),
                                      ('state', 'in', ['draft'])])
            if len(statements) > 0:
                raise exceptions.ValidationError(_(u'Error! Ya existe una conciliacion anterior para el mismo diario'
                                                   u' en estado Borrador.'))

    @api.multi
    def check_difference_balance(self):
        "Check if difference balance is zero or not."
        for statement in self:
            if statement.difference != 0.0 and not statement.justificacion_part:
                raise exceptions.ValidationError(_(u"Existe diferencia con el saldo conciliado"
                                                   u" debe conciliarla o ingresar"
                                                   u" la explicación de partidas conciliatorias"
                                                   u" en el campo \"Justificación"
                                                   u" de partidas conciliatorias\""))
        return True

    @api.multi
    @api.depends('credit_move_line_ids', 'debit_move_line_ids')
    def _get_balance(self):
        """Computed as following:
        A) Deposits, Credits, and Interest Amount: Total SUM of Amts of lines with Cleared = True
        Deposits, Credits, and Interest # of Items: Total of number of lines with Cleared = True
        B) Checks, Withdrawals, Debits, and Service Charges Amount:
        Checks, Withdrawals, Debits, and Service Charges Amount # of Items:
        Cleared Balance (Total Sum of the Deposit Amount Cleared (A) – Total Sum of Checks Amount Cleared (B))
        Difference= (Ending Balance – Beginning Balance) - cleared balance = should be zero.
        """
        res = {}
        account_precision = self.env['decimal.precision'].precision_get('Account')
        for statement in self:
            if isinstance(statement.id, int):
                for line in statement.credit_move_line_ids:
                    statement.sum_of_credits += line.cleared_bank_account and\
                                                           round(line.amount, account_precision) or 0.0
                    statement.sum_of_credits_lines += line.cleared_bank_account and 1.0 or 0.0
                for line in statement.debit_move_line_ids:
                    statement.sum_of_debits += line.cleared_bank_account and\
                                                          round(line.amount, account_precision) or 0.0
                    statement.sum_of_debits_lines += line.cleared_bank_account and 1.0 or 0.0
                statement.cleared_balance = round(statement.sum_of_debits
                                                             - statement.sum_of_credits, account_precision)
                acc_rec_obj = self.search([('account_id', '=', statement.account_id.id),
                                           ('id', '<', statement.id)], order="id desc", limit=1)
                if acc_rec_obj:
                    amount = acc_rec_obj and acc_rec_obj.difference or 0.0
                    if amount > 0:
                        statement.part_conciliatorias = abs(amount)
                    elif amount < 0:
                        statement.part_conciliatorias = -abs(amount)
                    else:
                        statement.part_conciliatorias = 0.0
                else:
                    statement.part_conciliatorias = 0.0
                account_precision = self.env['decimal.precision'].precision_get('Account')
                statement.difference = round(statement.part_conciliatorias
                                                        + (statement.ending_balance - statement.starting_balance)
                                                        - statement.cleared_balance, account_precision)
        return res

    #MVARELA 24/06/2016 - Se sobrescribe el metod refresh_record, antes no hacia nada
    @api.multi
    def refresh_record(self):
        account_move_line_obj = self.env["account.move.line"]
        for obj in self:
            if not obj.account_id:
                continue
            #PCAR 20 10 2016 se vuelven para atras las lineas eliminadas de la conciliacion al refrescar
            deleted_line_ids = [
                line.id
                for line in obj.unlink_debit_move_line_ids + obj.unlink_credit_move_line_ids
            ]

            if deleted_line_ids:
                self.env['bank.acc.rec.statement.line'].browse(deleted_line_ids).write({'deleted': False})
                deleted_move_ids = []
                for line in obj.unlink_debit_move_line_ids + obj.unlink_credit_move_line_ids:
                    if line.move_line_id.id not in deleted_move_ids:
                        deleted_move_ids.append(line.move_line_id.id)
                account_move_line_obj.browse(deleted_move_ids).write({'draft_assigned_to_statement': True})
            # fin

            to_write = {'credit_move_line_ids': [], 'debit_move_line_ids': []}
            move_line_ids = [
                line.move_line_id.id
                for line in obj.credit_move_line_ids + obj.debit_move_line_ids
                if line.move_line_id
                ]

            domain = [
                ('id', 'not in', move_line_ids),
                ('account_id', '=', obj.account_id.id),
                ('move_id.state', '=', 'posted'),
                ('cleared_bank_account', '=', False),
            ]

            domain += [('draft_assigned_to_statement', '=', False)]

            if not obj.suppress_ending_date_filter:
                domain += [('date', '<=', obj.ending_date)]
            line_ids = account_move_line_obj.search(domain)
            for line in line_ids:
                type_crdr = ((line.credit >= 0) and not line.debit) and 'cr' or 'dr'
                if line.debit == 0.0 and line.credit == 0.0:
                    type_crdr = line.amount_currency > 0 and 'dr' or 'cr'
                res = {
                    'ref': line.ref,
                    'date': line.date,
                    'partner_id': line.partner_id.id,
                    'currency_id': line.currency_id.id,
                    'amount': line.credit or line.debit,
                    'name': line.name,
                    'move_line_id': line.id,
                    'type': type_crdr
                }
                val = (0, 0, res)
                if line.credit:
                    to_write['credit_move_line_ids'].append(val)
                else:
                    to_write['debit_move_line_ids'].append(val)

            obj.write(to_write)

        return True

    @api.multi
    def action_select_all(self):
        """Mark all the statement lines as 'Cleared'."""
        statement_line_obj = self.env['bank.acc.rec.statement.line']
        for statement in self:
            statement_lines = statement.credit_move_line_ids + statement.debit_move_line_ids
            statement_line_ids = map(lambda x: x.id, statement_lines)
            # statement_line_obj.write(statement_line_ids, {'cleared_bank_account': True})
            statement_line_obj.browse(statement_line_ids).write({'cleared_bank_account': True})
        return True

    @api.multi
    def action_cancel_draft(self):
        """Reset the statement to draft and perform resetting operations."""
        account_move_line_obj = self.env['account.move.line']
        statement_line_obj = self.env['bank.acc.rec.statement.line']
        for statement in self:
            statement_lines = statement.credit_move_line_ids + statement.debit_move_line_ids
            line_ids = []
            statement_line_ids = []
            for statement_line in statement_lines:
                statement_line_ids.append(statement_line.id)
                line_ids.append(statement_line.move_line_id.id)  # Find move lines related to statement lines

            # Reset 'Cleared' and 'Bank Acc Rec Statement ID' to False
            account_move_line_obj.browse(line_ids).write({
                'cleared_bank_account': False,
                'bank_acc_rec_statement_id': False,
            })
            # Reset 'Cleared' in statement lines
            statement_line_obj.browse(statement_line_ids).write({
                'cleared_bank_account': False,
                'research_required': False
            })
            # Reset statement
            self.browse([statement.id]).write({
                'state': 'draft',
                'verified_by_user_id': False,
                'verified_date': False
            })

        return True

    @api.onchange('account_id', 'ending_date', 'suppress_ending_date_filter')
    def onchange_account_id_2(self):
        account_move_line_obj = self.env['account.move.line']
        statement_line_obj = self.env['bank.acc.rec.statement.line']
        val = {'value': {'credit_move_line_ids': [], 'debit_move_line_ids': [], 'unlink_debit_move_line_ids': [],
                         'unlink_credit_move_line_ids': []}}
        if self.account_id:
            statement_line_ids = statement_line_obj.search([('statement_id', '=', self.id)])
            # call unlink method to reset and remove existing statement lines and
            # mark reset field values in related move lines
            # statement_line_obj.unlink(statement_line_ids)
            statement_line_ids.unlink()

            # Apply filter on move lines to allow
            #1. credit and debit side journal items in posted state of the selected GL account
            #2. Journal items which are not assigned to previous bank statements
            #3. Date less than or equal to ending date provided the 'Suppress Ending Date Filter' is not checkec
            domain = [('account_id', '=', self.account_id.id), ('move_id.state', '=', 'posted'),
                      ('cleared_bank_account', '=', False), ('draft_assigned_to_statement', '=', False)]
            if not self.suppress_ending_date_filter:
                domain += [('date', '<=', self.ending_date)]
            line_ids = account_move_line_obj.search(domain)
            lista_cr = []
            lista_dr = []
            for line in line_ids:
                #INICIO 002 - Para lo movimientos con debito y credito en moneda base
                #  igual a 0, se mira el monto en moneda divisa
                type_crdr = ((line.credit >= 0) and not line.debit) and 'cr' or 'dr'
                if line.debit == 0.0 and line.credit == 0.0:
                    type_crdr = line.amount_currency > 0 and 'dr' or 'cr'
                #FIN 002
                res = {
                       'ref': line.ref,
                       'date': line.date,
                       'partner_id': line.partner_id.id,
                       'currency_id': line.currency_id.id,
                       'amount': line.credit or line.debit,
                       'name': line.name,
                       'move_line_id': line.id,
                       #INICIO 002
                       'type': type_crdr,
                       #FIN 002
                }

                if res['type'] == 'cr':
                    lista_cr.append(res)
                    # self.credit_move_line_ids.new(res)
                else:
                    lista_dr.append(res)
                    # self.debit_move_line_ids.new(res)
            self.credit_move_line_ids = lista_cr
            self.debit_move_line_ids = lista_dr

    # Columns
    cleared_balance = fields.Float(
        string=u'Cleared Balance',
        digits_compute=dp.get_precision('Account'),
        compute='_get_balance'
    )

    difference = fields.Float(
        string=u'Difference',
        digits_compute=dp.get_precision('Account'),
        compute='_get_balance'
    )

    sum_of_credits = fields.Float(
        string=u'Checks, Withdrawals, Debits, and Service Charges Amount',
        digits_compute=dp.get_precision('Account'),
        compute='_get_balance'
    )

    sum_of_debits = fields.Float(
        string=u'Deposits, Credits, and Interest Amount',
        digits_compute=dp.get_precision('Account'),
        compute='_get_balance'
    )

    sum_of_credits_lines = fields.Float(
        string=u'Checks, Withdrawals, Debits, and Service Charges',
        digits_compute=dp.get_precision('Account'),
        compute='_get_balance'
    )

    sum_of_debits_lines = fields.Float(
        string=u'Deposits, Credits, and Interest',
        digits_compute=dp.get_precision('Account'),
        compute='_get_balance'
    )

    justificacion_part = fields.Text(
        string=u'Justificación de partidas conciliatorias',
    )

    part_conciliatorias = fields.Float(
        string=u'Partidas conciliatorias',
        digits_compute=dp.get_precision('Account'),
        compute='_get_balance'
    )

    credit_move_line_ids = fields.One2many(
        string=u'Credits',
        comodel_name=u'bank.acc.rec.statement.line',
        inverse_name=u'statement_id',
        domain=[('type', '=', 'cr'), ('deleted', '=', False)],
        context={'default_type': 'cr'},
        states={'done': [('readonly', True)]}
    )

    debit_move_line_ids = fields.One2many(
        string=u'Debits',
        comodel_name=u'bank.acc.rec.statement.line',
        inverse_name=u'statement_id',
        domain=[('type', '=', 'dr'), ('deleted', '=', False)],
        context={'default_type': 'dr'},
        states={'done': [('readonly', True)]}
    )

    unlink_debit_move_line_ids = fields.One2many(
        string=u'Partidas pendientes de banco débito',
        comodel_name=u'bank.acc.rec.statement.line',
        inverse_name=u'statement_id',
        domain=[('type', '=', 'dr'), ('deleted', '=', True)],
    )

    unlink_credit_move_line_ids = fields.One2many(
        string=u'Partidas pendientes de banco crédito',
        comodel_name=u'bank.acc.rec.statement.line',
        inverse_name=u'statement_id',
        domain=[('type', '=', 'cr'), ('deleted', '=', True)],
    )

    @api.model
    def create(self, vals):
        statement = super(BankAccRecStatementTesoreriaInh, self).create(vals)
        # statement = self.browse(id_creado)

        account_move_line_obj = self.env['account.move.line']
        statement_line_obj = self.env['bank.acc.rec.statement.line']
        val = {'value': {'credit_move_line_ids': [], 'debit_move_line_ids': [], 'unlink_move_line_ids': []}}
        move_ids = []
        for credit in statement.credit_move_line_ids:
            if credit.move_line_id.id not in move_ids:
                move_ids.append(credit.move_line_id.id)
        for debit in statement.debit_move_line_ids:
            if debit.move_line_id.id not in move_ids:
                move_ids.append(debit.move_line_id.id)
        domain = [('account_id', '=', statement.account_id.id), ('move_id.state', '=', 'posted'),
                  ('cleared_bank_account', '=', False), ('draft_assigned_to_statement', '=', False),
                  ('id', 'not in', move_ids)]
        if not statement.suppress_ending_date_filter:
            domain += [('date', '<=', statement.ending_date)]
        line_ids = account_move_line_obj.search(domain)
        for line in line_ids:
            # INICIO 002 - Para lo movimientos con debito y credito en moneda base igual a 0, se mira el monto en moneda divisa
            type_crdr = ((line.credit >= 0) and not line.debit) and 'cr' or 'dr'
            if line.debit == 0.0 and line.credit == 0.0:
                type_crdr = line.amount_currency > 0 and 'dr' or 'cr'
            # FIN 002
            res = {
                'ref': line.ref,
                'date': line.date,
                'partner_id': line.partner_id.id,
                'currency_id': line.currency_id.id,
                'amount': line.credit or line.debit,
                'name': line.name,
                'move_line_id': line.id,
                # INICIO 002
                'type': type_crdr,
                # FIN 002
                'statement_id': statement.id,
                'deleted': True,
            }
            statement_line_obj.create(res)

        return statement

    @api.multi
    def action_review(self):
        for self_obj in self:
            for credit in self_obj.credit_move_line_ids:
                if not credit.cleared_bank_account:
                    raise exceptions.ValidationError(_(u'Tiene líneas sin conciliar.'
                                                       u' Debe eliminarlas o conciliarlas. '))
            for debit in self_obj.debit_move_line_ids:
                if not debit.cleared_bank_account:
                    raise exceptions.ValidationError(_(u'Tiene líneas sin conciliar.'
                                                       u' Debe eliminarlas o conciliarlas. '))
        return super(BankAccRecStatementTesoreriaInh, self).action_review()

    @api.multi
    def write(self, vals):
        _logger.info("WRITE CONCILIACION VALS: %s", vals)
        super(BankAccRecStatementTesoreriaInh, self).write(vals)
        if 'credit_move_line_ids' in vals or 'debit_move_line_ids' in vals or\
                        'unlink_debit_move_line_ids' in vals or 'unlink_credit_move_line_ids' in vals:
            for statement in self:
                account_move_line_obj = self.env['account.move.line']
                statement_line_obj = self.env['bank.acc.rec.statement.line']
                val = {'value': {'credit_move_line_ids': [], 'debit_move_line_ids': [], 'unlink_move_line_ids': []}}
                move_ids = []
                for credit in statement.credit_move_line_ids:
                    if credit.move_line_id.id not in move_ids:
                        move_ids.append(credit.move_line_id.id)
                for debit in statement.debit_move_line_ids:
                    if debit.move_line_id.id not in move_ids:
                        move_ids.append(debit.move_line_id.id)
                #MVARELA 10/11/2016: Se toman en cuenta las lineas ya eliminadas para que no las duplique
                for deleted_debit in statement.unlink_debit_move_line_ids:
                    if deleted_debit.move_line_id.id not in move_ids:
                        move_ids.append(deleted_debit.move_line_id.id)
                for deleted_credit in statement.unlink_credit_move_line_ids:
                    if deleted_credit.move_line_id.id not in move_ids:
                        move_ids.append(deleted_credit.move_line_id.id)

                domain = [('account_id', '=', statement.account_id.id), ('move_id.state', '=', 'posted'),
                          ('cleared_bank_account', '=', False), ('draft_assigned_to_statement', '=', False),
                          ('id', 'not in', move_ids)]
                if not statement.suppress_ending_date_filter:
                    domain += [('date', '<=', statement.ending_date)]
                line_ids = account_move_line_obj.search(domain)
                for line in line_ids:
                    # INICIO 002 - Para lo movimientos con debito y credito en moneda base igual a 0, se mira el monto en moneda divisa
                    type_crdr = ((line.credit >= 0) and not line.debit) and 'cr' or 'dr'
                    if line.debit == 0.0 and line.credit == 0.0:
                        type_crdr = line.amount_currency > 0 and 'dr' or 'cr'
                    # FIN 002
                    res = {
                        'ref': line.ref,
                        'date': line.date,
                        'partner_id': line.partner_id.id,
                        'currency_id': line.currency_id.id,
                        'amount': line.credit or line.debit,
                        'name': line.name,
                        'move_line_id': line.id,
                        # INICIO 002
                        'type': type_crdr,
                        # FIN 002
                        'statement_id': statement.id,
                        'deleted': True,
                    }
                    statement_line_obj.create(res)
                    account_move_line_obj.browse([line.id]).write({'draft_assigned_to_statement': False})
        else:
            for statement in self:
                account_move_line_obj = self.env['account.move.line']
                statement_line_obj = self.env['bank.acc.rec.statement.line']
                val = {'value': {'credit_move_line_ids': [], 'debit_move_line_ids': [], 'unlink_move_line_ids': []}}
                move_ids = []
                for credit in statement.credit_move_line_ids:
                    if credit.move_line_id.id not in move_ids:
                        move_ids.append(credit.move_line_id.id)
                for debit in statement.debit_move_line_ids:
                    if debit.move_line_id.id not in move_ids:
                        move_ids.append(debit.move_line_id.id)
        return True

    @api.multi
    def unlink(self):
        "Reset the related account.move.line to be re-assigned later to statement."
        statement_line_obj = self.env['bank.acc.rec.statement.line']
        self.check_group()  # Check if the user is allowed to perform the action
        for statement in self:
            statement_lines = statement.credit_move_line_ids + statement.debit_move_line_ids
            statement_line_ids = map(lambda x: x.id, statement_lines)
            statement_line_obj.browse(statement_line_ids).unlink()  # call unlink method to reset
        return super(BankAccRecStatementTesoreriaInh, self).unlink()



