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

import res_company
import grp_product
import grp_tesoreria
import grp_bank_statement
import grp_bank_statement_v8
import grp_valores_custodia
import grp_account_bank_statement_line
import grp_pedido_compra
import grp_cotizaciones
import grp_valores_custodia_v8
import grp_tipo_valores_custodia
import grp_account_transfer
import grp_bank_acc_rec_statement
import grp_retenciones_manuales
import grp_caja # TODO: SPRING 10 GAP 474 M
import grp_caja_pagadora_tesoreria # TODO: SPRING 10 GAP 474 M
import grp_checkbook # TODO: SPRING 10 GAP 283 L
import grp_account_voucher_v8 # TODO: SPRING 10 GAP 266 C
import grp_internal_pay_order # TODO: SPRING 10 GAP 474 M
import grp_caja_chica_tesoreria # TODO: SPRING 10 GAP 474 C
import grp_account_invoice_v8
import amount_to_text_es
import grp_transferencia_cabezal# TODO: SPRING 11 GAP 285 C
import grp_caja_recaudadora_tesoreria # TODO: SPRING 11 GAP 292 M
import grp_vale_caja # TODO: C SPRING 12 GAP 301
import res_partner # TODO: SPRING 10 GAP 274.275 K
import grp_account_journal # TODO: SPRING 10 GAP 274.275 K
import grp_tipo_rendicion # TODO: M SPRING 13 GAP 281
import grp_rendicion_caja # TODO: M SPRING 13 GAP 281
import grp_rendicion_cuentas_bancarias # TODO: M SPRING 13 GAP 281
import grp_solicitud_anticipos_fondos # TODO: M SPRING 14 GAP 29_31
import grp_anticipos_fondos # TODO: M SPRING 14 GAP 29_31
import grp_rendicion_anticipo # TODO: M SPRING 14 GAP 29_31
import grp_devolucion_anticipos_fondos # TODO: M SPRING 14 GAP 29_31
import grp_account_move_line_v8
import grp_remesa # TODO: K SPRING 15
import grp_account_invoice_line_v8
import res_users

import grp_cashbox_register
import grp_cashbox_register_execution