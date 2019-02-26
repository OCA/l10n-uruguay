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
    'name': 'GRP - Tesoreria',
    'version': '1.0',
    'author': 'Quanam',
    'website': 'www.quanam.com',
    'category': '',
    'images': [],
    'depends': ['base','account','npg_bank_account_reconciliation', 'grp_account',
                'grp_factura_siif','grp_factura_sice','account_transfer','grp_seguridad',
                'grp_viaticos', 'report_xls','base_suspend_security',
                'account_financial_report_webkit'],
    'description': """
GRP - Tesoreria
""",
    'demo': [],
    'data': [
        'security/grp_tesoreria_security.xml',  
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'report/reports.xml',
        'data/grp_tesoreria_data.xml',
        'views/res_company_view.xml',
        'views/grp_product_view.xml',
        'views/grp_tesoreria_view.xml',
        'views/grp_bank_statement_view.xml',
        'views/grp_valores_custodia_view.xml',
        'views/grp_account_bank_statement_lines.xml',
        'views/grp_account_transfer_view.xml',
        'views/grp_cotizaciones_view.xml',
        'views/grp_pedido_compra_view.xml',
        'data/sequence_data.xml',
        'views/grp_tipo_valores_custodia.xml',
        'views/grp_baja_oficio_view.xml',
        'views/grp_bank_acc_rec_statement_view.xml',
        'views/grp_retenciones_manuales_view.xml',
        # 'views/grp_retenciones_manuales_view_tounify.xml',
        'views/grp_internal_pay_order_view.xml',# TODO: SPRING 10 GAP 474 M
        'views/grp_caja_view.xml',# TODO: SPRING 10 GAP 474 M
        'views/grp_producto_cuenta_deposito_view.xml',# TODO: SPRING 11 GAP 292 M
        'views/grp_concepto_factura_view.xml',# TODO: M SPRING 11 GAP 292.A
        'views/grp_origen_factura_view.xml',# TODO: M SPRING 11 GAP 292.A
        'views/account_voucher_sales_purchase_view.xml',
        'wizard/grp_caja_pagadora_account_voucher_wizard_view.xml',# TODO: SPRING 10 GAP 474 M
        'wizard/grp_caja_pagadora_account_voucher_payment_view.xml',# TODO: SPRING 10 GAP 474 M
        'wizard/grp_caja_chica_account_voucher_wizard_view.xml',# TODO: SPRING 10 GAP 474 C
        'wizard/grp_caja_chica_valores_custodia_wizard_view.xml',# TODO: SPRING 10 GAP 474 C
        'wizard/grp_caja_chica_movimiento_efectivo_wizard_view.xml',# TODO: SPRING 10 GAP 474 C
        'wizard/grp_caja_recaudadora_boleto_siif_voucher_wizard_view.xml',# TODO: SPRING 11 GAP 292 M
        'wizard/grp_caja_recaudadora_boleto_siif_valores_custodia_wizard_view.xml',# TODO: SPRING 11 GAP 292 M
        'wizard/grp_transferencia_cabezal_comprobantes_wizard_view.xml',# TODO: SPRING 11 GAP 285 C
        'wizard/grp_anular_voucher_wizard_view.xml',# RAGU
        'wizard/grp_caja_recaudadora_boleto_siif_cajas_wizard_view.xml', #MVARELA
        'wizard/grp_remesa_wizard_view.xml', # TODO: K SPRING 15
        'wizard/grp_confirmacion_eleminar_ret_manuales_wizard.xml', # TODO: K SPRING 15
        'wizard/grp_frcomposition_wizard_view.xml',
        'views/grp_account_voucher_view.xml',# TODO: SPRING 10 GAP 266 C
        'views/account_invoice_obligacion_view.xml',# TODO: SPRING 10 GAP 274.275 K
        'views/res_partner_view.xml',# TODO: SPRING 10 GAP 274.275 K
        'views/grp_account_journal_view.xml',# TODO: SPRING 10 GAP 274.275 K
        'views/grp_account_invoice_view.xml',# TODO: SPRING 11 GAP 292 M
        'views/grp_caja_pagadora_tesoreria_view.xml',# TODO: SPRING 10 GAP 474 M
        'views/grp_caja_recaudadora_tesoreria_view.xml',# TODO: SPRING 11 GAP 292 M
        'views/grp_caja_recaudadora_boleto_siif_view.xml',# TODO: SPRING 11 GAP 292 M
        'views/grp_remesa_view.xml',# TODO: K SPRING 15
        'views/grp_caja_chica_tesoreria_view.xml',# TODO: SPRING 10 GAP 474 C
        'views/grp_checkbook.xml',# TODO: SPRING 10 GAP 283 L
        'views/grp_caja_menus_view.xml',# TODO: SPRING 10 GAP 474 M
        'views/grp_transferencia_cabezal_view.xml',# TODO: SPRING 11 GAP 285 C
        'views/grp_vale_caja_view.xml',# TODO: C SPRING 12 GAP 301
        'views/grp_tesoreria_menus.xml',# TODO: SPRING 11 GAP 474 K
        'views/product_view.xml',# TODO: M SPRING 11 GAP 292
        'views/grp_tipo_rendicion_view.xml',# TODO: M SPRING 13 GAP 281
        'views/grp_rendicion_caja_view.xml',# TODO: M SPRING 13 GAP 281
        'views/grp_rendicion_cuentas_bancarias_view.xml',# TODO: M SPRING 13 GAP 281
        'data/grp_fodos_sequence.xml',  # TODO: M SPRING 14 GAP 29_31
        'views/grp_solicitud_anticipos_fondos_view.xml',  # TODO: M SPRING 14 GAP 29_31
        'views/grp_anticipos_fondos_view.xml',  # TODO: M SPRING 14 GAP 29_31
        'views/grp_rendicion_anticipo.xml',  # TODO: M SPRING 14 GAP 29_31
        'views/grp_devolucion_anticipos_fondos_view.xml',  # TODO: M SPRING 14 GAP 29_31
        'report/grp_registro_caja_chica_report.xml',  # TODO: M SPRING 14 GAP 29_31
        'report/grp_recaudacion_report_view.xml',  # TODO: L SPRING 12 GAP 479
        'report/grp_anticipo_report_view.xml',  # TODO: L SPRING 12 GAP 479
        'report/grp_bank_statement_trace_report.xml',  # TODO: L SPRING 12 GAP 479
        'report/grp_remesas_siif_report_view.xml',

        'views/grp_cashbox_register_view.xml',
        'views/grp_cashbox_register_composition_view.xml',
        'views/grp_cashbox_register_execution_view.xml'
    ],
    'installable': True,
    'auto_install': False,
}
