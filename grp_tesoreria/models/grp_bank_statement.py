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

import datetime
import logging

# from openerp import models
from openerp.exceptions import ValidationError
from openerp.osv import osv, fields
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


#001- Inicio
class grp_account_journal(osv.osv):

    _inherit = "account.journal"
    _columns={
        'cuenta_analitica_id':fields.many2one('account.analytic.account',u'Cuenta analítica'),
        'users': fields.many2many('res.users', 'res_groups_users_rel_account_journal', 'gid', 'uid', 'Users'),
        'caja_viaticos': fields.boolean(u'Caja chica'),
        'caja_recaudadora': fields.boolean(u'Caja recaudadora'),# TODO: SPRING 10 GAP 474 M
        'caja_pagadora': fields.boolean(u'Caja pagadora'),# TODO: SPRING 10 GAP 474 M
        'caja_chica_t': fields.boolean(u'Caja chica Tesorería'),# TODO: SPRING 10 GAP 474 M
        'fondo_rotatorio': fields.boolean(u'Fondo rotatorio'),# TODO: SPRING 10 GAP 266 C
        'recaudacion_cta': fields.boolean(u'Dep. recaudación cta. org'),  # TODO: SPRING 11 GAP 292 M
    }

    # TODO: SPRING 11 GAP 292 M
    def _check_recaudacion_cta(self, cr, uid, ids, context=None):
        journal_ids = self.search(cr, uid, [('recaudacion_cta', '=', True)], context=context)
        if len(journal_ids) > 1:
            return False
        return True

    _default={
        'caja_viaticos': False,
        'caja_recaudadora': False,# TODO: SPRING 10 GAP 474 M
        'caja_pagadora': False,# TODO: SPRING 10 GAP 474 M
        'caja_chica_t': False,# TODO: SPRING 10 GAP 474 M
        'recaudacion_cta': False,# TODO: SPRING 11 GAP 292 M
    }

    # TODO: SPRING 10 GAP 474 M
    _constraints = [
        (_check_recaudacion_cta, u'Sólo puede existir un diario con la opción Dep. recaudación cta. org', ['recaudacion_cta']),
        ]


grp_account_journal()

class grp_res_users_journal(osv.osv):

    _inherit = "res.users"
    _columns={
        'journal_ids': fields.many2many('account.journal', 'res_groups_users_rel_account_journal', 'uid', 'gid', 'Lista de diarios'),
    }


grp_res_users_journal()
#001-Fin

class grp_extracto_bancario(osv.osv):
    _inherit = ['account.bank.statement','mail.thread']
    _name='account.bank.statement'

    def check_status_condition(self, cr, uid, state, journal_type='bank'):
        return state in ('draft','open','revisado')

    def _check_opening_balance(self):
        if self.journal_id.cash_control and self.balance_start != sum(self.opening_details_ids.mapped('subtotal_opening')):
            raise ValidationError(u'El total de la composición del Registro de caja debe ser igual al total del saldo inicial!')


    def button_open(self, cr, uid, ids, context=None):
        """ Changes statement state to Running.
        @return: True
        """
        obj_seq = self.pool.get('ir.sequence')
        if context is None:
            context = {}
        statement_pool = self.pool.get('account.bank.statement')
        for statement in statement_pool.browse(cr, uid, ids, context=context):
            statement._check_opening_balance()
            vals = {}
            if not self._user_allow(cr, uid, statement.id, context=context):
                raise osv.except_osv(_('Error!'), (_('You do not have rights to open this %s journal!') % (statement.journal_id.name, )))

            if statement.name and statement.name == '/':
                c = {'fiscalyear_id': statement.period_id.fiscalyear_id.id}
                if statement.journal_id.sequence_id:
                    st_number = obj_seq.next_by_id(cr, uid, statement.journal_id.sequence_id.id, context=c)
                else:
                    st_number = obj_seq.next_by_code(cr, uid, 'account.cash.statement', context=c)
                vals.update({
                    'name': st_number
                })

            vals.update({
                'state': 'open',
            })
            self.write(cr, uid, [statement.id], vals, context=context)
        return True

    def button_confirm_cash(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.journal_id.caja_viaticos != True:
                cr.execute(""" SELECT abl.amount as importe,
                                      cg.id as concepto_id
                               FROM account_bank_statement ab, account_bank_statement_line abl, grp_concepto_gasto_cc_viaticos cg
                               WHERE cg.a_rendir=True and abl.concepto_id is not null and ab.id=%s
                                     and ab.id = abl.statement_id and cg.id = abl.concepto_id """, (obj.id,))# TODO: SPRING 10 GAP 296 L
                for vals in cr.dictfetchall():
                    vals.update({'registro_caja_id': obj.id })
                    self.pool.get('grp_llave_presupuestal_registro_caja').create(cr, uid, vals, context)
        return super(grp_extracto_bancario, self).button_confirm_bank(cr, uid, ids, context=context)


    def _es_diario_control_efectivo(self, cr, uid, ids, name, args, context=None):
        result = {}
        cash_control=False
        for account_bank in self.browse(cr,uid,ids):
            if account_bank.journal_id:
                _logger.info('account_bank.journal_id %s',account_bank.journal_id)
                journal_id=self.pool.get('account.journal').browse(cr,uid,account_bank.journal_id.id)
                if journal_id.cash_control == True and account_bank.state in ('open'):
                    cash_control= True
        result[account_bank.id]= cash_control
        return result

    def _tiene_grupos_grp(self, cr, uid, ids, name, args, context=None):
        result = {}
        tiene=True
        for account_bank in self.browse(cr,uid,ids):
            if account_bank.journal_id:
                # tiene_grupo_contabilidad = self.pool.get('res.users').has_group(cr, uid, 'grp_tesoreria.group_grp_contabilidad_tesoreria')
                tiene_grupo_tesoreria = self.pool.get('res.users').has_group(cr, uid, 'grp_tesoreria.group_grp_tesoreria_interior')
                if tiene_grupo_tesoreria:
                    user= self.pool.get('res.users').browse(cr,uid,uid)
                    if account_bank.journal_id.id in [e.id for e in user.journal_ids]:
                        tiene=False
            result[account_bank.id]= tiene
        return result

    def _tiene_grupo_grp_tesoreria(self, cr, uid, ids, name, args, context=None):
        result = {}
        tiene=False
        account_journal_obj= self.pool.get('account.journal')
        for account_bank in self.browse(cr,uid,ids):
            if account_bank.journal_id:
                tiene_grupo = self.pool.get('res.users').has_group(cr, uid, 'grp_tesoreria.group_grp_tesoreria')
                if tiene_grupo:
                    tiene=True
            result[account_bank.id]= tiene
        return result

    # 005-Inicio
    def _get_control_revision(self, cr, uid, ids, name, arg, context=None):
        res = {}
        statement_pool = self.pool.get('account.bank.statement')
        for rec in self.browse(cr, uid, ids, context=context):
            cr.execute("""select max(ab.id)
             from account_bank_statement ab
             where ab.journal_id=%s and ab.id not in
             (select max (ab.id) from account_bank_statement ab where ab.journal_id = %s)""",
                       (rec.journal_id.id, rec.journal_id.id))
            resultado = False
            for r in cr.fetchall():
                resultado = True
                id_encontrado = r[0]
                if id_encontrado:
                    ultimo_registro_caja = statement_pool.browse(cr, uid, int(id_encontrado), context=context)
                    if ultimo_registro_caja.state not in ('confirm','revisado'):
                        res[rec.id] = True
                    else:
                        res[rec.id] = False
                else:
                    res[rec.id] = False
            if not resultado:
                res[rec.id] = False
        return res
    # 005-Fin

    # RAGU reabriendo en estado revisado
    def button_reopen(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'open'}, context=context)
        return True

    _columns={
        'state': fields.selection([
            ('draft','Borrador'),
            ('open',u'Abierto/a'),
            ('end','Cerrado'),
            ('revisado','Revisado'),
            ('confirm','Finalizado'),
            ],u'Estado',track_visibility='onchange'),
        'caja_viaticos':fields.related('journal_id','caja_viaticos',type='boolean',string='Diario de tipo caja viaticos?', readonly=True),
        'linea_llp_ids': fields.one2many('grp_llave_presupuestal_registro_caja', 'registro_caja_id', 'Lineas de llave presupuestal registro de caja'),
        'es_diario_control_efectivo': fields.function(_es_diario_control_efectivo, string='Es diario control efectivo?',type='boolean'),
        'tiene_grupos': fields.function(_tiene_grupos_grp,type='boolean', string='Tiene grupos?'),
        # 005-Inicio
        'control_revision': fields.function(_get_control_revision, type='boolean', string='Aplica control revision?'),
        # 005-Fin
    }


    _defaults={
        'es_diario_control_efectivo':False,
    }

    def _recompute_balance_end_real(self, cr, uid, id, journal_id, context=None):
        res = False
        if journal_id:
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
            if journal.with_last_closing_balance:
                cr.execute('SELECT balance_end_real \
                      FROM account_bank_statement \
                      WHERE journal_id = %s AND NOT state = %s AND id < %s\
                      ORDER BY date DESC,id DESC LIMIT 1', (journal_id, 'draft', id))
                res = cr.fetchone()
        return res and res[0] or 0.0

    # Corrigiendo error de ejecucion desconocido
    def create(self, cr, uid, vals, context=None):
        new_id = super(grp_extracto_bancario, self).create(cr, uid, vals, context=context)
        self.action_update_balance_start(cr, uid, [new_id], context)
        return new_id

    def write(self, cr, uid, ids, vals, context=None):
        to_return = super(grp_extracto_bancario, self).write(cr, uid, ids, vals, context=context)
        if vals.get('state') and vals['state'] == 'open':
            self.action_update_balance_start(cr,uid,ids,context)
        return to_return
    # 006-Fin



    def _check_balance_end(self):
        _balance_end = self.balance_start
        for line in self.line_ids:
            _balance_end += line.amount
        if _balance_end < 0:
            raise ValidationError(_("El 'Saldo teórico de cierre' no puede ser negativo!"))
        return True

    def action_cancelado(self, cr, uid, ids, context):

        absl_proxy = self.pool.get('account.bank.statement.line')

        for obj in self.browse(cr, uid, ids, context=context):
            obj._check_balance_end()
            if obj.difference == 0.0:
                continue
            elif obj.difference < 0.0:
                account = obj.journal_id.loss_account_id
                name = _('Loss')
                concepto_id= self.pool.get('grp_concepto_gasto_cc_viaticos').search(cr,uid,[('perdida_diferencia','=',True)])
                if not obj.journal_id.loss_account_id:
                    raise osv.except_osv(_('Error!'), _('There is no Loss Account on the journal %s.') % (obj.journal_id.name,))
            else: # obj.difference > 0.0
                account = obj.journal_id.profit_account_id
                name = _('Profit')
                concepto_id= self.pool.get('grp_concepto_gasto_cc_viaticos').search(cr,uid,[('ganancia_diferencia','=',True)])
                if not obj.journal_id.profit_account_id:
                    raise osv.except_osv(_('Error!'), _('There is no Profit Account on the journal %s.') % (obj.journal_id.name,))

            values = {
                'statement_id' : obj.id,
                'concepto_id': concepto_id[0] if concepto_id else False,
                'journal_id' : obj.journal_id.id,
                'account_id' : account.id,
                'amount' : obj.difference,
                'name' : name,
            }
            absl_proxy.create(cr, uid, values, context=context)
        return self.write(cr, uid, ids, {'state':'end'}, context=context)

    def action_revisado(self, cr, uid, ids, context):
        return self.write(cr, uid, ids, {'state':'revisado'}, context=context)

    def action_abrir(self, cr, uid, ids, context):
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)

    # TODO: SPRING 10 GAP 493 C
    def button_cancel(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state == 'confirm':
                move_ids = [line.journal_entry_id.id for line in obj.line_ids if line.journal_entry_id]
                if len(move_ids):
                    period = self.pool.get('account.period').find(cr, uid, datetime.datetime.today())
                    self.pool.get('account.move').create_reversals(cr, uid, move_ids, datetime.datetime.today(),
                                                                   reversal_period_id=period[0] if len(period) else False)
                    obj.line_ids.write({'journal_entry_id': False})
                obj.linea_llp_ids.unlink()
        return super(grp_extracto_bancario, self).button_cancel(cr, uid, ids, context=context)

    # TODO: SPRING 10 GAP 493 C
    def button_draft(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state == 'confirm':
                move_ids = [line.journal_entry_id.id for line in obj.line_ids if line.journal_entry_id]
                if len(move_ids):
                    period = self.pool.get('account.period').find(cr, uid, datetime.datetime.today())
                    self.pool.get('account.move').create_reversals(cr, uid, move_ids, datetime.datetime.today(),
                                                                   reversal_period_id=period[0] if len(period) else False)
        return super(grp_extracto_bancario, self).button_draft(cr, uid, ids, context=context)

    # RAGU actualizar saldo inicial
    # revisar, se tuvo que hacer un sql porque un trigger de la vieja api odoo core estaba desbaratando el resultado del ORM
    def action_update_balance_start(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            cr.execute('UPDATE account_bank_statement SET balance_start = %s WHERE id = %s' % (self._recompute_balance_end_real(cr, uid,rec.id, rec.journal_id.id, context=context),rec.id))
        self.invalidate_cache(cr, uid, ids=ids) # clear cache in order to update recorsets

    def _get_cash_open_box_lines(self, cr, uid, journal_id, context):
        details_ids = []
        if not journal_id:
            return details_ids
        journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
        if journal and (journal.type == 'cash'):
            last_pieces = None

            if journal.with_last_closing_balance == True:
                domain = [('journal_id', '=', journal.id),
                          ('state', 'in', ['confirm','revisado','end'])]
                last_bank_statement_ids = self.search(cr, uid, domain, limit=1, order='create_date desc', context=context)
                if last_bank_statement_ids:
                    last_bank_statement = self.browse(cr, uid, last_bank_statement_ids[0], context=context)

                    last_pieces = dict(
                        (line.pieces, line.number_closing) for line in last_bank_statement.details_ids
                    )
            for value in journal.cashbox_line_ids:
                nested_values = {
                    'number_closing' : 0,
                    'number_opening' : last_pieces.get(value.pieces, 0) if isinstance(last_pieces, dict) else 0,
                    'pieces' : value.pieces
                }
                details_ids.append([0, False, nested_values])
        return details_ids


grp_extracto_bancario()
#003 y 004-Fin

class grp_llave_presupuestal_registro_caja(osv.osv):
    _name='grp_llave_presupuestal_registro_caja'

    def _compute_journal_id(self, cr, uid, ids, name, args, context=None):
        result = {}
        for row in self.browse(cr, uid, ids, context=context):
            if row.registro_caja_id:
                result[row.id] = row.registro_caja_id.journal_id and row.registro_caja_id.journal_id.id or False
            elif row.caja_chica_id:
                result[row.id] = row.caja_chica_id.journal_id and row.caja_chica_id.journal_id.id or False
            else:
                result[row.id] = False
        return result

    _columns = {
        'registro_caja_id': fields.many2one('account.bank.statement', 'Registro de caja'),
        'caja_chica_id': fields.many2one('grp.caja.chica.tesoreria', 'Caja chica'),
        'concepto_id': fields.many2one('grp_concepto_gasto_cc_viaticos', 'Concepto', ondelete='restrict'),
        #'inciso_siif_id': fields.related('concepto_id','inciso_siif_id',type='many2one',relation='grp.estruc_pres.inciso', string='Inciso',store=True),
        #'journal_id': fields.related('registro_caja_id','journal_id',type='many2one',relation='account.journal', string='Diario',store=True),# TODO: SPRING 10 GAP 296 L
        'journal_id': fields.function(_compute_journal_id, type='many2one', relation='account.journal', string='Diario', store=True),
        #'ue_siif_id': fields.related('journal_id','operating_unit',type='many2one',relation='operating.unit', string='Unidad ejecutora',store=True),# TODO: SPRING 10 GAP 296 L
        # llave presupuestal
        #'fin_id' : fields.related ('concepto_id','fin_id',type='many2one',relation='grp.estruc_pres.ff', string='Fin',store=True),
        #'programa_id' : fields.related ('concepto_id','programa_id',type='many2one',relation='grp.estruc_pres.programa', string='Programa',store=True),
        'programa_id' : fields.related ('concepto_id', 'programa_id', type='char', string='Programa', store=True, readonly=True),
        #'proyecto_id' : fields.related ('concepto_id','proyecto_id',type='many2one',relation='grp.estruc_pres.proyecto', string='Proyecto',store=True),
        'proyecto_id' : fields.related ('concepto_id', 'proyecto_id', type='char', string='Proyecto', store=True, readonly=True),
        #'odg_id' : fields.related ('concepto_id','odg_id',type='many2one',relation='grp.estruc_pres.odg',string='ODG',store=True),
        'odg_id' : fields.related ('concepto_id', 'odg_id', type='char', string='ODG', store=True, readonly=True),
        #'auxiliar_id' : fields.related ('concepto_id','auxiliar_id',type='many2one',relation='grp.estruc_pres.aux', string='Auxiliar',store=True),
        'auxiliar_id' : fields.related ('concepto_id', 'auxiliar_id', type='char', string='Auxiliar', store=True, readonly=True),
        #'mon_id' : fields.related ('concepto_id','mon_id',type='many2one',relation='grp.estruc_pres.moneda', string='Mon',store=True),
        'mon_id' : fields.related ('concepto_id', 'mon_id', type='char', string='Mon', store=True, readonly=True),
        #'tc_id' : fields.related ('concepto_id','tc_id',type='many2one',relation='grp.estruc_pres.tc', string='TC',store=True),
        'tc_id' : fields.related ('concepto_id', 'tc_id', type='char', string='TC', store=True, readonly=True),
        'importe': fields.float('Importe'),

    }

grp_llave_presupuestal_registro_caja()

class grp_conciliacion_bancaria(osv.osv):
    _inherit='bank.acc.rec.statement'

    def onchange_journal_id(self, cr, uid, ids, journal_id, context=None):
        value = {}
        domain_ids=[]
        if journal_id:
            obj=self.pool.get('account.journal').browse(cr, uid, journal_id)
            value = {
                'account_id':obj.default_debit_account_id.id
            }
        else:
            value = {'account_id':False}
        return {'value': value}


    _columns={
        'journal_id': fields.many2one('account.journal', u'Diario', required=True, states={'done': [('readonly', True)]},),
        # esto esta causando un error de una constraint  revisar para quitar - ECHAVIANO 18/11
        # npg_bank_account_reconciliation
        'account_id': fields.related('journal_id','default_debit_account_id',string='Cuenta',type='many2one',relation='account.account',store=True, readonly=True),
    }


grp_conciliacion_bancaria()


class grp_registro_caja_linea(osv.osv):
    _inherit = 'account.bank.statement.line'
    _columns = {
        'concepto_id': fields.many2one('grp_concepto_gasto_cc_viaticos', 'Concepto', ondelete='restrict'),
        'state': fields.related('statement_id', 'state', type='selection',
                                selection=[
                                    ('draft', 'Borrador'),
                                    ('open', u'Abierto/a'),
                                    ('end', 'Cerrado'),
                                    ('revisado', 'Revisado'),
                                    ('confirm', 'Finalizado'),
                                ],
                                string=u'Estado', store=False, readonly=True)

    }

    def onchange_concepto_id(self, cr, uid, ids, concepto_id, context=None):
        value = {}
        if concepto_id:
            concepto = self.pool.get('grp_concepto_gasto_cc_viaticos').browse(cr, uid, concepto_id, context=context)
            value = {'account_id':concepto.cuenta_id.id}
        return {'value': value}

    def _check_linea(self, cr, uid, ids, context=None):
        for linea in self.browse(cr,uid,ids):
            if linea.ref and not linea.partner_id:
                lineas_ids = self.search(cr,uid,[('statement_id','=',linea.statement_id.id,),('date','=',linea.date),('ref','=',linea.ref),('name','=',linea.name),('amount','=',linea.amount),('partner_id','=',False)])
                if len(lineas_ids) > 1:
                    return False
            if not linea.ref and linea.partner_id:
                lineas_ids = self.search(cr,uid,[('statement_id','=',linea.statement_id.id,),('date','=',linea.date),('ref','=',False),('name','=',linea.name),('amount','=',linea.amount),('partner_id','=',linea.partner_id.id)])
                if len(lineas_ids) > 1:
                    return False
            if not linea.ref and not linea.partner_id:
                lineas_ids = self.search(cr,uid,[('statement_id','=',linea.statement_id.id,),('date','=',linea.date),('ref','=',False),('name','=',linea.name),('amount','=',linea.amount),('partner_id','=',False)])
                if len(lineas_ids) > 1:
                    return False
        return True

    _constraints = [(_check_linea,
        'No se puede ingresar dos veces la misma linea',
        ['date','name','ref','partner_id','amount'])]

    _sql_constraints = [
        ('sequence_linea_uniq', 'unique(statement_id,date,name,ref,partner_id,amount)', 'No se puede ingresar dos veces la misma linea')
    ]

    # 006-Inicio
    def create(self, cr, uid, vals, context=None):
        concepto_obj = self.pool.get('grp_concepto_gasto_cc_viaticos')
        if vals.get('concepto_id', False):
            concepto = concepto_obj.browse(cr, uid, vals['concepto_id'])
            if 'amount' in vals:
                amount = vals['amount']
                if amount == 0:
                    raise osv.except_osv(_(u'Error!'), _(u'No se deben ingresar importes nulos.'))
                if not concepto.otros:
                    if concepto.signo in ['pos']:
                        vals.update({'amount': abs(amount)})
                    else:
                        vals.update({'amount': -abs(amount)})
        return super(grp_registro_caja_linea, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        concepto_obj = self.pool.get('grp_concepto_gasto_cc_viaticos')
        if isinstance(ids, (int, long)):
            ids = [ids]
        super(grp_registro_caja_linea, self).write(cr, uid, ids, vals, context=context)
        for rec in self.browse(cr, uid, ids):
            if vals.get('concepto_id', False):
                conc_id = vals['concepto_id']
                concepto = concepto_obj.browse(cr, uid, conc_id)
            else:
                concepto = rec.concepto_id
            _amount = vals['amount'] if vals.get('amount', False) else rec.amount
            if _amount == 0:
                raise osv.except_osv(_(u'Error!'), _(u'No se deben ingresar importes nulos.'))
            if not concepto.otros:
                _amount = abs(_amount) if concepto.signo == 'pos' else -abs(_amount)
                if _amount != rec.amount and rec.state == 'revisado':
                    raise osv.except_osv(_(u'Error!'), _(u"No se puede cambiar a un concepto de otro signo si el Registro de Caja está 'Revisado'!"))
            super(osv.osv, self).write(cr, uid, rec.id, {'amount': _amount}, context)
        return True

grp_registro_caja_linea()

class grp_CashBoxIn(osv.osv):
    _inherit = 'cash.box.in'

    def run(self, cr, uid, ids, context=None):
        if context.get('active_model') == 'account.bank.statement' and context.get('active_ids') and self.pool.get(
                'account.bank.statement').search_count(cr, uid, [('id', 'in', context.get('active_ids')),
                                                                 ('state', '!=', 'open')]):
            raise ValidationError(_(u"La caja debe estar en estado Abierto para utilizar la opción de Poner dinero"))
        return super(grp_CashBoxIn, self).run(cr, uid, ids, context=context)

    def _compute_values_for_statement_line(self, cr, uid, box, record, context=None):
        if not record.journal_id.internal_account_id.id:
            raise osv.except_osv(_('Configuration Error'), _("You should have defined an 'Internal Transfer Account' in your cash register's journal!"))

        concepto_poner_dinero_id = self.pool.get('grp_concepto_gasto_cc_viaticos').search(cr,uid,[('poner_dinero','=',True)])
        if len(concepto_poner_dinero_id) >0:
            return {
                'statement_id': record.id,
                'journal_id': record.journal_id.id,
                'amount': box.amount or 0.0,
                'account_id': record.journal_id.internal_account_id.id,
                'ref': '%s' % (box.ref or ''),
                'name': 'Poner dinero',
                'concepto_id': concepto_poner_dinero_id[0]
            }
        else:
            raise osv.except_osv(_('Configuration Error'), _("No hay un concepto de ingreso en el sistema"))

grp_CashBoxIn()


class grp_CashBoxOut(osv.osv):
    _inherit = 'cash.box.out'

    def run(self, cr, uid, ids, context=None):
        if context.get('active_model') == 'account.bank.statement' and context.get('active_ids') and self.pool.get(
                'account.bank.statement').search_count(cr, uid, [('id', 'in', context.get('active_ids')),
                                                                 ('state', '!=', 'open')]):
            raise ValidationError(_(u"La caja debe estar en estado Abierto para utilizar la opción de Sacar dinero"))
        return super(grp_CashBoxOut, self).run(cr, uid, ids, context=context)

    def _compute_values_for_statement_line(self, cr, uid, box, record, context=None):
        if not record.journal_id.internal_account_id.id:
            raise osv.except_osv(_('Configuration Error'), _("You should have defined an 'Internal Transfer Account' in your cash register's journal!"))
        amount = box.amount or 0.0
        concepto_sacar_dinero_id = self.pool.get('grp_concepto_gasto_cc_viaticos').search(cr,uid,[('sacar_dinero','=',True)])
        if len(concepto_sacar_dinero_id) >0:
            return {
                'statement_id': record.id,
                'journal_id': record.journal_id.id,
                'amount': -amount if amount > 0.0 else amount,
                'account_id': record.journal_id.internal_account_id.id,
                'name': 'Sacar dinero',
                'concepto_id': concepto_sacar_dinero_id[0]
            }
        else:
            raise osv.except_osv(_('Configuration Error'), _(u"No hay un concepto de extracción en el sistema"))

grp_CashBoxOut()
