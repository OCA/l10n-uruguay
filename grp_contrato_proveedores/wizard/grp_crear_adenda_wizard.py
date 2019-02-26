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

from openerp import fields, models, api, _
from openerp.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


# TODO: C SPRING 12 GAP_75_76
class GrpCrearAdendaWizard(models.TransientModel):
    _name = 'grp.crear.adenda.wizard'

    fecha = fields.Date(string=u'Fecha finalización')
    descripcion = fields.Text(string=u'Descripción detallada')
    contrato_id = fields.Many2one("grp.contrato.proveedores", string=u"Contrato")
    convenio = fields.Boolean(string='Contratos sin procedimiento de compras', related='contrato_id.convenio', readonly=True)
    contrato_particular_dom = fields.Many2many("grp.contrato.proveedores", string=u"Dominio de contrato particulares",
                                               compute='_compute_contrato_particular_dom')
    lineas_ids = fields.One2many('grp.crear.adenda.linea.wizard', "wizard_id", 'Lineas')

    afectaciones_ids = fields.Many2many('grp.afectacion','adenda_wizard_afectations_rel','adenda_wizard_id','afectacion_id',
                                        string='Afectaciones', domain=[('state', '=', 'afectado')])

    @api.multi
    @api.depends('contrato_id')
    def _compute_contrato_particular_dom(self):
        for rec in self:
            rec.contrato_particular_dom = []
            if rec.contrato_id:
                rec.contrato_particular_dom = self.env['grp.contrato.proveedores'].search(
                    [('contrato_general_id', '=', rec.contrato_id.id)]).ids

    @api.one
    @api.constrains('fecha')
    def _check_fecha(self):
        if self.fecha and self.fecha <= fields.Date.today():
            raise ValidationError(u'La fecha debe ser mayor que la fecha actual')

    # TODO C INCIDENCIA 21-09-17
    @api.one
    def crear_contratos(self):
        dict_update = {}
        if self.convenio:
            dict_update.update({'afectaciones_ids':[(4,x.id) for x in self.afectaciones_ids]})
        if self.fecha:
            nuevo_contrato_general_id = self.contrato_id.copy({'state': 'end'})
            dict_update.update({
                'fecha_fin': self.fecha,
                'origen_adenda': True,
                'state': 'vigente',
                'acciones_ids': [(0, 0, {'tipo': 'Otras adendas', 'se_copio': True, 'se_registro': False,
                                         'descripcion': self.descripcion, 'link': nuevo_contrato_general_id.id})],

            })
        else:
            nuevo_contrato_general_id = self.contrato_id
        self.contrato_id.write(dict_update)
        if self.lineas_ids:
            self.lineas_ids.copiar_contrato_particular(nuevo_contrato_general_id.id, self.convenio and self.afectaciones_ids.ids or False)
        return True


class GrpCrearAdendaLineaWizard(models.TransientModel):
    _name = 'grp.crear.adenda.linea.wizard'

    wizard_id = fields.Many2one('grp.crear.adenda.wizard', 'Crear adenda')
    contrato_particular_id = fields.Many2one("grp.contrato.proveedores", string=u"Nº Contrato", required=True)
    codigo_articulo = fields.Integer(string='Producto', related='contrato_particular_id.codigo_articulo', readonly=True)
    cantidad_actual = fields.Float(string='Cantidad actual', related='contrato_particular_id.cantidad', readonly=True)
    precio_actual = fields.Float(string='Precio actual', related='contrato_particular_id.precio', readonly=True)

    cantidad = fields.Float(string='Cantidad modificada')
    precio = fields.Float(string='Precio modificado')

    @api.one
    @api.constrains('cantidad', 'precio')
    def _check_cantidad_precio(self):
        if not self._context.get('ajuste_contrato_particular',False):
            if self.cantidad == self.cantidad_actual and self.precio == self.precio_actual:
                raise ValidationError(
                    u'La cantidad modificada y el precio modificado no deben ser iguales que la cantidad y precio actual, debe modificar al menos uno de los dos.')
            if self.cantidad * self.precio != self.cantidad_actual * self.precio_actual:
                raise ValidationError(
                    u'El importe del nuevo contrato particular no puede diferir del importe del contrato particular origen!')

    # TODO C INCIDENCIA 21-09-17
    @api.multi
    def copiar_contrato_particular(self, copia_contrato_general, afectationes_ids):
        for rec in self:
            dic_update = {'origen_adenda': True, 'state': 'vigente'}
            if rec.cantidad != rec.cantidad_actual:
                dic_update.update({'cantidad': rec.cantidad})
            if rec.precio != rec.precio_actual:
                dic_update.update({'precio': rec.precio, 'precio_ajustado': rec.precio})
            if dic_update.get('cantidad') or dic_update.get('precio'):
                cp_copy = rec.contrato_particular_id.copy({'contrato_general_id': copia_contrato_general, 'state': 'end'})

                dic_update.update(
                    {'acciones_ids': [(0, 0, {'tipo': 'Otras adendas', 'se_copio': True, 'se_registro': False,
                                              'descripcion': rec.wizard_id.descripcion,
                                              'contrato_general_id': rec.contrato_particular_id.contrato_general_id.id,
                                              'link': cp_copy.id})]})
                if afectationes_ids:
                    dic_update.update({
                        'afectaciones_ids':[(4,x) for x in afectationes_ids]
                    })
                rec.contrato_particular_id.write(dic_update)
