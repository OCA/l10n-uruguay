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
{
    'name':     u'GRP - Control de Flota',
    'author':   'Quanam',
    'website':  'http://www.quanam.com',
    'category': 'GRP',
    'license':  'AGPL-3',
    'version':  '1.0',
    'description': u"""
Control de Flota GRP
=============
* Registro de cambio de cubierta

""",
    'depends' : ['fleet','account','hr','calendar','account_auto_fy_sequence','readonly_fields'],# TODO SPRING 5 GAP 249
                                                    #TODO SPRING 5 GAP 51: Agregando la dependecia de calendar para poder crear eventos
    'data' : [
        'data/grp_flota_data.xml',
        'security/grp_flota_security.xml',
        'security/ir.model.access.csv',
        'views/grp_inherit_fleet_view.xml',
        'views/grp_solicitud_viaje_view.xml',
        'views/grp_inherit_calendar_view.xml',
        'views/grp_rendimiento_vehiculo_report_tmpl.xml',  # TODO: L SPRING 13 GAP 370
        'report/grp_rendimiento_vehiculo_report.xml',  # TODO: L SPRING 13 GAP 370
        'report/grp_flota_document.xml',  # TODO: L SPRING 13 GAP 370
        'report/grp_cantidad_viaje_periodo_report_view.xml',
    ],
    'auto_install': False,
    'installable': True,
    'application': True
}
