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
# TODO: SPRING 11 GAP 495 K

from openerp import exceptions, fields, models, api
from openerp import tools
import openerp.addons.decimal_precision as dp
from openerp.exceptions import ValidationError

# TODO: K SPRING 13 GAP 452
class grp_estimado_ejecutar_contrato(models.Model):
    _name = 'grp.estimado.ejecutar.contrato'
    _auto = False

    contrato_id = fields.Many2one('grp.contrato.proveedores', 'Contrato')
    nro_interno = fields.Char(string=u"Número Contrato")
    proveedor = fields.Many2one('res.partner', string=u"Proveedor")
    fecha_inicio = fields.Date('Fecha de inicio')
    fecha_fin = fields.Date('Fecha de fin')
    moneda = fields.Char(string=u"Moneda")
    monto_ajustado = fields.Float(string='Monto contrato ajustado', digits_compute=dp.get_precision('Account'))
    monto_facturar = fields.Float(string='Saldo pendiente', compute='_compute_monto_facturar',
                                  digits_compute=dp.get_precision('Account'))
    monto_ejecutar_actual = fields.Float(string='Monto a ejecutar ejercicio actual',
                                         digits_compute=dp.get_precision('Account'))
    monto_ejecutar_futuro = fields.Float(string='Monto a ejecutar ejercicios futuros', compute='_compute_monto_ejecutar_futuro',
                                         digits_compute=dp.get_precision('Account'))
    listo = fields.Boolean(u"Listo para procesar", default=False)
    fecha_procesamiento = fields.Datetime(string=u'Último procesamiento')

    # TODO: K SPRING 13 GAP 452
    @api.one
    @api.depends('contrato_id', 'moneda')
    def _compute_monto_facturar(self):
        self.monto_facturar = 0.0
        contrato_particulares_moneda_ids = self.env['grp.contrato.proveedores'].search([('contrato_general_id','=',self.contrato_id.id),
                                                                                    ('currency.name','=',self.moneda)])
        if contrato_particulares_moneda_ids:
            self.monto_facturar = sum(map(lambda x: x.monto_facturar, contrato_particulares_moneda_ids))

    # TODO: K SPRING 13 GAP 452
    @api.one
    @api.depends('monto_facturar', 'monto_ejecutar_actual')
    def _compute_monto_ejecutar_futuro(self):
        self.monto_ejecutar_futuro = self.monto_facturar - self.monto_ejecutar_actual

    # TODO: K SPRING 13 GAP 452
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_estimado_ejecutar_contrato')
        cr.execute("""
            create or replace view grp_estimado_ejecutar_contrato as (
                SELECT ROW_NUMBER() OVER(ORDER BY c.id) as id,
    c.id AS contrato_id,
    c.nro_interno,
    c.proveedor,
    c.fecha_inicio,
    c.fecha_fin,
    m.moneda,
    m.monto_ajustado,
    m.monto_ejecutar_actual,
    m.listo,
    m.fecha_procesamiento
   FROM grp_contrato_proveedores c
     LEFT JOIN grp_monedas_contrato m ON m.contrato_id = c.id
  WHERE c.state::text = 'vigente'::text AND NOT (c.id IN ( SELECT grp_contrato_proveedores.id
           FROM grp_contrato_proveedores
          WHERE c.contrato_general_id > 0))
            )
        """)

    @api.multi
    def write(self, vals):
        moneda_obj =  self.env['grp.monedas.contrato']
        estimado_ejecutar_obj =  self.pool.get('grp.estimado.ejecutar.contrato')
        for line in self:
            moneda = moneda_obj.search([('id', '=', line.id)])[0]
            if moneda:
                vals_write = {}
                if vals.get('monto_ejecutar_actual', False):
                    if vals.get('monto_ejecutar_actual', False) > self.monto_facturar:
                        raise exceptions.ValidationError(u'Monto a ejecutar ejercicio actual no puede ser mayor que el Saldo pendiente.')
                    vals_write['monto_ejecutar_actual'] = vals.get('monto_ejecutar_actual')
                if vals.has_key('listo'):
                    vals_write['listo'] = vals.get('listo')
                if len(vals_write) > 0:
                    moneda.write(vals_write)
        estimado_ejecutar_obj.init(self._cr)
        return True
