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

# TODO: K SPRING 12 GAP 70, 71, 73, 74
class GrpCrearRenovacionWizard(models.TransientModel):
    _name = 'grp.crear.renovacion.wizard'

    # TODO: K SPRING 12 GAP 70, 71, 73, 74
    @api.model
    def _default_contrato_id(self):
        contrato_id = self._context.get('default_contrato_id', False)
        return contrato_id and contrato_id or self.env['grp.contrato.proveedores']

    # TODO: K SPRING 12 GAP 70, 71, 73, 74
    @api.model
    def _domain_adjudicacion_ids(self):
        adjudicacion_ids = [('id', 'in', [])]
        adjudicacion_cont_ids = self._context.get('adjudicacion_ids', False)
        if adjudicacion_cont_ids:
            adjudicacion_ids = [('id', 'in', adjudicacion_cont_ids)]
        return adjudicacion_ids

    contrato_id = fields.Many2one('grp.contrato.proveedores', 'Contrato', default=lambda self: self._default_contrato_id())
    convenio = fields.Boolean(string='Contratos sin procedimiento de compras',related='contrato_id.convenio', readonly=True)
    tipo = fields.Selection([('renovacion', u'Renovación'),('ampliacion', u'Ampliación')], string=u"Renovación/ampliación", default='renovacion')
    nro_renovacion = fields.Integer(string='Nro de renovación', compute='_compute_nro_renovacion', readonly=True)
    adjudicacion_id = fields.Many2one('grp.cotizaciones', string=u'Adjudicación ampliada',
                                      domain=lambda self: self._domain_adjudicacion_ids())

    # TODO: K SPRING 12 GAP 70, 71, 73, 74
    @api.one
    @api.depends('contrato_id')
    def _compute_nro_renovacion(self):
        self.nro_renovacion = self.contrato_id.contador_renovaciones + 1

    # TODO: K SPRING 12 GAP 70, 71, 73, 74
    @api.multi
    def crear_renovacion(self):
        contrato_obj = self.env['grp.contrato.proveedores']
        mod_obj = self.env['ir.model.data']
        for rec in self:
            if rec.contrato_id.convenio and rec.tipo == 'renovacion':
                contrato_copy_id = rec.contrato_id.copy({'nro_renovacion':rec.nro_renovacion, 'state': 'draft'})

                rec.contrato_id.write({'contador_renovaciones': rec.nro_renovacion})
                descripcion = u"Nro Contrato/Resolucion %s, Nro. Renovacion %s" % (rec.contrato_id.nro_contrato, rec.nro_renovacion)

                res = mod_obj.get_object_reference('grp_contrato_proveedores', 'view_contract_proveedores_form')
                models = 'grp.contrato.proveedores'
                res_id = res and res[1] or False
                self.env['grp.acciones.contrato'].create({'contrato_id': rec.contrato_id.id,
                                                          'link': contrato_copy_id.id,
                                                          'se_copio': False,
                                                          'se_registro': True,
                                                          'tipo': 'Renovación/ampliación',
                                                          'descripcion': descripcion, })

                return {
                    'name': "Contrato de condiciones generales",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': models,
                    'res_id': contrato_copy_id.id,
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'context': self._context,
                }
            elif rec.adjudicacion_id:
                ordenes_a_crear = defaultdict(lambda:[])
                for lineas in rec.adjudicacion_id.sice_page_aceptadas.filtered(lambda x: x.contrato_generado != True and x.proveedor_cot_id.id == rec.contrato_id.proveedor.id):
                    key = str(lineas.proveedor_cot_id.id)
                    ordenes_a_crear[key].append(lineas)

                contratos_ids = []
                for k,v in ordenes_a_crear.items():
                    vals_contrato ={
                        'proveedor' : v[0].proveedor_cot_id.id,
                        'fecha_resolucion': fields.Date.today(),
                        'operating_unit_id': rec.adjudicacion_id.operating_unit_id.id,
                        'nro_adj_id': rec.adjudicacion_id.id,
                        'pedido_compra': rec.adjudicacion_id.pedido_compra_id.id,
                        'currency':self.env.user.company_id.currency_id.id,
                        'moneda':self.env.user.company_id.currency_id.id,
                        'convenio': False,
                    }
                    contrato_original_ids = contrato_obj.search([('contrato_original_id','=', False), ('contrato_general_id','=', False),
                                                 ('pedido_compra','=', rec.adjudicacion_id.nro_pedido_original_id.id),
                                                 ('proveedor','=', v[0].proveedor_cot_id.id)])
                    if rec.tipo == 'renovacion':
                        vals_contrato['nro_renovacion'] = rec.nro_renovacion
                        # TODO: K VARIANZA GRP
                        vals_contrato['contrato_original_id'] = contrato_original_ids[0].id
                        vals_contrato['nro_interno'] = contrato_original_ids[0].nro_interno
                    contrato_gen_id = contrato_obj.create(vals_contrato)
                    if contrato_original_ids:
                        descripcion = "Nro Contrato/Resolucion " + contrato_original_ids[0].nro_contrato
                        if rec.tipo == 'renovacion':
                            descripcion += u". Nro. Renovacion " + str(rec.nro_renovacion)
                            contrato_original_ids[0].write({'contador_renovaciones': rec.nro_renovacion})
                        self.env['grp.acciones.contrato'].create({'contrato_id': contrato_original_ids[0].id,
                                                          'link': contrato_gen_id.id,
                                                          'se_copio': False,
                                                          'se_registro': True,
                                                          'tipo': 'Renovación/ampliación',
                                                          'descripcion': descripcion,})
                    contratos_ids.append(contrato_gen_id.id)
                    for linea in v:
                        vals_contrato_part ={
                            'proveedor' : linea.proveedor_cot_id.id,
                            'fecha_resolucion': fields.Date.today(),
                            'operating_unit_id': linea.pedido_cot_id.operating_unit_id.id,
                            'nro_adj_id': linea.pedido_cot_id.id,
                            'pedido_compra': linea.pedido_cot_id.pedido_compra_id.id,
                            'contrato_general_id': contrato_gen_id.id,
                            'nro_line_adj_id': linea.id,
                            'codigo_articulo': linea.codigo_articulo,
                            'cantidad': linea.cantidad,
                            'currency': linea.currency.id,
                            'moneda': linea.currency.id,
                            'precio': linea.precio,
                            'precio_ajustado': linea.precio,
                            'convenio': False,
                        }
                        contrato_part_id = contrato_obj.create(vals_contrato_part)
                        contratos_ids.append(contrato_part_id.id)
                        # linea.write({'contrato_generado': True})

                # lineas_sin_cont = self.env['grp.cotizaciones.lineas.aceptadas'].search([('pedido_cot_id', '=', rec.adjudicacion_id.id),
                #                                        ('contrato_generado', '=', False)])
                # if not lineas_sin_cont:
                    # rec.adjudicacion_id.write({'contrato_generado': True})
                if contratos_ids:
                    data_pool = self.pool.get('ir.model.data')
                    action_model, action_id = data_pool.get_object_reference(self._cr, self._uid, 'grp_contrato_proveedores',
                                                                             'action_contract_proveedores_form')
                    if action_model:
                        action_pool = self.pool.get(action_model)
                        action = action_pool.read(self._cr, self._uid, action_id, context=self._context)
                        action['domain'] = "[('id','in', [" + ','.join(map(str, contratos_ids)) + "])]"
                    return action

        return True




