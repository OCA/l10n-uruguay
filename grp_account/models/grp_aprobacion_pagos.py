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

from openerp import models, fields, api
from lxml import etree
from openerp.tools.translate import _
from openerp.exceptions import Warning
from openerp import SUPERUSER_ID



class GrpAccountInvoiceAprobacionPagos(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

    @api.model
    def fields_view_get(self, view_id=None, view_type='tree', toolbar=False, submenu=False):
        res = super(GrpAccountInvoiceAprobacionPagos, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                                  toolbar=toolbar, submenu=submenu)
        if res.get('toolbar', False):
            if self._context.get('aprobacion_pagos'):
                res['toolbar']['action'] = list(
                    filter(lambda d: d['res_model'] in [u'aprobar.pago.guardar', u'aprobar.pago.cancel'],
                           res['toolbar']['action']))
                res['toolbar']['print'] = []
            else:
                res['toolbar']['action'] = list(
                    filter(lambda d: d['res_model'] not in [u'aprobar.pago.guardar', u'aprobar.pago.cancel'],
                           res['toolbar']['action']))
        return res


    # Incidencia 2382 campos dobles al filtrar en busqueda avanzada
    def fields_get(self, cr, uid, allfields=None, context=None, write_access=True, attributes=None):
        fields_to_hide = ['cuenta_bancaria_id','res_partner_bank_id','rupe_cuenta_bancaria_id','partner_bank_id','move_name']
        fields_to_hide_aprob_pagos = ['id_compra','monto_afectado','monto_comprometido','notas_credito_ids',
                                      'doc_type','oficina','origin_str','tipo_de_cambio','internal_number']
        res = super(GrpAccountInvoiceAprobacionPagos, self).fields_get(cr, uid, allfields=allfields, context=context, write_access=write_access, attributes=attributes)
        for field in fields_to_hide + fields_to_hide_aprob_pagos:
            if field in res:
                # campo en pestaña Otra información, no se usa
                if field == 'partner_bank_id':
                    res[field]['selectable'] = False
                # en Aprobacion Pagos solamente se utiliza el campo cuenta_bancaria_id dentro de fields_to_hide,
                # pero no debe verse ninguno de los de fields_to_hide_aprob_pagos
                if context.get('aprobacion_pagos', False):
                    if field != 'cuenta_bancaria_id' or field in fields_to_hide_aprob_pagos:
                        res[field]['selectable'] = False
                # en Proveedor, 3 en 1, Obligación y Fondo rotatorio no se debe ver cuenta_bancaria_id
                elif context.get('doc_type','') in ['3en1_invoice','obligacion_invoice','invoice'] or context.get('type','') == 'in_invoice':
                    if field in ['cuenta_bancaria_id','move_name'] or field in fields_to_hide_aprob_pagos:
                        res[field]['selectable'] = False
        return res

    fecha_aprobacion = fields.Date(string=u'Fecha de aprobación', copy=False)
    cuenta_bancaria_id = fields.Many2one('account.journal', string=u'Cuenta bancaria')
    pago_aprobado = fields.Boolean(string='Pago aprobado', default=False, copy=False)
    fecha_inicio_pago = fields.Date('Fecha Inicio Pago', copy=False)
    voucher_state = fields.Selection([('draft', 'Borrador'),
                                       ('cancel', 'Cancelado'),
                                       ('proforma', 'Pro-forma'),
                                       ('confirm', 'Confirmado'),
                                       ('posted', 'Contabilizado'),
                                       ('issue', 'Emitido'),
                                       ('pagado', 'Pagado')],
                                      string='Estado del pago', compute='_compute_voucher_state', search='_search_voucher_state')
    fecha_pago = fields.Date('Fecha Pago', copy=False)
    account_voucher_id = fields.Many2one('account.voucher', string='Formulario de pago')

    related_document = fields.Char('Nº documento relacionado', compute='_compute_related_document', multi='related_document')
    related_document2 = fields.Char('Nº documento relacionado 2', compute='_compute_related_document', multi='related_document')

    doc_type_computed = fields.Char(string=u"Tipo Documento", compute="_compute_doc_type", store=True)

    @api.model
    def prepare_voucher_data(self, invoice, journal, date, amount):
        voucher_data = super(GrpAccountInvoiceAprobacionPagos, self).prepare_voucher_data(invoice, journal, date, amount)
        voucher_data.update({'fecha_inicio_pago': date})
        return voucher_data

    @api.depends('doc_type','type')
    def _compute_doc_type(self):
        for rec in self:
            if rec.doc_type != 'invoice':
                dict_types = dict(self.fields_get(allfields=['doc_type'])['doc_type']['selection'])
                # FIXME => Attribute 'selection' does not return key 'vales_caja' defined as ´´selection_add´´ in addon ´´grp_tesoreria´´
                # Maybe we have to redefine this method in addon ´´grp_tesoreria´´ in order to get key 'vales_caja' returned by 'selection' attribute
                dict_types.update({'vales_caja': 'Vales de caja'})
                dict_types.update({'adelanto_viatico': u'Adelanto de viáticos'})
                rec.doc_type_computed = dict_types.get(rec.doc_type, rec.doc_type)
            else:
                if rec.type == 'out_refund':
                    rec.doc_type_computed = "Nota de crédito de cliente"
                elif rec.type == 'in_refund':
                    rec.doc_type_computed = "Nota de crédito de proveedor"
                elif rec.type == 'out_invoice':
                    rec.doc_type_computed = "Factura de cliente"
                elif rec.type == 'in_invoice':
                    rec.doc_type_computed = "Factura de proveedor"

    def _search_voucher_state(self, operator, value):
        if operator not in ('=', '!=', '<', '<=', '>', '>=', 'in', 'not in'):
            return []
        if operator == '=':
            operator = '=='
        valid_ids = []
        VoucherLine = self.sudo().env['account.voucher.line']

        for line in self.search([('fecha_aprobacion','!=',False)]):
            voucher_line = VoucherLine.search([('move_line_id.invoice', '=', line.id), ('amount', '!=', 0)], limit=1, order='date_original DESC, id DESC')
            if not voucher_line:
                voucher_line = VoucherLine.search([('origin_voucher_id.invoice_id', '=', line.id), ('amount', '!=', 0)], limit = 1, order = 'date_original DESC, id DESC')
            _voucher_state = voucher_line and voucher_line.voucher_id.state == 'posted' and 'pagado' or voucher_line.voucher_id.state

            if eval("'%s' %s '%s'" % (_voucher_state,operator,value)):
                valid_ids.append(line.id)
        return [('id', 'in', valid_ids)]

    @api.multi
    def _compute_voucher_state(self):
        VoucherLine = self.sudo().env['account.voucher.line']
        for rec in self:
            voucher_line = VoucherLine.search([('move_line_id.invoice','=',rec.id),('amount','!=',0)], limit=1, order='date_original DESC, id DESC')
            if not voucher_line:
                voucher_line = VoucherLine.search([('origin_voucher_id.invoice_id','=',rec.id),('amount','!=',0)], limit=1, order='date_original DESC, id DESC')
            rec.voucher_state = voucher_line and voucher_line.voucher_id.state == 'posted' and 'pagado' or voucher_line.voucher_id.state

    @api.one
    def _compute_related_document(self):
        self.related_document = self.nro_factura_grp
        self.related_document2 = False

    @api.multi
    def action_link_related_document(self):
        self.ensure_one()
        _related_info_dict = {'related_model': self._name, 'related_id': self.id}
        dict_toreturn = {
            'type': 'ir.actions.act_window',
            'res_model': _related_info_dict['related_model'],
            'display_name': 'Documento relacionado',
            'view_type': 'form',
            'name': 'Documento relacionado',
            'target': 'current',
            'view_mode': 'form',
            'res_id': _related_info_dict['related_id']
        }

        if self.doc_type == 'invoice':
            _related_info_dict.update({'module_name':'account','view_id':'invoice_supplier_form'})
        elif self.doc_type == 'obligacion_invoice':
            _related_info_dict.update({'module_name':'grp_factura_siif','view_id':'view_account_form_obligacion'})
        elif self.doc_type == '3en1_invoice':
            _related_info_dict.update({'module_name':'grp_factura_siif','view_id':'view_account_form_obligacion'})

        if _related_info_dict.get('view_id') and _related_info_dict['view_id']:
            res = self.env['ir.model.data'].get_object_reference(_related_info_dict['module_name'],
                                                                 _related_info_dict['view_id'])
            res_id = res and res[1] or False
            dict_toreturn.update({
                'view_id': res_id
            })
        return dict_toreturn


class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    fecha_aprobacion_pago = fields.Date(string=u'Fecha aprobación de pago')
    fecha_inicio_pago = fields.Date(string=u'Fecha inicio pago', required=True, default=lambda *a: fields.Date.today(),
                                    readonly=True, states={'draft': [('readonly', False)],'confirm': [('readonly', False)]})

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(AccountVoucher, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                          context=context,
                                                          toolbar=toolbar, submenu=submenu)

        doc = etree.XML(res['arch'])

        account_id = self._context.get('account_id')
        domain_user = str([('invoice_id.account_id', '=', account_id), ('invoice_id.fecha_aprobacion', '!=', False),
                           ('invoice_id.state', 'in', ['open'])])

        if view_type == 'tree':
            for node_tree in doc.xpath("//tree"):
                node_tree.set('domain', domain_user)

        res['arch'] = etree.tostring(doc)

        return res

    @api.multi
    def proforma_voucher(self):
        for record in self:
            if not record.date:
                raise Warning(_('El campo Fecha es requerido'))
            if record.payment_method in ['transfer'] and not record.no_operation:
                raise Warning(_(u'El campo Nro. de Operación es requerido'))
        return super(AccountVoucher, self).proforma_voucher()

    @api.multi
    def proforma_voucher_auxiliary(self):
        for record in self:
            if not record.date:
                raise Warning(_('El campo Fecha es requerido'))
        return super(AccountVoucher, self).proforma_voucher_auxiliary()

    #RAGU GAP 56
    def _filter_voucher_lines(self, cr, uid, ids, line_ids, journal_id, partner_id, context=None):
        voucher_line_obj = self.pool.get('account.voucher.line')
        lines_filtered = [(5,)]
        lines_filtered.extend(list(filter(lambda x: not isinstance(x, dict) and x[0] == 2, line_ids)))
        # lines2link = list(filter(lambda x: not isinstance(x, dict) and x[0] == 2, line_ids))
        voucher_journal_id = self.pool.get('account.journal').browse(cr,uid,journal_id)
        # RAGU:
        # no adicionar lineas que ya estan en otra gestion de pagos
        # comprobar diario de aprobacion de pagos
        voucher_obj = self.pool.get('account.voucher')
        domain = [('voucher_id','not in',ids),
                  ('voucher_id.state','!=','cancel'),
                  ('reconcile','=',True),
                  ('move_line_id', '!=', False)]
        if partner_id:
            domain.append(('voucher_id.partner_id','=',partner_id))
        move_lines_to_exlude = [x.move_line_id.id for x in voucher_line_obj.browse(cr,uid,voucher_line_obj.search(cr,uid,domain))]
        for line in list(filter(lambda x: isinstance(x, dict), line_ids)):
            #Se pasa el superuser por tema de pagos entre operating units
            invoice_id = line['origin_voucher_id'] and voucher_obj.browse(cr,SUPERUSER_ID,line['origin_voucher_id']).invoice_id or self.pool.get('account.move.line').browse(cr,SUPERUSER_ID,line['move_line_id']).invoice_id or False
            _journal_id = invoice_id.cuenta_bancaria_id if invoice_id else False
            if line['move_line_id'] not in move_lines_to_exlude and (not _journal_id or _journal_id.id == journal_id or (_journal_id.fondo_rotatorio and voucher_journal_id.caja_chica_t)):
                if (invoice_id and (invoice_id.pago_aprobado or invoice_id.type in [u'out_invoice',u'out_refund'])) or not invoice_id:
                    lines_filtered.append(line)
        return lines_filtered

    # TODO R GAP 56
    def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date,
                                context=None):
        res = super(AccountVoucher, self).recompute_voucher_lines(cr, uid, ids, partner_id, journal_id, price,
                                                                  currency_id, ttype, date,
                                                                  context=context)
        if partner_id:
            res['value']['line_dr_ids'] = self._filter_voucher_lines(cr, uid, ids, res['value']['line_dr_ids'], journal_id, partner_id, context)
            res['value']['line_cr_ids'] = self._filter_voucher_lines(cr, uid, ids, res['value']['line_cr_ids'], journal_id, partner_id, context)
        return res


    def _unreconcile_voucher_lines(self):
        move_lines_2cancel_ids = []
        for rec in self:
            move_lines_2cancel_ids += rec.line_ids.filtered(lambda x: x.amount != 0).mapped('move_line_id').ids
        # SE REALIZA QUERY Y NO ORM PORQUE DE USARLO SE ACTUALIZAN AUTOMATICAMENTE OTROS DATOS DE LOS VOUCHER LINES QUE SE ESTAN DESMARCANDO
        if move_lines_2cancel_ids:
            self.env.cr.execute('UPDATE account_voucher_line SET reconcile = False WHERE move_line_id IN %s AND reconcile = True', (tuple(move_lines_2cancel_ids),))
        return True
        # ESTE LINEA HACE LO MISMO QUE EL SQL SE COMENTA PARA QUE NO DISPARE CAMBIOS EN LAS LINEAS
        # self.env['account.voucher.line'].search([('move_line_id','in',move_lines_2cancel_ids),('reconcile','=',True)]).write({'reconcile':False})



    @api.multi
    def cancel_voucher(self):
        to_return = super(AccountVoucher, self).cancel_voucher()
        self._unreconcile_voucher_lines()
        for rec in self:
            invoice_ids = self.env['account.invoice']
            if rec.invoice_id:
                rec.invoice_id.write({'fecha_inicio_pago': False})
            for line_id in self.line_ids.filtered(lambda x: x.amount != 0):
                if line_id.origin_voucher_id.invoice_id:
                    invoice_ids += line_id.origin_voucher_id.invoice_id
                elif line_id.invoice_id:
                    invoice_ids += line_id.invoice_id
            invoice_ids.write({'fecha_inicio_pago': False, 'fecha_pago': False})
        return to_return
