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

# TODO: K SPRING 12 GAP 70, 71, 73, 74
class GrpCrearProrrogaWizard(models.TransientModel):
    _name = 'grp.crear.prorroga.wizard'

    # TODO: K SPRING 12 GAP 70, 71, 73, 74
    @api.model
    def _default_contrato_id(self):
        contrato_id = self._context.get('default_contrato_id', False)
        return contrato_id and contrato_id or self.env['grp.contrato.proveedores']

    contrato_id = fields.Many2one('grp.contrato.proveedores', 'Contrato', default=lambda self: self._default_contrato_id())
    fecha_fin = fields.Date(string=u"Fecha finalización")

    # TODO: K SPRING 12 GAP 70, 71, 73, 74
    @api.multi
    def crear_prorroga(self):
        for rec in self:
            if rec.contrato_id:
                if rec.contrato_id.fecha_fin >= rec.fecha_fin:
                    raise exceptions.ValidationError(u'La fecha de finalización seleccionada debe ser mayor que la del contrato que se prorroga.')
                link = rec.contrato_id.copy({
                    'contrato_original_id': rec.contrato_id.id,
                    'state': 'end',
                })

                #  TODO: L SPRING 12 GAP 84
                c_o = rec.contrato_id
                vals_contrato = {
                    'nro_interno': c_o.nro_interno,
                    'secuencia': c_o.secuencia,
                    'proveedor': c_o.proveedor.id,
                    'tipo_resolucion': c_o.tipo_resolucion.id,
                    'fecha_resolucion': c_o.fecha_resolucion,
                    'fecha_inicio': c_o.fecha_inicio,
                    'fecha_fin': c_o.fecha_fin,
                    'nro_contrato': c_o.nro_contrato,
                    'moneda': c_o.moneda.id,
                    'monto_resolucion': c_o.monto_resolucion,
                    'prorroga': c_o.prorroga,
                    'state': c_o.state,
                    'tipo_prorroga': c_o.tipo_prorroga,
                    'renovacion': c_o.renovacion,
                    'plazo': c_o.plazo,
                    'parametrica_formula_id': c_o.parametrica_formula_id.id,
                    'parametrica_periodicidad_id': c_o.parametrica_periodicidad_id.id,
                    'fecha_base_ajuste': c_o.fecha_base_ajuste,
                    'ultima_actualizacion': c_o.ultima_actualizacion,
                    'proxima_actualizacion': c_o.proxima_actualizacion,
                    'precio_ajustado': c_o.precio_ajustado,
                    'note': c_o.note,
                    'pedido_compra': c_o.pedido_compra.id,
                    'tipo_compra': c_o.tipo_compra.id,
                    'description': c_o.description,
                    'periodo_oc': c_o.periodo_oc,
                    'se_valido': c_o.se_valido,
                    'cession_type': c_o.cession_type,
                    'operating_unit_id': c_o.operating_unit_id.id,
                    'department_id': c_o.department_id.id,
                    'nro_adj_id': c_o.nro_adj_id.id,
                    'tipo_contrato_id': c_o.tipo_contrato_id.id,
                    'nro_cuenta': c_o.nro_cuenta,
                    'fecha_celebracion': c_o.fecha_celebracion,
                    'give_amount_total': c_o.give_amount_total,
                    'contrato_original_id': c_o.contrato_original_id.id,
                    'nro_renovacion': c_o.nro_renovacion,
                    'renovacion_alert': c_o.renovacion_alert,
                    'show_warning': c_o.show_warning,
                    'cantidad_renovaciones': c_o.cantidad_renovaciones,
                    'contador_renovaciones': c_o.contador_renovaciones,
                    'convenio': c_o.convenio,
                    'control_proveedores': c_o.control_proveedores,
                    'link': c_o.id,
                    'fecha_modificacion': fields.Date.today(),
                }
                self.env['grp.historial.contratos'].create(vals_contrato)
                self.env['grp.acciones.contrato'].create({'contrato_id': rec.contrato_id.id,
                                                          'link': link.id,
                                                          'se_copio': True,
                                                          'se_registro': False,
                                                          'tipo': 'Prórroga',
                                                          'descripcion': "Fecha original " + \
                                                                         datetime.strptime(rec.contrato_id.fecha_fin, "%Y-%m-%d").strftime("%d/%m/%Y") \
                                                                         + ". Nueva Fecha Fin " + \
                                                                         datetime.strptime(rec.fecha_fin, "%Y-%m-%d").strftime("%d/%m/%Y"),})

                rec.contrato_id.write({'fecha_fin': rec.fecha_fin})
        return True




