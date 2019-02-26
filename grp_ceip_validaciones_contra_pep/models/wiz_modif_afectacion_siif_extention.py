# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Enterprise Management Solution
#    GRP Estado Uruguay
#    Copyright (C) 2018 ATOS Uruguay
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
import logging

_logger = logging.getLogger(__name__)

class wiz_modif_afectacion_siif_extention_api_nueva(models.Model):
    _inherit = "wiz.modif.afectacion.siif"

    name = fields.Char(string=u"Nombre del Documento", compute='compute_nombre_del_documento_wizard')

    @api.multi
    @api.depends('tipo')
    def compute_nombre_del_documento_wizard(self):
        _logger.info('Se carga el Nombre del Documento')
        print 'Se carga el Nombre del Documento'

        for record in self:
            if record._context:
                modelo_afectacion = record._context['active_model']
                ids_de_modelos_activos = record._context['active_ids']

                afectaciones_activas = record.env[modelo_afectacion].browse(ids_de_modelos_activos)

                for afectacion in afectaciones_activas:
                    record.name = afectacion.name

wiz_modif_afectacion_siif_extention_api_nueva()
