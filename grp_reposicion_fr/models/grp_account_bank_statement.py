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

from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp
import time

# TODO: SPRING 8 GAP 111.228.339 K
class grp_account_bank_statement_line(models.Model):
    _inherit = 'account.bank.statement.line'

    fondo_rotarios = fields.Boolean(string='En 3 en 1-Fondo rotatorio', default=False) # TODO: SPRING 8 GAP 111.228.339 K
    fondo_rotatorio_id = fields.Many2one('grp.fondo.rotatorio', string='Fondo rotatorio',
                                              compute='_compute_fondo_rotatorio_id')

    @api.multi
    def _compute_fondo_rotatorio_id(self):
        FR_Line = self.env['grp.fondo.rotatorio.line'].suspend_security()
        for rec in self:
            rec.fondo_rotatorio_id = FR_Line.search([('bank_statement_id', '=', rec.id)],
                                                         limit=1).fondo_rotatorios_id.id


# TODO: SPRING 8 GAP 111.228.339 K
class grp_account_bank_statement(models.Model):
    _inherit = 'account.bank.statement'

    # RAGU redefiniendo comportamiento del journal, sacando Desconocido
    @api.model
    def _default_journal_id(self):
        # return self.env['account.journal'].search(
        #     [('type', '=', 'purchase'), '|', ('currency', '=', self.env.user.company_id.currency_id.id),
        #      ('currency', '=', False)], limit=1).id or self.env['account.journal']
        return False

    journal_id = fields.Many2one('account.journal', string=u'Diario', required=True,
                                 default=_default_journal_id)

    def button_cancel(self, cr, uid, ids, context):
        bank_statements_line_obj = self.pool.get('account.bank.statement.line')
        for id in ids:
            bank_statements_line_ids =bank_statements_line_obj.search(cr, uid, [('statement_id','=',id),('fondo_rotarios','=',True)])
            if len(bank_statements_line_ids) > 0:
                raise exceptions.ValidationError(u'No puede cancelar un registro de caja incluido en un 3 en 1.')
        return super(grp_account_bank_statement, self).button_cancel(cr, uid, ids, context)

class GrpCajaChicaTesoreriaLine(models.Model):
    _inherit = 'grp.caja.chica.tesoreria.line'

    fondo_rotario = fields.Boolean(string='En 3 en 1')
    fondo_rotatorio_id = fields.Many2one('grp.fondo.rotatorio', string='Fondo rotatorio',
                                         compute='_compute_fondo_rotatorio_id')

    @api.multi
    def _compute_fondo_rotatorio_id(self):
        FR_Line = self.env['grp.fondo.rotatorio.line'].suspend_security()
        for rec in self:
            rec.fondo_rotatorio_id = FR_Line.search([('caja_chica_line_id', '=', rec.id)],
                                                    limit=1).fondo_rotatorios_id.id

class GrpCajaChicaTesoreria(models.Model):
    _inherit = 'grp.caja.chica.tesoreria'

    @api.multi
    def button_cancel(self):
        for rec in self:
            for line in rec.transaction_ids:
                if line.fondo_rotario:
                    raise exceptions.ValidationError(u'No puede cancelar una caja con registros incluidos en un 3 en 1.')
        return super(GrpCajaChicaTesoreria, self).button_cancel()
