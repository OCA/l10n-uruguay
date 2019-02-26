# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Enterprise Management Solution
#    GRP Estado Uruguay
#    Copyright (C) 2018 ATOS Uruguay
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

from openerp.exceptions import Warning
import smtplib
import logging

_logger = logging.getLogger(__name__)

PROCESO_ORIGEN_3EN1 = '3en1'
PROCESO_ORIGEN_AFECTACION = 'afectacion'
PROCESO_ORIGEN_APG = 'apg'

PROCESO_ORIGEN_3EN1_MODIFICACION = '3en1_modificacion'
PROCESO_ORIGEN_AFECTACION_MODIFICACION = 'afectacion_modificacion'
PROCESO_ORIGEN_APG_MODIFICACION = 'apg_modificacion'

TIPO_DE_MENSAJE_ADVERTENCIA = 'Advertido'
TIPO_DE_MENSAJE_BLOQUEO = 'Bloqueado'


def generar_llave_a_utilizar(inciso_id, ue_id, llave_a_utilizar):
    odg_id = llave_a_utilizar.odg_id
    aux_id = llave_a_utilizar.auxiliar_id
    ff_id = llave_a_utilizar.fin_id
    programa_id = llave_a_utilizar.programa_id
    proyecto_id = llave_a_utilizar.proyecto_id
    moneda_id = llave_a_utilizar.mon_id
    tc_id = llave_a_utilizar.tc_id

    display_name = inciso_id.display_name or ''
    display_name += '-'
    display_name += ue_id.display_name or ''
    display_name += '-'
    display_name += odg_id.display_name or ''
    display_name += '-'
    display_name += aux_id.display_name or ''
    display_name += '-'
    display_name += ff_id.display_name or ''
    display_name += '-'
    display_name += programa_id.display_name or ''
    display_name += '-'
    display_name += proyecto_id.display_name or ''
    display_name += '-'
    display_name += moneda_id.display_name or ''
    display_name += '-'
    display_name += tc_id.display_name or ''
    return display_name


def obtener_plan_activo(self):
    _logger.info('### Obtener el Plan Activo ###')

    plan_presupuestal = self.env['grp.pep.anual']
    plan_activo = plan_presupuestal.obtener_plan_activo()

    if plan_activo:
        _logger.info('El ID del Plan Activo es: %s\n' % plan_activo.id)
    else:
        _logger.error('ERROR, no pudo obtenerce el Plan Activo!')

    return plan_activo


def valido_contra_pep(self, id_concepto, llave_a_validar, importe):
    _logger.info('### Validacion contra PEP ###')
    print '### Validacion contra PEP ###'

    plan_actual = obtener_plan_activo(self)

    resultado_pep = plan_actual.saldo_disponible(id_concepto, llave_a_validar, importe)
    _logger.info('Referencias de respuestas de la Validacion PEP:\n \
                    %s: CONCEPTO_LLAVE_CON_SALDO\n \
                    %s: CONCEPTO_LLAVE_SIN_SALDO_ADVERTENCIA\n \
                    %s: CONCEPTO_LLAVE_SIN_SALDO_BLOQUEO\n\n \
                    Resultado de la Validacion del PEP: %s\n' % \
                    (plan_actual.CONCEPTO_LLAVE_CON_SALDO, 
                    plan_actual.CONCEPTO_LLAVE_SIN_SALDO_ADVERTENCIA,
                    plan_actual.CONCEPTO_LLAVE_SIN_SALDO_BLOQUEO,
                    resultado_pep))

    resultado_de_validacion = { 'puede_continuar': False, 'mensaje': str() }

    if resultado_pep == plan_actual.CONCEPTO_LLAVE_CON_SALDO:
        _logger.info('Resultado PEP => OK')
        print 'Resultado PEP => OK'
        resultado_de_validacion['puede_continuar'] = True

    elif resultado_pep == plan_actual.CONCEPTO_LLAVE_SIN_SALDO_ADVERTENCIA:
        _logger.info('Resultado PEP => ALERTA')
        print 'Resultado PEP => ALERTA'
        resultado_de_validacion['puede_continuar'] = True
        resultado_de_validacion['mensaje'] = u'Advertencia, Llave sin Saldo en Plan de Ejecución Presupuestal.'

    elif resultado_pep == plan_actual.CONCEPTO_LLAVE_SIN_SALDO_BLOQUEO:
        _logger.info('Resultado PEP => BLOQUEAR')
        print 'Resultado PEP => BLOQUEAR'
        resultado_de_validacion['puede_continuar'] = False
        resultado_de_validacion['mensaje'] = u'Bloqueado, Llave sin Saldo en Plan de Ejecución Presupuestal.'

    return resultado_de_validacion

def mensaje_de_advertencia_a_retornar(self, mensaje_pep):
    nuevo_wizard = self.env['mensaje.de.advertencia.wizard'].create({'mensaje_a_mostrar': mensaje_pep})

    return {
        'name': u"Warning",
        'type': 'ir.actions.act_window',
        'res_model': 'mensaje.de.advertencia.wizard',
        'view_mode': 'form',
        'view_type': 'form',
        'res_id': nuevo_wizard.id,
        'views': [(False, 'form')],
        'target': 'new',
    }

def obtener_conceptos_del_plan_activo(self):
    plan_activo = obtener_plan_activo(self)
    conceptos_del_plan_activo = plan_activo.obtener_conceptos_plan_activo()

    return [('id', 'in', conceptos_del_plan_activo.ids)]

def obtener_llaves_a_mostrar_en_la_tabla(self):
    concepto_seleccionado = self.concepto_id

    if 'concepto_de_modificacion_id' in self:
        if self.concepto_de_modificacion_id:
            concepto_seleccionado = self.concepto_de_modificacion_id

    llaves_del_concepto = concepto_seleccionado.lineas_gasto

    llaves_a_mostrar = list()
    for llave in llaves_del_concepto:
        llaves_a_mostrar.append((0, 0, {
                                            'odg_id': llave.odg_id.id,    
                                            'auxiliar_id': llave.aux_id.id,    
                                            'fin_id': llave.ff_id.id,    
                                            'programa_id': llave.programa_id.id,    
                                            'proyecto_id': llave.proyecto_id.id,    
                                            'mon_id': llave.moneda_id.id,    
                                            'tc_id': llave.tc_id.id,    
                                        }))

    return llaves_a_mostrar


def obtener_usuarios_del_grupo_elaboracion_plan_ejecucion(self):
    grupo_de_responsables = self.env['res.groups'].search([('name', '=', u'Elaboración de Plan de Ejecución')])
    usuarios_del_grupo = grupo_de_responsables.users

    return usuarios_del_grupo

def obtener_este_concepto(self, id_concepto):
    concepto = self.env['grp.pep.concepto'].browse(id_concepto)

    return concepto


def enviar_mail_de_error_a_todos_los_responsables(self, id_concepto, llaves_con_error, tipo_mensaje):
    usuarios_del_grupo = obtener_usuarios_del_grupo_elaboracion_plan_ejecucion(self)
    usuarios_responsables = filter(lambda un_usuario : un_usuario.es_responsable_de_validacion_pep, usuarios_del_grupo)

    concepto = obtener_este_concepto(self, id_concepto)
    nombre_concepto = concepto.name_get()[0][1]
    usuario_activo = self.create_uid

    nombre_documento = 'Sin Documento'

    if not 'modificacion' in self._name:
        nombre_documento = self.name

    elif 'factura_original' in self:
        factura_original = self.factura_original

        if 'modificacion_apg' in self._name:
            nombre_documento = factura_original.name

        else:
            nombre_documento = factura_original.nro_factura_grp

    nombre_usuario_activo = usuario_activo.name
    mail_usuario_activo = usuario_activo.email

    for usuario in usuarios_responsables:
        mail_responsable = usuario.email

        for llave_utilizada in llaves_con_error:
            enviar_mail_de_error_al_responsable(self, mail_responsable, nombre_usuario_activo, mail_usuario_activo, nombre_documento, nombre_concepto, llave_utilizada, tipo_mensaje)


def enviar_mail_de_error_al_responsable(self, mail_destino, nombre_usuario_activo, mail_usuario_activo, nombre_documento, nombre_concepto, llave_utilizada, tipo_mensaje):
    _logger.info('### Enviando Mail al Responsable ###')
    print '### Enviando Mail al Responsable ###'

    asunto_a_mostar = 'Advertencia' if tipo_mensaje == TIPO_DE_MENSAJE_ADVERTENCIA else 'Bloqueo'

    mail_body = """<![CDATA[
                    <div style="font-family: 'Lucida Sans Unicode', 'Lucida Grande', Helvetica, Arial, sans-serif;font-size: 12px; color: #000; background-color: #FFF;">
                        <h3>ERROR! - %(asunto_mail)s</h3>
                        <p>Al Usuario <b>%(nombre_usuario)s</b> (<i>%(mail_usuario)s</i>) se lo ha <b>%(bloqueo_advertencia)s</b> en el Documento <b>%(nombre_documento)s</b> para el Concepto <b>%(nombre_concepto)s</b> y la Llave <b>%(llave_utilizada)s</b>.</p>
                        <br/><br/>
                        <p>Saludos,</p>
                        <h4>Odoo - CEIP</h4>
                    </div>
                """ % {'asunto_mail': asunto_a_mostar, 'nombre_usuario': nombre_usuario_activo, 'mail_usuario': mail_usuario_activo, 'bloqueo_advertencia': tipo_mensaje, 'nombre_documento': nombre_documento, 'nombre_concepto': nombre_concepto, 'llave_utilizada': llave_utilizada}

    _logger.info('Body del Mail a enviar:\n%s\n' % mail_body)
    
    mail_values = {
        'type': 'email',
        'state': 'outgoing',
        'subject': '*** ERROR - %s ***' % asunto_a_mostar,
        'body_html': mail_body,
        'email_to': mail_destino,
        'email_from': mail_usuario_activo
     }

    _logger.info('Valores de configuracion del Mail a enviar:\n%s\n' % mail_values)

    objeto_mail = self.env['mail.mail']
    id_del_mensaje = objeto_mail.create(mail_values)

    if id_del_mensaje:
        objeto_mail.send([id_del_mensaje])
        _logger.info('Se ha enviado mail a la direccion %s!' % mail_destino)

    else:
        _logger.error('ERROR, no se pudo enviar mail a la direccion %s!' % mail_destino)


def realizar_validacion_contra_pep(self):
    id_concepto = self.concepto_id.id 

    if 'concepto_de_modificacion_id' in self:
        if self.concepto_de_modificacion_id:
            id_concepto = self.concepto_de_modificacion_id.id

    llaves_con_importe_a_validar = self.llpapg_ids
    inciso = self.inciso_siif_id
    unidad_ejecutora = self.ue_siif_id

    puedo_seguir = True
    mensaje_pep = str()
    llaves_con_error = list()

    for llave_con_importe in llaves_con_importe_a_validar:
        importe_llave = llave_con_importe.importe

        llave_a_validar = generar_llave_a_utilizar(inciso, unidad_ejecutora, llave_con_importe)

        resultado_pep = valido_contra_pep(self, id_concepto, llave_a_validar, importe_llave)
        puedo_seguir &= resultado_pep['puede_continuar']
        mensaje_pep = resultado_pep['mensaje'] if not mensaje_pep or not puedo_seguir else mensaje_pep

        if puedo_seguir:
            if mensaje_pep:
                llaves_con_error.append(llave_a_validar)
        else:
            llaves_con_error.append(llave_a_validar)
            break

    if puedo_seguir:
        if not mensaje_pep:
            self.continuar_envio_a_siif()

        else:
            enviar_mail_de_error_a_todos_los_responsables(self, id_concepto, llaves_con_error, TIPO_DE_MENSAJE_ADVERTENCIA)
            return mensaje_de_advertencia_a_retornar(self, mensaje_pep)

    else:
        enviar_mail_de_error_a_todos_los_responsables(self, id_concepto, llaves_con_error, TIPO_DE_MENSAJE_BLOQUEO)
        raise Warning(mensaje_pep)

def ejecutar_pep_para_proceso_origen(self, codigo_identificador_documento, proceso_origen):
    _logger.info('Se realiza la Ejecucion de Fondos Presupuestales')
    print 'Se realiza la Ejecucion de Fondos Presupuestales'

    id_concepto = self.concepto_id.id

    if 'concepto_de_modificacion_id' in self:
        if self.concepto_de_modificacion_id:
            id_concepto = self.concepto_de_modificacion_id.id

    llaves_con_importe_a_validar = self.llpapg_ids
    inciso = self.inciso_siif_id
    unidad_ejecutora = self.ue_siif_id

    puedo_seguir = True
    mensaje_pep = str()
    plan_actual = obtener_plan_activo(self)

    for llave_con_importe in llaves_con_importe_a_validar:
        importe_llave = llave_con_importe.importe

        llave_a_validar = generar_llave_a_utilizar(inciso, unidad_ejecutora, llave_con_importe)
        resultado, diagnostico = plan_actual.ejecutar_fondo_presupuestal(id_concepto, llave_a_validar, importe_llave, codigo_identificador_documento, proceso_origen)

        ocurrio_un_error = resultado == plan_actual.EJECUCION_ERROR
        if ocurrio_un_error:
            raise Warning('Error al ejecutar el Fondo Presupuestal\n' + diagnostico)

def realizar_cancelacion_de_pep(self, codigo_identificador_documento, proceso_origen):
    id_concepto = self.concepto_id.id

    if 'concepto_de_modificacion_id' in self:
        if self.concepto_de_modificacion_id:
            id_concepto = self.concepto_de_modificacion_id.id

    llaves_con_importe_a_validar = self.llpapg_ids
    inciso = self.inciso_siif_id
    unidad_ejecutora = self.ue_siif_id

    plan_actual = obtener_plan_activo(self)

    for llave_con_importe in llaves_con_importe_a_validar:
        importe_llave = llave_con_importe.importe

        llave_a_validar = generar_llave_a_utilizar(inciso, unidad_ejecutora, llave_con_importe)
        resultado, diagnostico = plan_actual.cancelar_ejecucion_fondo(id_concepto, llave_a_validar, importe_llave, codigo_identificador_documento, proceso_origen)

        ocurrio_un_error = resultado == plan_actual.EJECUCION_ERROR
        if ocurrio_un_error:
            raise Warning('Error al cancelar el Fondo Presupuestal\n' + diagnostico)

#### WIZARD ####
def realizar_validacion_contra_pep_en_modificacion(self, id_concepto, inciso, unidad_ejecutora, llave_a_utilizar):
    importe_llave = llave_a_utilizar.importe
    llave_a_validar = generar_llave_a_utilizar(inciso, unidad_ejecutora, llave_a_utilizar)

    resultado_pep = valido_contra_pep(self, id_concepto, llave_a_validar, importe_llave)
    puedo_seguir = resultado_pep['puede_continuar']
    mensaje_pep = resultado_pep['mensaje']

    if puedo_seguir:
        if not mensaje_pep:
            self.continuar_envio_a_siif()

        else:
            enviar_mail_de_error_a_todos_los_responsables(self, id_concepto, [llave_a_utilizar], TIPO_DE_MENSAJE_ADVERTENCIA)
            return mensaje_de_advertencia_a_retornar(self, mensaje_pep)

    else:
        enviar_mail_de_error_a_todos_los_responsables(self, id_concepto, [llave_a_utilizar], TIPO_DE_MENSAJE_BLOQUEO)
        raise Warning(mensaje_pep)

def ejecutar_pep_para_proceso_origen_en_modificacion(self, datos_a_utilizar):
    _logger.info('Se realiza la Ejecucion de Fondos Presupuestales')
    print 'Se realiza la Ejecucion de Fondos Presupuestales'

    id_concepto = datos_a_utilizar['id_concepto']
    inciso = datos_a_utilizar['inciso']
    unidad_ejecutora = datos_a_utilizar['unidad_ejecutora']
    llave_a_utilizar = datos_a_utilizar['llave_a_utilizar']
    codigo_identificador_documento = datos_a_utilizar['codigo_identificador_documento']
    proceso_origen = datos_a_utilizar['proceso_origen']

    plan_actual = obtener_plan_activo(self)
    es_un_aumento = llave_a_utilizar.tipo == 'A'
    importe_llave = llave_a_utilizar.importe if es_un_aumento else -llave_a_utilizar.importe

    llave_a_validar = generar_llave_a_utilizar(inciso, unidad_ejecutora, llave_a_utilizar)
    resultado, diagnostico = plan_actual.ejecutar_fondo_presupuestal(id_concepto, llave_a_validar, importe_llave, codigo_identificador_documento, proceso_origen)

    ocurrio_un_error = resultado == plan_actual.EJECUCION_ERROR
    if ocurrio_un_error:
        raise Warning('Error al ejecutar el Fondo Presupuestal\n' + diagnostico)
