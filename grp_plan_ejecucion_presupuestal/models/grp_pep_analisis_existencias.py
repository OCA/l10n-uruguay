# -*- encoding: utf-8 -*-
from collections import defaultdict

from openerp import models, fields, api, tools
from openerp.exceptions import Warning, ValidationError


class grp_pep_anual_linea_existencia(models.Model):
    _name = 'grp.pep.anual.linea.existencia'

    plan_anual_id = fields.Many2one(comodel_name='grp.pep.anual')
    plan_state = fields.Selection(related='plan_anual_id.state', string=u'Estado', readonly=True)
    product_id = fields.Many2one(string='Producto', comodel_name='product.product', required=True)
    cantidad_planificada = fields.Integer(string=u"Cantidad a Comprar Planificada")
    inventario_stock = fields.Integer(string=u"Inventario de Stock",
                                      compute='_compute_inventario',
                                      store=True)

    inventario_cantidad_a_mano = fields.Integer(string=u"Inventario Cantidad a Mano",
                                                compute='_compute_inventario',
                                                store=True)
    inventario_salida = fields.Integer(string=u"Inventario Salida",
                                       compute='_compute_inventario',
                                       store=True)

    stock_move_domain_ids = fields.Many2many(comodel_name='stock.move',
                                             compute='_compute_stock_move_domain_ids')
    stock_move_ids = fields.Many2many(comodel_name='stock.move')
    cantidad_considerada = fields.Integer(string=u"Cantidad Considerada en Compras",
                                          compute='_compute_cantidad_considerada',
                                          store=True)
    existencias = fields.Integer(compute='_compute_existencias')
    por_procesar = fields.Boolean()
    necesidad = fields.Integer(string=u"Necesidad",
                               compute='_compute_necesidad', store=True)
    cantidad_comprar = fields.Integer(string=u"Cantidad a Comprar Actualizada")
    show_warning = fields.Boolean(compute='_compute_show_warning_success')
    show_success = fields.Boolean(compute='_compute_show_warning_success')

    @api.multi
    def _compute_existencias(self):
        for rec in self:
            rec.existencias = rec.cantidad_comprar - rec.cantidad_planificada

    @api.multi
    @api.depends('product_id')
    @api.onchange('product_id')
    def _compute_stock_move_domain_ids(self):
        for rec in self:
            # Obtengo las lineas de OCs en estado confirmado que contienen al producto
            purchase_order_lines = self.env['purchase.order.line'].search([('product_id.id', '=', rec.product_id.id),
                                                                           ('order_id.state', '=', 'confirmed')])

            # Obtengo los ids de la OCs a las que corresponden las lineas, sin repetidos
            purchase_orders_ids = list(set([x.order_id.id for x in purchase_order_lines]))

            # Obtengo las OCs con esos ids
            purchase_orders = self.env['purchase.order'].browse(purchase_orders_ids)

            # Obtengo los stock_pickings de esas OCs
            po_pick_tuples = []
            for po in purchase_orders:
                po_pick_tuples += [(po.id, picking.id) for picking in po.picking_ids]

            # Quito repetidos
            po_pick_tuples = list(set(po_pick_tuples))
            # Armo un dict { stock_picking --> purchase_order }
            # pick_po_dict = {x[1]: x[0] for x in po_pick_tuples}

            # Obtengo los stock_move de los pickings que correspondan al producto actual
            pick_ids = [x[1] for x in po_pick_tuples]
            stock_move_ids = self.env['stock.move'].search([('picking_id', 'in', pick_ids),
                                                            ('product_id', '=', rec.product_id.id),
                                                            ('state', '=', 'assigned')])
            rec.stock_move_domain_ids = [(6, 0, stock_move_ids.ids)]

    @api.multi
    @api.depends('product_id')
    @api.onchange('product_id')
    def _compute_inventario(self):
        for rec in self:
            # Obtengo la suma de las cantidades minimas de las reglas de re-abastecimiento para ese prod
            reglas = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', rec.product_id.id)])
            cant_minima = sum([r.product_min_qty for r in reglas])

            # Calculo los campos de inventario
            rec.inventario_cantidad_a_mano = rec.product_id.qty_available - cant_minima
            rec.inventario_salida = rec.product_id.outgoing_qty
            rec.inventario_stock = rec.inventario_cantidad_a_mano - rec.inventario_salida

    @api.multi
    @api.depends('cantidad_planificada', 'inventario_cantidad_a_mano', 'inventario_salida', 'cantidad_considerada')
    @api.onchange('cantidad_planificada', 'inventario_cantidad_a_mano', 'inventario_salida', 'cantidad_considerada')
    def _compute_necesidad(self):
        for rec in self:
            inventario = rec.inventario_cantidad_a_mano - rec.inventario_salida
            if inventario + rec.cantidad_considerada >= rec.cantidad_planificada:
                rec.necesidad = 0
            else:
                rec.necesidad = rec.cantidad_planificada - inventario - rec.cantidad_considerada

    @api.multi
    @api.depends('stock_move_ids')
    @api.onchange('stock_move_ids')
    def _compute_cantidad_considerada(self):
        for rec in self:
            cant = 0
            for stock_move in rec.stock_move_ids:
                cant += stock_move.product_uom_qty
            rec.cantidad_considerada = cant

    @api.multi
    def write(self, values):
        super(grp_pep_anual_linea_existencia, self).write(values)
        for rec in self:
            copiar_necesidad = not self.env.context.get('no_copiar_necesidad', False)
            if rec.cantidad_comprar == 0 and copiar_necesidad:
                super(grp_pep_anual_linea_existencia, rec).write({'cantidad_comprar': rec.necesidad})
            if rec.existencias != 0:
                por_procesar = True
            else:
                por_procesar = False
            super(grp_pep_anual_linea_existencia, rec).write({'por_procesar': por_procesar})
        return True

    @api.multi
    def abrir_compras_consideradas(self):
        self.ensure_one()

        # Calculo el domain para los stock move a considerar
        self._compute_stock_move_domain_ids()

        xml_id_obj = self.env['ir.model.data']
        form_id = xml_id_obj.get_object_reference('grp_plan_ejecucion_presupuestal',
                                                  'view_grp_pep_anual_existencias_compras_consideradas_form')[1]
        return {
            'name': "Compras Consideradas",
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(form_id, 'form')],
            'target': 'new'
        }

    @api.multi
    @api.constrains('cantidad_comprar')
    def _control_cantidad_comprar(self):
        for rec in self:
            res = {'value': {}}
            if rec.cantidad_comprar < rec.necesidad:
                res['warning'] = {'title': 'Advertencia',
                                  'messagge': 'La cantidad a comprar es menor a la necesidad'}
            return res

    @api.multi
    @api.onchange('cantidad_comprar')
    def _compute_show_warning_success(self):
        for rec in self:
            if rec.cantidad_comprar < rec.necesidad:
                rec.show_warning = True
                rec.show_success = False
            elif rec.cantidad_comprar == rec.necesidad:
                rec.show_warning = False
                rec.show_success = True
            else:
                rec.show_warning = False
                rec.show_success = False

    @api.multi
    def obtener_cantidad_comprar_por_producto(self):
        """
            Esta función debería llamarse sobre las lineas de un analisis de adquisiciones.

            Retorna un diccionario { product_id: <cantidad_actualizada_a_comprar> }
            agregando los productos en caso de repetirse en el recordset (no debería pasar
            a menos que se esté usando mal la función)
        """
        dict_prod_cant = defaultdict(int)
        for rec in self:
            dict_prod_cant[rec.product_id] = rec.cantidad_comprar

        return dict_prod_cant


grp_pep_anual_linea_existencia()

