# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv  import osv, fields
import openerp
import time
import base64
from openerp import SUPERUSER_ID
import re


_logger = logging.getLogger(__name__)

class x_firma(osv.osv):
    _name = 'x_firma'


    # FirmaServer configuration parameters
    param_firma_server = "agesic.firma.server"
    param_url_applet = "agesic.firma.applet"
    param_url_wsdl = "agesic.firma.wsdl"
    param_odoo_server = "agesic.firma.odoo.server"

    # Default configuration valus
    #default_firma_server = "http://localhost:8080"
    default_firma_server = "https://testsirc.inau.gub.uy"
    default_url_applet = "FirmasWebStart/FirmaOdoo.jnlp"
    default_url_wsdl = "AgesicFirmaWS/AgesicFirmaServer?wsdl"
    default_odoo_server = "http://127.0.0.1:8069"

    # Initial module setup
    def init (self, cr):
        uid = SUPERUSER_ID
        _logger.debug('TRACE: init x_firma')
        sys_cfg = self.pool.get('ir.config_parameter')

        # If server parameters not defined, set to default configuration values
        if not sys_cfg.get_param(cr, uid, self.param_firma_server):
            sys_cfg.set_param(cr, uid, self.param_firma_server, self.default_firma_server)
        if not sys_cfg.get_param(cr, uid, self.param_url_applet):
            sys_cfg.set_param(cr, uid, self.param_url_applet, self.default_url_applet)
        if not sys_cfg.get_param(cr, uid, self.param_url_wsdl):
            sys_cfg.set_param(cr, uid, self.param_url_wsdl, self.default_url_wsdl)
        if not sys_cfg.get_param(cr, uid, self.param_odoo_server):
            sys_cfg.set_param(cr, uid, self.param_odoo_server, self.default_firma_server)
        return True


    # Invocación de Web Service firmarDocumentos
    def invocar_ws_firmarDocumentos(self, cr, uid, params, context=None):
        _logger.debug('TRACE: invocar_ws_firmarDocumentos')
        from suds.client import Client

        base_firma_server = self.pool.get('ir.config_parameter').get_param(cr, uid, self.param_firma_server)
        firma_server_wsdl = self.pool.get('ir.config_parameter').get_param(cr, uid, self.param_url_wsdl)

        url_envio = base_firma_server + "/" + firma_server_wsdl
        client = Client(url_envio)
        tipo_firma = params[0]
        documento = params[1]
        id_registro = params[2]
        nombre_reporte = params[3]

        id_transaction = client.service.firmarDocumentos(tipo_firma, documento)
        if id_transaction :
            id_firma = self.create(cr, SUPERUSER_ID, {'id_transaction': id_transaction, 'id_registro': id_registro, 'nombre_doc': nombre_reporte})
	    return id_firma
        else:
            return False

    # Invocación de Web Service ws_obtenerDocumentosFirmados
    def invocar_ws_obtenerDocumentosFirmados(self, cr, uid, param, context=None):
        _logger.debug('TRACE: invocar_ws_obtenerDocumentosFirmados')
        from suds.client import Client

        resultado = self.browse(cr, uid, param[0])

        if param[1]:
            base_firma_server = self.pool.get('ir.config_parameter').get_param(cr, uid, self.param_firma_server)
            firma_server_wsdl = self.pool.get('ir.config_parameter').get_param(cr, uid, self.param_url_wsdl)
            # Build URL from it's components
            url_envio = base_firma_server + "/" + firma_server_wsdl

            client = Client(url_envio)
            respuesta = client.service.obtenerDocumentosFirmados(param[1])
            if respuesta:
                if respuesta[0].valid:
                    return respuesta[0].doc[0]
                else:
                    return False
            return False
        return False

    # Transfer to applet page
    def muestra_applet_doc(self, cr, uid, params, context=None):
        _logger.debug('TRACE: muestra_applet_doc')
        id_firma = params[0]
        modelo = params[1]
        adjunto = params[2]
        data = self.browse(cr, SUPERUSER_ID, id_firma, context=context)
        base_firma_server = self.pool.get('ir.config_parameter').get_param(cr, uid, self.param_firma_server)
        base_odoo_server = self.pool.get('ir.config_parameter').get_param(cr, uid, self.param_odoo_server)
        firma_server_applet = self.pool.get('ir.config_parameter').get_param(cr, uid, self.param_url_applet)
        applet_options = "id_transaction=" + data.id_transaction + "&model=" + modelo + "&attachment=" + adjunto + "&uid=" + str(uid) + "&odoo=" + base_odoo_server
        
        # Build applet URL from server, path and options
        url_envio = base_firma_server + "/" + firma_server_applet + "?" + applet_options
        _logger.info('url_envio %s',url_envio)
        return {
            'type' : 'ir.actions.act_url',
            'url':   url_envio,
            'target': 'self',
        }

    # Se implementa en cada clase para modelar el comportamiento de cambio de estado del workflow o la acción que corresponda
    def utiles(self, cr, uid, modelo, id_registro, context = None ):
        return True

    # Adjunta el documento al modelo
    def adjuntar_documento(self, cr, uid, params, context = None ):
        _logger.info('params %s',params)
        attachment_obj = self.pool.get('ir.attachment')
        id_registro = params[0]
        rec_id = params[1]
        documento = params[2]
        modelo = params[3]
        adjunto = params[4]

        x_firma_rec = self.browse(cr, SUPERUSER_ID, rec_id, context)
        nombre_reporte = x_firma_rec.nombre_doc

        file_name = re.sub(r'[^a-zA-Z0-9_-]', '_', nombre_reporte)
        file_name += ".pdf"

        if adjunto == 'True':
            user_obj = self.pool.get('res.users')
            compania_id = user_obj.browse (cr, uid, uid, context).company_id.id

            attachment_id = attachment_obj.search (cr, uid, [('res_model', '=', modelo), ('company_id', '=', compania_id), ('res_id', '=', id_registro)])
            attachment_obj.write(cr, uid, attachment_id, {'datas': documento}, context)
        else:
            attachment_id = attachment_obj.create(cr, uid,
                {   'name': file_name,
                    'datas': documento,
                    'datas_fname': file_name,
                    'res_model': modelo,
                    'res_id': id_registro,
                    'type': 'binary'
                }, context=context)

        modelo_obj = self.pool.get(modelo)
        modelo_obj.write(cr, uid, [id_registro], {'x_doc_firmado': True}, context)



    # Arma el documento a partir del reporte
    def genera_documento(self, cr, uid, ids, modelo, nombre_reporte, context=None):
        _logger.debug('TRACE: generar_documento')
        result = {}
        format = ''
        record = {}
        modelo_obj = self.pool.get(modelo)
        for record in modelo_obj.browse(cr, uid, ids, context=context):
            ir_actions_report = self.pool.get('ir.actions.report.xml')
            matching_reports = ir_actions_report.search(cr, uid, [('name','=', nombre_reporte)])
            if matching_reports:
                report = ir_actions_report.browse(cr, uid, matching_reports[0])
                result, format = openerp.report.render_report(cr, uid, [record.id], report.report_name, {'model': modelo}, context=context)
                eval_context = {'time': time, 'object': record}
                if not report.attachment or not eval(report.attachment, eval_context):
                    # no auto-saving of report as attachment, need to do it manually
                    result = base64.b64encode(result)
        return result, format, record


    # Invoca al applet de firma electrónica
    def firmar_documento (self, cr, uid, ids, modelo, nombre_reporte, adjunto, context=None):
        _logger.debug('TRACE: firmar_documento')
        if adjunto == 'True':
            # busca el reporte ya generado en los adjuntos
            user_obj = self.pool.get('res.users')
            compania_id = user_obj.browse (cr, uid, uid, context).company_id.id

            attachment_obj = self.pool.get('ir.attachment')
            attachment_id = attachment_obj.search (cr, uid, [('res_model', '=', modelo), ('company_id', '=', compania_id), ('res_id', '=', ids[0])])
            documento = attachment_obj.read (cr, uid, attachment_id, ['datas'], context)[0]['datas']
            format = 'pdf'
            id_record = ids[0]
        else:
            documento, format, record = self.genera_documento(cr, uid, ids, modelo, nombre_reporte, context)
            id_record = record.id

        id_firma = self.invocar_ws_firmarDocumentos(cr, uid, [format, documento, id_record, nombre_reporte], context)
        applet = self.muestra_applet_doc(cr, uid, [id_firma, modelo, adjunto], context=context)
        return applet


    # Campos del modelo
    _columns = {
        'id_transaction': fields.char(u'Id Transacción', size=64, readonly=True),
        'id_registro': fields.integer('Id registro'),
        'nombre_doc': fields.char('Nombre', size=100),
        'certificado': fields.binary("Certificado"),
    }

x_firma()

class res_company(osv.osv):
    _inherit = 'res.company'
    # Campo para habilitar firma electronica
    _columns = {
        'firma_electronica': fields.boolean(u'Firma Electrónica'),
    }
res_company()

class res_users(osv.osv):
    _inherit = 'res.users'
    # campo para firma electronica
    _columns = {
        'firma_electronica': fields.boolean(u'Firma Electrónica'),
    }
res_users()
