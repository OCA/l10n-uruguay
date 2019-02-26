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

from openerp import fields as fields_new, models, api, _
from openerp.exceptions import Warning
import logging

from ..library import validaciones_contra_pep_operations as validacion_ops

_logger = logging.getLogger(__name__)

class res_users_extention_api_nueva(models.Model):
    _inherit = "res.users"

    es_responsable_de_validacion_pep = fields_new.Boolean(string=u"¿Es responsable de Validación PEP?", default=False)

    def es_usuario_parte_del_grupo_elaboracion_plan_ejecucion(self):
        usuarios_del_grupo = validacion_ops.obtener_usuarios_del_grupo_elaboracion_plan_ejecucion(self)
        informacion_de_login_de_usuarios_del_grupo = [usuario.login for usuario in usuarios_del_grupo]
        es_parte_del_grupo = self.login in informacion_de_login_de_usuarios_del_grupo

        return es_parte_del_grupo

    def validar_que_pueda_ser_responsable_de_recibir_mails(self):
        es_parte_del_grupo = self.es_usuario_parte_del_grupo_elaboracion_plan_ejecucion()

        if self.es_responsable_de_validacion_pep and not es_parte_del_grupo:
            raise Warning(u'El usuario debe pertenecer al grupo "Elaboración de Plan de Ejecución" para poder ser Responsable de los Mails por Errores relacionados con PEP.')


    @api.multi
    @api.onchange('es_responsable_de_validacion_pep')
    def onchange_es_responsable_de_validacion_pep(self):
        _logger.info(u'Se valida que el usuario sea parte del Grupo "Elaboración de Plan de Ejecución" para permitir que sea el responsable de los Mails por Errores relacionados con PEP.')

        for record in self:
            record.validar_que_pueda_ser_responsable_de_recibir_mails()

    @api.multi
    def write(self, vals):
        for record in self:
            res = super(res_users_extention_api_nueva, record).write(vals)

            record.validar_que_pueda_ser_responsable_de_recibir_mails()

            return res

res_users_extention_api_nueva()
