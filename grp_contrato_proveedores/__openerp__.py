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
    'name': 'GRP - Contratos de Proveedores',
    'version': '1.0',
    'author': 'Quanam',
    'website': 'www.quanam.com',
    'category': 'Accounting & Finance',
    'images': [],
    'depends': [
        'base',
        'account',
        'mail',
        'grp_seguridad',
        'grp_tesoreria',
        'contracts_pro',
	    'report_xls',
        'grp_activo_fijo'
    ],
    'description': """
    Mantenimiento de contratos de proveedores
    """,
    'demo': [],
    'test': [],
    'data': [
        'security/grp_contrato_proveedores_security.xml',
        'wizard/grp_crear_adenda_wizard.xml', # TODO C SPRING 12 GAP_75_76
        'wizard/grp_crear_prorroga_wizard.xml', # TODO: K SPRING 12 GAP 70, 71, 73, 74
        'wizard/grp_crear_renovacion_wizard.xml', # TODO: K SPRING 12 GAP 70, 71, 73, 74
        'views/grp_contrato_proveedores_view.xml',
        'wizard/grp_invoice_contract_cession_wizard_view.xml', # TODO: M SPRING 12 GAP 77
	    'views/grp_account_invoice_view.xml',# TODO: L SPRING 12 GAP 499
        'views/grp_tipo_contrato_view.xml', # TODO: K SPRING 12 GAP 67
        'views/grp_cotizaciones_view.xml', # TODO: K SPRING 12 GAP 67
        'views/grp_afectacion_view.xml', # TODO: K SPRING 12 GAP 205
        'views/grp_compromiso_view.xml', # TODO: K SPRING 12 GAP 205
        'views/grp_valores_custodia_view.xml', # TODO C SPRING 12 GAP_315
        'views/grp_historial_contratos_view.xml', # TODO L SPRING 12 GAP 84
        'views/grp_contrato_historial_parametrica_report_view.xml', # TODO C SPRING 12 GAP_360
        'wizard/grp_crear_contratos_wizard.xml', # TODO: K SPRING 12 GAP 67
        'wizard/grp_motivo_desvios_montos_wizard.xml', # TODO: K SPRING 12 GAP 205
        'wizard/grp_resumen_ejecucion_contrato_wizard.xml', # TODO: K SPRING 13 GAP 452
        'wizard/grp_ejecucion_futura_contrato_wizard.xml', # TODO: K SPRING 13 GAP 452
        'data/sequence_data.xml',
        'data/grp_contrato_proveedores_alertas_data.xml',  # TODO: L SPRING 12 GAP 85
        'security/ir.model.access.csv',
        'report/contract_account_cession_report.xml',# TODO: M SPRING 12 GAP 79
        'report/grp_resumen_ejecucion_contrato.xml',# TODO: K SPRING 13 GAP 452
        'report/grp_estimado_ejecutar_contrato_view.xml',# TODO: K SPRING 13 GAP 452
        'report/grp_ejecucion_futura_contrato.xml',# TODO: K SPRING 13 GAP 452
        'report/grp_registro_ejecucion_futura_contrato_view.xml',# TODO: K SPRING 13 GAP 452
        'views/account_asset_asset_view.xml',
        'views/invite_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
