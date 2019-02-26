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

from openerp.osv import osv
from openerp.tools import float_compare, float_round
from psycopg2 import OperationalError
import openerp


class procurement_order(osv.osv):
    _inherit = "procurement.order"

    # Metodo que obtiene la cantidad disponible del producto en la ubicacion
    # dada por la orden de reabastecimiento
    def _product_qty_available_get(self, cr, uid, order_point):
        product_obj = self.pool.get('product.product')
        return product_obj._product_available(cr, uid,
                [order_point.product_id.id],
                context={'location': order_point.location_id.id})[order_point.product_id.id]['qty_available']

    def cron_procure_orderpoint(self, cr, uid, context=None):
        user_obj = self.pool.get('res.users')
        company_id = user_obj.browse(cr, uid, uid, context=context).company_id.id
        return self._procure_orderpoint_confirm(cr, uid, company_id=company_id, context=context)

    def _procure_orderpoint_confirm(self, cr, uid, use_new_cursor=False, company_id=False, context=None):
        '''
        Create procurement based on Orderpoint

        :param bool use_new_cursor: if set, use dedicated cursors and auto-commit after processing
            100 orderpoints.
            This is appropriate for batch jobs only.
        '''
        if context is None:
            context = {}
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')

        procurement_obj = self.pool.get('procurement.order')
        dom = company_id and [('company_id', '=', company_id)] or []
        orderpoint_ids = orderpoint_obj.search(cr, uid, dom, context=context)
        prev_ids = []
        while orderpoint_ids:
            ids = orderpoint_ids[:100]
            del orderpoint_ids[:100]
            if use_new_cursor:
                cr = openerp.registry(cr.dbname).cursor()
            for op in orderpoint_obj.browse(cr, uid, ids, context=context):
                try:
                    # PCAR 02 05 2017 Podria no tener configurada la ubicacion
                    # por lo tanto _product_virtual_get no deberia ejecutarse en ese caso
                    # en su lugar se realiza chequeo de disponibilidad para todas las ubicaciones
                    # del almacen configurado
                    pool_location = self.pool.get('stock.location')
                    pool_quant = self.pool.get('stock.quant')
                    prods = 0
                    if op.location_id:
                        prods = self._product_qty_available_get(cr, uid, op)
                    else:
                        internal_loc_ids = pool_location.search(cr, uid, [('usage', 'in', ['internal'])])
                        locations = []
                        for loc in pool_location.browse(cr, uid, internal_loc_ids, context=context):
                            # obtengo el almacen de la ubicacion y lo comparo con almacen de la op
                            wrh_id = pool_location.get_warehouse(cr, uid, loc, context=context)
                            if wrh_id == op.warehouse_id.id:
                                locations.append(loc)
                        qty_total = 0
                        # Busco las cantidades disponibles para ese producto de los quants de las ubicaciones
                        # para ese almacen
                        for elem in locations:
                            quant_ids = pool_quant.search(cr, uid, [('product_id', '=', op.product_id.id),
                                                                    ('location_id', '=', elem.id)])
                            for quant in pool_quant.browse(cr, uid, quant_ids, context=context):
                                qty_total += quant.qty
                        prods = qty_total
                    if prods is None:
                        continue
                    # Si el disponible es menor que el minimo se hace el envio de la notificacion
                    if float_compare(prods, op.product_min_qty, precision_rounding=op.product_uom.rounding) < 0:
                        # PCAR 02 05 2017 Este bloque estandar no se
                        # utiliza ya que se usaba para la creacion de la orden
                        # de reabastecimmiento, y ya no se va a ejecutar mas esa operacion
                        # qty = max(op.product_min_qty, op.product_max_qty) - prods
                        # reste = op.qty_multiple > 0 and qty % op.qty_multiple or 0.0
                        # if float_compare(reste, 0.0, precision_rounding=op.product_uom.rounding) > 0:
                        #     qty += op.qty_multiple - reste
                        #
                        # if float_compare(qty, 0.0, precision_rounding=op.product_uom.rounding) <= 0:
                        #     continue
                        #
                        # qty -= orderpoint_obj.subtract_procurements(cr, uid, op, context=context)
                        #
                        # qty_rounded = float_round(qty, precision_rounding=op.product_uom.rounding)
                        # if qty_rounded > 0:
                            # proc_id = procurement_obj.create(cr, uid,
                            # self._prepare_orderpoint_procurement(cr, uid, op, qty_rounded, context=context),
                            # context=context)
                            # self.check(cr, uid, [proc_id])
                            # self.run(cr, uid, [proc_id])
                        # Agregar notificacion a los encargados del almacen
                        body = u"El producto %s en el almacén %s"
                        if op.location_id:
                            body += u" de la ubicación %s está por debajo" \
                                    u" del stock mínimo definido en la regla del" \
                                    u" reabastecimiento."
                            body = body % (op.product_id.display_name, op.warehouse_id.name, op.location_id.name)
                        else:
                            body += u" está por debajo del stock mínimo definido en" \
                                    u" la regla del reabastecimiento."
                            body = body % (op.product_id.display_name, op.warehouse_id.name)

                        partners = [usr.partner_id.id for usr in op.warehouse_id.encargado_ids]

                        self.pool.get('mail.thread').message_post(cr, uid, op.id, type="notification",
                                                                  subtype='mt_comment', body=body,
                                                                  partner_ids=partners, context=context)
                        # PCAR 28 04 2017 Fin
                    if use_new_cursor:
                        cr.commit()
                except OperationalError:
                    if use_new_cursor:
                        orderpoint_ids.append(op.id)
                        cr.rollback()
                        continue
                    else:
                        raise
            if use_new_cursor:
                cr.commit()
                cr.close()
            if prev_ids == ids:
                break
            else:
                prev_ids = ids

        return {}
