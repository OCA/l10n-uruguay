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

from openerp import models, fields, api, _

# TODO: SPRING 11 GAP 25 K
TIPO_CONF_V = [('categ_a', u'Categoría A'),
                ('categ_b', u'Categoría B')
                ]

class GrpHrEmployeeViaticos(models.Model):
    _inherit = 'hr.employee'

    categoria = fields.Selection(selection=TIPO_CONF_V, string=u'Categoría')
    cantidad_horas_trabajadas = fields.Float(u'Cantidad de horas trabajadas', digits=(16,2))

