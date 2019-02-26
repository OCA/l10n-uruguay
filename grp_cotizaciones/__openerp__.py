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
    'name':     u'GRP - Cotizaciones SIIF',
    'author':   'Quanam',
    'website':  'http://www.quanam.com',
    'category': 'GRP',
    'license':  'AGPL-3',
    'version':  '1.0',
    'description': u"""
Actualiza cotización de las monedas según SIIF
==============================================
Este addon provee la acción planificada: SIIF: Actualización de la cotización de las monedas

Tareas a realizar post-instalación del addon:

Periodicidad de ejecución
-------------------------
Ajustar los valores relativos a periodicidad de ejecución de la acción planificada:

* Número de intervalos
* Unidad de intervalo

Parámetro del sistema
---------------------
Crear parámetro del sistema con la url del servicio web SIIF:

* Clave: url_ws.siif
* Valor: url del servicio web SiiF en el Conector PGE

Para que una moneda GRP pueda ser actualizada según los valores de tasa de cambio en SIIF, debe setearse en la misma el campo Código SIIF.
""",
    'depends' : ['base','grp_calculo_tipo_cambio'],
    'data' : [
        'views/res_currency_view.xml',
        'data/create_unique_index_codigo_siif.sql',
        'data/cotizacion_cron_job.xml',
    ],
    'auto_install': False,
    'installable': True,
    'application': False
}
