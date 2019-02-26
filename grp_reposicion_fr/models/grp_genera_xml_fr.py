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

from openerp.osv import osv
from lxml import etree
import time
from datetime import datetime
from suds.sax.text import Raw
from openerp import SUPERUSER_ID
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

from openerp import models, api

class siif_fr_xml_generator(models.TransientModel):
    _inherit = 'grp.siif.xml_generator'

    def gen_xml_obligacion_3en1_fr(self, cr, uid, fondo_rotatorio, llaves_presupuestales, importe, nro_carga, tipo_doc_grp, nro_modif_grp, tipo_modificacion, es_modif=False, retenciones=False, motivo=False, enviar_datos_sice=True, nro_obl_sist_aux=False):

        _tipo_registro = '01'
        _tipo_registracion= '04' if es_modif is False else '14'
        _concepto_gasto = fondo_rotatorio.siif_concepto_gasto.concepto
        _monto=str(int(round(importe,0)))

        company = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid).company_id

        estructura_obj = self.pool.get('presupuesto.estructura')

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        estructura = estructura_obj.obtener_estructura(cr, uid, fondo_rotatorio.fiscal_year_id.id,
                                                       fondo_rotatorio.inciso_siif_llp_id.inciso,
                                                       fondo_rotatorio.ue_siif_llp_id.ue,
                                                       llaves_presupuestales[0].programa,
                                                       llaves_presupuestales[0].proyecto,
                                                       llaves_presupuestales[0].mon,
                                                       llaves_presupuestales[0].tc,
                                                       llaves_presupuestales[0].fin,
                                                       llaves_presupuestales[0].odg,
                                                       llaves_presupuestales[0].auxiliar)

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'desc_tipo_mov').text = 'OBL_ORIG_Y_MODIF_GRP'
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = fondo_rotatorio.fiscal_year_id.name

        etree.SubElement(e_movimiento_presup, 'inciso').text = fondo_rotatorio.inciso_siif_llp_id.inciso or ''
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = fondo_rotatorio.ue_siif_llp_id.ue or ''

        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp

        # En 3en1 nro_afect_sist_aux, nro_comp_sist_aux y nro_obl_sist_aux son nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux').text = nro_obl_sist_aux

        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)

        etree.SubElement(e_movimiento_presup, 'nro_afectacion').text = str(fondo_rotatorio.nro_afectacion) if es_modif else ''
        etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(fondo_rotatorio.nro_compromiso) if es_modif else ''
        etree.SubElement(e_movimiento_presup, 'nro_obligacion').text = str(fondo_rotatorio.nro_obligacion) if es_modif or tipo_modificacion == 'N' else ''
        etree.SubElement(e_movimiento_presup, 'sec_obligacion')
        etree.SubElement(e_movimiento_presup, 'tipo_modificacion').text = tipo_modificacion
        etree.SubElement(e_movimiento_presup, 'fecha_elaboracion').text = time.strftime('%Y%m%d')

        etree.SubElement(e_movimiento_presup, 'monto_obligacion').text = str(int(round(fondo_rotatorio.total_reponer,0))) if not es_modif else _monto
        etree.SubElement(e_movimiento_presup, 'total_retenciones').text = str(int(round(fondo_rotatorio.total_retenciones,0)))
        etree.SubElement(e_movimiento_presup, 'liquido_pagable').text = str(int(round(fondo_rotatorio.liquido_pagable,0))) if not es_modif else _monto

        #FR siempre es Moneda Nacional
        etree.SubElement(e_movimiento_presup, 'partidas_mon_ext').text = 'N' if llaves_presupuestales[0].mon == '0' else 'S'
        etree.SubElement(e_movimiento_presup, 'monto_mon_ext')

        etree.SubElement(e_movimiento_presup, 'tipo_ejecucion').text = fondo_rotatorio.siif_tipo_ejecucion.codigo
        etree.SubElement(e_movimiento_presup, 'tipo_programa').text = 'T'
        etree.SubElement(e_movimiento_presup, 'tipo_documento').text = fondo_rotatorio.siif_tipo_documento.codigo or ''

        etree.SubElement(e_movimiento_presup, 'numero_documento')
        etree.SubElement(e_movimiento_presup, 'ano_doc_respaldo')
        etree.SubElement(e_movimiento_presup, 'fecha_doc_respaldo')
        etree.SubElement(e_movimiento_presup, 'serie_documento')
        etree.SubElement(e_movimiento_presup, 'secuencia_documento')
        etree.SubElement(e_movimiento_presup, 'fecha_recepcion').text = datetime.strptime(fondo_rotatorio.date_invoice, '%Y-%m-%d').strftime('%Y%m%d')
        etree.SubElement(e_movimiento_presup, 'fecha_vencimiento').text = datetime.strptime(fondo_rotatorio.fecha_vencimiento, '%Y-%m-%d').strftime('%Y%m%d')

        etree.SubElement(e_movimiento_presup, 'clase_doc_benef').text = 'T'

        inciso = company and int(company.inciso)
        # u_e = company and int(company.u_e)
        if fondo_rotatorio.unidad_ejecutora_id.codigo:
            u_e = fondo_rotatorio.unidad_ejecutora_id.codigo
        else:
            u_e = int(fondo_rotatorio.operating_unit_id.unidad_ejecutora)

        etree.SubElement(e_movimiento_presup, 'num_doc_benef').text = '%s%s' % (str(inciso).zfill(2), str(u_e).zfill(3))

        if fondo_rotatorio.res_partner_bank_id:
            if not fondo_rotatorio.res_partner_bank_id.bank_bic:
                raise osv.except_osv(('Error'),
                                     (u'Debe especificar el código de la cuenta bancaria.'))
            etree.SubElement(e_movimiento_presup, 'banco_cta_benef').text = fondo_rotatorio.res_partner_bank_id.bank_bic
            etree.SubElement(e_movimiento_presup, 'agencia_cta_benef').text = fondo_rotatorio.res_partner_bank_id.agencia or ''
            etree.SubElement(e_movimiento_presup, 'nro_cta_benef').text = fondo_rotatorio.res_partner_bank_id.acc_number
            etree.SubElement(e_movimiento_presup, 'tipo_cta_benef').text = 'A' if fondo_rotatorio.res_partner_bank_id.state == 'caja de ahorros' else 'C'
            etree.SubElement(e_movimiento_presup, 'moneda_cta_benef').text = '0' if not fondo_rotatorio.res_partner_bank_id.currency_id else '1'
        else:
            raise osv.except_osv(('Error'),
                                 (u'No se especificó la cuenta bancaria.'))

        etree.SubElement(e_movimiento_presup, 'concepto_gasto').text = _concepto_gasto

        etree.SubElement(e_movimiento_presup, 'financiamiento').text = fondo_rotatorio.siif_financiamiento.codigo
        etree.SubElement(e_movimiento_presup, 'codigo_sir').text = fondo_rotatorio.siif_codigo_sir.codigo

        # FR envia vacio los siguientes datos
        etree.SubElement(e_movimiento_presup, 'ano_proc_compra')
        etree.SubElement(e_movimiento_presup, 'inciso_proc_compra')
        etree.SubElement(e_movimiento_presup, 'unidad_ejec_proc_compra')
        etree.SubElement(e_movimiento_presup, 'tipo_proc_compra')
        etree.SubElement(e_movimiento_presup, 'subtipo_proc_compra')
        etree.SubElement(e_movimiento_presup, 'nro_proc_compra')
        etree.SubElement(e_movimiento_presup, 'nro_amp_proc_compra')

        etree.SubElement(e_movimiento_presup, 'tipo_cambio')
        etree.SubElement(e_movimiento_presup, 'anticipo').text = 'N'
        etree.SubElement(e_movimiento_presup, 'moneda').text = '0'

        etree.SubElement(e_movimiento_presup, 'resumen').text = fondo_rotatorio.siif_descripcion or '' if not es_modif else motivo
        etree.SubElement(e_movimiento_presup, 'nro_doc_fondo_rotatorio').text = fondo_rotatorio.siif_nro_fondo_rot.name or ''

        etree.SubElement(e_movimiento_presup, 'inciso_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'unidad_ejec_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_optgn')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transferencia')

        etree.SubElement(e_movimiento_presup, 'monto_compromiso')
        etree.SubElement(e_movimiento_presup, 'nro_doc_transf_monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva')
        etree.SubElement(e_movimiento_presup, 'monto_iva_mon_ext')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers')
        etree.SubElement(e_movimiento_presup, 'monto_serv_pers_mon_ext')
        etree.SubElement(e_movimiento_presup, 'sec_compromiso')

        e_detalle = etree.SubElement(e_movimiento_presup, 'Detalle')
        for llave in llaves_presupuestales:
            estructura = estructura_obj.obtener_estructura(cr, uid, fondo_rotatorio.fiscal_year_id.id, fondo_rotatorio.inciso_siif_llp_id.inciso,
                                                                       fondo_rotatorio.ue_siif_llp_id.ue,
                                                                       llave.programa, llave.proyecto, llave.mon, llave.tc,
                                                                       llave.fin, llave.odg, llave.auxiliar)
            e_detalle_siif = etree.SubElement(e_detalle, 'DetalleSIIF')
            if estructura:
                etree.SubElement(e_detalle_siif, 'tipo_registro').text = '02'
                etree.SubElement(e_detalle_siif, 'tipo_registracion').text = _tipo_registracion
                etree.SubElement(e_detalle_siif, 'programa').text = estructura.linea_programa
                etree.SubElement(e_detalle_siif, 'desc_tipo_mov').text='PART_OBL_ORIG_Y_MODIF_GRP'
                etree.SubElement(e_detalle_siif, 'proyecto').text = estructura.linea_proyecto
                etree.SubElement(e_detalle_siif, 'objeto_gasto').text = estructura.linea_og
                etree.SubElement(e_detalle_siif, 'auxiliar').text = estructura.linea_aux
                etree.SubElement(e_detalle_siif, 'financiamiento').text = estructura.linea_ff
                etree.SubElement(e_detalle_siif, 'moneda').text = estructura.linea_moneda
                etree.SubElement(e_detalle_siif, 'tipo_credito').text = estructura.linea_tc
            if es_modif:
                if tipo_modificacion == 'N':
                    monto = str(int(-llave.importe))
                else:
                    monto = _monto
            else:
                monto = str(int(llave.importe))
            etree.SubElement(e_detalle_siif, 'importe').text = monto

        e_retencion = etree.SubElement(e_movimiento_presup, 'Retenciones')
        for retencion in retenciones:
            if retencion['monto'] != 0:
                e_retencion_siif = etree.SubElement(e_retencion, 'RetencionSIIF')
                etree.SubElement(e_retencion_siif, 'tipo_registro').text = '03'
                etree.SubElement(e_retencion_siif, 'tipo_registracion').text = _tipo_registracion
                etree.SubElement(e_retencion_siif, 'grupo_acreedor').text = retencion['grupo'] and str(retencion['grupo']) or ''
                etree.SubElement(e_retencion_siif, 'acreedor').text = retencion['acreedor'] and str(retencion['acreedor']) or ''
                etree.SubElement(e_retencion_siif, 'importe').text = str(int(round(retencion['monto'],0)))

        e_impuestos = etree.SubElement(e_movimiento_presup, 'Impuestos')
        # MVARELA 04/12/2018: Los FR no deben enviar Impuestos
        # for retencion in retenciones:
        #     if not retencion['es_manual']:
        #         e_impuesto_siif = etree.SubElement(e_impuestos, 'ImpuestoSIIF')
        #         etree.SubElement(e_impuesto_siif, 'tipo_registro').text = '05'
        #         etree.SubElement(e_impuesto_siif, 'tipo_registracion').text = _tipo_registracion
        #         etree.SubElement(e_impuesto_siif, 'tipo_impuesto').text = str(retencion['acreedor'])
        #         # if 'base_impuesto' in retencion:
        #         etree.SubElement(e_impuesto_siif, 'monto_calculo').text = str(int(round(retencion['base_impuesto']))) if tipo_modificacion != 'N' else str(-int(round(retencion['base_impuesto'])))
        #         # if 'base_impuesto_mont_ext' in retencion:
        #         #     etree.SubElement(e_impuesto_siif, 'monto_calculo_mon_ext').text = str(int(round(retencion['base_impuesto_mont_ext']))) if tipo_modificacion != 'N' else str(-int(round(retencion['base_impuesto_mont_ext'])))

        e_ces_o_emb = etree.SubElement(e_movimiento_presup, 'CesionesOEmbargos')

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')

        return xml2


    def gen_xml_borrado_3en1_fr(self, cr, uid, fondo_rotatorio, nro_carga, tipo_doc_grp, nro_modif_grp, nro_obl_sist_aux=False):

        _tipo_registracion= '24'
        _tipo_registro = '01'

        root = etree.Element('MovimientosSIIF')
        etree.SubElement(root, 'nro_carga').text = nro_carga
        e_movimientos = etree.SubElement(root, 'movimientos')

        e_movimiento_presup = etree.SubElement(e_movimientos, 'MovimientoPresupuestalSIIF')
        etree.SubElement(e_movimiento_presup, 'tipo_registro').text = _tipo_registro
        etree.SubElement(e_movimiento_presup, 'tipo_registracion').text = _tipo_registracion
        etree.SubElement(e_movimiento_presup, 'ano_fiscal').text = fondo_rotatorio.fiscal_year_id.name
        etree.SubElement(e_movimiento_presup, 'inciso').text = fondo_rotatorio.inciso_siif_llp_id.inciso
        etree.SubElement(e_movimiento_presup, 'unidad_ejecutora').text = fondo_rotatorio.ue_siif_llp_id.ue
        etree.SubElement(e_movimiento_presup, 'tipo_doc_sist_aux').text = tipo_doc_grp

        etree.SubElement(e_movimiento_presup, 'nro_afect_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_comp_sist_aux').text = nro_obl_sist_aux
        etree.SubElement(e_movimiento_presup, 'nro_obl_sist_aux').text = nro_obl_sist_aux

        etree.SubElement(e_movimiento_presup, 'nro_modif_sist_aux').text = str(nro_modif_grp)
        etree.SubElement(e_movimiento_presup, 'nro_afectacion').text= str(fondo_rotatorio.nro_afectacion)
        etree.SubElement(e_movimiento_presup, 'financiamiento').text = fondo_rotatorio.siif_financiamiento.codigo
        etree.SubElement(e_movimiento_presup, 'nro_compromiso').text = str(fondo_rotatorio.nro_compromiso)
        etree.SubElement(e_movimiento_presup, 'nro_obligacion').text = str(fondo_rotatorio.nro_obligacion)
        etree.SubElement(e_movimiento_presup, 'sec_obligacion').text = fondo_rotatorio.siif_sec_obligacion or ''

        xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2


    def gen_xml_estado_solicitud(self, anio_fiscal, inciso, unidad_ejecutora, nro_carga):
        root = etree.Element('ConsultaWS')
        e_movimiento = etree.SubElement(root, 'movimiento')
        etree.SubElement(e_movimiento, 'nro_carga').text = nro_carga
        etree.SubElement(e_movimiento, 'ano_fiscal').text = anio_fiscal.name
        etree.SubElement(e_movimiento, 'inciso').text = inciso
        etree.SubElement(e_movimiento, 'unidad_ejecutora').text = unidad_ejecutora
        xml = etree.tostring(root, pretty_print=False, xml_declaration=True, encoding='UTF-8', standalone="no")
        xml2 = Raw(u'<![CDATA[' + xml.decode('utf-8') + u']]>')
        return xml2


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
