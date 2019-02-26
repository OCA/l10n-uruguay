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

from openerp import fields, models, api, exceptions, _
from openerp.exceptions import ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

# TODO: K SPRING 12 GAP 205
class GrpMotivoDesviosMontosWizard(models.TransientModel):
    _name = 'grp.motivo.desvios.montos.wizard'

    contrato_id = fields.Many2one('grp.contrato.proveedores', 'Contrato')
    invoice_id = fields.Many2one("account.invoice", string=u'Factura')
    motivo = fields.Char(string=u"Motivo", required=True)

    # TODO: K SPRING 12 GAP 70, 71, 73, 74
    @api.multi
    def crear_control_proveedores(self):
        for rec in self:
            if self.contrato_id and self.contrato_id:
                monto_mensual = 0
                proveedores_hab_id = self.contrato_id.proveedores_hab_ids.filtered(lambda x: x.proveedor.id == self.invoice_id.partner_id.id)
                if proveedores_hab_id:
                    monto_mensual = proveedores_hab_id[0].monto_mensual
                self.env['grp.control.proveedores.contrato'].create({'contrato_id': self.contrato_id.id,
                                                          'invoice_id': self.invoice_id.id,
                                                          'monto_mensual': monto_mensual,
                                                          'motivo': self.motivo,
                                                          })
        return True




