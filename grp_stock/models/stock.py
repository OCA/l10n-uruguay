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
from datetime import datetime
import pytz

# Stock Inventory  inheritance
# ----------------------------------------------------------
class StockInventory(models.Model):
    _inherit = "stock.inventory"
    observaciones = fields.Text(string='Observaciones')


# Stock Inventory Line inheritance
# ----------------------------------------------------------
class StockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"
    # diferencia = fields.Float(string='Diferencias recuento', store=True, readonly=True, compute='_compute_diferencia')
    diferencia = fields.Float(string='Diferencias recuento', readonly=True, compute='_compute_diferencia')
    # 003-Inicio
    solo_lectura = fields.Boolean(string=u'Sólo lectura', compute='_get_solo_lectura', default=False)
    fecha_vencimiento_lote = fields.Datetime("Fecha de vencimiento", related='prod_lot_id.life_date', readonly=True)

    @api.depends()
    def _get_solo_lectura(self):
        for rec in self:
            rec.solo_lectura = True

    # 003-Fin
    @api.one
    @api.depends('theoretical_qty', 'product_qty')
    def _compute_diferencia(self):
        delta = self.product_qty - self.theoretical_qty
        self.diferencia = delta


# Stock Warehouse Orderpoint inheritance
# ----------------------------------------------------------
class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"
    location_id = fields.Many2one("stock.location", required=False)

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    fecha_vencimiento_lote = fields.Date("Fecha de vencimiento", compute="_compute_vencimiento", store=True)

    @api.depends('lot_id.life_date')
    def _compute_vencimiento(self):
        for record in self:
            if record.lot_id:
                record.fecha_vencimiento_lote = record.lot_id.life_date
            else:
                record.fecha_vencimiento_lote = False

class StockPackOperation(models.Model):
    _inherit = "stock.pack.operation"

    fecha_vencimiento_lote = fields.Datetime("Fecha de vencimiento", related='lot_id.life_date', readonly=True)

class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    _order = 'life_date, id'

    @api.multi
    def name_get(self):
        if not self._context.get('mostrar_fecha_vencimiento', False):
            return super(StockProductionLot, self).name_get()
        result = []
        for lot in self:
            info_vencimiento = ''
            if lot.life_date:
                fecha = datetime.strptime(lot.life_date, "%Y-%m-%d %H:%M:%S")
                user_time_zone = self._context.get('tz') or 'America/Montevideo'
                fecha = pytz.utc.localize(fecha)
                fecha_convertida = fecha.astimezone(pytz.timezone(user_time_zone))
                fecha_venc = fecha_convertida.strftime("%d/%m/%Y")
                info_vencimiento = ", %s" % (fecha_venc)
            result.append((lot.id, "%s%s" % (lot.name, info_vencimiento or '')))
        return result

class stock_transfer_details_items(models.TransientModel):
    _inherit = 'stock.transfer_details_items'

    fecha_vencimiento_lote = fields.Datetime("Fecha de vencimiento", related='lot_id.life_date', readonly=True)