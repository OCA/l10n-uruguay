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

from openerp import models, fields, api, exceptions
from openerp.tools.translate import _
from datetime import *

# TODO: SPRING 10 GAP 474 M

class GrpCaja(models.Model):
    _name = 'grp.caja'
    _description = "Caja"
    _rec_name = 'caja'

    caja = fields.Char('Caja', size=60)
    caja_chica_t = fields.Boolean(u"Caja chica tesorería", related='journal_id.caja_chica_t', readonly=True, store=True)
    type = fields.Selection(u"Tipo de diario", related='journal_id.type', readonly=True, store=True)
    operating_unit_id = fields.Many2one('operating.unit', string='Unidad ejecutora')
    operating_unit_ids = fields.Many2many('operating.unit',
                                          'operating_unit_grp_caja_rel',
                                          'user_id', 'box_id', 'Unidades ejecutoras')
    journal_id = fields.Many2one('account.journal', 'Diario',domain=[('type', 'in', ['cash','bank'])])# TODO: M INCIDENCIA
    currency_id = fields.Many2one('res.currency', u'Divisa',related='journal_id.currency', readonly=True)
    active = fields.Boolean(u'Activo',default=True)
    caja_pagadora = fields.Boolean(u'Caja pagadora', default=False)
    caja_recaudadora = fields.Boolean(u'Caja recaudadora', default=False)
    control_efectivo = fields.Boolean(u'Control de efectivo', default=False)
    caja_principal = fields.Boolean(u'Caja principal', default=False)
    fondo_terceros = fields.Boolean(u'Fondo de terceros')
    otras_cajas = fields.Boolean(u'Otras cajas - tickets, vales combustible, otro')
    # TODO: De momento se va a implementar una relacion Many2many para no afectar la clase account.cashbox.line
    cashbox_line_ids = fields.Many2many('account.cashbox.line', 'account_cashbox_caja_rel'
                                        'cashbox_id', 'caja_id', string=u'Monedas disponibles', copy=False)
    cuenta_analitica_id = fields.Many2one('account.analytic.account', u'Cuenta analítica')
    users = fields.Many2many('res.users', 'res_groups_users_rel_grp_caja', 'box_id', 'uid', 'Users')

    @api.onchange('caja_pagadora')
    def _onchange_caja_pagadora(self):
        for record in self:
            if record.caja_pagadora:
                record.caja_recaudadora = False


    @api.onchange('caja_recaudadora')
    def _onchange_caja_recaudadora(self):
        for record in self:
            if record.caja_recaudadora:
                record.caja_pagadora = False

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        res = {}
        pieces_list = [x.pieces for x in self.journal_id.cashbox_line_ids] if self.journal_id else []
        domain = str([('pieces', 'in', pieces_list)])
        res.update({'domain': {'cashbox_line_ids': domain}})
        return res

    @api.multi
    @api.constrains('cashbox_line_ids')
    def _check_cashbox_line_ids(self):
        for rec in self:
            if rec.cashbox_line_ids and rec.control_efectivo:
                pieces =rec.cashbox_line_ids.mapped('pieces')
                value = filter(lambda x: pieces.count(x)>1, pieces)
                if value:
                    raise exceptions.ValidationError(
                        u'Existe mas de una moneda con el mismo valor.')


    @api.multi
    def unlink(self):
        for rec in self:
            if self.env['grp.caja.pagadora.tesoreria'].search([('box_id', '=', rec.id)]):
                raise exceptions.ValidationError(
                    _(u'No se puede eliminar una caja que está relacionada en una caja pagadora.'))
            if self.env['grp.caja.recaudadora.tesoreria'].search([('box_id', '=', rec.id)]):
                raise exceptions.ValidationError(
                    _(u'No se puede eliminar una caja que está relacionada en una caja recaudadora.'))
        return super(GrpCaja, self).unlink()


class grpAccountCashboxLine(models.Model):
    _inherit = 'account.cashbox.line'

    @api.multi
    def unlink(self):
        for rec in self:
            caja_ids = self.env['grp.caja'].search([('cashbox_line_ids', '=', rec.id)])
            if caja_ids:
                raise exceptions.ValidationError(
                    _(u'La moneda esta siendo utilizada en una caja.'))
        return super(grpAccountCashboxLine, self).unlink()


# TODO: SPRING 11 GAP 292 M
class GrpProductoCuentaDeposito(models.Model):
    _name = 'grp.producto.cuenta.deposito'
    _rec_name = 'product_id'
    _description = u"Mapeo producto cuenta depósito"

    product_id = fields.Many2one('product.product', u'Producto', domain=[('sale_ok', '=', True)])
    account_id = fields.Many2one('account.account', u'Cuenta depósito')
    active = fields.Boolean(u'Activo',default=True)
    no_siif = fields.Boolean(u'No SIIF',default=False)

    @api.constrains('product_id')
    def _check_name(self):
        for rec in self:
            product = self.search([('product_id', '=', rec.product_id.id)])
            if product and len(product.ids) > 1:
                raise exceptions.ValidationError(_(u'Solo debe existir un registro por producto.'))


# TODO: M SPRING 11 GAP 292.A
class GrpConceptoFactura(models.Model):
    _name = 'grp.concepto.factura'
    _rec_name = 'product_id'
    _description = u"Mapeo conceptos-facturas"

    product_id = fields.Many2one('product.product', u'Producto', domain=[('sale_ok', '=', True)])
    concept = fields.Char('Concepto', size=20)
    active = fields.Boolean(u'Activo', default=True)


# TODO: M SPRING 11 GAP 292.A
class GrpOrigenFactura(models.Model):
    _name = 'grp.origen.factura'
    _rec_name = 'origin'
    _description = u'Origen de factura'

    origin = fields.Char('Origen', size=20)
    active = fields.Boolean(u'Activo', default=True)






