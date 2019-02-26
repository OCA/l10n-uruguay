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
import time
from openerp.exceptions import ValidationError
from openerp.tools import float_compare
import base64
import StringIO
from datetime import *

# TODO: SPRING 11 GAP 285 C
TYPE = [
    ('obligacion_invoice', u'Obligación'),
    ('3en1_invoice', u'3en1'),
    ('invoice', u'Factura'),
    ('nota_credito', u'Nota de crédito'),
    ('viatico', u'Viáticos')
]

TRANSFER_MTOIVE = [
    ('00', u'00-OTROS'),
    ('02', u'02-SUELDOS'),
    ('03', u'03-JUB Y PENSIONES'),
    ('04', u'04-HONORARIOS PROFESIONALES'),
    ('05', u'05-INGRESO X SERV. PERSONALES'),
    ('06', u'06-PRESTACIONES SOCIALES'),
    ('07', u'07-ALQUILERES'),
    ('08', u'08-PROVEEDORES')
]

STATE_SUMMARY = [('draft', 'Nuevo'),
                 ('send', 'Enviado'),
                 ('file_return', 'Archivo devuelto'),
                 ('confirm', 'Confirmado')]


def _get_selection_key(selection, current):
    result = filter(lambda x: x[0] == current, selection)
    return result[0][0] if len(result) else False


def _get_selection_value(selection, current):
    result = filter(lambda x: x[0] == current, selection)
    return result[0][1] if len(result) else False


class GrpTransferenciaCabezal(models.Model):
    _name = 'grp.transferencia.cabezal'
    _description = "Cabezal de transferencia"
    _rec_name = 'agreement'

    # TODO: C INCIDENCIA
    @api.model
    def _get_company_agreement(self):
        res = self.env['res.users'].browse(self._uid)
        if res and res.company_id:
            return res.company_id.agreement
        return ''

    journal_id = fields.Many2one('account.journal', string=u'Cuenta bancaria', required=True,
                                 domain=[('type', '=', 'bank')], states={'draft': [('readonly', False)]}, readonly=True)
    agreement = fields.Char(string=u'Convenio', required=True, default=lambda self: self._get_company_agreement(),
                            size=6, states={'draft': [('readonly', False)]}, readonly=True)
    date = fields.Date(string=u'Fecha', required=True, states={'draft': [('readonly', False)]}, readonly=True)
    production_date = fields.Many2one('account.period', string=u'Fecha de producción', required=True,
                                      states={'draft': [('readonly', False)]}, readonly=True)
    state = fields.Selection([('draft', 'Borrador'),
                              ('confirm', 'Confirmado'),
                              ('end', 'Finalizado')], required=True, default='draft')
    line_ids = fields.One2many('grp.transferencia.cabezal.line', 'transfer_id', string=u'Comprobantes',
                               states={'draft': [('readonly', False)]}, readonly=True)

    # RESUMEN BROU
    file_generate = fields.Binary(string='Archivo generado', filename="filename")
    filename = fields.Char(string='Archivo generado')
    file_return = fields.Binary(string='Archivo devuelto', filename="file_return_name")
    file_return_name = fields.Char(string='Archivo devuelto')
    state_brou = fields.Selection(STATE_SUMMARY, string="Estado", default='draft')
    line_brou_ids = fields.One2many('grp.transferencia.resumen.brou', 'transfer_id', string=u'Resumen BROU',
                                    states={'confirm': [('readonly', False)]}, readonly=True)

    # RESUMEN OTROS BANCOS
    state_other = fields.Selection(STATE_SUMMARY, string="Estado", default='draft')
    line_other_ids = fields.One2many('grp.transferencia.resumen.otro', 'transfer_id', string=u'Resumen otros bancos',
                                     states={'confirm': [('readonly', False)]}, readonly=True)
    line_other1_ids = fields.One2many('grp.transferencia.resumen.otro', 'transfer_id', string=u'Resumen otros bancos',
                                      states={'confirm': [('readonly', False)]}, readonly=True,
                                      domain=[('type', '=', 'UYU')])
    line_other2_ids = fields.One2many('grp.transferencia.resumen.otro', 'transfer_id', string=u'Resumen otros bancos',
                                      states={'confirm': [('readonly', False)]}, readonly=True,
                                      domain=[('type', '=', 'USD')])
    line_other3_ids = fields.One2many('grp.transferencia.resumen.otro', 'transfer_id', string=u'Resumen otros bancos',
                                      states={'confirm': [('readonly', False)]}, readonly=True,
                                      domain=[('type', '=', 'EUR')])
    other_files_ids = fields.One2many('grp.transferencia.resumen.otros_bancos_archivo', 'transfer_id',
                                      string=u'Archivos', states={'confirm': [('readonly', False)]}, readonly=True)
    mov_line_domain = fields.Many2many('account.move.line', string=u'Dominio de apuntes',
                                       compute='_compute_mov_line_domain')
    show_btn_send = fields.Boolean('Mostrar boton enviar', compute='_compute_show_btn_send')

    @api.multi
    def _compute_show_btn_send(self):
        for rec in self:
            rec.show_btn_send = len(rec.other_files_ids) > 0

    @api.multi
    @api.depends('journal_id')
    def _compute_mov_line_domain(self):
        for rec in self:
            mov_invoice_ids = self.env['account.invoice'].search([
                ('siif_tipo_ejecucion.codigo', '=', 'P'),
                ('type', '=', 'in_invoice'),
                ('fecha_aprobacion', '!=', False),
                ('state', '!=', 'paid'),
                ('cuenta_bancaria_id', '=',
                 rec.journal_id.id),
                ('move_id', '!=', False),
            ]).mapped('move_id').mapped('line_id').filtered(lambda l: l.credit > 0)

            mov_refund_ids = self.env['account.invoice'].search([
                ('siif_tipo_ejecucion.codigo', '=', 'P'),
                ('type', '=', 'in_refund'),
                ('fecha_aprobacion', '!=', False),
                ('state', '!=', 'paid'),
                ('cuenta_bancaria_id', '=',
                 rec.journal_id.id),
                ('move_id', '!=', False),
            ]).mapped('move_id').mapped('line_id').filtered(lambda l: l.debit > 0)

            # TODO Falta preguntar por el campo fecha_aprobacion del account.voucher que no se encuentra implementado
            # TODO verificar bien si el estado del acount.voucher es distino de Pago(posted) o Pagado (pagado)
            mov_voucher_ids = self.env['account.voucher'].search([('move_id', '!=', False),
                                                                  ('state', '!=', 'pagado'),
                                                                  '|', ('rendicion_viaticos_id', '!=', False),
                                                                  ('solicitud_viatico_id', '!=', False)]).mapped(
                'move_id').mapped('line_id').filtered(lambda l: l.credit > 0)

            mov_voucher_cancel_ids = self.env['account.voucher.line'].search([
                ('move_line_id', '!=', False),
                ('voucher_id.state', 'in', ['cancel'])
            ]).mapped('move_line_id').filtered(lambda l: l.credit > 0)

            result = mov_invoice_ids + mov_voucher_ids
            result = mov_invoice_ids + mov_refund_ids + mov_voucher_ids
            existing_transfer = self.env['grp.transferencia.cabezal.line'].search(
                [('move_line_id', 'in', result.ids), ('move_line_id', 'not in', mov_voucher_cancel_ids.ids)]).mapped('move_line_id')
            rec.mov_line_domain = (result - existing_transfer).ids

    @api.onchange('other_files_ids')
    def onchange_other_files_ids(self):
        if len(self.other_files_ids) and not len(self.other_files_ids.filtered(lambda x: not x.file_return)):
            self.state_other = 'file_return'

    @api.onchange('journal_id')
    def onchange_transfer_journal_id(self):
        if self.journal_id:
            self.line_ids = [(5,)]

    @api.multi
    def button_confirm(self):
        self.ensure_one()
        if len(self.line_ids) == 0:
            raise ValidationError(_("No se puede confirmar sin tener al menos un Comprobante añadido!"))
        brou_lines = self._prepare_lines('BROU')
        other_lines = self._prepare_lines('BROU', equals=False)
        # TODO: C INCIDENCIA
        self.mapped('line_brou_ids').unlink()
        self.mapped('line_other_ids').unlink()
        self.write({'state': 'confirm', 'line_brou_ids': [(0, 0, values) for values in brou_lines],
                    'line_other_ids': [(0, 0, values) for values in other_lines],
                    })

    @api.multi
    def button_cancel(self):
        self.write({'state': 'draft'})

    @api.multi
    def write(self, vals):
        if 'file_return' in vals:
            vals.update({'state_brou': 'file_return'})
        res = super(GrpTransferenciaCabezal, self).write(vals)
        if 'other_files_ids' in vals:
            for rec in self:
                if rec.other_files_ids and not rec.other_files_ids.filtered(lambda x: not x.file_return):
                    rec.write({'state_other': 'file_return'})
        return res

    @api.multi
    def btn_send(self):
        if 'brou' in self._context and self._context['brou']:
            self.write({'state_brou': 'send'})
        else:
            self.write({'state_other': 'send'})

    @api.multi
    def btn_cancel(self):
        if 'brou' in self._context and self._context['brou']:
            self.write({'state_brou': 'draft'})
        else:
            self.write({'state_other': 'draft'})

    @api.multi
    def btn_confirm(self):
        if 'brou' in self._context and self._context['brou']:
            filter_line = self.mapped('line_brou_ids').filtered('paid')
            self.line_confirm(filter_line, 'BROU')
            self.write({'state_brou': 'confirm'})
        else:
            filter_line = self.mapped('line_other_ids').filtered('paid')
            self.line_confirm(filter_line, 'BROU', False)
            self.write({'state_other': 'confirm'})
        if self.state_other == 'confirm' and self.state_brou == 'confirm' or \
                (not len(self.mapped('line_brou_ids')) and self.state_other == 'confirm') or \
                (not len(self.mapped('line_other_ids')) and self.state_brou == 'confirm'):
            self.write({'state': 'end'})

    @api.multi
    def btn_cancel(self):
        if 'brou' in self._context and self._context['brou']:
            self.write({'state_brou': 'draft'})
        else:
            self.write({'state_other': 'draft'})

    @api.multi
    def btn_select_all(self):
        for rec in self:
            if 'brou' in self._context and self._context['brou']:
                rec.line_brou_ids.write({'paid': True})
            else:
                rec.line_other_ids.write({'paid': True})

    @api.multi
    def btn_remove_all(self):
        for rec in self:
            if 'brou' in self._context and self._context['brou']:
                rec.line_brou_ids.write({'paid': False})
            else:
                rec.line_other_ids.write({'paid': False})

    @api.multi
    def _prepare_lines(self, bank_name, equals=True):
        for rec in self:
            filter_lines = rec.line_ids.filtered(
                lambda x: x.bank_id.name == bank_name if equals else x.bank_id.name != bank_name)
            result = {}
            for line in filter_lines:
                if str(line.partner_id.id) + '-' + str(line.currency_id.id) not in result:
                    result[str(line.partner_id.id) + '-' + str(line.currency_id.id)] = {
                        'currency_id': line.currency_id.id,
                        'acc_number': line.res_partner_bank_id.acc_number[:6],
                        'move_line_id': line.move_line_id.id,
                        'res_partner_bank_id': line.res_partner_bank_id.id,
                        'amount': 0}
                    if not equals:
                        result[str(line.partner_id.id) + '-' + str(line.currency_id.id)].update(
                            {'receiver': line.partner_id.name, 'acc_number': line.res_partner_bank_id.acc_number})
                result[str(line.partner_id.id) + '-' + str(line.currency_id.id)]['amount'] += line.amount
            return result.values()

    @api.multi
    def generate_file_brou(self):
        filter_line = self.line_brou_ids.filtered(lambda x: not x.paid)
        if len(filter_line):
            _head = 'Tipo Registro Marca Banco Filler Fecha de vencimiento Referencia de servicio Convenio Moneda Codigo del registro ' \
                    'Cuenta de credito Fecha de produccion Importe Filler Informacion empresa\r\n'
            lines = [_head]

            cant_register = total_amount = 0
            date_str = datetime.strptime(self.date, '%Y-%m-%d').strftime('%y%m%d')
            date_prod_str = datetime.strptime(self.production_date.name, '%m/%Y').strftime('%y%m')
            for line in filter_line:
                l = str(
                    1) + ' ' + ' ' + ' ' + '001' + ' ' + '00' + ' ' + date_str + ' ' + str('0' * 15) + ' ' + str(
                    self.agreement)
                if line.currency_id.name == 'UYU':
                    l += ' ' + '98'
                elif line.currency_id.name == 'USD':
                    l += ' ' + '01'
                else:
                    raise ValidationError(u'La moneda es diferente de UYU y USD')
                l += ' ' + 'D'
                credit_account = ''
                if line.concept == 'caja de ahorros':
                    credit_account += line.concept[:2]
                if line.concept == 'cuenta corriente':
                    credit_account += line.concept[:1]
                credit_account += line.office[:3] + line.acc_number + line.digit
                l += ' ' + credit_account + ' ' + date_prod_str + ' ' + str(
                    round(line.amount, 2)) + ' ' + '0' * 13 + ' ' + 'informacion_empresa' + '\r\n'
                lines.append(l)
                cant_register += 1
                total_amount += line.amount

            total_head = 'Tipo Registro Marca Banco Filler Fecha de vencimiento Pagos a acreditar Importe total a acreditar Pagos acreditados Importe total acreditado ' \
                         'Pagos no acreditadas Total no acreditado Comision IVA Informacion empresa\r\n'
            lines.append(total_head)
            # partner = filter_line[0].partner_id.name[:11] if len(filter_line) else ' ' * 11
            l = str(2) + ' ' + ' ' + ' ' + '001' + ' ' + '00' + ' ' + date_str + ' ' + str(
                cant_register) + ' ' + str(
                round(total_amount, 2)) + ' ' + '0' * 6 + ' ' + '0' * 18 + ' ' + '0' * 6 + ' ' + '0' * 18 \
                + ' ' + '0' * 16 + ' ' + '0' * 16 + ' ' + 'informacion_empresa'
            lines.append(l)
            iostr = StringIO.StringIO()
            iostr.writelines(lines)
            self.file_generate = base64.encodestring(iostr.getvalue())
            self.filename = 'PAGO_PROVEEDORES_BROU_.' + self.date + '.txt'
            self.set_account_format(filter_line)

    @api.one
    def generate_file_other(self):
        if len(self.line_other_ids):
            date_str = datetime.strptime(self.date, '%Y-%m-%d').strftime('%y%m%d')
            files = []
            filter_line1 = self.line_other_ids.filtered(lambda x: not x.paid and x.type == 'UYU')
            filter_line2 = self.line_other_ids.filtered(lambda x: not x.paid and x.type == 'USD')
            filter_line3 = self.line_other_ids.filtered(lambda x: not x.paid and x.type == 'EUR')
            self.get_other_file(filter_line1, date_str, files)
            self.get_other_file(filter_line2, date_str, files)
            self.get_other_file(filter_line3, date_str, files)
            self.other_files_ids.unlink()
            self.write({'other_files_ids': [(0, 0, value) for value in files]})
            self.set_account_format(filter_line1 + filter_line2 + filter_line3)

    def get_other_file(self, filter_lines, date_str, result):
        if len(filter_lines):
            _head = 'Tipo Registro Marca de proceso Banco Fecha de pago Código Convenio BIC Banco destino Moneda de la transferencia Importe a transferir Nombre del destinatario ' \
                    'Cuenta destino Motivo de la transferencia Relleno Dirección destinatario Observaciones\r\n'
            lines = [_head]
            cant_register = total_amount = 0
            # currency = len(filter_lines) and filter_lines[0].currency_id or False
            currency = filter_lines[0].currency_id
            convenio = self.agreement
            for line in filter_lines:
                l = str(
                    1) + ' ' + ' ' + ' ' + '001' + ' ' + date_str + ' ' + str(convenio) + ' ' + str(
                    line.bic)
                if line.currency_id.name == 'UYU':
                    l += ' ' + '98'
                if line.currency_id.name == 'USD':
                    l += ' ' + '02'
                if line.currency_id.name == 'EUR':
                    l += ' ' + '87'
                l += ' ' + str(round(line.amount, 2)) + ' ' + str(line.receiver) + ' ' + str(line.acc_number) + ' ' \
                     + str(_get_selection_value(TRANSFER_MTOIVE, line.transfer_motive)) + ' ' + '0' * 8
                l += ' ' + str(line.receiver_address) if line.receiver_address else ' ' * 35
                l += ' ' + str(line.observation) if line.observation else ' ' * 78
                l += '\r\n'

                lines.append(l)
                cant_register += 1
                total_amount += line.amount

            total_head = 'Tipo Registro Marca Banco Fecha de vencimiento Cantidad de transferencias a realizar Importe total a transferir Cantidad de transferencias realizadas ' \
                         'Cantidad de transferencias rechazadas Importe total rechazado Total de comisiones cobradas por BROU IVA de comisiones cobradas Relleno\r\n'
            lines.append(total_head)
            l = str(2) + ' ' + ' ' + ' ' + '001' + ' ' + date_str + ' ' + str(cant_register) + ' ' + str(
                round(total_amount,
                      2)) + ' ' + '0' * 6 + ' ' + '0' * 6 + ' ' + '0' * 14 + ' ' + '0' * 14 + ' ' + '0' * 14 + ' ' + ' ' * 135

            lines.append(l)
            iostr = StringIO.StringIO()
            iostr.writelines(lines)
            file_generate = base64.encodestring(iostr.getvalue())
            filename = 'PAGO_PROVEEDORES_OTROSBANCOS_' + self.date
            filename += '_' + currency.name + '.txt' if currency else ''
            filename += '.txt'
            Attachment = self.env['ir.attachment']
            attachment_id = Attachment.create({'name': filename, 'datas_fname': filename, 'db_datas': file_generate})
            result.append({'file_generate': attachment_id.id, 'filename': filename, 'currency': currency.id})
        return result

    def set_account_format(self, filter_lines):
        for line in filter_lines:
            partner_bank = line.res_partner_bank_id
            account = '{format}'
            acc_format = ''
            if partner_bank.bank.name == 'BROU':
                acc_str = partner_bank.agencia[:3] + partner_bank.acc_number[:6] + line.digit
                acc_format = '0' * (10 - len(acc_str)) + acc_str
                if not acc_str.isdigit():
                    raise ValidationError(
                        u'Formato de cuenta incorrecto para los bancos BROU, debe contener solo dígitos')
            if partner_bank.bank.name == 'CITI':
                acc_format = '0' * (10 - len(partner_bank.acc_number[:10])) + partner_bank.acc_number[:10]
                if acc_format[0] not in ['0', '1', '5']:
                    raise ValidationError(
                        u'El formato de la cuenta incorrecto para los bancos CITI, debe comenzar con 0, 1 ó 5')
            if partner_bank.bank.name == 'BANDES':
                acc_str = partner_bank.acc_number[:6]  # TODO falta iniciar con 3 digitos de la sucursal
                acc_format = acc_str
                if not acc_str.isdigit():
                    raise ValidationError(
                        u'Formato de cuenta incorrecto para los bancos BANDES, debe contener solo dígitos')
            if partner_bank.bank.name == 'ITAU':
                acc_str = partner_bank.acc_number[:7]
                acc_format = '0' * (7 - len(acc_str)) + acc_str
                if not acc_str.isdigit():
                    raise ValidationError(
                        u'Formato de cuenta incorrecto para los bancos ITAU, debe contener solo dígitos')
            if partner_bank.bank.name == 'SCOTIABANK':
                acc_str = partner_bank.bank_bic[:2]  # TODO falta iniciar con 8 digitos del numero del cliente
                acc_format = '0' * (10 - len(acc_str)) + acc_str
                if not acc_str.isdigit():
                    raise ValidationError(
                        u'Formato de cuenta incorrecto para los bancos SCOTIABANK, debe contener solo dígitos')
            if partner_bank.bank.name == 'DISCOUNT':
                acc_format = partner_bank.acc_number[:7]
            if partner_bank.bank.name == 'SANTANDER':
                acc_str = line.currency_id.name[:3]  # TODO falta completar con 4 digitos de la sucursal
                acc_format = '0' * (7 - len(acc_str)) + acc_str + ('0' * (
                    12 - len(partner_bank.bank_bic[:12]))) + partner_bank.bank_bic[:12]
                if not partner_bank.bank_bic[:12].isdigit():
                    raise ValidationError(
                        u'Formato de cuenta incorrecto para los bancos SANTANDER, la identificaión de la cuenta debe contener solo dígitos')
            if partner_bank.bank.name == 'NACION':
                acc_format = partner_bank.bank_bic[:12]
            if partner_bank.bank.name == 'BBVA':
                acc_format = partner_bank.bank_bic[:9]
                if not acc_format.isdigit():
                    raise ValidationError(
                        u'Formato de cuenta incorrecto para los bancos BBVA, la identificaión de la cuenta debe contener solo dígitos')
            if partner_bank.bank.name == 'HSBC':
                acc_format = '0' * (10 - len(partner_bank.bank_bic[:10])) + partner_bank.bank_bic[:10]
            if partner_bank.bank.name == 'BAPRO':
                acc_format = partner_bank.bank_bic[:7]
            if partner_bank.bank.name == 'HERITAGE':
                acc_str = '0' * (7 - len(partner_bank.acc_number[:7])) + partner_bank.acc_number[:7]
                acc_format = acc_str  # TODO falta completar con los 2 digitos de la subcuenta
                if not acc_format.isdigit():
                    raise ValidationError(
                        u'Formato de cuenta incorrecto para los bancos HERITAGE, debe contener solo dígitos')
            if partner_bank.bank.name == 'BHU':
                # TODO falta inicial con lo 3 digitos del sucursal
                # TODO falta 2 digitos del producto de la cuenta
                acc_str = '000-' + '00-' + '0' * (6 - len(partner_bank.acc_number[:6])) + partner_bank.acc_number[:6]
                acc_format = acc_str + '-' + partner_bank.acc_number[-1]
                if not acc_format.replace('-', '').isdigit():
                    raise ValidationError(
                        u'Formato de cuenta incorrecto para los bancos BHU, debe contener solo dígitos')

            line.write({'acc_number': account.format(format=acc_format)})

    def line_confirm(self, filter_lines, bank_name, equals=True):
        Voucher = self.env['account.voucher']
        for rec in filter_lines:
            voucher_data = {
                'type': 'payment',
                'partner_id': rec.partner_id.id,
                'amount': rec.amount,
                'journal_id': rec.transfer_id.journal_id.id,
                'account_id': rec.transfer_id.journal_id.default_credit_account_id.id,
                # 'advance_account_id': rec.transfer_id.journal_id.default_credit_account_id.id,
                'payment_method': 'transfer',
                'no_operation': '/',
                'date': rec.transfer_id.date,
                'company_id': self.env['res.users'].browse(self._uid).company_id.id,
                'operating_unit_id': rec.transfer_id.journal_id.operating_unit_id.id,
                'line_ids': [(0, 0, value) for value in
                             self._get_voucher_lines(rec.partner_id, rec.currency_id.id, bank_name, equals)]
            }
            voucher = Voucher.create(voucher_data)
            voucher.proforma_voucher()

    def _get_voucher_lines(self, partner_id, currency, bank_name, equals):
        data = []
        result = self.line_ids.filtered(lambda x: x.partner_id.id == partner_id.id and x.currency_id.id == currency and
                                                  (
                                                      x.bank_id.name == bank_name if equals else x.bank_id.name != bank_name))
        for line in result:
            data.append({
                'move_line_id': line.move_line_id.id,
                'amount': line.amount,
                'amount_unreconciled': line.amount,
                'amount_original': line.amount,
                'account_id': line.move_line_id.account_id.id,
                'type': 'dr',
            })
        return data

    # TODO: C INCIDENCIA
    @api.constrains('agreement')
    def _check_agreement(self):
        for rec in self:
            if not str(rec.agreement).isdigit():
                raise ValidationError(u"Convenio solo debe puede contener dígitos!")
        return True

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise ValidationError(u"No se pueden eliminar transferencias que no están en Borrador!")
        return super(GrpTransferenciaCabezal, self).unlink()


class GrpTransferenciaCabezalLine(models.Model):
    _name = 'grp.transferencia.cabezal.line'
    _description = "Comprobantes"

    transfer_id = fields.Many2one('grp.transferencia.cabezal', string=u'Apunte contable', ondelete='cascade')
    move_line_id = fields.Many2one('account.move.line', string=u'Transferencia cabezal', required=True)
    partner_id = fields.Many2one('res.partner', string=u'Proveedor/funcionario', related='move_line_id.partner_id',
                                 store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', string=u'Moneda', compute='_compute_common_fields',
                                  multi='fields')  # , related='move_line_id.currency_id'

    type = fields.Selection(TYPE, string=u'Tipo', compute='_compute_common_fields', multi='fields')
    number = fields.Char(string=u'Número', compute='_compute_common_fields', multi='fields')
    date = fields.Date(string=u'Fecha de comprobante', compute='_compute_common_fields', multi='fields')
    amount = fields.Float(string=u'Monto pendiente', compute='_compute_amount')
    approve_date = fields.Date(string=u'Fecha de aprobación', compute='_compute_common_fields', multi='fields')
    res_partner_bank_id = fields.Many2one('res.partner.bank', string=u'Información bancaria',
                                          compute='_compute_res_partner_bank_id', store=True)
    bank_id = fields.Many2one('res.bank', string=u'Banco')

    bank_domain = fields.Many2many('res.bank', string=u'Dominio_banks', compute='_compute_bank_domain')
    nro_factura_proveedor = fields.Char(string=u'Nro. Factura Proveedor', compute='_compute_common_fields')

    @api.multi
    @api.depends('partner_id')
    def _compute_bank_domain(self):
        for rec in self:
            rec.bank_domain = []
            if len(rec.partner_id.bank_ids.mapped('bank')):
                rec.bank_domain = rec.partner_id.bank_ids.mapped('bank').ids

    # TODO optimizar esto
    @api.one
    @api.constrains('bank_id', 'partner_id', 'res_partner_bank_id')
    def _check_bank(self):
        if self.partner_id and self.bank_id:
            if self.bank_id.name == 'BROU':
                if not self.res_partner_bank_id or (
                                    not self.res_partner_bank_id.state or not self.res_partner_bank_id.agencia or
                                not self.res_partner_bank_id.acc_number or not self.res_partner_bank_id.bank):
                    raise ValidationError(
                        u'Para el Proveedor %s falta definir Banco/Concepto/Oficina/Cuenta' % (self.partner_id.name,))
            else:
                if not self.res_partner_bank_id or (
                                        not self.res_partner_bank_id.bank_bic or
                                        not self.res_partner_bank_id.state or not self.res_partner_bank_id.agencia or
                                not self.res_partner_bank_id.acc_number or not self.res_partner_bank_id.bank):
                    raise ValidationError(u'Para el Proveedor %s falta definir Banco/Concepto/Oficina/Cuenta/BIC' % (
                        self.partner_id.name,))

    @api.onchange('move_line_id')
    def _onchange_move_line_id(self):
        if self.move_line_id:
            self.bank_id = len(self.move_line_id.partner_id.bank_ids) and self.move_line_id.partner_id.bank_ids[
                0].bank.id or False

    @api.multi
    @api.depends('move_line_id')
    def _compute_common_fields(self):
        for rec in self:
            if rec.move_line_id:
                rec.currency_id = rec.move_line_id.currency_id.id
                if not rec.move_line_id.currency_id.id:
                    rec.currency_id = self.env['res.users'].browse(self._uid).company_id.currency_id.id
                invoice = self.env['account.invoice'].search([('move_id', '=', rec.move_line_id.move_id.id)])
                if invoice.id:
                    rec.date = invoice.date_invoice
                    rec.number = invoice.number
                    rec.approve_date = invoice.fecha_aprobacion
                    if invoice.type == 'in_refund':
                        rec.type = 'nota_credito'
                    if invoice.type == 'in_invoice':
                        rec.type = _get_selection_key(TYPE, invoice.doc_type)
                    rec.nro_factura_proveedor = invoice.supplier_invoice_number
                else:
                    voucher = self.env['account.voucher'].search([('move_id', '=', rec.move_line_id.move_id.id)])
                    if voucher.id:
                        rec.date = voucher.date
                        rec.number = voucher.number
                        rec.type = 'viatico'

    @api.multi
    @api.depends('move_line_id', 'currency_id', 'type')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.move_line_id.credit
            currency_base_obj = self.env['res.users'].browse(self._uid).company_id.currency_id
            currency_base = currency_base_obj.id
            if currency_base != rec.currency_id.id:
                # rec.amount = rec.move_line_id.amount_currency
                ctx = dict(self._context)
                ctx.update({'date': rec.date or time.strftime('%Y-%m-%d')})
                currency_conversion = rec.transfer_id.journal_id.currency and\
                                      rec.transfer_id.journal_id.currency or\
                                      currency_base_obj
                rec.amount = rec.currency_id.with_context(ctx). \
                    compute(abs(rec.move_line_id.amount_currency), currency_conversion)
            else:
                if rec.type == 'nota_credito':
                    rec.amount = -rec.move_line_id.debit

    @api.multi
    @api.depends('partner_id', 'bank_id')
    def _compute_res_partner_bank_id(self):
        for rec in self:
            rec.res_partner_bank_id = False
            # TODO verificar si un partner puede tener varios res_partner_bank con el mismo Banco
            result = rec.partner_id.bank_ids.filtered(lambda x: x.bank.id == rec.bank_id.id)
            if len(result):
                rec.res_partner_bank_id = result[0].id

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.transfer_id.state not in ['draft']:
                raise ValidationError(u"No se pueden eliminar líneas de transferencias que no están en Borrador!")
        return super(GrpTransferenciaCabezalLine, self).unlink()


class GrpTransferenciaResumenBrou(models.Model):
    _name = 'grp.transferencia.resumen.brou'
    _description = "Resumen BROU"

    @api.one
    def _bank_type_get(self):
        bank_type_obj = self.env['res.partner.bank.type']
        result = []
        bank_types = bank_type_obj.search([])
        for bank_type in bank_types:
            result.append((bank_type.code, bank_type.name))
        return result

    @api.depends('move_line_id')
    def _get_factura_proveedor(self):
        for rec in self:
            invoice = self.env['account.invoice'].search([('move_id', '=', rec.move_line_id.move_id.id)])
            if invoice.id:
                rec.nro_factura_proveedor = invoice.supplier_invoice_number
            else:
                rec.nro_factura_proveedor = False

    move_line_id = fields.Many2one('account.move.line', string=u'Apunte contable', required=True)
    transfer_id = fields.Many2one('grp.transferencia.cabezal', string=u'Transferencia cabezal', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string=u'Proveedor/funcionario', related='move_line_id.partner_id',
                                 store=True, readonly=True)
    res_partner_bank_id = fields.Many2one('res.partner.bank', string=u'Información bancaria')
    state_brou = fields.Selection(STATE_SUMMARY, related='transfer_id.state_brou', string='Estado', readonly=True)
    currency_id = fields.Many2one('res.currency', string=u'Moneda')
    amount = fields.Float(string=u'Importe', digits=(15, 2))
    concept = fields.Selection(_bank_type_get, string=u'Concepto', related='res_partner_bank_id.state', readonly=True)
    office = fields.Char(string=u'Oficina', related='res_partner_bank_id.agencia', readonly=True)
    acc_number = fields.Char(string=u'Cuenta')  # , related='res_partner_bank_id.acc_number'
    digit = fields.Char(string=u'Dígito', size=1, compute='_compute_digit')
    paid = fields.Boolean(string=u'Pagado', default=False)
    nro_factura_proveedor = fields.Char(string=u'Nro. Factura Proveedor', compute='_get_factura_proveedor')

    @api.multi
    @api.depends('res_partner_bank_id')
    def _compute_digit(self):
        for rec in self:
            rec.digit = rec.res_partner_bank_id.acc_number[-1]

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.transfer_id.state not in ['draft']:
                raise ValidationError(u"No se pueden eliminar líneas de transferencias que no están en Borrador!")
        return super(GrpTransferenciaResumenBrou, self).unlink()


class GrpTransferenciaResumenOtros(models.Model):
    _name = 'grp.transferencia.resumen.otro'
    _description = "Resumen otros bancos"

    @api.one
    def _bank_type_get(self):
        bank_type_obj = self.env['res.partner.bank.type']
        result = []
        bank_types = bank_type_obj.search([])
        for bank_type in bank_types:
            result.append((bank_type.code, bank_type.name))
        return result

    @api.depends('move_line_id')
    def _get_factura_proveedor(self):
        for rec in self:
            invoice = self.env['account.invoice'].search([('move_id', '=', rec.move_line_id.move_id.id)])
            if invoice.id:
                rec.nro_factura_proveedor = invoice.supplier_invoice_number
            else:
                rec.nro_factura_proveedor = False

    move_line_id = fields.Many2one('account.move.line', string=u'Apunte contable', required=True)
    transfer_id = fields.Many2one('grp.transferencia.cabezal', string=u'Transferencia cabezal', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string=u'Proveedor/funcionario', related='move_line_id.partner_id',
                                 store=True, readonly=True)
    state_other = fields.Selection(STATE_SUMMARY, related='transfer_id.state_other', string='Estado', readonly=True)
    type = fields.Char(string='Tipo', compute='_compute_type', store=True)
    currency_id = fields.Many2one('res.currency', string=u'Moneda')
    res_partner_bank_id = fields.Many2one('res.partner.bank', string=u'Información bancaria')
    amount = fields.Float(string=u'Importe')
    bic = fields.Char(string=u'BIC', related='res_partner_bank_id.bank_bic', readonly=True)
    acc_number = fields.Char(string=u'Cuenta destino')  # , related='res_partner_bank_id.acc_number'
    receiver = fields.Char(string=u'Destinatario', size=35, required=True)
    transfer_motive = fields.Selection(TRANSFER_MTOIVE, string=u'Motivo de transferecia', required=True, default='00')
    receiver_address = fields.Char(string=u'Dirección del destinatario')
    observation = fields.Char(string=u'Observaciones', size=78)
    paid = fields.Boolean(string=u'Pagado', default=False)
    nro_factura_proveedor = fields.Char(string=u'Nro. Factura Proveedor', compute='_get_factura_proveedor')

    @api.multi
    @api.depends('move_line_id')
    def _compute_type(self):
        for rec in self:
            rec.type = rec.currency_id and rec.currency_id.name or ''

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.transfer_id.state not in ['draft']:
                raise ValidationError(u"No se pueden eliminar líneas de transferencias que no están en Borrador!")
        return super(GrpTransferenciaResumenOtros, self).unlink()


class GrpTransferenciaResumenOtrosArchivo(models.Model):
    _name = 'grp.transferencia.resumen.otros_bancos_archivo'
    _description = "Resumen otros bancos archivo"

    transfer_id = fields.Many2one('grp.transferencia.cabezal', string=u'Transferencia cabezal', ondelete='cascade')
    state_other = fields.Selection(STATE_SUMMARY, related='transfer_id.state_other', string='Estado', readonly=True)
    currency = fields.Many2one('res.currency', string=u'Moneda', readonly=True)
    file_generate = fields.Many2one('ir.attachment', string='Archivo generado', readonly=True)
    filename = fields.Char(string='Archivo generado')
    # file_return = fields.Many2one('ir.attachment', string='Archivo devuelto')
    file_return = fields.Binary(string='Archivo devuelto', filename="file_return_name")
    file_return_name = fields.Char(string='Archivo devuelto')

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.transfer_id.state not in ['draft']:
                raise ValidationError(u"No se pueden eliminar líneas de transferencias que no están en Borrador!")
        return super(GrpTransferenciaResumenOtrosArchivo, self).unlink()
