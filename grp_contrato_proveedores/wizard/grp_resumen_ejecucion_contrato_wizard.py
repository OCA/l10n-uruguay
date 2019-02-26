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
from collections import defaultdict
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

# TODO: K SPRING 13 GAP 452
class GrpResumenEjecucionContratoWizard(models.TransientModel):
    _name = 'grp.resumen.ejecucion.contrato.wizard'

    # TODO: K SPRING 13 GAP 452
    # @api.model
    # @api.depends('proveedor')
    # def _domain_contrato_ids(self):
    #     contrato_obj = self.env['grp.contrato.proveedores']
    #     if self.proveedor:
    #         contrato_ids = contrato_obj.search([('contrato_general_id','=', False),('proveedor','=', self.proveedor.id)])
    #     else:
    #         contrato_ids = contrato_obj.search([('contrato_general_id','=', False)])
    #     contrato_domain_ids = [('id', 'in', [])]
    #     if contrato_ids:
    #         contrato_domain_ids = [('id', 'in', contrato_ids._ids)]
    #     return contrato_domain_ids

    fecha_inicio = fields.Date(string=u"Fecha inicio")
    fecha_fin = fields.Date(string=u"Fecha finalización")
    proveedor = fields.Many2one('res.partner', string=u"Proveedor", domain=[('supplier', '=', True)])
    contrato_id = fields.Many2one('grp.contrato.proveedores', 'Contrato')
    contrato_domain_ids = fields.Many2many('grp.contrato.proveedores',string='Dominio dinámico para contrato', compute='_compute_contrato_domain_ids')

    # TODO: K SPRING 13 GAP 452
    @api.multi
    @api.depends('proveedor')
    def _compute_contrato_domain_ids(self):
        contrato_obj = self.env['grp.contrato.proveedores']
        for record in self:
            if record.proveedor :
                ids = contrato_obj.search([('contrato_general_id','=', False),('proveedor','=', self.proveedor.id),('state','=', 'vigente')]).ids
            else:
                ids = contrato_obj.search([('contrato_general_id','=', False),('state','=', 'vigente')]).ids
            record.contrato_domain_ids = ids

    # TODO: K SPRING 13 GAP 452
    def print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}

        data = self.read(cr, uid, ids)[0]
        datas = {
             'ids': [],
             'model': 'grp.contrato.proveedores',
             'form': data
            }
        return self.pool['report'].get_action(cr, uid, [], 'grp_contrato_proveedores.report_resumen_ejecucion_contrato', data=datas, context=context)


    # TODO: K SPRING 13 GAP 452
    def xls_export(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}

        data = self.read(cr, uid, ids)[0]
        datas = {
             'ids': data['contrato_domain_ids'],
             'model': 'grp.contrato.proveedores',
             'form': data
            }
        # return self.pool['report'].get_action(cr, uid, [], 'grp_contrato_proveedores.grp_ejecucion_futura_contrato_xls', data=datas, context=context)
        return {'type': 'ir.actions.report.xml',
                    'report_name': 'grp_contrato_proveedores.grp_resumen_ejecucion_contrato_xls',
                    'datas': datas}





