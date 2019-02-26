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

from openerp import models, fields, exceptions, api, _
from openerp.tools import float_round
import openerp.addons.decimal_precision as dp
from openerp.exceptions import ValidationError
import logging
import time

_logger = logging.getLogger(__name__)

# TODO: SPRING 11 GAP 25 K
TIPO_CONF_V = [('categ_a', u'Categoría A'),
               ('categ_b', u'Categoría B'),
               ('complemento', u'Complemento')
               ]


class GrpConfiguracionImportesViaticos(models.Model):
    _name = 'grp.configuracion.importes.viaticos'
    _descripcion = u'Configuración importes de viáticos'

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "%s" % (rec.fiscal_year_id.name_get()[0][1])))
        return result

    # TODO: SPRING 11 GAP 25 K
    @api.model
    def _default_fiscal_year(self):
        fecha_hoy = time.strftime('%Y-%m-%d')
        uid_company_id = self.env['res.users'].browse(self._uid).company_id.id
        fiscal_year_id = self.env['account.fiscalyear'].search(
            [('date_start', '<=', fecha_hoy), ('date_stop', '>=', fecha_hoy),
             ('company_id', '=', uid_company_id)])
        fiscal_year = fiscal_year_id and fiscal_year_id[0].id or False
        return fiscal_year

    # TODO: SPRING 11 GAP 25 K
    @api.multi
    @api.depends('viatico_anual')
    def _compute_valor_porciento(self):
        for record in self:
            record.valor_porciento_alimentacion = float_round(record.viatico_anual * 0.5 * 0.5, 2)

    # TODO: SPRING 11 GAP 25 K
    @api.multi
    @api.depends('viatico_anual')
    def _compute_valor(self):
        for record in self:
            record.valor_alimentacion = float_round(record.viatico_anual * 0.5, 2)

    @api.multi
    @api.depends('viatico_anual')
    def _compute_valor_pernocte(self):
        for record in self:
            record.valor_pernocte = float_round(record.viatico_anual * 0.5, 2)

    # RAGU configurando pernocte igual que alimentacion
    @api.multi
    @api.depends('viatico_anual')
    def _compute_valor_porciento_pernocte(self):
        for record in self:
            record.valor_porciento_pernocte = float_round(record.viatico_anual * 0.5 * 0.5, 2)

    # definicion de campos
    # name = fields.Char(string=u'Nº Configuración importes de viáticos', readonly=True, default=u'Viático Borrador')
    fiscal_year_id = fields.Many2one('account.fiscalyear', u'Año fiscal',
                                     default=lambda self: self._default_fiscal_year(), required=True)
    fecha_desde = fields.Date(string=u'Fecha Desde', required=True)
    fecha_hasta = fields.Date(string=u'Fecha Hasta', required=True)
    tipo = fields.Selection(selection=TIPO_CONF_V, string='Tipo', required=True)
    viatico_anual = fields.Integer(string=u'Viático del año', size=8, required=False)

    # Pestaña Alimentacion
    product_alimentacion_id = fields.Many2one('product.product', domain=[('viatico_ok', '=', True)], string=u'Producto')
    h_seis = fields.Integer(string=u' <X≤ ', size=2, readonly=True, default=6)
    h_doce = fields.Integer(string=u' Hr', size=2, readonly=True, default=12)
    valor_porciento_alimentacion = fields.Float(compute='_compute_valor_porciento', string=u"Valor")
    h_doce_uno = fields.Integer(string=u' <X≤ ', size=2, readonly=True, default=12)
    h_veinticuatro = fields.Integer(string=u' Hr', size=2, readonly=True, default=24)
    valor_alimentacion = fields.Float(compute='_compute_valor', string=u"Valor")

    # Pestaña Pernocte
    product_pernocte_id = fields.Many2one('product.product', domain=[('viatico_ok', '=', True)], string=u'Producto')
    pernocte_h_seis = fields.Integer(string=u' <X≤ ', size=2, readonly=True, default=6)
    pernocte_h_doce = fields.Integer(string=u' Hr', size=2, readonly=True, default=12)
    valor_porciento_pernocte = fields.Float(compute='_compute_valor_porciento_pernocte', string=u"Valor")
    valor_pernocte = fields.Float(compute='_compute_valor_pernocte', string=u"Valor")

    # Pestaña Complemento
    complemento_ids = fields.One2many('grp.complemento.configuracion.viaticos', 'configuracion_viaticos_id',
                                      string=u'Complemento')

    @api.one
    @api.constrains('fiscal_year_id', 'tipo', 'fecha_desde', 'fecha_hasta')
    def _check_unitary(self):
        if self.search_count([('fiscal_year_id', '=', self.fiscal_year_id.id),
                              ('tipo', '=', self.tipo),
                              ('id', '!=', self.id),
                              '|', '&', ('fecha_desde', '<=', self.fecha_desde),
                              ('fecha_hasta', '>=', self.fecha_desde),
                              '&', ('fecha_desde', '<=', self.fecha_hasta), ('fecha_hasta', '>=', self.fecha_hasta)
                              ]):
            raise ValidationError(_(
                u"Existe una configuración de importes que se solapa con esta fecha para el mismo 'Año fiscal', 'Tipo'!"))

    @api.one
    @api.constrains('viatico_anual')
    def _check_viatico_anual(self):
        if len(str(self.viatico_anual)) > 8:
            raise ValidationError(_(
                u"El Viático del año no puede ser un número con más de 8 dígitos!"))

    # TODO: SPRING 11 GAP 25 K
    @api.multi
    def unlink(self):
        for rec in self:
            solicitud_ids = self.env['grp.solicitud.viaticos'].search(['|', ('config_importe_viatico_id', '=', rec.id),
                                                                       ('config_complemento_viatico_id', '=', rec.id)])
            rendicion_ids = self.env['hr.expense.expense'].search(['|', ('config_importe_viatico_id', '=', rec.id),
                                                                   ('config_complemento_viatico_id', '=', rec.id)])
            if solicitud_ids or rendicion_ids:
                raise ValidationError(
                    u'No se puede eliminar la configuracion de importe porque esta siendo utilizada en una solicitud de viaje o una rendición de viáticos')
        return super(GrpConfiguracionImportesViaticos, self).unlink()


# TODO: SPRING 11 GAP 25 K
class GrpComplementoConfiguracionViaticos(models.Model):
    _name = 'grp.complemento.configuracion.viaticos'
    _descripcion = u'Complemento de configuracion de viáticos'

    localidad = fields.Many2one('grp.localidad', string='Localidad o zona', ondelete='restrict', required=True)
    product_alimentacion_id = fields.Many2one('product.product', domain=[('viatico_ok', '=', True)],
                                              string=u'Complemento por alimentación', required=True)
    valor_alimentacion = fields.Float(string=u"Valor", required=True, digits_compute=dp.get_precision('Account'))
    product_pernocte_id = fields.Many2one('product.product', domain=[('viatico_ok', '=', True)],
                                          string=u'Complemento por pernocte', required=True)
    valor_pernocte = fields.Float(string=u"Valor", required=True, digits_compute=dp.get_precision('Account'))
    configuracion_viaticos_id = fields.Many2one('grp.configuracion.importes.viaticos',
                                                string=u'Configuración importes de viáticos')
