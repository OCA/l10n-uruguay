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

import logging

from openerp import models, fields

_logger = logging.getLogger(__name__)


class ConfigRecuperacionFondoRotatorio(models.Model):
    _name = 'config.recuperacion.fondo.rotatorio'
    _description = "Configuración Recuperación Fondo Rotatorio"
    _rec_name = 'journal_id'

    cuenta_credito_id = fields.Many2one('account.account', string=u'Cuenta de Créditos Presupuestales', required=True)
    unidad_ejecutora_id = fields.Many2one('operating.unit', string=u'Unidad Ejecutora', required=True)
    journal_id = fields.Many2one('account.journal', string=u'Cuenta Bancaria Recuperación FR',
                                         domain=[('type', '=', 'bank')], required=True)
