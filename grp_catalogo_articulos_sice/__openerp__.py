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
    'name':     u'GRP - Catálogo de artículos SICE',
    'author':   'Quanam',
    'website':  'http://www.quanam.com',
    'category': 'GRP',
    'license':  'AGPL-3',
    'version':  '1.0',
    'description': u"""
Catálogo de artículos SICE en GRP
=================================

* Artículos
* Familias, Sub familias, Clases, Sub clases
* Impuestos y Porcentajes
* Medidas
* Unidades de medida
* Marcas
* Objetos del gasto
* Colores
* Presentaciones
* Variantes
* Relación impuestos SICE - GRP
""",
    "depends" : ['stock','product','grp_seguridad'],
    'data': [
        'views/grp_catalogo_articulos_sice_mnu.xml',
        'views/grp_sice_familia_view.xml',
        'views/grp_sice_subflia_view.xml',
        'views/grp_sice_clase_view.xml',
        'views/grp_sice_subclase_view.xml',
        'views/grp_sice_impuesto_view.xml',
        'views/grp_sice_medida_view.xml',
        'views/grp_sice_unidades_med_view.xml',
        'views/grp_sice_marca_view.xml',
        'views/grp_sice_odg_view.xml',
        'views/grp_sice_color_view.xml',
        'views/grp_sice_presentacion_view.xml',
        'views/grp_sice_propiedad_view.xml',
        'views/grp_sice_art_serv_obra_view.xml',
        'views/grp_sice_rel_impuestos_view.xml',
        # 'wizard/carga_catalogo_sice_wizard_view.xml',
        'views/grp_sice_art_serv_busqueda_view.xml',
        'views/product_view.xml',
        'wizard/grp_novedades_sice.xml',
        'views/grp_sice_historico_view.xml',
        'views/grp_sice_error_log_view.xml',
        'views/grp_importar_articulos_view.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install': False,
    'installable': True,
    'application': True
}
