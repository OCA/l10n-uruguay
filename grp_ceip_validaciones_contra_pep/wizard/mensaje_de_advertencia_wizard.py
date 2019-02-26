# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2018 Datamatic All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api
from openerp.exceptions import Warning

class mensaje_de_advertencia_wizard(models.TransientModel):
    _name = 'mensaje.de.advertencia.wizard'

    mensaje_a_mostrar = fields.Char(string="Mensaje a mostrar", readonly=True)

    @api.multi
    def boton_continuar(self):
        for record in self:
            elementos_origen = False

            try:
                modelo_activo = self._context['active_model']
                ids_de_modelos_activos = self._context['active_ids']
                elementos_origen = self.env[modelo_activo].search([('id', 'in', ids_de_modelos_activos)])

            except Exception as exc:
                raise Warning(u'Ocurrió un Error al continuar con la comunicación hacia SIIF!')

            if not elementos_origen:
                raise Warning(u'No es posible continuar con la comunicación hacia SIIF!')

            for elemento in elementos_origen:
                elemento.continuar_envio_a_siif()

mensaje_de_advertencia_wizard()
