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

from openerp import models, fields, exceptions, api, _
import logging
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

# TODO: SPRING 11 GAP 28 L

class utec_adelanto_viaticos_v8(models.Model):
    _inherit = 'account.voucher'

    state = fields.Selection(selection_add=[('posted', 'Contabilizado'), ('pagado', 'Pagado')])
    fecha_hasta = fields.Datetime(related='solicitud_viatico_id.fecha_hasta', store=True, readonly=True) # TODO: K SPRING 12 GAP 33

    @api.one
    @api.constrains('solicitud_viatico_id', 'type', 'state')
    def _check_viatico(self):
        if self.state != 'cancel' and self.solicitud_viatico_id and self.search_count(
                [('id', '!=', self.id), ('solicitud_viatico_id', '=', self.solicitud_viatico_id.id),
                 ('type', '=', self.type), ('state', '!=', 'cancel')]):
            raise exceptions.ValidationError(_(u"La Solicitud de Viático está asociada a otro Adelanto no cancelado!"))
        return True

    # TODO: K SPRING 12 GAP 33
    def enviar_notificacion_af_anticipos(self, cr, uid, ids=None, context=None):
        rendicion_viatico_obj = self.pool.get('hr.expense.expense')
        fecha_asiento = (datetime.now() - relativedelta(days=60)).strftime('%Y-%m-%d')
        env = api.Environment(cr, 1, {})
        adelanto_ids = env['account.voucher'].search([('solicitud_viatico_id', '!=', False)])
        ir_model_data = env['ir.model.data']
        _model, group_id1 = ir_model_data.get_object_reference('account', 'group_account_manager')
        users1 = env['res.users'].search([('groups_id', 'in', group_id1)])
        if users1:
            body = u"Los siguientes funcionarios han tenido anticipos sin rendir por más de 60 días o tienen dos anticipos sin rendir\n\n"
            flag = False
            adelanto_atrasados_ids = adelanto_ids.filtered(lambda x: x.entry_date <= fecha_asiento)
            if adelanto_atrasados_ids:
                flag = True
                for adelanto_atrasados_id in adelanto_atrasados_ids:
                    body += (u"%s - %s. \n\n") % (adelanto_atrasados_id.partner_id.name, adelanto_atrasados_id.number or "")
            if not flag:
                funcionarios = {}
                for adelanto in adelanto_ids:
                    if not rendicion_viatico_obj.search_count(cr,uid,[('solicitud_viatico_id', '=', adelanto.solicitud_viatico_id.id)], context):
                        funcionario_id = adelanto.solicitud_viatico_id.solicitante_id
                        if not funcionarios.get(funcionario_id.id):
                            funcionarios.update({funcionario_id.id:[funcionario_id.name_get()[0][1],[str(adelanto.number)],1]})
                        else:
                            funcionarios[funcionario_id.id][1].append(str(adelanto.number))
                            funcionarios[funcionario_id.id][2] += 1
                for funcionario in funcionarios.values():
                    if funcionario[2] >= 2:
                        flag = True
                        body += (u"%s - %s. \n\n") % (funcionario[0], ', '.join(funcionario[1]))
            if flag:
                msg = body
                self.pool['mail.thread'].message_post(cr, uid, 0, body=msg, subject='Anticipos sin rendir', partner_ids=[user.partner_id.id for user in users1], context=context, subtype='mail.mt_comment')
        return True

    # TODO: K SPRING 12 GAP 33
    def enviar_notificacion_func_anticipos(self, cr, uid, ids=None, context=None):
        user = self.pool.get('res.users').browse(cr,uid, [uid])
        if ids:
            for record in self.browse(cr, uid, ids, context=context):
                retencion_ids = self.pool.get('hr.expense.expense').search(cr, uid, [('solicitud_viatico_id', '=', record.solicitud_viatico_id.id)])
                if not retencion_ids:
                    number = record.number or ""
                    msg = (u"Usted tiene un anticipo %s sin rendir. Debe realizar la rendición a la brevedad o el adelanto podrá ser descontado en la próxima liquidación de sueldos. \n\n") % (number)
                    self.pool['mail.thread'].message_post(cr, uid, 0, body=msg, subject='Anticipos sin rendir', partner_ids=[user.partner_id.id], context=context, subtype='mail.mt_comment')
        return True

    # TODO: SPRING 11 GAP 318 K
    @api.multi
    def actualizar_hr_expense(self):
        hr_expense = self.env['hr.expense.expense']
        rendicion_ids = []
        for voucher in self:
            if voucher.rendicion_viaticos_id or voucher.solicitud_viatico_id:
                if voucher.rendicion_viaticos_id:
                    if voucher.type == 'sale':
                        rendicion_ids.append(voucher.rendicion_viaticos_id.id)
                    # voucher_not_paid = self.search(
                    #     ['|', ('rendicion_viaticos_id', '=', voucher.rendicion_viaticos_id.id),
                    #      ('solicitud_viatico_id', '=', voucher.rendicion_viaticos_id.solicitud_viatico_id.id),
                    #      ('state', '!=', 'posted'),
                    #      ('id', '!=', voucher.id)])
                    # if not voucher_not_paid:
                    #     rendicion_ids.append(voucher.rendicion_viaticos_id.id)
                elif voucher.solicitud_viatico_id:
                    rendicion_viaticos_id = hr_expense.search(
                        [('solicitud_viatico_id', '=', voucher.solicitud_viatico_id.id),
                         ('state', '=', 'autorizado')], limit=1)
                    if rendicion_viaticos_id:
                        voucher_not_paid = self.search(
                            ['|', ('rendicion_viaticos_id', '=', rendicion_viaticos_id.id),
                             ('solicitud_viatico_id', '=', voucher.solicitud_viatico_id.id),
                             ('state', '!=', 'posted'),
                             ('id', '!=', voucher.id)])
                        if not voucher_not_paid:
                            rendicion_ids.append(rendicion_viaticos_id.id)
        if rendicion_ids:
            hr_expense.suspend_security().browse(rendicion_ids).write({'state': 'paid'})

    # TODO: L SPRING 11 GAP 28 M
    # TODO: R SPRING 11 GAP 28 M
    @api.multi
    def proforma_voucher(self):
        res = super(utec_adelanto_viaticos_v8, self).proforma_voucher()
        self.actualizar_hr_expense()
        for rec in self:
            for line_id in rec.line_ids.filtered(lambda x: x.amount > 0 and x.move_line_id.id):
                if not line_id.move_line_id.invoice:
                    voucher_id = self.env['account.voucher'].search(
                        [('move_id', '=', line_id.move_line_id.move_id.id)])
                    invoice_id = voucher_id.invoice_id
                    if voucher_id.solicitud_viatico_id:#RAGU si se gestiona el pago de la solicitud de viatico entonces marcar adelanto pagado
                        voucher_id.solicitud_viatico_id.suspend_security().write({'adelanto_pagado':True})
                    if voucher_id.rendicion_viaticos_id:#RAGU si se gestiona el pago de la rendicion de viatico entonces marcar adelanto pagado
                        #se cambia el estado con admin por temas de seguridad
                        voucher_id.rendicion_viaticos_id.suspend_security().write({'state': 'paid'})
                    if invoice_id.doc_type == 'adelanto_viatico':
                        voucher_id.write({'state':'pagado'})
                else:
                    invoice_id = line_id.move_line_id.invoice

                # RAGU al parecer la actualización del number está incorrecta, fue sacada
                # invoice_id.write({'fecha_inicio_pago': rec.fecha_inicio_pago, 'fecha_pago': rec.date,
                #      'number': rec.move_ids[0].ref})
                invoice_id.suspend_security().write({'fecha_inicio_pago': rec.fecha_inicio_pago, 'fecha_pago': rec.date})
        return res

    def _get_related_document(self):
        self.ensure_one()
        _related_document2 = False
        if self.rendicion_viaticos_id:
            _related_model = self.rendicion_viaticos_id._name
            _related_id = self.rendicion_viaticos_id.id
            # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
            # _related_document = self.rendicion_viaticos_id.sequence
            _related_document = self.rendicion_viaticos_id.x_sequence
            #
            _related_document2 = self.rendicion_viaticos_id.solicitud_viatico_id.name
            _view_id = u'view_expenses_form'
            _module_name = u'grp_viaticos'
        elif self.solicitud_viatico_id:
            _related_model = self.solicitud_viatico_id._name
            _related_id = self.solicitud_viatico_id.id
            _related_document = self.solicitud_viatico_id.name
            _view_id = False
            _module_name = False
        else:
            _related_model = False
            _related_id = False
            _related_document = False
            _view_id = False
            _module_name = False
        return {'related_document': _related_document, 'related_model': _related_model, 'related_id': _related_id,
                'module_name': _module_name, 'view_id': _view_id, 'related_document2':_related_document2}

#RAGU adicionando origenes de viaticos a las lineas del voucher
class grp_account_voucher_line(models.Model):
    _inherit = 'account.voucher.line'

    def _get_origin_dict(self):
        _supplier_invoice_number2 = False
        if self.origin_voucher_id.rendicion_viaticos_id:
            _related_model = self.origin_voucher_id.rendicion_viaticos_id._name
            _related_id = self.origin_voucher_id.rendicion_viaticos_id.id
            # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
            # _related_document = self.origin_voucher_id.rendicion_viaticos_id.sequence
            _related_document = self.origin_voucher_id.rendicion_viaticos_id.x_sequence
            #
            _invoice_id = False
            # 28/12/2018 ASM renombrar sequence (nombre reservado) a x_sequence
            # _supplier_invoice_number = self.origin_voucher_id.rendicion_viaticos_id.sequence
            _supplier_invoice_number = self.origin_voucher_id.rendicion_viaticos_id.x_sequence
            #
            _supplier_invoice_number2 = self.origin_voucher_id.rendicion_viaticos_id.solicitud_viatico_id.name
            _view_id = u'view_expenses_form'
            _module_name = u'grp_viaticos'
        elif self.origin_voucher_id.solicitud_viatico_id:
            _related_model = self.origin_voucher_id.solicitud_viatico_id._name
            _related_id = self.origin_voucher_id.solicitud_viatico_id.id
            _view_id = False
            _module_name = False
            _related_document = self.origin_voucher_id.solicitud_viatico_id.name
            _invoice_id = False
            _supplier_invoice_number = self.origin_voucher_id.solicitud_viatico_id.name
        else:
            return super(grp_account_voucher_line, self)._get_origin_dict()

        return {'related_document': _related_document,
                'related_model': _related_model,
                'related_id': _related_id,
                'module_name': _module_name,
                'view_id': _view_id,
                'invoice_id': _invoice_id,
                'supplier_invoice_number': _supplier_invoice_number,
                'supplier_invoice_number2': _supplier_invoice_number2}
