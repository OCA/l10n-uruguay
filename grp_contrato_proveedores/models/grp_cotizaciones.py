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

from openerp import api, fields, models, exceptions, _
from openerp import SUPERUSER_ID
import time
from collections import defaultdict


# ================================================================
## COTIZACIONES
# ================================================================
#
# TODO: K SPRING 12 GAP 67
class GrpContratoCotizaciones(models.Model):
    _inherit = 'grp.cotizaciones'

    contratos_ids = fields.One2many("grp.contrato.proveedores", "nro_adj_id", string=u"Contratos")
    contrato_generado = fields.Boolean(u"Todos los contatos generados", compute='_compute_contrato_generado',
                                       store=False)

    @api.multi
    def _compute_contrato_generado(self):
        contrato_obj = self.env['grp.contrato.proveedores']
        for rec in self:
            rec.contrato_generado = contrato_obj.search_count(
                [('nro_line_adj_id', 'in', rec.sice_page_aceptadas.ids), ('state', '!=', 'cancel')]) == len(
                rec.sice_page_aceptadas)

    # @api.multi
    # def button_Crear_OC(self):
    #     purchase_obj = self.env['purchase.order']
    #     action = super(GrpContratoCotizaciones, self).button_Crear_OC()
    #     str_ids = action['domain'][action['domain'].find('in'):]
    #     ids = str_ids[str_ids.find('[')+1:str_ids.find(']')].split(',')
    #     purchases = purchase_obj.search([('id','in', ids)])
    #     if purchases:
    #         for pucharse in purchases:
    #             pucharse.contrato_id
    #     return action

    def button_Crear_OC(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context = dict(context)
        order_pool = self.pool.get('purchase.order')
        product_product = self.pool.get('product.product')
        # TODO: SPRING 12 GAP 67 K
        contrato_obj = self.pool.get('grp.contrato.proveedores')
        order_ids = []
        rate_date = time.strftime('%Y-%m-%d')
        for cotizacion in self.browse(cr, uid, ids, context=context):
            pc_apg_id = False
            if cotizacion.pedido_compra_id.id:
                if cotizacion.pedido_compra_id.apg_ids:
                    for apg in cotizacion.pedido_compra_id.apg_ids:
                        # if apg.state != 'anulada':
                        if apg.state in ['afectado']:
                            pc_apg_id = apg.id
                            break
                else:
                    raise exceptions.ValidationError(u'No hay APG asociada al pedido de compra.')

            ordenes_a_crear = defaultdict(lambda: [])
            for lineas in cotizacion.sice_page_aceptadas:
                key = str(lineas.proveedor_cot_id.id) + str(lineas.currency.id)
                ordenes_a_crear[key].append(lineas)
                # ordenes_a_crear[lineas.proveedor_cot_id.id].append(lineas)
            for k, v in ordenes_a_crear.items():
                newlines = []
                llavep_data = []
                if v[0].currency.id:
                    context.update({ 'date': rate_date })
                    currency = self.pool.get('res.currency').browse(cr, uid, v[0].currency.id, context=context)
                    rate = currency.rate_presupuesto
                else:
                    raise exceptions.ValidationError(u'Debe definir la moneda!')
                    # raise osv.except_osv ( 'Error!', u'Debe definir la moneda!' )
                # 001 - Default location
                loc_id = self._get_location(cr, uid, cotizacion, context=context)
                if loc_id:
                    picking_aux = self._get_picking(cr, uid, loc_id)
                else:
                    picking_aux = False
                values = {
                    'doc_origen': cotizacion.id,
                    'origin': cotizacion.name,  # agregado
                    'notes': cotizacion.observaciones,  # agregado por incidencia 12/02, cambiado a notes
                    'descripcion': cotizacion.sice_descripcion,  # agregado por incidencia dia 13/03
                    # 'type' : 'cancilleria',     # agregado   comentado echaviano
                    'partner_id': v[0].proveedor_cot_id.id,
                    'pedido_compra_id': cotizacion.pedido_compra_id.id or False,
                    'pc_apg_id': pc_apg_id or False,
                    'currency_oc': v[0].currency.id,
                    'cod_moneda': v[0].cod_moneda.id,
                    'fecha_tipo_cambio_oc': rate_date,
                    'tipo_de_cambio': rate or False,
                    # 'currency_oc' : cotizacion.currency.id,
                    'order_line': newlines,
                    'page_apg_oc': False,
                    # 'location_id' : v[0].product_id and v[0].product_id.property_stock_inventory and v[0].product_id.property_stock_inventory.id or False,
                    'location_id': loc_id,
                    # 'location_id' : self.pool.get('stock.inventory.line')._default_stock_location(cr,uid),
                    'pricelist_id': self.pool.get('res.partner').browse(cr, SUPERUSER_ID, v[
                        0].proveedor_cot_id.id).property_product_pricelist_purchase.id,
                    # 'picking_type_id': 6, # echaviano, esto no se como sacarlo
                    'picking_type_id': picking_aux,
                }
                # inicializando diccionario lineas agrupadas
                # 002 Inicio
                lineas_crear = defaultdict(lambda: [])
                for lines in v:
                    if not lines.product_id:
                        raise exceptions.ValidationError(
                            u'No hay producto definido en alguna línea de la adjudicación!')
                        # raise osv.except_osv('Error!', u'No hay producto definido en alguna línea de la adjudicación!' )
                    # key = str(lines.product_id.id)
                    key = str(lines.product_id.id) + str(lines.id_item).zfill(3) + str(lines.id_variacion).zfill(3)
                    lineas_crear[key].append(lines)
                data_prod_group = defaultdict(lambda: [])
                for k, v in lineas_crear.items():
                    first_taxes = []
                    rest_taxes = []
                    sum_ttal = 0.0
                    sum_cantidad = 0.0
                    i = 0
                    for elem in v:
                        sum_ttal += elem.precio * elem.cantidad  # elem.subtotal
                        sum_cantidad += elem.cantidad
                        if elem.iva:
                            ivas = [x.id for x in elem.iva]
                            if i == 0:
                                first_taxes.append(ivas)
                            else:
                                rest_taxes.append(ivas)
                        i += 1
                    if first_taxes:
                        # if len(first_taxes[0]) != len(rest_taxes[0]):
                        #     raise osv.except_osv('Error!', u'Los impuestos de los productos deben ser correspondientes!' )
                        for tax in first_taxes[0]:
                            for rtax in rest_taxes:
                                if tax not in rtax or len(first_taxes[0]) != len(rtax):
                                    raise exceptions.ValidationError(
                                        u'Los impuestos de los productos deben ser correspondientes!')
                                    # raise osv.except_osv('Error!', u'Los impuestos de los productos deben ser correspondientes!' )

                    if sum_cantidad > 0:
                        data_prod_group[k] = {'precio': sum_ttal / sum_cantidad, 'cantidad': sum_cantidad}
                    else:
                        data_prod_group[k] = {'precio': 0, 'cantidad': 0}

                    # 'taxes_id':  [(6, 0, [x.id for x in v[0].iva])],
                    # data_prod_group[k].append({'precio': sum_ttal / sum_cantidad, 'cantidad':sum_cantidad })
                    # precio promedio y cantidad

                for k, v in lineas_crear.items():
                    dummy, prod_name = product_product.name_get(cr, uid, v[0].product_id.id, context=context)[0]
                    # # TODO: C SPRING 13 GAP 451
                    # if v[0].cantidad < data_prod_group[k]['cantidad']:
                    #     raise exceptions.ValidationError(u'La cantidad de la linea de la orden de compra es mayor que la cantidad de la linea adjudicada!')
                    if data_prod_group[k]['cantidad']:
                        newlines.append((0, 0, {
                            'product_id': v[0].product_id.id,
                            'product_uom': v[0].uom_id.id,
                            'name': prod_name or v[0].product_id.product_tmpl_id.description or '',  # incidencia
                            'date_planned': cotizacion.fecha_respuesta,
                            'product_qty': data_prod_group[k]['cantidad'],  # v[0].cantidad,
                            # 'product_qty' : lines.product_requested_qty,
                            'price_unit': data_prod_group[k]['precio'],  # lines.precio,
                            'taxes_id': [(6, 0, [x.id for x in v[0].iva])],
                            # 'taxes_id' :  [(6, 0, [x.id for x in lines.tax_id])],
                            # MVARELA 24_03 - Campos intefaz SICE
                            'id_variacion': v[0].id_variacion,
                            'id_item': v[0].id_item,
                            'desc_variacion': v[0].desc_variacion,
                            'cod_moneda': v[0].cod_moneda.id,
                            'cotizaciones_linea_id': v[0].id,  # TODO: SPRING 12 GAP 67 K
                        }))
                # 002 Fin
                # ACTUALIZAR FECHA CONTEXTO
                fiscalyear_obj = self.pool.get('account.fiscalyear')
                uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
                fecha_hoy = cotizacion.fecha_respuesta
                fiscal_year_id = False
                if fecha_hoy:
                    fiscal_year_id = fiscalyear_obj.search(cr, uid, [('date_start', '<=', fecha_hoy),
                                                                     ('date_stop', '>=', fecha_hoy),
                                                                     ('company_id', '=', uid_company_id)],
                                                           context=context)
                    fiscal_year_id = fiscal_year_id and fiscal_year_id[0] or False
                    context.update({'fiscalyear_id': fiscal_year_id})
                    # agregado, echaviano 05/01
                    values.update({'fiscalyear_siif_id': fiscal_year_id})

                cotizacion_values_lines = []
                for linea_apg in cotizacion.page_apg:
                    if fiscal_year_id and fiscal_year_id == linea_apg.fiscalyear_siif_id.id:
                        monto_apg = 0
                        for llp in linea_apg.llpapg_ids:
                            monto_apg += llp.importe
                        cotizacion_values_lines.append((0, 0, {
                            'nro_apg': linea_apg.id,
                            'descripcion_apg': linea_apg.descripcion,
                            # 'monto_apg': linea_apg.monto,
                            'monto_apg': monto_apg,
                            'currency': linea_apg.moneda.id,
                            'fecha_apg': linea_apg.fecha,
                            'nro_afectacion_apg': linea_apg.nro_afectacion_siif,
                        }))
                if cotizacion_values_lines:
                    values.update({'page_apg_oc': cotizacion_values_lines})

                values['operating_unit_id'] = cotizacion.operating_unit_id.id
                # TODO: SPRING 12 GAP 67 K
                contrato_id = contrato_obj.search(cr, uid, [('nro_adj_id', '=', cotizacion.id),
                                                            ('contrato_general_id', '=', False),
                                                            ('proveedor', '=', values['partner_id'])], context=context)
                if contrato_id:
                    values['contrato_id'] = contrato_id[0]
                id_order = order_pool.create(cr, uid, values, context=context)
                order_ids.append(id_order)
        if order_ids:
            data_pool = self.pool.get('ir.model.data')
            # action_model,action_id = data_pool.get_object_reference(cr, uid, 'purchase', 'purchase_form_action')
            # comentado, echaviano 12/01
            action_model, action_id = data_pool.get_object_reference(cr, uid, 'grp_compras_estatales',
                                                                     'purchase_form2_action')
            if action_model:
                action_pool = self.pool.get(action_model)
                action = action_pool.read(cr, uid, action_id, context=context)
                action['domain'] = "[('id','in', [" + ','.join(map(str, order_ids)) + "])]"
            return action

        return True

    # TODO: SPRING 12 GAP 67 K
    @api.multi
    def abrir_contratos_tree_view(self):
        contratos_ids = []
        if not self.contratos_ids:
            return
        for rec in self.contratos_ids:
            contratos_ids.append(rec.id)
        # domain = [('id', 'in', contratos_ids)]
        if contratos_ids:
            data_pool = self.pool.get('ir.model.data')
            action_model, action_id = data_pool.get_object_reference(self._cr, self._uid, 'grp_contrato_proveedores',
                                                                     'action_contract_proveedores_form')
            if action_model:
                action_pool = self.pool.get(action_model)
                action = action_pool.read(self._cr, self._uid, action_id, context=self._context)
                action['domain'] = "[('id','in', [" + ','.join(map(str, contratos_ids)) + "])]"
            return action

    # TODO: SPRING 12 GAP 67 K
    @api.multi
    def button_create_contrato(self):
        if self.sice_page_aceptadas:
            context = dict(self._context)
            mod_obj = self.env['ir.model.data']
            res = mod_obj.get_object_reference('grp_contrato_proveedores', 'grp_crear_contratos_wizard_view')
            models = 'grp.crear.contratos.wizard'
            res_id = res and res[1] or False
            ctx = context.copy()
            ctx.update(
                {'lineas_cotizacion_ids': self.sice_page_aceptadas.filtered(lambda x: x.contrato_generado != True).ids})
            return {
                'name': "Crear contratos",
                'view_mode': 'form',
                'view_id': res_id,
                'view_type': 'form',
                'res_model': models,
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': ctx,
            }
        return True

    # def act_cotizaciones_cancelado(self, cr, uid, ids, context=None):
    #     for rec in self.browse(cr,uid,ids,context=context):
    #         if rec.contratos_ids.filtered(lambda x: x.state != 'cancel'):
    #             raise exceptions.ValidationError(_("No se puede cancelar una adjudicación si tiene contratos en estado Borrador o Vigente, primero debe cancelarlos!"))
    #     self.write(cr, uid, ids, {'state': 'cancelado'}, context=context)
    #     return True


# TODO: C SPRING 13 GAP 451

class GrpContratoCotizaciones(models.Model):
    _inherit = 'grp.cotizaciones.lineas.aceptadas'

    #MVARELA 05/06/2018 - Se mueve a grp_compras_estatales
    # order_linea_ids = fields.One2many('purchase.order.line', 'cotizaciones_linea_id', string=u'Línea de orden de compra')
    # MVARELA 02/07/2018 - Se mueve a grp_compras_estatales
    # cantidad_pendiente_oc = fields.Float(string=u'Cantidad pendiente oc', compute='_compute_cantidad_pendiente_oc')
    contrato_generado = fields.Boolean(u"Contrato generado", store=False,
                                       compute='_compute_contrato_generado')  # TODO: SPRING 12 GAP 67 K

    @api.multi
    def _compute_contrato_generado(self):
        contrato_obj = self.env['grp.contrato.proveedores']
        for rec in self:
            rec.contrato_generado = contrato_obj.search_count([
                ('nro_line_adj_id', '=', rec.id), ('state', '!=', 'cancel')])

        # MVARELA 02/07/2018 - Se mueve a grp_compras_estatales
    # @api.multi
    # def _compute_cantidad_pendiente_oc(self):
    #     for rec in self:
    #         oc = sum(rec.order_linea_ids.filtered(lambda x: x.order_id.state == 'confirmed').mapped('product_qty'))
    #         rec.cantidad_pendiente_oc = rec.cantidad - oc
