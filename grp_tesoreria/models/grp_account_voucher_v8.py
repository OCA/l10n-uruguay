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
from openerp.exceptions import ValidationError
import openerp.addons.grp_account.models.grp_aprobacion_pagos as grp_aprobacion_pagos
from lxml import etree
from openerp.tools import float_round
from openerp import SUPERUSER_ID
import logging

# TODO: SPRING 10 GAP 266 C

class grp_account_voucher(models.Model):
    _inherit = 'account.voucher'

    # TODO: SPRING 11 GAP 292 M
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(grp_account_voucher, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                               context=context,
                                                               toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        if self._context.get('default_caja_recaudadora_id'):
            for node in doc.xpath("//field[@name='journal_id']"):
                node.set('domain', "[('id', '=', %s)]" % (self.env['grp.caja.recaudadora.tesoreria'].search(
                    [('id', '=', self._context.get('default_caja_recaudadora_id'))]).box_id.journal_id.id))
        elif self._context.get('opi'):
            operating_unit_ids = self.env.user.operating_unit_ids.ids
            operating_unit_ids.append(self.env.user.default_operating_unit_id.id)
            for node in doc.xpath("//field[@name='journal_id']"):
                node.set('domain', "[('type','in',['purchase'])]")
            for node in doc.xpath("//field[@name='operating_unit_id']"):
                node.set('domain', "[('id','in',%s)]" % (operating_unit_ids))

        elif self._context.get('invoice_type') and self._context.get('invoice_type') == 'out_invoice':
            for node in doc.xpath("//field[@name='journal_id']"):
                node.set('domain', "[('type','in',['bank'])]")
        res['arch'] = etree.tostring(doc)
        return res

    @api.one
    @api.depends('line_dr_ids.reconcile','line_dr_ids.move_line_id')
    def _compute_show_field_vc(self):
        if self.suspend_security().line_dr_ids.filtered(lambda x: x.reconcile and x.move_line_id.vc):
            self.show_field_vc = True
        else:
            self.show_field_vc = False


    payment_method = fields.Selection([('check', 'Cheque'), ('cash', 'Efectivo'), ('transfer', 'Transferencia')],
                                      string="Medio de pago", readonly=True,
                                      states={'draft': [('readonly', False)]})

    checkbook_id = fields.Many2one('grp.checkbook', string=u'Chequera', readonly=True,
                                   states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    serial = fields.Char(string=u'Serie', related='checkbook_id.serial', readonly=True)
    check_id = fields.Many2one('grp.checkbook.line', u'Cheque', readonly=True,
                               states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    state = fields.Selection([('draft', 'Borrador'),
                              ('confirm', 'Confirmado'),
                              ('issue', 'Emitido'),
                              ('proforma', 'Pro-forma'),
                              ('posted', 'Pago'),
                              ('cancel', 'Cancelado')
                              ])
    endorse = fields.Boolean('Endoso', default=False, readonly=True,
                             states={'issue': [('readonly', False)], 'posted': [('readonly', False)]})
    endorse_date = fields.Date('Fecha de endoso', readonly=True,
                               states={'issue': [('readonly', False)], 'posted': [('readonly', False)]})
    cancel_motive = fields.Char(string=u'Motivo de anulación', readonly=True, states={'cancel': [('readonly', False)]})
    show_motive = fields.Boolean(string=u'Mostrar motivo', default=False)

    caja_chica = fields.Boolean(string=u'Caja chica tesorería', related='journal_id.caja_chica_t', readonly=True)
    caja_recaudadora = fields.Boolean(string=u'Caja chica tesorería', related='journal_id.caja_recaudadora', readonly=True)
    no_operation = fields.Char(string=u'Nro. de Operación')
    serial = fields.Char(string=u'Serie', related='checkbook_id.serial', readonly=True)

    show_cancel_voucher = fields.Boolean(string=u'Mostrar botón', compute='_compute_show_cancel_voucher')
    show_change_voucher = fields.Boolean(string=u'Mostrar botón', compute='_compute_show_change_voucher')
    receipt_serial = fields.Char(string=u'Serie', size=10)  # TODO: SPRING 11 GAP 292 M
    # receipt_check = fields.Integer(string=u'Nº cheque')  # TODO: SPRING 11 GAP 292 M
    receipt_check = fields.Char(string=u'Nº cheque', size=20)
    check_date = fields.Date('Fecha cheque')  # TODO: M SPRING 11 GAP 292.A
    bank_id = fields.Many2one('res.bank', string=u'Banco')  # TODO: M SPRING 11 GAP 292.A
    # no_bank_account = fields.Integer(string=u'Nº cuenta bancaria')  # TODO: SPRING 11 GAP 292 M
    no_bank_account = fields.Char(string=u'Nº cuenta bancaria', size=20)
    # currency_id = fields.Many2one('res.currency', u'Divisa')  # TODO: SPRING 11 GAP 292 M
    check_amount = fields.Float(compute='_compute_check_amount', string=u'Monto cheque',
                                store=True)  # TODO: M SPRING 11 GAP 292.A

    caja_recaudadora_id = fields.Many2one('grp.caja.recaudadora.tesoreria',
                                          string=u'Caja recaudadora')  # TODO: SPRING 11 GAP 292 M
    # TODO: M INCIDENCIA 692
    payment_method_alert = fields.Boolean(u"Mostar alerta medio de pago", compute='_compute_payment_method_alert')
    show_warning = fields.Boolean(u"Mostar alerta", default=True)

    # TODO: SPRING 10 GAP 222 K
    pago_ret_sueldo = fields.Boolean(string=u'Pago retención de sueldo', default=False)
    no_recibo = fields.Char('Nro. Recibo', size=10)
    # RAGU alterando comportamiento
    in_cashbox = fields.Boolean(string=u'En caja', store=True)

    valor_custodia_id = fields.Many2one('grp.valores_custodia', string='Valor en custodia',
                                        readonly=True,
                                        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                        domain="[('state','=','entrega_autorizada'),('tipo_id.efectivo','=',True),('readonly','=',False),('partner_id','=',partner_id)]")
    show_field_vc = fields.Boolean(string='Mostrar campo VC', compute='_compute_show_field_vc')
    nro_documento = fields.Char(string=u'Nro. Documento', compute='_compute_nro_documento', compute_sudo=True, store=False)

    @api.one
    @api.depends('line_ids')
    def _compute_nro_documento(self):
        if self.line_ids:
            if isinstance(self.id, (int, long)):
                # asegurar que no ejecute la función en las líneas
                query = """
                    SELECT string_agg(l.supplier_invoice_number::text,', ')
                    FROM account_voucher_line l
                        inner join account_voucher v on (l.voucher_id=v.id)
                    WHERE v.id=%s and l.amount>0 and l.supplier_invoice_number is not null
                """
                self._cr.execute(query, (self.id,))
                res = self._cr.fetchone()
                self.nro_documento = res and res[0] or False
            else:
                self.nro_documento = ', '.join(filter(None, self.line_ids.filtered(lambda x: x.amount > 0).mapped('supplier_invoice_number')))

    @api.onchange('show_field_vc')
    def _onchange_show_field_vc(self):
        if not self.show_field_vc and self.state == 'draft':
            self.valor_custodia_id = False

    # TODO: SPRING 10 GAP 222 K
    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount,
                            currency_id, ttype, date, context=None):
        if context.get('pago_ret_sueldo', False):
            return self.onchange_pago_ret_sueldo(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date,
                                                 context.get('pago_ret_sueldo'), context=context)
        else:
            return super(grp_account_voucher, self).onchange_partner_id(
                cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype,
                date, context=context)

    # TODO: SPRING 10 GAP 222 K
    def onchange_pago_ret_sueldo(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date,
                                 pago_ret_sueldo=False, context=None):
        if not journal_id:
            return {}
        if context is None:
            context = {}
        # TODO: comment me and use me directly in the sales/purchases views
        res = {'value': {}}
        if pago_ret_sueldo:
            if ttype in ['sale', 'purchase']:
                return res
            ctx = context.copy()
            # not passing the payment_rate currency and the payment_rate in the context but it's ok because they are reset in recompute_payment_rate
            ctx.update({'date': date})
            ctx.update({'pago_ret_sueldo': pago_ret_sueldo})
            vals = self.recompute_voucher_lines(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date,
                                                context=ctx)
            vals2 = self.recompute_payment_rate(cr, uid, ids, vals, currency_id, date, ttype, journal_id, amount,
                                                context=context)
            for key in vals.keys():
                res[key].update(vals[key])
            for key in vals2.keys():
                res[key].update(vals2[key])
            if ttype == 'sale':
                del (res['value']['line_dr_ids'])
                del (res['value']['pre_line'])
                del (res['value']['payment_rate'])
            elif ttype == 'purchase':
                del (res['value']['line_cr_ids'])
                del (res['value']['pre_line'])
                del (res['value']['payment_rate'])
        else:
            res = self.onchange_partner_id(cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date,
                                           context)
        return res

    # RAGU limpiando chequeras
    def onchange_journal(self, cr, uid, ids, journal_id, line_ids, tax_id, partner_id, date, amount, ttype, company_id,
                         context=None):
        to_return = super(grp_account_voucher, self).onchange_journal(cr, uid, ids, journal_id, line_ids, tax_id,
                                                                      partner_id, date, amount, ttype, company_id,
                                                                      context=context)
        if context.get('default_opi') and isinstance(to_return,dict) and 'operating_unit_id' in to_return.get('value',{}):
            journal_currency_id = self.pool.get('account.journal').browse(cr,uid,journal_id,context=context).currency
            company_currency_id = self.pool.get('res.company').browse(cr,SUPERUSER_ID,company_id,context=context).currency_id
            if journal_currency_id and journal_currency_id.id != company_currency_id.id:
                to_return['value']['account_id'] = self.pool.get('res.partner').browse(cr,uid,partner_id,context=context).cuenta_a_pagar_me.id
            del to_return['value']['operating_unit_id']
        if to_return:
            to_return['value'].update({
                'checkbook_id': False,
                'check_id': False
            })
        return to_return

    # TODO: SPRING 10 GAP 222 K
    def _filter_voucher_lines_pr(self, line_ids, partner_id):
        line_retenciones_manuales = self.env['grp.lineas.retenciones.manuales']

        lines_filtered = [(5,)]
        line_retenciones_manuales_ids = line_retenciones_manuales.search(
            [('empresa','=',partner_id), ('retencion_manual_id.state', '=', 'aprobacion_pago'), ('pagado', '=', False),
             ('cheque_emitido', '=', False),
             ('resumen_id.cancelado', '=', False), ('resumen_id.move_id', '!=', False)])
        if line_retenciones_manuales_ids:
            move_line_id_rm = [x.id for x in
                               line_retenciones_manuales_ids.mapped('resumen_id').mapped('move_id').mapped(
                                   lambda x: x.line_id)]
            for line in line_ids:
                if isinstance(line, dict) and line['move_line_id'] in move_line_id_rm:
                    lines_filtered.append(line)
        return lines_filtered

    # TODO: SPRING 10 GAP 222 K
    def _filter_voucher_lines_not_pr(self, line_ids, ttype, partner_id):
        line_retenciones_manuales = self.env['grp.lineas.retenciones.manuales.resumen']

        lines_filtered = [(5,)]
        resumenes = line_retenciones_manuales.search([('empresa','=',partner_id), ('move_id', '!=', False)])
        if resumenes:
            move_line_id_rm = [x.id for x in resumenes.mapped('move_id').mapped(lambda x: x.line_id)]
            new_lines_filtered = (list(filter(lambda x: isinstance(x, dict) and x['move_line_id'] not in move_line_id_rm, line_ids)))
            # lines_filtered.extend(list(filter(lambda x: isinstance(x, dict) and x['move_line_id'] not in move_line_id_rm, line_ids)))
        else:
            new_lines_filtered = line_ids

        if ttype == 'receipt':
            # APUNTES YA INCLUIDOS EN DEVOLUCIONES EN CAJA
            move_line_ids = self.env['account.voucher'].search([('in_cashbox', '=', True), ('state', '=', 'pagado')]).mapped('move_ids').ids
            lines_filtered.extend(list(filter(lambda x: isinstance(x, dict) and x['move_line_id'] not in move_line_ids, new_lines_filtered)))
        else:
            lines_filtered = new_lines_filtered

        return lines_filtered

    # RAGU filtrando lineas en caso de caja recaudadora
    # def _filter_voucher_lines_cajarecaudadora(self, cajarecaudadora_id, line_ids):
    #     move_line_obj = self.env['account.move.line']
    #     #MVARELA: Se buscan todas las operating unit ya que se pueden pagar de otras
    #     operating_units = self.env['grp.caja.recaudadora.tesoreria'].sudo().search([('id','=',cajarecaudadora_id)], limit=1).box_id.operating_unit_ids.ids
    #     lines_filtered = [(5,)]
    #     for line in line_ids:
    #         if isinstance(line, dict) and move_line_obj.search([('id', '=', line['move_line_id'])], limit=1).operating_unit_id.id in operating_units:
    #             lines_filtered.append(line)
    #     return lines_filtered

    def _filter_voucher_lines_cajarecaudadora(self, cajarecaudadora_id, line_ids):
        move_line_obj = self.env['account.move.line']
        voucher_obj = self.env['account.voucher']
        operating_units = self.env['grp.caja.recaudadora.tesoreria'].sudo().search([('id','=',cajarecaudadora_id)], limit=1).box_id.operating_unit_ids.ids
        lines_filtered = [(5,)]
        origin_vouchers = []
        for line in line_ids:
            if isinstance(line, dict) and line['origin_voucher_id']:
                origin_vouchers.append(line['origin_voucher_id'])
        origin_voucher_ids = voucher_obj.search([('id','in',origin_vouchers)])
        for line in list(filter(lambda x: isinstance(x, dict), line_ids)):
            origin_voucher_id = origin_voucher_ids.filtered(lambda x: x.id == line['origin_voucher_id'])
            move_line = move_line_obj.suspend_security().search([('id', '=', line['move_line_id'])], limit=1)
            if move_line.operating_unit_id.id in operating_units:
                if self.env.user.company_id.box_refund_in_selection == 'out_box' and not origin_voucher_id.rendicion_viaticos_id and not origin_voucher_id.rendicion_anticipos_id:
                    lines_filtered.append(line)
                elif self.env.user.company_id.box_refund_in_selection == 'in_box':
                    lines_filtered.append(line)
        return lines_filtered


    # TODO: SPRING 10 GAP 222 K
    def onchange_line_ids_pr(self, cr, uid, ids, line_dr_ids, line_cr_ids, amount, voucher_currency, type,
                             pago_ret_sueldo, no_recibo, context=None):
        res = super(grp_account_voucher, self).onchange_line_ids(cr, uid, ids, line_dr_ids, line_cr_ids, amount,
                                                                 voucher_currency, type, context=context)
        move_line_pool = self.pool.get('account.move.line')
        line_retenciones_manuales = self.pool.get('grp.lineas.retenciones.manuales')

        if pago_ret_sueldo and (no_recibo == '' or not no_recibo) and len(line_dr_ids) > 0:
            no_recibo = False
            flag_no_recibo_dif = False
            for line_dr_id in line_dr_ids:
                if len(line_dr_id) < 3:
                    continue
                if line_dr_id[0] == 0 and line_dr_id[2] and len(line_dr_id[2]) > 0 and line_dr_id[2]['move_line_id'] and \
                        line_dr_id[2]['amount']:
                    line = move_line_pool.browse(cr, uid, line_dr_id[2]['move_line_id'], context=context)
                    line_retenciones_manuales_ids = line_retenciones_manuales.search(cr, uid, [
                        ('retencion_manual_id.state', '=', 'aprobacion_pago'),
                        ('resumen_id.move_id.id', '=', line.move_id.id),
                        ('resumen_id.cancelado', '=', False), ('importe', '=', line.credit or line.debit or 0.0),
                        ('operating_unit_id.id', '=', line.move_id.operating_unit_id.id)], context=context)
                    for line_retenciones_manuales_value in line_retenciones_manuales.browse(cr, uid,
                                                                                            line_retenciones_manuales_ids,
                                                                                            context=context):
                        if not line_retenciones_manuales_value.resumen_id.pagado and not line_retenciones_manuales_value.resumen_id.cheque_emitido and line_retenciones_manuales_value.resumen_id.no_recibo != '' and line_retenciones_manuales_value.resumen_id.no_recibo != False:
                            if not no_recibo:
                                no_recibo = line_retenciones_manuales_value.resumen_id.no_recibo
                            elif no_recibo != line_retenciones_manuales_value.resumen_id.no_recibo:
                                flag_no_recibo_dif = True
            if no_recibo and not flag_no_recibo_dif:
                res['value']['no_recibo'] = no_recibo
        return res

    @api.multi
    def _compute_show_cancel_voucher(self):
        for rec in self:
            _show_cancel_voucher = True
            if rec.payment_method == 'cash':
                caja_id = self.env['grp.caja.chica.tesoreria.line'].search([('voucher_id', '=', rec.id)], limit=1)
                if not (not caja_id or (caja_id and caja_id.state_caja in ['end', 'check'])):
                    _show_cancel_voucher = False
            elif rec.payment_method == 'check':
                caja_id = self.env['grp.caja.recaudadora.tesoreria.line'].search([('voucher_id', '=', rec.id)], limit=1)
                if not (not caja_id or (caja_id and caja_id.caja_recaudadora_id.state in ['close', 'checked'])):
                    _show_cancel_voucher = False
                caja_id = self.env['grp.caja.pagadora.tesoreria.line'].search([('voucher_id', '=', rec.id)], limit=1)
                if not (not caja_id or (caja_id and caja_id.payment_box_id.state in ['close', 'checked'])):
                    _show_cancel_voucher = False
            rec.show_cancel_voucher = _show_cancel_voucher

    @api.multi
    def _compute_show_change_voucher(self):
        for rec in self:
            _show_change_voucher = False
            if rec.payment_method == 'check':
                rec.show_change_voucher = False
                if not rec.check_id.in_cashbox:
                    _show_change_voucher = True
                else:
                    caja = self.env['grp.caja.pagadora.tesoreria.line'].search([('voucher_id', '=', rec.id)], limit=1)
                    _show_change_voucher = caja and caja.payment_box_id.state == 'open' or False
            rec.show_change_voucher = _show_change_voucher

    @api.multi
    def action_move_line_create(self):
        res = super(grp_account_voucher, self).action_move_line_create()
        for voucher in self:
            if voucher.state == 'posted' and voucher.valor_custodia_id:
                voucher.valor_custodia_id.write({ 'state': 'entrega_tesoreria', 'fecha_baja': fields.Date.today(),
                                                  'asiento_baja': voucher.move_id.id, 'diario_baja': voucher.move_id.journal_id.id })

        #     RAGU cambiado ref a asientos
            if voucher.caja_recaudadora_id:
                move_ids = self.env['account.move']
                move_ids += voucher.move_id
                move_ids += voucher.line_ids.filtered(lambda x: x.amount != 0).mapped('invoice_id.move_id')
                move_ids.write({'ref':voucher.caja_recaudadora_id.box_id.name_get()[0][1]})
        return res


    @api.onchange('checkbook_id')
    def onchange_checkbook_id(self):
        checks = self.checkbook_id.check_ids.filtered(lambda x: x.state == 'available' and not x.cancel_use).ids
        self.check_id = checks and checks[0] or False

    @api.onchange('caja_chica')
    def onchange_caja_chica(self):
        self.payment_method = False
        if self.caja_chica:
            self.payment_method = 'cash'

    @api.onchange('payment_method')
    def onchange_payment_method(self):
        if self.payment_method != 'check':
            self.check_id = False
            self.checkbook_id = False

    @api.onchange('no_operation')
    def onchange_no_operation(self):
        self.reference = self.no_operation

    def _check_values_dict(self, values):
        if self._context.get('opi') or self.opi:
            return True
        elif (self._context.get('default_caja_recaudadora_id') or self._context.get('caja_recaudadora_id')) and values.get('payment_method') == 'transfer':
            raise ValidationError(
                _("Un pago asociado a una Caja recaudadora no puede ser de tipo 'Transferencia'!"))
        elif self._context.get('invoice_type') and self._context.get('invoice_type') == 'out_invoice' and values.get('payment_method') != 'transfer':
            raise ValidationError(_("Un pago asociado a una Factura de cliente debe ser de tipo 'Transferencia'!"))
        return True

    @api.model
    def create(self, vals):
        if vals.get('check_id'):
            vals['reference'] = vals['check_id']
        res = super(grp_account_voucher, self).create(vals)
        if vals.get('valor_custodia_id', False):
            res.valor_custodia_id.write({'readonly': True})
        return res

    @api.multi
    def write(self, values):
        if values.get('check_id'):
            values['reference'] = values['check_id']
        if 'endorse_date' in values and values['endorse_date']:
            self.mapped('check_id').write({'check_date': values['endorse_date']})
        if values.get('state',False):
            self.change_state_caja_pagadora(values.get('state'))
        res = super(grp_account_voucher, self).write(values)
        if values.get('valor_custodia_id', False):
            for rec in self:
                rec.valor_custodia_id.write({'readonly': True})
        return res

    @api.multi
    def unlink(self):
        self.mapped(lambda x: x.valor_custodia_id).write({'readonly': False})
        super(grp_account_voucher, self).unlink()

    def change_state_caja_pagadora(self, state):
        for rec in self:
            caja_id = self.env['grp.caja.pagadora.tesoreria.line'].search([('voucher_id', '=', rec.id),('payment_box_id.state','not in', ['close', 'checked'])])
            if caja_id:
                caja_id.write({'state':state})

    # TODO: SPRING 10 GAP 222 K
    @api.multi
    def actualizar_retenciones_manuales(self, vals):
        line_retenciones_manuales = self.env['grp.lineas.retenciones.manuales']
        for voucher in self:
            if voucher.pago_ret_sueldo:
                for line in voucher.line_dr_ids:
                    if line.amount > 0:
                        line_retenciones_manuales_ids = line_retenciones_manuales.search(
                            [('retencion_manual_id.state', '=', 'aprobacion_pago'),
                             ('resumen_id.move_id.id', '=', line.move_line_id.move_id.id),
                             ('importe', '=', line.move_line_id.credit or line.move_line_id.debit or 0.0)])
                        for line_retenciones_manuales_value in line_retenciones_manuales_ids:
                            if vals.has_key('pagado'):
                                if vals.get('pagado', False):
                                    line_retenciones_manuales_value.write(vals)
                                    lines = line_retenciones_manuales.search(
                                        [('resumen_id', '=', line_retenciones_manuales_value.resumen_id.id),
                                         ('pagado', '!=', True)])
                                    if not lines:
                                        line_retenciones_manuales_value.resumen_id.write(vals)
                                else:
                                    line_retenciones_manuales_value.write(vals)
                                    # lines = line_retenciones_manuales.search(
                                    #     ['|', ('pagado', '=', True), ('cheque_emitido', '=', True),
                                    #      ('resumen_id', '=', line_retenciones_manuales_value.resumen_id.id)])
                                    # if lines:
                                    #     vals['cheque_emitido'] = True
                                    line_retenciones_manuales_value.resumen_id.retencion_manual_id.write({'state':'aprobacion_pago'})
                                    line_retenciones_manuales_value.resumen_id.write(vals)
                            else:
                                line_retenciones_manuales_value.write(vals)
                                line_retenciones_manuales_value.resumen_id.write(vals)
                                if line_retenciones_manuales_value.resumen_id.retencion_manual_id.state == 'cerrado':
                                    line_retenciones_manuales_value.resumen_id.retencion_manual_id.write(
                                        {'state': 'aprobacion_pago'})

    # RAGU validando monto al confirmar
    @api.multi
    def _check_valid_amount(self):
        for rec in self:
            if rec.amount == 0:
                raise ValidationError(_(u"No se puede procesar un Comprobante con 'Total' en 0!"))
            if rec.payment_option != u'with_writeoff' and float_round(abs(rec.amount), 2) != float_round(abs(rec.get_topay_amount()), 2):
                raise ValidationError(
                    _(u"El total no coincide con el monto a pagar. Debe actualizar el Pago antes de continuar!"))
            if rec.valor_custodia_id:
                line_vc_amount = sum([ line.amount for line in rec.line_dr_ids if line.reconcile and line.move_line_id.vc ])
                if float_round(rec.valor_custodia_id.monto, 2) != float_round(line_vc_amount, 2):
                    raise ValidationError('El monto de la OPI no coincide con el monto del valor en custodia, por favor verificar la OPI.')
        return True

    @api.multi
    def confirm_voucher(self):
        self._check_valid()
        self._check_valid_amount()
        # self.filtered(lambda x: x.check_id.exists()).mapped('check_id').write({'state': 'assign','amount': rec.amount, 'check_date': rec.fecha_inicio_pago,
        #                         'partner_id': rec.partner_id.id})
        self.write({'state': 'confirm'})
        # self.modificar_aprobacion_estado_pago('confirm')  # TODO: L SPRING 11 GAP 28
        # self.actualizar_retenciones_manuales({'cheque_emitido': True})

        for rec in self:
            rec.check_id.write({'state': 'assign', 'amount': rec.amount, 'check_date': rec.fecha_inicio_pago,
                                'partner_id': rec.partner_id.id})

    @api.multi
    def issue_voucher(self):
        for rec in self:
            rec.check_id.write({'state': 'issue', 'amount': rec.amount, 'check_date': rec.fecha_inicio_pago,
                                'partner_id': rec.partner_id.id})
        self.write({'state': 'issue'})

    def _update_check(self, action = False):
        if action == 'change_voucher':
            for rec in self:
                if rec.payment_method == 'check':
                    rec.check_id.state = 'available'
                    if rec.state == 'cancel' and rec.check_id.in_cashbox:
                        rec.check_id.in_cashbox = False
        return True


    @api.multi
    def change_voucher(self):
        self._update_check('change_voucher')
        self.create_workflow()
        self.actualizar_retenciones_manuales({'cancelado': False})
        self.write({'state': 'draft'})
        return True

    @api.multi
    def btn_anular(self):
        for rec in self:
            if rec.payment_method == 'check':
                rec.check_id.write({'state': 'cancel'})
        self.write({'show_motive': True})

    @api.multi
    def cancel_voucher(self):
        for rec in self:
            if rec.state == 'posted':
                invoice = rec.invoice_id
                # FACTURAS y FACTURAS DE FONDO ROTATORIO
                for line in rec.line_ids:
                    if line.invoice_id:
                        if line.invoice_id.fondo_rotarios:
                            raise ValidationError(_(u"No es posible cancelar la gestión de pagos, el/los documentos "
                                                u"asociados están incluidos en 3 en 1 para reposición."))
                    if line.origin_voucher_id.rendicion_anticipos_id:
                        if line.origin_voucher_id.rendicion_anticipos_id.fondo_rotarios:
                            raise ValidationError(_(u"No es posible cancelar la gestión de pagos, el/los documentos "
                                                    u"asociados están incluidos en 3 en 1 para reposición."))
                    elif line.origin_voucher_id.rendicion_viaticos_id:
                        if line.origin_voucher_id.rendicion_viaticos_id.fondo_rotarios:
                            raise ValidationError(_(u"No es posible cancelar la gestión de pagos, el/los documentos "
                                                    u"asociados están incluidos en 3 en 1 para reposición."))
                if invoice:
                    reconcile_id = rec.move_ids.mapped('reconcile_id')
                    reconcile_partial_id = rec.move_ids.mapped('reconcile_partial_id')
                    invoice.move_id.line_id.filtered(lambda x: x.reconcile_id.id in reconcile_id.ids).write(
                        {'reconcile_id': False})
                    invoice.move_id.line_id.filtered(
                        lambda x: x.reconcile_partial_id.id in reconcile_partial_id.ids).write(
                        {'reconcile_partial_id': False})
                    invoice.write({'state': 'open'})
                # ANTICIPO DE VIATICO
                if rec.solicitud_viatico_id:
                    rec.solicitud_viatico_id.write({'state': 'autorizado'})
                # RENDICION DE VIATICO
                if rec.rendicion_viaticos_id:
                    rec.rendicion_viaticos_id.write({'state': 'autorizado'})
                vale = self.env['grp.vale.caja'].search([('aprobacion_pago_id', '=', rec.invoice_id.id)])
                if vale:
                    vale.write({'state': 'posted'})
            if rec.payment_method in ['cash','check']:
                rec.check_id.write({'in_cashbox': False})
                rec.write({'in_cashbox': False})
            if rec.valor_custodia_id:
                rec.valor_custodia_id.write({'readonly': False, 'state': 'entrega_autorizada', 'fecha_baja': False,
                                             'asiento_baja': False, 'diario_baja': False })
            #RAGU analizando origenes de lineas
            solicitud_anticipos_tocancel_ids = rec.line_ids.filtered(lambda x: x.origin_voucher_id.solicitud_anticipos_id and x.amount != 0 and not x.origin_voucher_id.rendicion_anticipos_id).mapped('origin_voucher_id.solicitud_anticipos_id')
            if self.env['hr.expense.expense'].search_count([('solicitud_anticipos_id','in',solicitud_anticipos_tocancel_ids.ids),('state','not in',['cancelled','cancelado'])]):
                raise ValidationError(_(u"No se pueden cancelar Solicitudes de anticipos asociadas a una Rendición de Anticipos no 'Cancelada' o 'Rechazada'!"))
            solicitud_anticipos_tocancel_ids.write({'adelanto_pagado': False})
        self.actualizar_retenciones_manuales({'cancelado': False})

        res = super(grp_account_voucher, self).cancel_voucher()
        return res

    # TODO: SPRING 10 GAP 222 K
    @api.multi
    def draft_voucher(self):
        self._update_check('change_voucher')
        self.write({'state': 'draft'})
        # self.actualizar_retenciones_manuales({'cheque_emitido': False})
        # self.modificar_aprobacion_estado_pago('draft')  # TODO: L SPRING 11 GAP 28

    # TODO: SPRING 11 GAP 292 M
    @api.multi
    @api.depends('amount')
    def _compute_check_amount(self):
        for rec in self:
            if rec.amount:
                rec.check_amount = rec.amount

    # TODO: SPRING 11 GAP 285 C
    @api.multi
    def recompute_voucher_lines(self, partner_id, journal_id, price, currency_id, ttype, date):
        # TODO: SPRING 10 GAP 222 K
        if self._context and self._context.get('pago_ret_sueldo', False):
            result = super(grp_aprobacion_pagos.AccountVoucher, self).recompute_voucher_lines(partner_id, journal_id,
                                                                                              price, currency_id,
                                                                                              ttype, date)
            result['value']['line_dr_ids'] = self._filter_voucher_lines_pr(result['value']['line_dr_ids'], partner_id)
            result['value']['line_cr_ids'] = self._filter_voucher_lines_pr(result['value']['line_cr_ids'], partner_id)
        else:
            result = super(grp_account_voucher, self).recompute_voucher_lines(partner_id, journal_id, price,
                                                                              currency_id,
                                                                              ttype, date)
            cr_ids = result['value']['line_cr_ids']
            dr_ids = result['value']['line_dr_ids']
            line_cr_ids = filter(
                lambda x: isinstance(x, tuple) or (isinstance(x, dict) and not self.in_transfer(x['move_line_id'])),
                cr_ids)
            line_dr_ids = filter(
                lambda x: isinstance(x, tuple) or (isinstance(x, dict) and not self.in_transfer(x['move_line_id'])),
                dr_ids)
            # TODO: SPRING 10 GAP 222 K
            result['value']['line_cr_ids'] = self._filter_voucher_lines_not_pr(line_cr_ids, ttype, partner_id)
            result['value']['line_dr_ids'] = self._filter_voucher_lines_not_pr(line_dr_ids, ttype, partner_id)
        if self._context.get('caja_recaudadora') and self._context.get('default_caja_recaudadora_id'):
            result['value']['line_cr_ids'] = self._filter_voucher_lines_cajarecaudadora(self._context.get('default_caja_recaudadora_id'), result['value']['line_cr_ids'])
            result['value']['line_dr_ids'] = self._filter_voucher_lines_cajarecaudadora(self._context.get('default_caja_recaudadora_id'), result['value']['line_dr_ids'])
        return result

    # TODO: SPRING 11 GAP 285 C
    def in_transfer(self, move_line_id):
        return self.env['grp.transferencia.cabezal.line'].search_count([('move_line_id', '=', move_line_id)])

    def _check_valid(self):
        for rec in self:
            if rec.check_id and rec.check_id.state != 'available' and self.search_count([('check_id','=',rec.check_id.id),('id','!=',rec.id)]):
                raise ValidationError(_(u"El cheque ya fué asociado a otro Pago!"))
            if rec.caja_recaudadora_id and rec.payment_method == 'transfer':
                raise ValidationError(_("Un pago asociado a una Caja recaudadora no puede ser de tipo 'Transferencia'!"))
            elif not rec.caja_recaudadora_id and rec.type == 'receipt' and rec.payment_method != 'transfer':
                raise ValidationError(_("Un pago asociado a una Factura de cliente debe ser de tipo 'Transferencia'!"))
            if rec.journal_id.type == 'bank' and rec.payment_method == 'cash':
                raise ValidationError(_("Un pago asociado a Banco no debe ser de tipo 'Efectivo'!"))
            if rec.journal_id.type == 'cash' and rec.payment_method == 'transfer':
                raise ValidationError(_("Un pago de Efectivo no puede ser de tipo 'Transferencia'!"))

    # TODO: SPRING 11 GAP 292 M
    @api.multi
    def proforma_voucher(self):
        self._check_valid()
        self._check_valid_amount()
        res = super(grp_account_voucher, self).proforma_voucher()
        # TODO: SPRING 10 GAP 222 K
        # self.actualizar_retenciones_manuales({'pagado': True})

        for rec in self:
            if rec.caja_recaudadora_id:
                rec.write({'in_cashbox': True})
            for line in rec.line_ids.filtered(lambda x: x.amount != 0):
                if line.origin_voucher_id:
                    vals = {'state':'pagado'}
                    if rec.caja_recaudadora_id:
                        vals.update({'in_cashbox': True})
                    line.origin_voucher_id.write(vals)
            if rec.payment_method == 'check':
                vals = {'state': 'paid', 'paid_date': rec.date}
                if rec.caja_recaudadora_id:
                    vals.update({'in_cashbox': True})
                rec.check_id.write(vals)# TODO: M INCIDENCIA
            if rec.caja_recaudadora_id:
                rec.move_ids.write({'caja_recaudadora_id': rec.caja_recaudadora_id.id})
                rec._generate_caja_recaudadora_line()
            lines = rec.line_cr_ids.filtered(lambda x: x.amount != 0) + rec.line_dr_ids.filtered(lambda x: x.amount != 0)
            lines.paid_valor_custodia()
            lines.paid_vale_caja()
        return res

    # TODO: SPRING 11 GAP 292 M
    def _make_journal_search(self, cr, uid, ttype, context=None):
        journal_pool = self.pool.get('account.journal')
        if 'default_caja_recaudadora_id' in context:
            return journal_pool.search(cr, uid, [('type', '=', ttype), ('caja_recaudadora', '=', True)], limit=1)
        else:
            return super(grp_account_voucher, self)._make_journal_search(cr, uid, ttype, context=context)


    def _get_devolucion_product_id(self):
        """
            Self debe ser el origin_voucher_id de la linea del voucher que es quien origina el pago
        :return: Id del producto correspondiente a una devolucion segun configuracion
        """
        if self.solicitud_anticipos_id:
            product_id = self.line_ids[0].product_id.id
            if not product_id:
                product_id = self.env['product.product'].search([('devolucion_anticipo', '=', True)], limit=1).id
        elif self.solicitud_viatico_id:
            product_id = self.env['product.product'].search([('devolucion_viatico', '=', True)], limit=1).id
        else:
            product_id = False
        return product_id

    # TODO: SPRING 11 GAP 292 M
    def _generate_caja_recaudadora_line(self):
        caja_recaudadora_line_obj = self.env['grp.caja.recaudadora.tesoreria.line']
        vouchers_toexclude = []
        voucher_difference = round(self.amount - self.topay_amount, 2)
        expensive_invoice_line_id = False
        voucher_lines = self.mapped(lambda x: x.line_ids).filtered(lambda x: x.amount > 0).sorted(
            key=lambda a: a.reconcile and a.amount, reverse=True)

        if voucher_lines:
            first_voucher_line = voucher_lines[0].id
        difference = float_round(self.amount, 2) - float_round(self.topay_amount, 2)
        _saldo_disponible_para_pagar_vcurrency = abs(self.amount > self.topay_amount and self.amount or self.topay_amount)
        for voucher_line in voucher_lines:
            amount = voucher_line.amount
            if voucher_line.id == first_voucher_line:
                amount += voucher_difference
            invoice = voucher_line.invoice_id
            sign = invoice.type == 'out_refund' and -1 or 1

            caja_recaudadora_line_obj.suspend_security().create({'voucher_id': voucher_line.voucher_id.id,
                                              'vline_id': voucher_line.id,
                                              'invoice_id': invoice.id,
                                              'origin_voucher_id': voucher_line.origin_voucher_id.id,
                                              'type': 'voucher',
                                              'amount': amount * sign,
                                              'caja_recaudadora_id': self.caja_recaudadora_id.id})

            invoice.write({'caja_recaudadora_id': self.caja_recaudadora_id.id})

            if voucher_line.voucher_id.payment_method == 'check' and voucher_line.voucher_id.id not in vouchers_toexclude:
                invoice_id = invoice.id if invoice.exists() else False
                caja_recaudadora_line_obj.suspend_security().create({'voucher_id': voucher_line.voucher_id.id,
                                                  'vline_id': voucher_line.id,
                                                  'invoice_id': invoice_id,
                                                  'origin_voucher_id': voucher_line.voucher_id.id,
                                                  'type': 'check',
                                                  'check_amount': voucher_line.voucher_id.check_amount,
                                                  'caja_recaudadora_id': self.caja_recaudadora_id.id})
                vouchers_toexclude.append(voucher_line.voucher_id.id)

            if invoice.exists():
                cr_tesoreria_line_obj = self.env['grp.caja.recaudadora.tesoreria.line']
                amount_exhausted = False
                _saldo_disponible_para_pagar_icurrency = voucher_line.voucher_id.with_context({'date':voucher_line.voucher_id.date}).currency_id.compute(_saldo_disponible_para_pagar_vcurrency,invoice.currency_id,round=False)
                ctx_copy = dict(self._context)
                ctx_copy.update({'date': voucher_line.voucher_id.date or fields.Date.today()})
                for line in invoice.invoice_line:

                    # SALDO QUE FALTA POR PAGAR PARA LA LINEA DE LA FACTURA
                    same_line_detail_ids = cr_tesoreria_line_obj.search(
                        [('caja_recaudadora_id', '=', self.caja_recaudadora_id.id),
                         ('invoice_line_id', '=', line.id)])
                    saldo_pagar_de_linea_icurrency = line.price_subtotal
                    if same_line_detail_ids:
                        invoice_line_paid_icurrency = sum(map(lambda x: x.price_subtotal, same_line_detail_ids))
                        saldo_pagar_de_linea_icurrency -= invoice_line_paid_icurrency

                    # SABER CUANDO SE ACABA EL SALDO PARA PAGAR
                    if saldo_pagar_de_linea_icurrency > _saldo_disponible_para_pagar_icurrency:
                        price_subtotal = _saldo_disponible_para_pagar_icurrency
                    else:
                        price_subtotal = saldo_pagar_de_linea_icurrency
                    _saldo_disponible_para_pagar_icurrency -= price_subtotal

                    if price_subtotal > 0:
                        cr_line_dict = {'voucher_id': voucher_line.voucher_id.id,
                                        'vline_id': voucher_line.id,
                                        'invoice_id': invoice.id,
                                        'invoice_line_id': line.id,
                                        'origin_voucher_id': voucher_line.voucher_id.id,
                                        'type': 'details',
                                        'product_id': line.product_id.id,
                                        'price_subtotal': price_subtotal * sign,
                                        'amount': voucher_line.amount,
                                        'caja_recaudadora_id': self.caja_recaudadora_id.id}
                        new_line_id = caja_recaudadora_line_obj.suspend_security().create(cr_line_dict)
                        if not expensive_invoice_line_id or expensive_invoice_line_id.price_subtotal < new_line_id.price_subtotal:
                            expensive_invoice_line_id = new_line_id

                    if amount_exhausted:
                        break;
            else:
                product_id = voucher_line.origin_voucher_id._get_devolucion_product_id()
                new_line_id = caja_recaudadora_line_obj.suspend_security().create({'voucher_id': voucher_line.voucher_id.id,
                                                                'vline_id': voucher_line.id,
                                                                'invoice_id': False,
                                                                'invoice_line_id': False,
                                                                'origin_voucher_id': voucher_line.voucher_id.id,
                                                                'type': 'details',
                                                                'product_id': product_id,
                                                                'price_subtotal': voucher_line.amount,
                                                                'amount': voucher_line.amount,
                                                                'caja_recaudadora_id': self.caja_recaudadora_id.id})
                if not expensive_invoice_line_id or expensive_invoice_line_id.price_subtotal < new_line_id.price_subtotal:
                    expensive_invoice_line_id = new_line_id

        if expensive_invoice_line_id and difference != 0:
            expensive_invoice_line_id.write({'plus_amount': difference})

        return True

    # TODO: C SPRING 13 GAP 494
    @api.model
    def account_move_get(self, voucher_id):
        move = super(grp_account_voucher, self).account_move_get(voucher_id)
        voucher = self.env['account.voucher'].browse(voucher_id)
        if not move.get('operating_unit_id',False):
            if voucher.operating_unit_id.id:
                move.update({'operating_unit_id': voucher.operating_unit_id.id})
            elif voucher.journal_id.operating_unit_id.id:
                move.update({'operating_unit_id': voucher.journal_id.operating_unit_id.id})
        return move

    # TODO: M INCIDENCIA 692
    @api.multi
    @api.depends('state', 'payment_method')
    def _compute_payment_method_alert(self):
        for rec in self:
            rec.payment_method_alert = True if rec.state == 'confirm' and rec.payment_method == 'check' else False

    # TODO: M INCIDENCIA 692
    @api.one
    def do_not_show_warning(self):
        self.write({'show_warning': False})

    # TODO: M SPRING 14 GAP 29_31
    @api.multi
    def actualizar_hr_expense(self):
        hr_expense = self.env['hr.expense.expense']
        rendicion_ids = []
        for voucher in self:
            if voucher.rendicion_viaticos_id or voucher.solicitud_viatico_id:
                if voucher.rendicion_viaticos_id:
                    if voucher.type == 'sale' and self._context.get('in_cashbox',False):
                        rendicion_ids.append(voucher.rendicion_viaticos_id.id)
                    # elif voucher.type == 'payment'
                        # and voucher or not self.search(
                        # ['|', ('rendicion_viaticos_id', '=', voucher.rendicion_viaticos_id.id),
                        #  ('solicitud_viatico_id', '=', voucher.rendicion_viaticos_id.solicitud_viatico_id.id),
                        #  ('state', '!=', 'posted'), ('type', '=', 'payment'),
                        #  ('id', '!=', voucher.id)]):
                        # rendicion_ids.append(voucher.rendicion_viaticos_id.id)
                elif voucher.solicitud_viatico_id:
                    rendicion_viaticos_id = hr_expense.search(
                        [('solicitud_viatico_id', '=', voucher.solicitud_viatico_id.id),
                         ('state', '=', 'autorizado')],
                        limit=1)
                    if rendicion_viaticos_id:
                        voucher_not_paid = self.search(
                            ['|', ('rendicion_viaticos_id', '=', rendicion_viaticos_id.id),
                             ('solicitud_viatico_id', '=', voucher.solicitud_viatico_id.id),
                             ('state', '!=', 'posted'),
                             ('type', '=', 'payment'),
                             ('id', '!=', voucher.id)])
                        if not voucher_not_paid:
                            rendicion_ids.append(rendicion_viaticos_id.id)
            if voucher.rendicion_anticipos_id or voucher.solicitud_anticipos_id:
                if voucher.rendicion_anticipos_id:
                    if voucher.type == 'sale' and self._context.get('in_cashbox',False):
                    # if voucher.type == 'sale' or not self.search(
                    #         ['|', ('rendicion_anticipos_id', '=', voucher.rendicion_anticipos_id.id),
                    #          ('solicitud_anticipos_id', '=', voucher.rendicion_anticipos_id.solicitud_anticipos_id.id),
                    #          ('state', '!=', 'posted'),
                    #          ('type', '=', 'payment'),
                    #          ('id', '!=', voucher.id)]):
                        rendicion_ids.append(voucher.rendicion_anticipos_id.id)
                elif voucher.solicitud_anticipos_id:
                    rendicion_anticipos_id = hr_expense.search(
                        [('solicitud_anticipos_id', '=', voucher.solicitud_anticipos_id.id),
                         ('state', '=', 'autorizado')],
                        limit=1)
                    if rendicion_anticipos_id:
                        voucher_not_paid = self.search(
                            ['|', ('rendicion_anticipos_id', '=', rendicion_anticipos_id.id),
                             ('solicitud_anticipos_id', '=', voucher.solicitud_anticipos_id.id),
                             ('state', '!=', 'posted'),
                             ('type', '=', 'payment'),
                             ('id', '!=', voucher.id)])
                        if not voucher_not_paid:
                            rendicion_ids.append(rendicion_anticipos_id.id)
        if rendicion_ids:
            hr_expense.suspend_security().browse(rendicion_ids).write({'state': 'paid'})
            # rendicion_viaticos.

    def _get_related_document(self):
        self = self.sudo()
        self.ensure_one()
        if self.rendicion_anticipos_id:
            _related_model = self.rendicion_anticipos_id._name
            _related_id = self.rendicion_anticipos_id.id
            # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
            # _related_document = self.rendicion_anticipos_id.sequence
            _related_document = self.rendicion_anticipos_id.x_sequence
            #
            _module_name = False
            _view_id = False
        elif self.solicitud_anticipos_id:
            _related_model = self.solicitud_anticipos_id._name
            _related_id = self.solicitud_anticipos_id.id
            _related_document = self.solicitud_anticipos_id.name
            _module_name = False
            _view_id = False
        else:
            return super(grp_account_voucher, self)._get_related_document()
        return {'related_document': _related_document, 'related_model': _related_model, 'related_id': _related_id,
                'module_name':_module_name, 'view_id': _view_id, 'related_document2':False}

# TODO: SPRING 10 GAP 222 K
class grp_account_voucher_line(models.Model):
    _inherit = 'account.voucher.line'

    beneficiario = fields.Char(string=u'Beneficiario', size=50, compute='_compute_beneficiario', store=False)
    pago_ret_sueldo = fields.Boolean(string=u'Pago retención de sueldo', compute='_compute_pago_ret_sueldo',
                                     store=False, default=False)
    # TODO: C SPRING 10 GAP_266
    valor_custodia_id = fields.Many2one('grp.valores_custodia', string=u'Valor en custodia',
                                        domain=[('state', '=', 'entrega_autorizada'), ('tipo_id.efectivo', '=', True)])
    apunte_vc = fields.Boolean(string=u'Apunte VC?', compute='_compute_apunte_vc')

    concept_id = fields.Many2one('grp_concepto_gasto_cc_viaticos', u'Concepto', domain="[('viaticos','=', True)]")

    # Por performance se calcula este campo y se guarda en BD
    supplier_invoice_number = fields.Char(string=u'Nro. de documento', compute='_compute_supplier_invoice_number', compute_sudo=True, store=True)

    @api.one
    @api.depends('origin_voucher_id',
                 'origin_voucher_id.rendicion_anticipos_id',
                 'origin_voucher_id.solicitud_anticipos_id',
                 #'origin_voucher_id.opi', # NOTE: Descomentar si depende de algún campo de OPI, ver TODO
                 'invoice_id',
                 'move_line_id',
                 'move_line_id.move_id',
                 #'move_line_id.move_id.ONE2MANY-A-LIN_RET.retencion_manual_id', # NOTE: Evaluar si es necesario
                 'origin_voucher_id.rendicion_viaticos_id',
                 'origin_voucher_id.solicitud_viatico_id',
                 )
    def _compute_supplier_invoice_number(self):
        if self.origin_voucher_id.rendicion_anticipos_id:
            # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
            # self.supplier_invoice_number = self.origin_voucher_id.rendicion_anticipos_id.sequence
            self.supplier_invoice_number = self.origin_voucher_id.rendicion_anticipos_id.x_sequence
            #
        elif self.origin_voucher_id.solicitud_anticipos_id:
            self.supplier_invoice_number = self.origin_voucher_id.solicitud_anticipos_id.name
        elif self.origin_voucher_id.opi:
            self.supplier_invoice_number = self.origin_voucher_id.number # TODO: verificar, no toma nada de OPI
        else:
            invoice_id = self.invoice_id and self.invoice_id.id or self.move_line_id.invoice.id
            if invoice_id and self.env['grp.vale.caja'].search_count([('aprobacion_pago_id', '=', invoice_id)]):
                self.supplier_invoice_number = u'Vale de caja'
            else:
                move = self.move_line_id and self.move_line_id.move_id or False
                retencion_manual = move and self.env['grp.lineas.retenciones.manuales.resumen'].search([('move_id','=',move.id)], limit=1).retencion_manual_id or False
                if retencion_manual:
                    self.supplier_invoice_number = u'Retención de Sueldo de Habilitaciones'
                elif self.origin_voucher_id.rendicion_viaticos_id:
                    # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
                    # self.supplier_invoice_number = self.origin_voucher_id.rendicion_viaticos_id.sequence
                    self.supplier_invoice_number = self.origin_voucher_id.rendicion_viaticos_id.x_sequence
                    #
                elif self.origin_voucher_id.solicitud_viatico_id:
                    self.supplier_invoice_number = self.origin_voucher_id.solicitud_viatico_id.name
                elif move:
                    invoice = self.env['account.invoice'].search([('move_id', '=', move.id)], order="id desc", limit=1)
                    if invoice:
                        if invoice.type in ('in_invoice', 'in_refund') and invoice.supplier_invoice_number:
                            invoice_number = invoice.supplier_invoice_number
                        elif invoice.type in ('out_invoice',):
                            invoice_number = invoice.number
                        elif invoice.nro_factura_grp:
                            invoice_number = invoice.nro_factura_grp
                        else:
                            invoice_number = invoice.name_get()[0][1]
                        self.supplier_invoice_number = invoice.nro_afectacion and u'%s Nro Afect: %s' % (invoice_number or '', invoice.nro_afectacion) or invoice_number
                    else:
                        self.supplier_invoice_number = move.name_get()[0][1]
                elif self._context.get('move_line_id') and hasattr(self._context['move_line_id'], 'move_id'):
                    self.supplier_invoice_number = self._context['move_line_id'].move_id.name_get()[0][1]

    # TODO: M SPRING 14 GAP 29_31
    @api.onchange('concept_id')
    def _onchange_concept_id(self):
        if self.concept_id and self.concept_id.cuenta_id:
            _account_id = self.concept_id.cuenta_id.id
        else:
            context_journal = self.env.context.get('journal_id')
            if context_journal:
                _account_id = self.env['account.journal'].search(
                    [('id', '=', context_journal)]).default_debit_account_id.id
            else:
                _account_id = False
        self.account_id = _account_id

    # TODO: SPRING 10 GAP 222 K
    @api.multi
    def _compute_beneficiario(self):
        line_retenciones_manuales = self.env['grp.lineas.retenciones.manuales']
        for rec in self:
            line_retenciones_manuales_ids = line_retenciones_manuales.search(
                [('retencion_manual_id.state', '=', 'aprobacion_pago'),
                 ('retencion_manual_id.name', '=', rec.move_line_id.name), ('resumen_id.pagado', '=', False),
                 ('resumen_id.cheque_emitido', '=', False),
                 ('resumen_id.cancelado', '=', False),
                 ('importe', '=', rec.move_line_id.credit or rec.move_line_id.debit or 0.0)])

            if line_retenciones_manuales_ids and len(line_retenciones_manuales_ids) > 0:
                rec.beneficiario = line_retenciones_manuales_ids[0].beneficiario

    # TODO: SPRING 10 GAP 222 K
    @api.one
    def _compute_pago_ret_sueldo(self):
        if self.voucher_id.pago_ret_sueldo and self.voucher_id.partner_id and self.voucher_id.partner_id.es_inciso_default:
            self.pago_ret_sueldo = self.voucher_id.pago_ret_sueldo
        else:
            self.pago_ret_sueldo = False

    # TODO: C SPRING 10 GAP_266
    @api.one
    @api.depends('move_line_id')
    def _compute_apunte_vc(self):
        self.apunte_vc = False
        if self.move_line_id.vc:
            self.apunte_vc = True

    def _get_origin_dict(self):
        self = self.sudo()
        if self.origin_voucher_id.rendicion_anticipos_id:
            _related_model = self.origin_voucher_id.rendicion_anticipos_id._name
            _related_id = self.origin_voucher_id.rendicion_anticipos_id.id
            _view_id = False
            _module_name = False
            # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
            # _related_document = self.origin_voucher_id.rendicion_anticipos_id.sequence
            _related_document = self.origin_voucher_id.rendicion_anticipos_id.x_sequence
            #
            _invoice_id = False
            # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
            # _supplier_invoice_number = self.origin_voucher_id.rendicion_anticipos_id.sequence
            _supplier_invoice_number = self.origin_voucher_id.rendicion_anticipos_id.x_sequence
            #
        elif self.origin_voucher_id.solicitud_anticipos_id:
            _related_model = self.origin_voucher_id.solicitud_anticipos_id._name
            _related_id = self.origin_voucher_id.solicitud_anticipos_id.id
            _view_id = False
            _module_name = False
            _related_document = self.origin_voucher_id.solicitud_anticipos_id.name
            _invoice_id = False
            _supplier_invoice_number = self.origin_voucher_id.solicitud_anticipos_id.name
        elif self.origin_voucher_id.opi:
            _related_model = self.origin_voucher_id._name
            _related_id = self.origin_voucher_id.id
            _view_id = u'view_internal_pay_order_form'
            _module_name = u'grp_tesoreria'
            _related_document = self.origin_voucher_id._name
            _invoice_id = False
            _supplier_invoice_number = self.origin_voucher_id.number
        else:
            _invoice_id = self.invoice_id.id or self.move_line_id.invoice.id
            vale_caja_id = self.env['grp.vale.caja'].search([('aprobacion_pago_id', '=', _invoice_id)], limit=1)
            if vale_caja_id:
                _related_model = vale_caja_id._name
                _related_id = vale_caja_id.id
                _view_id = False
                _module_name = False
                _related_document = vale_caja_id._name
                _invoice_id = False
                _supplier_invoice_number = u'Vale de caja'
            else:
                retencion_manual_id = self.env['grp.lineas.retenciones.manuales.resumen'].search([('move_id','=',self.move_line_id.move_id.id)], limit=1).retencion_manual_id
                if retencion_manual_id and self.move_line_id:
                    _related_model = retencion_manual_id._name
                    _related_id = retencion_manual_id.id
                    _view_id = False
                    _module_name = False
                    _related_document = retencion_manual_id._name
                    _invoice_id = False
                    _supplier_invoice_number = u'Retención de Sueldo de Habilitaciones'
                else:
                    return super(grp_account_voucher_line, self)._get_origin_dict()

        return {'related_document': _related_document,
                'related_model': _related_model,
                'related_id': _related_id,
                'module_name': _module_name,
                'view_id': _view_id,
                'invoice_id': _invoice_id,
                'supplier_invoice_number': _supplier_invoice_number}


    # TODO: C SPRING 10 GAP_266
    @api.multi
    def paid_valor_custodia(self):
        for rec in self:
            if rec.valor_custodia_id:
                rec.valor_custodia_id.write({'state': 'entrega_tesoreria', 'asiento_baja': rec.voucher_id.move_id.id,
                                             'diario_baja': rec.voucher_id.move_id.journal_id.id,
                                             'fecha_baja': rec.voucher_id.move_id.date})

    @api.multi
    def paid_vale_caja(self):
        for rec in self:
            if rec.reconcile and rec.invoice_id and rec.invoice_id.state == 'paid':
                vale = self.env['grp.vale.caja'].search([('aprobacion_pago_id', '=', rec.invoice_id.id)])
                if vale and vale.state != 'pagado':
                    vale.write({'state': 'pagado'})

    @api.onchange('product_id')
    def onchange_sales_product_id(self):
        if self.product_id:
            self.account_id = self.product_id.property_account_income.id
        else:
            self.account_id = False

    @api.model
    def _update_supplier_invoice_number(self, limit=1000):
        logging.info('Ejecutando Cron de actualizacion supplier_invoice_number en account.voucher.line')
        domain = [('supplier_invoice_number','=',False)]
        ICP = self.env['ir.config_parameter']
        last_avl_id = ICP.get_param('last_updated_avl_id')
        if last_avl_id:
            domain.append(('id','>',last_avl_id))
        records2update = self.search(domain, order="id", limit=limit)
        cr = self.env.cr
        logging.info('Cantidad de registros a actualizar: ' + str(len(records2update)))
        for record in records2update:
            try:
                record._compute_supplier_invoice_number() # force to recompute
                ICP.set_param('last_updated_avl_id', record.id)
                cr.commit()
            except Exception as e:
                cr.rollback()
                logging.info("Registro ID %s Error => '%s'" % (record.id, e))
        logging.info('Termina ejecucion Cron de actualizacion supplier_invoice_number en account.voucher.line')

