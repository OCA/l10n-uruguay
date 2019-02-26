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

import logging
import string
from openerp.osv import osv, fields
from suds.client import Client
from datetime import date, timedelta

_logger = logging.getLogger(__name__)

class grp_sice_historico_novedades(osv.osv):
    _name = 'grp.sice_historico_novedades'
    _order = 'id desc'
    _columns = {
        'name': fields.char('Tipo de novedad', size=50),
        'operacion': fields.char(u'Operación', size=1),
        'cod': fields.integer(u'Código'),
        'cod_str': fields.char(u'Código', size=8),
        'descripcion': fields.char(u'Descripción', size=100),
        'fecha': fields.date('Fecha de novedad'),
        'fecha_proceso': fields.datetime('Fecha de proceso'),
    }
    _defaults = {
        'fecha_proceso':fields.datetime.now,
    }
grp_sice_historico_novedades()


class grp_sice_novedades_error_log(osv.osv):
    _name = 'grp.sice_novedades_error_log'
    _order = 'id desc'
    _columns = {
        'name': fields.datetime('Fecha de proceso'),
        # 'fecha': fields.datetime('Fecha / Hora'),
        'tipo_novedad': fields.char(u'Tipo', size=30),
        'fecha_novedad': fields.date(u'Fecha de novedad', size=30),
        'operacion': fields.char(u'Operación', size=1),
        'detalle': fields.char(u'Detalle', size=1000),
        'mensaje': fields.char(u'Mensaje', size=200),
        'tipo_error': fields.selection([('W', 'Warning'), ('E', 'Error')], 'Tipo de error'),
    }
    _defaults = {
        'name':fields.datetime.now,
    }
grp_sice_novedades_error_log()


class wizard_novedades_sice(osv.osv_memory):
    """Wizard que carga las novedades de Articulos en el staging SICE"""

    _name = 'wizard.novedades.sice'
    _columns = {
        'name': fields.char('Descripcion', size=200),
    }

    # Parámetro del sistema: URL del WS de novedades de Articulos
    key_novedades = "grp.sice_novedades_wsdl"
    # url_novedades = "http://sice.compras.red.uy:8080/ws/ActualizacionCatalogoWS/ActualizacionCatalogoService.ActualizacionCatalogoServiceHttpSoap12Endpoint?wsdl"
    url_novedades = "http://www.comprasestatales.gub.uy/ws/ActualizacionCatalogoWS/ActualizacionCatalogoService.ActualizacionCatalogoServiceHttpSoap12Endpoint?wsdl"

    # Parámetro del sistema: Cantidad de días hacia atrás a solicitar las novedades
    key_dias_atras = "grp.sice_novedades_dias_atras"
    dias_atras = "3"

    # Parámetro del sistema: Cantidad de días que se mantienen los registros del proceso de novedades SICE
    key_sice_dias_log = "grp.sice_novedades_dias_log"
    val_sice_dias_log = "180"

    # Parámetro del sistema: Cantidad de días registro de errores del proceso de novedades RUPE
    key_sice_dias_error_log = "grp.sice_novedades_dias_error_log"
    val_sice_dias_error_log = "90"


    # Los objetos SOAP para la conexión
    ws_novedades = None

    def configurar_cron_novedades_sice(self, cr, uid, ids=None, context=None):
        """
        Se dan de alta la acción planificada, la URL del WS de novedades
        de Articulos y la cantidad de días atrás con que se pedirán dichas
        novedades.

        La tarea planificada se crea con las siguientes características:

            Nombre:             La identificación de la tarea
            Activo:             False (Para que el administrador la active)
            Repetir períodos:   False (Para que los atrasados no se ejecuten)
            Intervalo:          Días
            Veces de invocación: -1 (para que se ejecute siempre))
            Demás valores: default de la clase ir.cron

        La URL del WS
            A travéz de red.uy

        Días Atrás
            Se solicitan las novedades de los últimos 10 días
        """

        # La tarea planificada
        tarea = {}
        tarea['name'] = 'SICE: Recepción de Novedades'
        tarea['model'] = 'wizard.novedades.sice'
        tarea['function'] = 'recibir_novedades_sice'
        tarea['args'] = '()'
        tarea['interval_type'] = 'days'
        tarea['numbercall'] = -1
        tarea['doall'] = False
        tarea['active'] = False

        cr.execute("select id from ir_cron where name = %(name)s", {'name': tarea['name']})
        if not cr.rowcount:
            self.pool.get('ir.cron').create(cr, uid, tarea, context=context)

        # Las URLs de los WS de novedades y datos de Articulos
        sys_cfg = self.pool.get('ir.config_parameter')
        if not sys_cfg.get_param(cr, uid, self.key_novedades):
            sys_cfg.set_param(cr, uid, self.key_novedades, self.url_novedades)
        if not sys_cfg.get_param(cr, uid, self.key_dias_atras):
            sys_cfg.set_param(cr, uid, self.key_dias_atras, self.dias_atras)

        # Cantidad de dias de mantenimiento de logs
        if not sys_cfg.get_param(cr, uid, self.key_sice_dias_log):
            sys_cfg.set_param(cr, uid, self.key_sice_dias_log, self.val_sice_dias_log)

        return True


    def conectar_sice(self, cr, uid):
        """
        Establece la conexión con el WS y crea el objeto SOAP cliente
        de dicha conexión.
        """

        # Obtener las URL necesaria de los parámetros del sistema
        sys_cfg = self.pool.get('ir.config_parameter')

        wsdl_novedades = sys_cfg.get_param(cr, uid, self.key_novedades)
        if not wsdl_novedades:
            raise osv.except_osv('Error!',u'No se encuentra configurada la ruta del WSDL para consumir el servicio de Novedades SICE')

        # Establecer las conexiones
        try:
            self.ws_novedades = Client(wsdl_novedades)
            # _logger.info('self.ws_novedades: %s', self.ws_novedades)
        except:
            raise osv.except_osv('Error!', u'No se pudo conectar con sice')

        return True


    def registar_historico(self, cr, uid, datos, tabla, objeto, operacion):
        """
        Recibe:
           datos: diccionario con los datos de la novedad
           objeto: 'ARTICULO', 'FAMILIA', 'SUBFAMILIA', 'CLASE', 'SUBCLASE', 'UNIDAD MEDIDA', 'IMPUESTO'
           operacion: el codigoOperacion informado por SICE A-Alta, B-Baja, M-Modificacion
        Inserta en la tabla del modelo grp.sice_historico_novedades un registro como testigo del proceso de la novedad
        """
        sice_hist_nov = self.pool.get('grp.sice_historico_novedades')

        datos_hist = {}
        datos_hist['name'] = objeto
        datos_hist['operacion'] = operacion
        datos_hist['descripcion'] = datos['descripcion']
        datos_hist['fecha'] = tabla['fecha']

        if 'cod' in datos:
            datos_hist['cod'] = datos['cod']
            datos_hist['cod_str'] = string.replace(str(datos_hist['cod']), '.0', '')

        # Verifico que no haya sido registrado en un proceso previo la misma novedad
        rec_hists = sice_hist_nov.search(cr, uid, [('name', '=', objeto), ('operacion', '=', operacion), ('descripcion', '=', datos['descripcion']), ('fecha', '=', tabla['fecha'])], context={'active_test': False})
        if not rec_hists:
            sice_hist_nov.create(cr, uid, datos_hist)
        return

    def log_error(self, cr, uid, msg, tabla, datos, tipo_error):
        """
        Deja registro de inconsistencias
        """
        nov_obj = self.pool.get('grp.sice_novedades_error_log')
        nov_dat = {}
        nov_dat['tipo_novedad'] = tabla['nombre']
        nov_dat['fecha_novedad'] = tabla['fecha']
        nov_dat['operacion'] = tabla['operacion']
        nov_dat['mensaje'] = msg
        nov_dat['detalle'] = datos
        nov_dat['tipo_error'] = tipo_error

        nov_obj.create(cr, uid, nov_dat)
        return


    def purge_error_log(self, cr, uid):
        """
        Elimina del registro del log de errores aquellos registros mas viejos que la cantidad de dias definido en parámetro del sistema
        """

        # La cantidad de días atrás a mantener el registro de log
        sys_cfg = self.pool.get('ir.config_parameter')
        dias_atras = sys_cfg.get_param(cr, uid, self.key_sice_dias_error_log)

        if not dias_atras:
            raise osv.except_osv('Error!',u'No se encuentra configurada la cantidad de días atrás para mantenimiento de logs de errores de novedades de artículos SICE')
        fecha_min = date.today() - timedelta(days=int(dias_atras))

        # _logger.info('Fecha mínima para registros de error_log: %s', fecha_min.strftime("%Y-%m-%d"))
        cr.execute("DELETE FROM grp_sice_novedades_error_log WHERE date_trunc('day',fecha) < %s", (fecha_min,))
        return


    def purge_proc_log(self, cr, uid):
        """
        Elimina del registro del proceso de novedades aquellos registros mas viejos que la cantidad de dias definido en parámetro del sistema
        """

        # La cantidad de días atrás a mantener el registro de log
        sys_cfg = self.pool.get('ir.config_parameter')
        dias_atras = sys_cfg.get_param(cr, uid, self.key_sice_dias_log)

        if not dias_atras:
            raise osv.except_osv('Error!',u'No se encuentra configurada la cantidad de días atrás para mantenimiento de logs de novedades de artículos SICE')
        fecha_min = date.today() - timedelta(days=int(dias_atras))

        # _logger.info('Fecha minima para registros de proc log: %s', fecha_min.strftime("%Y-%m-%d"))
        cr.execute("DELETE FROM sice_historico_novedades WHERE date_trunc('day',fecha_proceso) < %s", (fecha_min,))
        return


    # -
    # - Proceso de novedad de tipo: familia
    # -
    def procesar_familia(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de familia
        """
        fam_obj = self.pool.get('grp.sice_familia')
        fam_dat = {}

        # Busco si ya existe la familia
        familias = fam_obj.search(cr, uid, [("cod", "=", datos['cod']), ], context={'active_test': False})

        if 'fecha_baja' in datos:
            if familias:
                # Verifico si la familia ya esta dada de baja
                if fam_obj.browse(cr, uid, familias[0]).active:
                    fam_dat['fecha_baja'] = datos['fecha_baja']
                    fam_dat['active'] = False
                    if 'motivo_baja' in datos:
                        fam_dat['motivo_baja'] = datos['motivo_baja']

                    fam_obj.write(cr, uid, familias[0], fam_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'FAMILIA', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not familias:
                    fam_dat['cod'] = datos['cod']
                    fam_dat['descripcion'] = datos['descripcion']
                    fam_dat['comprable'] = datos['comprable']

                    fam_obj.create(cr, uid, fam_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'FAMILIA', 'A')

            elif tabla['operacion'] == 'M':
                if familias:
                    fam_dat['descripcion'] = datos['descripcion']
                    fam_dat['comprable'] = datos['comprable']
                    fam_obj.write(cr, uid, familias[0], fam_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'FAMILIA', 'M')
                else:
                    self.log_error(cr, uid, u"Se intentó modificar una familia no existente", tabla, datos, 'W')
        return

    # -
    # - Proceso de novedad de tipo: subflia
    # -
    def procesar_subflia(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de subfamilia
        """
        fam_obj = self.pool.get('grp.sice_familia')
        subf_obj = self.pool.get('grp.sice_subflia')
        subf_dat = {}

        # Existencia de familia
        familias = fam_obj.search(cr, uid, [("cod", "=", datos['fami_cod']), ], context={'active_test': False})
        if not familias:
            self.log_error(cr, uid, u"Se intentó procesar una subfamilia para una familia no existente", tabla, datos, 'W')
            return

        # Existencia de subfamilia
        subflias = sub_obj.search(cr, uid, [("cod", "=", datos['cod']), ("fami_cod", "=", datos['fami_cod']), ],
                                  context={'active_test': False})

        if 'fecha_baja' in datos:
            if subflias:
                # Verifico si la subfamilia ya esta dada de baja
                if subf_obj.browse(cr, uid, subflias[0]).active:
                    subf_dat['fecha_baja'] = datos['fecha_baja']
                    subf_dat['active'] = False
                    if 'motivo_baja' in datos:
                        subf_dat['motivo_baja'] = datos['motivo_baja']

                    subf_obj.write(cr, uid, subflias[0], subf_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'SUBFLIA', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not subflias:
                    subf_dat['cod'] = datos['cod']
                    subf_dat['fami_id'] = familias[0]
                    subf_dat['descripcion'] = datos['descripcion']

                    subf_obj.create(cr, uid, subf_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'SUBFLIA', 'A')

            elif tabla['operacion'] == 'M':
                if subflias:
                    subf_dat['descripcion'] = datos['descripcion']

                    subf_obj.write(cr, uid, subflias[0], subf_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'SUBFLIA', 'M')
                else:
                    self.log_error(cr, uid, u"Se intentó modificar una subfamilia no existente", tabla, datos, 'W')
        return

    # -
    # - Proceso de novedad de tipo: clase
    # -
    def procesar_clase(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de clase
        """
        fam_obj = self.pool.get('grp.sice_familia')
        subf_obj = self.pool.get('grp.sice_subflia')
        cla_obj = self.pool.get('grp.sice_clase')
        cla_dat = {}

        # Existencia de familia
        familias = fam_obj.search(cr, uid, [("cod", "=", datos['fami_cod']), ], context={'active_test': False})
        if not familias:
            self.log_error(cr, uid, u"Se intentó procesar una clase para una familia no existente", tabla, datos, 'W')
            return

        # Existencia de subfamilia
        subflias = subf_obj.search(cr, uid, [("cod", "=", datos['subf_cod']), ("fami_cod", "=", datos['fami_cod']), ],
                                   context={'active_test': False})
        if not subflias:
            self.log_error(cr, uid, u"Se intentó procesar una clase para una subfamilia no existente", tabla, datos, 'W')
            return

        # Existencia de clase
        clases = cla_obj.search(cr, uid, [("cod", "=", datos['cod']), ("subf_cod", "=", datos['subf_cod']),
                                          ("fami_cod", "=", datos['fami_cod']), ], context={'active_test': False})

        if 'fecha_baja' in datos:
            if clases:
                # Verifico si la clase ya esta dada de baja
                if cla_obj.browse(cr, uid, clases[0]).active:
                    cla_dat['fecha_baja'] = datos['fecha_baja']
                    cla_dat['active'] = False
                    if 'motivo_baja' in datos:
                        cla_dat['motivo_baja'] = datos['motivo_baja']

                    cla_obj.write(cr, uid, clases[0], cla_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'CLASE', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not clases:
                    cla_dat['cod'] = datos['cod']
                    cla_dat['fami_id'] = familias[0]
                    cla_dat['subf_id'] = subflias[0]
                    cla_dat['descripcion'] = datos['descripcion']

                    cla_obj.create(cr, uid, cla_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'CLASE', 'A')

            elif tabla['operacion'] == 'M':
                if clases:
                    cla_dat['descripcion'] = datos['descripcion']

                    cla_obj.write(cr, uid, clases[0], cla_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'CLASE', 'M')
                else:
                    self.log_error(cr, uid, u"Se intentó modificar una clase no existente", tabla, datos, 'W')
        return

    # -
    # - Proceso de novedad de tipo: subclase
    # -
    def procesar_subclase(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de subclase
        """
        fam_obj = self.pool.get('grp.sice_familia')
        subf_obj = self.pool.get('grp.sice_subflia')
        cla_obj = self.pool.get('grp.sice_clase')
        subc_obj = self.pool.get('grp.sice_subclase')
        subc_dat = {}

        # Existencia de familia
        familias = fam_obj.search(cr, uid, [("cod", "=", datos['fami_cod']), ], context={'active_test': False})
        if not familias:
            self.log_error(cr, uid, u"Se intentó procesar una subclase para una familia no existente", tabla, datos, 'W')
            return

        # Existencia de subfamilia
        subflias = subf_obj.search(cr, uid, [("cod", "=", datos['subf_cod']), ("fami_cod", "=", datos['fami_cod']), ],
                                   context={'active_test': False})
        if not subflias:
            self.log_error(cr, uid, u"Se intentó procesar una subclase para una subfamilia no existente", tabla, datos, 'W')
            return

        # Existencia de clase
        clases = cla_obj.search(cr, uid, [("cod", "=", datos['clas_cod']), ("subf_cod", "=", datos['subf_cod']),
                                          ("fami_cod", "=", datos['fami_cod']), ], context={'active_test': False})
        if not clases:
            self.log_error(cr, uid, u"Se intentó procesar una subclase para una clase no existente", tabla, datos, 'W')
            return

        # Existencia de subclase
        subclases = subc_obj.search(cr, uid, [("cod", "=", datos['cod']), ("clas_cod", "=", datos['clas_cod']),
                                              ("subf_cod", "=", datos['subf_cod']),
                                              ("fami_cod", "=", datos['fami_cod']), ], context={'active_test': False})

        if 'fecha_baja' in datos:
            if subclases:
                # Verifico si la subclase ya esta dada de baja
                if subc_obj.browse(cr, uid, subclases[0]).active:
                    subc_dat['fecha_baja'] = datos['fecha_baja']
                    subc_dat['active'] = False
                    if 'motivo_baja' in datos:
                        subc_dat['motivo_baja'] = datos['motivo_baja']

                    subc_obj.write(cr, uid, subclases[0], subc_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'SUBCLASE', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not subclases:
                    subc_dat['cod'] = datos['cod']
                    subc_dat['fami_id'] = familias[0]
                    subc_dat['subf_id'] = subflias[0]
                    subc_dat['clas_id'] = clases[0]
                    subc_dat['descripcion'] = datos['descripcion']

                    subc_obj.create(cr, uid, subc_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'SUBCLASE', 'A')

            elif tabla['operacion'] == 'M':
                if subclases:
                    subc_dat['descripcion'] = datos['descripcion']

                    subc_obj.write(cr, uid, subclases[0], subc_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'SUBCLASE', 'M')
                else:
                    self.log_error(cr, uid, u"Se intentó modificar una subclase no existente", tabla, datos, 'W')
        return

    # -
    # - Proceso de novedad de tipo: unidad_med
    # -
    def procesar_unidad_med(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de unidad de medida
        """
        un_med_obj = self.pool.get('grp.sice_unidades_med')
        un_med_dat = {}

        # Busco si ya existe la unidad de medida
        un_meds = un_med_obj.search(cr, uid, [("cod", "=", datos['cod']), ], context={'active_test': False})

        if 'fecha_baja' in datos:
            if un_meds:
                # Verifico si la unidad de medida ya esta dada de baja
                if un_med_obj.browse(cr, uid, un_meds[0]).active:
                    un_med_dat['fecha_baja'] = datos['fecha_baja']
                    un_med_dat['active'] = False
                    if 'motivo_baja' in datos:
                        un_med_dat['motivo_baja'] = datos['motivo_baja']

                    un_med_obj.write(cr, uid, un_meds[0], un_med_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'UNIDAD_MED', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not un_meds:
                    un_med_dat['cod'] = datos['cod']
                    un_med_dat['descripcion'] = datos['descripcion']
                    un_med_dat['tipo'] = datos['tipo']

                    un_med_obj.create(cr, uid, un_med_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'UNIDAD_MED', 'A')

            elif tabla['operacion'] == 'M':
                if un_meds:
                    un_med_dat['descripcion'] = datos['descripcion']
                    un_med_dat['tipo'] = datos['tipo']

                    un_med_obj.write(cr, uid, un_meds[0], un_med_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'UNIDAD_MED', 'M')
                else:
                    self.log_error(cr, uid, u"Se intentó modificar una unidad de medida no existente", tabla, datos, 'W')
        return

    # -
    # - Proceso de novedad de tipo: impuesto
    # -
    def procesar_impuesto(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de impuesto
        """
        imp_obj = self.pool.get('grp.sice_impuesto')
        imp_dat = {}

        # Busco si ya existe el impuesto
        impuestos = imp_obj.search(cr, uid, [("cod", "=", datos['cod']), ], context={'active_test': False})

        if 'fecha_baja' in datos:
            if impuestos:
                # Verifico si el impuesto ya está dado de baja
                if imp_obj.browse(cr, uid, impuestos[0]).active:
                    imp_dat['fecha_baja'] = datos['fecha_baja']
                    imp_dat['active'] = False
                    if 'motivo_baja' in datos:
                        imp_dat['motivo_baja'] = datos['motivo_baja']

                    imp_obj.write(cr, uid, impuestos[0], imp_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'IMPUESTO', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not impuestos:
                    imp_dat['cod'] = datos['cod']
                    imp_dat['descripcion'] = datos['descripcion']

                    imp_obj.create(cr, uid, imp_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'IMPUESTO', 'A')

            elif tabla['operacion'] == 'M':
                if impuestos:
                    imp_dat['descripcion'] = datos['descripcion']

                    imp_obj.write(cr, uid, impuestos[0], imp_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'IMPUESTO', 'M')
                else:
                    self.log_error(cr, uid, u"Se intentó modificar un impuesto no existente", tabla, datos, 'W')
        return

    # -
    # - Proceso de novedad de tipo: marca
    # -
    def procesar_marca(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de Marca
        """
        marc_obj = self.pool.get('grp.sice_marca')
        marc_dat = {}

        # Busco si ya existe la marca
        marcas = marc_obj.search(cr, uid, [("cod", "=", datos['cod']), ], context={'active_test': False})

        if 'fecha_baja' in datos:
            if marcas:
                # Verifico si la marca ya está dada de baja
                if marc_obj.browse(cr, uid, marcas[0]).active:
                    marc_dat['fecha_baja'] = datos['fecha_baja']
                    marc_dat['active'] = False
                    if 'motivo_baja' in datos:
                        marc_dat['motivo_baja'] = datos['motivo_baja']

                    marc_obj.write(cr, uid, marcas[0], marc_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'MARCA', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not marcas:
                    marc_dat['cod'] = datos['cod']
                    marc_dat['descripcion'] = datos['descripcion']

                    marc_obj.create(cr, uid, marc_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'MARCA', 'A')

            elif tabla['operacion'] == 'M':
                if marcas:
                    marc_dat['descripcion'] = datos['descripcion']

                    marc_obj.write(cr, uid, marcas[0], marc_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'MARCA', 'M')
                else:
                    self.log_error(cr, uid, u"Se intentó modificar una marca no existente", tabla, datos, 'W')
        return

    # -
    # - Proceso de novedad de tipo: medida
    # -
    def procesar_medida(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de Medida
        """
        med_obj = self.pool.get('grp.sice_medida')
        med_dat = {}

        # Busco si ya existe la medida
        medidas = med_obj.search(cr, uid, [("cod", "=", datos['cod']), ], context={'active_test': False})

        if 'fecha_baja' in datos:
            if medidas:
                # Verifico si la medida ya está dada de baja
                if med_obj.browse(cr, uid, medidas[0]).active:
                    med_dat['fecha_baja'] = datos['fecha_baja']
                    med_dat['active'] = False
                    if 'motivo_baja' in datos:
                        med_dat['motivo_baja'] = datos['motivo_baja']

                    med_obj.write(cr, uid, medidas[0], med_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'MEDIDA', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not medidas:
                    med_dat['cod'] = datos['cod']
                    med_dat['descripcion'] = datos['descripcion']

                    med_obj.create(cr, uid, med_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'MEDIDA', 'A')

            elif tabla['operacion'] == 'M':
                if medidas:
                    med_dat['descripcion'] = datos['descripcion']

                    med_obj.write(cr, uid, medidas[0], med_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'MEDIDA', 'M')
                else:
                    self.log_error(cr, uid, u"Se intentó modificar una medida no existente", tabla, datos, 'W')
        return

    # -
    # - Proceso de novedad de tipo: objetodelgasto
    # -
    def procesar_odg(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de ODG
        """
        odg_obj = self.pool.get('grp.sice_odg')
        odg_dat = {}

        # Busco si ya existe el ODG
        odgs = odg_obj.search(cr, uid, [("odg", "=", datos['odg']), ], context={'active_test': False})

        if 'fecha_baja' in datos:
            if odgs:
                # Verifico si el ODG ya está dado de baja
                if odg_obj.browse(cr, uid, odgs[0]).active:
                    odg_dat['fecha_baja'] = datos['fecha_baja']
                    odg_dat['active'] = False
                    if 'motivo_baja' in datos:
                        odg_dat['motivo_baja'] = datos['motivo_baja']

                    odg_obj.write(cr, uid, odgs[0], odg_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ODG', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not odgs:
                    odg_dat['odg'] = datos['odg']
                    odg_dat['descripcion'] = datos['descripcion']

                    odg_obj.create(cr, uid, odg_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ODG', 'A')

            elif tabla['operacion'] == 'M':
                if odgs:
                    odg_dat['descripcion'] = datos['descripcion']
                    odg_obj.write(cr, uid, odgs[0], odg_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ODG', 'M')
                else:
                    self.log_error(cr, uid, u"Se intentó modificar un ODG no existente", tabla, datos, 'W')
        return

    # -
    # - Proceso de novedad de tipo: presentacion
    # -
    def procesar_presentacion(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de Presentacion
        """
        pres_obj = self.pool.get('grp.sice_presentacion')
        umed_obj = self.pool.get('grp.sice_unidades_med')
        pres_dat = {}

        # _logger.info("NOVEDAD PRESENTACION: %s",datos)

        # Existencia de la Unidad de medida
        un_meds = umed_obj.search(cr, uid, [("cod", "=", datos['unme_cod']), ], context={'active_test': False})
        if not un_meds:
            self.log_error(cr, uid, u"Se intentó procesar una presentación con una unidad de medida no existente", tabla, datos, 'W')
            return

        # Busco si ya existe la Presentación
        press = pres_obj.search(cr, uid, [("cod", "=", datos['cod']), ], context={'active_test': False})

        if 'fecha_baja' in datos:
            if press:
                # Verifico si la presentacion ya está dado de baja
                if pres_obj.browse(cr, uid, press[0]).active:
                    pres_dat['fecha_baja'] = datos['fecha_baja']
                    pres_dat['active'] = False
                    if 'motivo_baja' in datos:
                        pres_dat['motivo_baja'] = datos['motivo_baja']

                        pres_obj.write(cr, uid, press[0], pres_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'PRESENTACION', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not press:
                    pres_dat['cod'] = datos['cod']
                    pres_dat['descripcion'] = datos['descripcion']
                    pres_dat['unme_id'] = un_meds[0]

                    pres_obj.create(cr, uid, pres_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'PRESENTACION', 'A')

            elif tabla['operacion'] == 'M':
                if press:
                    pres_dat['descripcion'] = datos['descripcion']
                    pres_obj.write(cr, uid, press[0], pres_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'PRESENTACION', 'M')
                else:
                    self.log_error(cr, uid, u"Se intentó modificar una PRESENTACION no existente", tabla, datos, 'W')
        return

    # -
    # - Proceso de novedad de tipo: familia
    # -
    def procesar_color(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de color
        """
        col_obj = self.pool.get('grp.sice_color')
        prod_prod_obj = self.pool.get('product.product')
        col_dat = {}

        # Busco si ya existe el color
        colores = col_obj.search(cr, uid, [("cod", "=", datos['cod']), ], context={'active_test': False})

        if 'fecha_baja' in datos:
            if colores:
                # Verifico si el color ya esta dado de baja
                if col_obj.browse(cr, uid, colores[0]).active:
                    col_dat['fecha_baja'] = datos['fecha_baja']
                    col_dat['active'] = False
                    if 'motivo_baja' in datos:
                        col_dat['motivo_baja'] = datos['motivo_baja']

                    prod_ids = prod_prod_obj.search(cr, uid, [('sice_color_id', '=', colores[0])])
                    if prod_ids:
                        prod_prod_obj.write(cr, uid, prod_ids, {'active': False})

                    col_obj.write(cr, uid, colores[0], col_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'COLOR', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not colores:
                    col_dat['cod'] = datos['cod']
                    col_dat['descripcion'] = datos['descripcion']

                    col_obj.create(cr, uid, col_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'COLOR', 'A')

            elif tabla['operacion'] == 'M':
                if colores:
                    col_dat['descripcion'] = datos['descripcion']
                    col_obj.write(cr, uid, colores[0], col_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'COLOR', 'M')
                else:
                    self.log_error(cr, uid, u"Se intentó modificar un color no existente", tabla, datos, 'W')
        return

    # -
    # - Proceso de novedad de tipo: propiedad
    # -
    def procesar_propiedad(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de Propiedad
        """
        prop_obj = self.pool.get('grp.sice_propiedad')
        umed_obj = self.pool.get('grp.sice_unidades_med')
        prod_prod_obj = self.pool.get('product.product')
        prop_dat = {}

        # Existencia de la Unidad de medida
        un_meds = umed_obj.search(cr, uid, [("cod", "=", datos['unme_cod']), ], context={'active_test': False})
        if not un_meds:
            self.log_error(cr, uid, u"Se intentó procesar una variante con una unidad de medida no existente", tabla, datos, 'W')
            return

        # Busco la propiedad (variante)
        propiedades = prop_obj.search(cr, uid, [("cod", "=", datos['cod']), ], context={'active_test': False})

        if 'fecha_baja' in datos:
            if propiedades:
                # Verifico si la propiedad ya está dada de baja
                if prop_obj.browse(cr, uid, propiedades[0]).active:
                    prop_dat['fecha_baja'] = datos['fecha_baja']
                    prop_dat['active'] = False
                    if 'motivo_baja' in datos:
                        prop_dat['motivo_baja'] = datos['motivo_baja']

                    prod_ids = prod_prod_obj.search(cr, uid, [('attribute_id.sice_propiedad_id', '=', propiedades[0])])
                    if prod_ids:
                        prod_prod_obj.write(cr, uid, prod_ids, {'active': False})

                    prop_obj.write(cr, uid, propiedades[0], prop_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'VARIANTE', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not propiedades:
                    prop_dat['cod'] = datos['cod']
                    prop_dat['descripcion'] = datos['descripcion']
                    prop_dat['unme_id'] = un_meds[0]

                    propiedad_id = prop_obj.create(cr, uid, prop_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'VARIANTE', 'A')

                    # Se da de alta una nueva dimension SICE en el catalogo de atributos de productos
                    prod_attr_obj = self.pool.get('product.attribute')
                    prod_attr_dat = {}
                    prod_attr_dat['sice_propiedad_id'] = propiedad_id
                    prod_attr_dat['name'] = 'VARIANTE: ' + datos['descripcion']
                    prod_attr_dat['dimension_sice'] = True
                    prod_attr_obj.create(cr, uid, prod_attr_dat)

            elif tabla['operacion'] == 'M':
                if propiedades:
                    prop_dat['descripcion'] = datos['descripcion']
                    prop_dat['unme_id'] = un_meds[0]

                    prop_obj.write(cr, uid, propiedades[0], prop_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'VARIANTE', 'M')
                else:
                    self.log_error(cr, uid, u"Se intentó modificar una variante no existente", tabla, datos, 'W')
        return

    # -
    # - Proceso de novedad de tipo: prop_unidad_med  (relacion variante - unidad de medida)
    # -
    def procesar_prop_unidades_med(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de Variante - Unidad de Medida
        """
        umed_obj = self.pool.get('grp.sice_unidades_med')
        prop_obj = self.pool.get('grp.sice_propiedad')
        prop_dat = {}

        # Existencia de la propiedad
        propiedades = prop_obj.search(cr, uid, [("cod", "=", datos['prop_cod']), ], context={'active_test': False})
        if not propiedades:
            self.log_error(cr, uid, u"Se intentó agregar una relacion variante - unidad de medida para una variante no existente",
                tabla, datos, 'W')
            return

        # Existencia de la unidad de medida
        un_meds = umed_obj.search(cr, uid, [("cod", "=", datos['unme_cod']), ], context={'active_test': False})
        if not un_meds:
            self.log_error(cr, uid, u"Se intentó agregar una relacion variante - unidad de medida para una unidad de medida no existente",
                tabla, datos, 'W')
            return

        # Existencia de la relacion propiedad - unidad de medida
        prop_un_meds = prop_obj.search(cr, uid, [("cod", "=", datos['prop_cod']), ("prop_unme_ids", "in", un_meds[0]),], context={'active_test': False})

        datos['descripcion'] = prop_obj.browse(cr, uid, propiedades[0]).descripcion + ' (' + string.replace(
            str(datos['prop_cod']), '.0', '') + ') ' + ' - ' + umed_obj.browse(cr, uid, un_meds[0]).descripcion + ' (' + string.replace(str(datos['unme_cod']), '.0', '') + ')'

        if 'fecha_baja' in datos:
            prop_dat['prop_unme_ids'] = [(3, un_meds[0])]
            prop_obj.write(cr, uid, propiedades[0], prop_dat)
            self.registar_historico(cr, uid, datos, tabla, 'VARIANTE - UNIDAD DE MEDIDA', 'B')

        else:
            if (tabla['operacion'] == 'A' or tabla['operacion'] == 'M'):
                if not prop_un_meds:
                    prop_dat['prop_unme_ids'] = [(4, un_meds[0])]
                    prop_obj.write(cr, uid, propiedades[0], prop_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'VARIANTE - UNIDAD DE MEDIDA', 'A')
        return

    # -
    # - Proceso de novedad de tipo: art_color
    # -
    def procesar_art_color(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de la relacion entre "Articulo" y "Color"
        """
        art_obj = self.pool.get('grp.sice_art_serv_obra')
        col_obj = self.pool.get('grp.sice_color')
        prod_prod_obj = self.pool.get('product.product')
        art_color_dat = {}

        # Existencia del articulo
        articulos = art_obj.search(cr, uid, [("cod", "=", datos['arse_cod']), ], context={'active_test': False})
        if not articulos:
            self.log_error(cr, uid, u"Se intentó procesar una relacion artículo - color para un artículo no existente", tabla, datos, 'W')
            return

        # Existencia del color
        colores = col_obj.search(cr, uid, [("cod", "=", datos['colo_cod']), ], context={'active_test': False})
        if not colores:
            self.log_error(cr, uid, u"Se intentó procesar una relacion artículo - color para un color no existente", tabla, datos, 'W')
            return

        # Existencia de la relacion articulo - color
        art_colores = art_obj.search(cr, uid, [("cod", "=", datos['arse_cod']), ("art_color_ids", "in", colores[0])], context={'active_test': False})

        datos['descripcion'] = art_obj.browse(cr, uid, articulos[0]).descripcion + ' (' + string.replace(str(datos['arse_cod']), '.0', '') + ') ' + ' - ' + col_obj.browse(cr, uid, colores[0]).descripcion + ' (' + string.replace(str(datos['colo_cod']), '.0', '') + ')'

        if 'fecha_baja' in datos:
            if art_colores:
                art_color_dat['art_color_ids'] = [(3, colores[0])]
                prod_id = prod_prod_obj.search(cr, uid, [('product_tmpl_id.grp_sice_cod', '=', datos['arse_cod']), ('sice_color_id', '=', colores[0])])
                if prod_id:
                    prod_prod_obj.write(cr, uid, prod_id, {'active': False})
                art_obj.write(cr, uid, articulos[0], art_color_dat)
                self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - COLOR', 'B')
        else:
            if (tabla['operacion'] == 'A' or tabla['operacion'] == 'M'):
                if not art_colores:
                    art_color_dat['art_color_ids'] = [(4, colores[0])]
                    art_obj.write(cr, uid, articulos[0], art_color_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - COLOR', 'A')
        return

    # -
    # - Proceso de novedad de tipo: art_impuesto
    # -
    def procesar_art_impuesto(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de la relacion entre "Articulo" e "Impuesto"
        """
        art_obj = self.pool.get('grp.sice_art_serv_obra')
        imp_obj = self.pool.get('grp.sice_impuesto')
        art_impuesto_dat = {}

        # Existencia del articulo
        articulos = art_obj.search(cr, uid, [("cod", "=", datos['arse_cod']), ], context={'active_test': False})
        if not articulos:
            self.log_error(cr, uid, u"Se intentó procesar una relacion artículo - impuesto para un artículo no existente",
                tabla, datos, 'W')
            return

        # Existencia del impuesto
        impuestos = imp_obj.search(cr, uid, [("cod", "=", datos['imp_cod']), ], context={'active_test': False})
        if not impuestos:
            self.log_error(cr, uid, u"Se intentó procesar una relacion artículo - impuesto para un impuesto no existente",
                tabla, datos, 'W')
            return

        # Existencia de la relacion articulo - impuesto
        art_impuestos = art_obj.search(cr, uid,
                                      [("cod", "=", datos['arse_cod']), ("art_impuesto_ids", "in", impuestos[0])],
                                      context={'active_test': False})

        datos['descripcion'] = art_obj.browse(cr, uid, articulos[0]).descripcion + ' (' + string.replace(str(datos['arse_cod']), '.0', '') + ') ' + ' - ' + imp_obj.browse(cr, uid, impuestos[0]).descripcion + ' (' + string.replace(str(datos['imp_cod']), '.0', '') + ')'

        if 'fecha_baja' in datos:
            if art_impuestos:
                art_impuesto_dat['art_impuesto_ids'] = [(3, impuestos[0])]
                art_obj.write(cr, uid, articulos[0], art_impuesto_dat)
                self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - IMPUESTO', 'B')
        else:
            if (tabla['operacion'] == 'A' or tabla['operacion'] == 'M'):
                if not art_impuestos:
                    art_impuesto_dat['art_impuesto_ids'] = [(4, impuestos[0])]
                    art_obj.write(cr, uid, articulos[0], art_impuesto_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - IMPUESTO', 'A')
        return

    # -
    # - Proceso de novedad de tipo: art_atributo
    # -
    def procesar_art_atributo(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de la relacion entre "Articulo" y "Atributo"
        """
        art_obj = self.pool.get('grp.sice_art_serv_obra')
        prop_obj = self.pool.get('grp.sice_propiedad')
        unme_obj = self.pool.get('grp.sice_unidades_med')
        art_atr_obj = self.pool.get('grp.sice_art_atributo')

        # Existencia del articulo
        articulos = art_obj.search(cr, uid, [("cod", "=", datos['arse_cod']), ], context={'active_test': False})
        if not articulos:
            self.log_error(cr, uid, u"Se intentó procesar un atributo para un artículo no existente", tabla, datos, 'W')
            return

        # Existencia de la propiedad
        propiedades = prop_obj.search(cr, uid, [("cod", "=", datos['prop_cod']), ], context={'active_test': False})
        if not propiedades:
            self.log_error(cr, uid, u"Se intentó procesar un atributo para una propiedad no existente", tabla, datos, 'W')
            return

        # Existencia de la Unidad de Medida de la Propiedad
        un_meds = unme_obj.search(cr, uid, [("cod", "=", datos['prop_unme_cod']), ], context={'active_test': False})
        if not un_meds:
            self.log_error(cr, uid, u"Se intentó procesar un atributo para una unidad de medidad (de propiedad) no existente",
                tabla, datos, 'W')
            return

        # Busco el atributo (si existe)
        art_atributos = art_atr_obj.search(cr, uid,
                                           [("arse_cod", "=", datos['arse_cod']), ("prop_cod", "=", datos['prop_cod']),
                                            ("prop_unme_cod", "=", datos['prop_unme_cod'])],
                                           context={'active_test': False})

        # Diccionario con datos de la novedad
        art_atributo_dat = {}

        # Cargo descripcion a desplegar en el historico
        datos['descripcion'] = art_obj.browse(cr, uid, articulos[0]).descripcion + ' (' + string.replace(
            str(datos['arse_cod']), '.0', '') + ') ' + ' - ' + \
                               prop_obj.browse(cr, uid, propiedades[0]).descripcion + ' (' + string.replace(
            str(datos['prop_cod']), '.0', '') + ')' + ' - ' + \
                               unme_obj.browse(cr, uid, un_meds[0]).descripcion + ' (' + string.replace(
            str(datos['prop_unme_cod']), '.0', '') + ')'

        if 'fecha_baja' in datos:
            if art_atributos:
                # Verifico que no esté dado de baja
                art_atributo = art_atr_obj.browse(cr, uid, art_atributos[0])
                if not art_atributo.fecha_baja or art_atributo.active:

                    art_atributo_dat['fecha_baja'] = datos['fecha_baja']
                    art_atributo_dat['active'] = False

                    if 'motivo_baja' in datos:
                        art_atributo_dat['motivo_baja'] = datos['motivo_baja']

                    art_atr_obj.write(cr, uid, art_atributos[0], art_atributo_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - ATRIBUTO', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not art_atributos:
                    art_atributo_dat['articulo_id'] = articulos[0]
                    art_atributo_dat['prop_id'] = propiedades[0]
                    art_atributo_dat['prop_unme_id'] = un_meds[0]

                    if 'patron' in datos:
                        art_atributo_dat['patron'] = datos['patron']

                    art_atr_obj.create(cr, uid, art_atributo_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - ATRIBUTO', 'A')

            elif tabla['operacion'] == 'M':
                if art_atributos:
                    # El atributo existe, solo lo actualizo si agrega "patron" (que es lo unico que podria actualizar)
                    if 'patron' in datos:
                        art_atributo_dat['patron'] = datos['patron']
                        art_atr_obj.write(cr, uid, art_atributos[0], art_atributo_dat)
                        self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - ATRIBUTO', 'M')
                else:
                    # El atributo no existe, entonces lo creo
                    art_atributo_dat['articulo_id'] = articulos[0]
                    art_atributo_dat['prop_id'] = propiedades[0]
                    art_atributo_dat['prop_unme_id'] = un_meds[0]
                    if 'patron' in datos:
                        art_atributo_dat['patron'] = datos['patron']

                    art_atr_obj.create(cr, uid, art_atributo_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - ATRIBUTO', 'A')
        return

    # -
    # - Proceso de novedad de tipo: art_unidad_med
    # -
    def procesar_art_unidad_med(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de la relacion entre "Articulo" y "Unidad de Medida" (m2m)
        """
        art_obj = self.pool.get('grp.sice_art_serv_obra')
        unme_obj = self.pool.get('grp.sice_unidades_med')

        # Existencia del articulo
        articulos = art_obj.search(cr, uid, [("cod", "=", datos['arse_cod']), ], context={'active_test': False})
        if not articulos:
            self.log_error(cr, uid, u"Se intentó procesar una unidad de medida para un artículo no existente",
                tabla, datos, 'W')
            return

        # Existencia de la unidad de medida
        un_meds = unme_obj.search(cr, uid, [("cod", "=", datos['unme_cod']), ], context={'active_test': False})
        if not un_meds:
            self.log_error(cr, uid, u"Se intentó procesar una unidad de medida para un artículo y la unidad de medida no existe",
                tabla, datos, 'W')
            return

        # Existencia de la relacion Articulo - Unidad de Medida
        art_unidad_meds = art_obj.search(cr, uid,
                                        [("cod", "=", datos['arse_cod']), ("unidades_med_ids", "in", un_meds[0])],
                                        context={'active_test': False})

        datos['descripcion'] = art_obj.browse(cr, uid, articulos[0]).descripcion + ' (' + string.replace(
            str(datos['arse_cod']), '.0', '') + ') ' + ' - ' + unme_obj.browse(cr, uid,
                                                                               un_meds[0]).descripcion + ' (' + string.replace(
            str(datos['unme_cod']), '.0', '') + ')'

        art_unidad_med_dat = {}

        if 'fecha_baja' in datos:
            if art_unidad_meds:
                art_unidad_med_dat['unidades_med_ids'] = [(3, un_meds[0])]
                art_obj.write(cr, uid, articulos[0], art_unidad_med_dat)
                self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - UNIDAD de MEDIDA', 'B')
        else:
            if (tabla['operacion'] == 'A' or tabla['operacion'] == 'M'):
                if not art_unidad_meds:
                    art_unidad_med_dat['unidades_med_ids'] = [(4, un_meds[0])]
                    art_obj.write(cr, uid, articulos[0], art_unidad_med_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - UNIDAD de MEDIDA', 'A')
        return

    # -
    # - Proceso de novedad de tipo: med_variante
    # -
    def procesar_med_variante(self, cr, uid, tabla, datos):
        """
        Procesa la novedad medidas de variante del articulo
        """
        art_obj = self.pool.get('grp.sice_art_serv_obra')
        med_obj = self.pool.get('grp.sice_medida')
        pre_obj = self.pool.get('grp.sice_presentacion')
        art_med_var_obj = self.pool.get('grp.sice_med_variante')
        prod_prod_obj = self.pool.get('product.product')

        # Existencia del articulo
        articulos = art_obj.search(cr, uid, [("cod", "=", datos['arse_cod']), ], context={'active_test': False})
        if not articulos:
            self.log_error(cr, uid, u"Se intentó procesar una medida de variante de artículo para un artículo no existente",
                tabla, datos, 'W')
            return

        # Existencia de la unidad de medida de la variante
        un_med_variantes = med_obj.search(cr, uid, [("cod", "=", datos['med_cod_variante']), ],
                                             context={'active_test': False})
        if not un_med_variantes:
            self.log_error(cr, uid, u"Se intentó procesar una medida de variante de artículo para una unidad de medida (de variante) no existente",
                tabla, datos, 'W')
            return

        # Existencia de la unidad de medida de la presentacion
        un_med_pres = med_obj.search(cr, uid, [("cod", "=", datos['med_cod_pres']), ], context={'active_test': False})
        if not un_med_pres:
            self.log_error(cr, uid, u"Se intentó procesar una medida de variante de artículo para una unidad de medida (de presentación) no existente",
                tabla, datos, 'W')
            return

        # Existencia de la presentacion
        presentaciones = pre_obj.search(cr, uid, [("cod", "=", datos['pres_cod']), ], context={'active_test': False})
        if not presentaciones:
            self.log_error(cr, uid, u"Se intentó procesar una medida de variante de artículo para una presentación no existente",
                tabla, datos, 'W')
            return

        # Busco la medida de variante del articulo
        art_med_variantes = art_med_var_obj.search(cr, uid, [("arse_cod", "=", datos['arse_cod']),
                                                             ("med_cod_variante", "=", datos['med_cod_variante']),
                                                             ("pres_cod", "=", datos['pres_cod']),
                                                             ("med_cod_pres", "=", datos['med_cod_pres'])],
                                                   context={'active_test': False})

        datos['descripcion'] = art_obj.browse(cr, uid, articulos[0]).descripcion + ' (' + string.replace(
            str(datos['arse_cod']), '.0', '') + ') ' + ' - ' + med_obj.browse(cr, uid,
                                                                              un_med_variantes[0]).descripcion + ' (' + string.replace(
            str(datos['med_cod_variante']), '.0', '') + ') ' + pre_obj.browse(cr, uid,
                                                                              presentaciones[0]).descripcion + ' (' + string.replace(
            str(datos['pres_cod']), '.0', '') + ') ' + med_obj.browse(cr, uid,
                                                                      un_med_pres[0]).descripcion + ' (' + string.replace(
            str(datos['med_cod_pres']), '.0', '') + ')'

        art_med_variante_dat = {}

        if 'fecha_baja' in datos:
            if art_med_variantes:
                # Verifico que no esté dado de baja
                art_med_variante = art_med_var_obj.browse(cr, uid, art_med_variantes[0])

                if not art_med_variante.fecha_baja or art_med_variante.active:
                    art_med_variante_dat['fecha_baja'] = datos['fecha_baja']
                    art_med_variante_dat['active'] = False
                    if 'motivo_baja' in datos:
                        art_med_variante_dat['motivo_baja'] = datos['motivo_baja']

                    prod_ids = prod_prod_obj.search(cr, uid, [('product_tmpl_id.grp_sice_cod', '=', art_med_variante.arse_cod),
                                                     ('med_cod_id', '=', art_med_variante.med_cod_id.id),
                                                     ('pres_id', '=', art_med_variante.pres_id.id),
                                                     ('med_cod_pres_id', '=', art_med_variante.med_cod_pres_id.id),
                                                     ('det_variante_id', '=', False)])
                    if prod_ids:
                        prod_prod_obj.write(cr, uid, prod_ids, {'active': False})

                    art_med_var_obj.write(cr, uid, art_med_variantes[0], art_med_variante_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - MEDIDAS VARIANTE', 'B')
        else:
            if tabla['operacion'] == 'A' or tabla['operacion'] == 'M':
                if not art_med_variantes:
                    art_med_variante_dat['articulo_id'] = articulos[0]
                    art_med_variante_dat['med_cod_id'] = un_med_variantes[0]
                    art_med_variante_dat['pres_id'] = presentaciones[0]
                    art_med_variante_dat['med_cod_pres_id'] = un_med_pres[0]

                    art_med_var_obj.create(cr, uid, art_med_variante_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - MEDIDAS VARIANTE', 'A')

        return

    # -
    # - Proceso de novedad de tipo: det_variante
    # -
    def procesar_det_variante(self, cr, uid, tabla, datos):
        """
        Procesa la novedad detalle de variante del articulo
        """
        art_obj = self.pool.get('grp.sice_art_serv_obra')
        med_obj = self.pool.get('grp.sice_medida')
        pre_obj = self.pool.get('grp.sice_presentacion')
        mar_obj = self.pool.get('grp.sice_marca')
        art_med_var_obj = self.pool.get('grp.sice_med_variante')
        art_det_var_obj = self.pool.get('grp.sice_det_variante')
        prod_prod_obj = self.pool.get('product.product')

        # Existencia del articulo
        if 'arse_cod' in datos:
            articulos = art_obj.search(cr, uid, [("cod", "=", datos['arse_cod']), ], context={'active_test': False})
            if not articulos:
                self.log_error(cr, uid, u"Se intentó procesar un detalle de variante de artículo para un artículo no existente", tabla, datos, 'W')
                return

        # Existencia de la unidad de medida de la variante
        if 'med_cod_variante' in datos:
            un_med_variantes = med_obj.search(cr, uid, [("cod", "=", datos['med_cod_variante']), ], context={'active_test': False})
            if not un_med_variantes:
                self.log_error(cr, uid, u"Se intentó procesar un detalle de variante de artículo con una unidad de medida (de variante) no existente",
                    tabla, datos, 'W')
                return

        # Existencia de la unidad de medida de la presentacion
        if 'med_cod_pres' in datos:
            un_med_pres = med_obj.search(cr, uid, [("cod", "=", datos['med_cod_pres']), ], context={'active_test': False})
            if not un_med_pres:
                self.log_error(cr, uid, u"Se intentó procesar un detalle de variante de artículo con una unidad de medida (de presentación) no existente",
                    tabla, datos, 'W')
                return

        # Existencia de la presentacion
        if 'pres_cod' in datos:
            presentaciones = pre_obj.search(cr, uid, [("cod", "=", datos['pres_cod']), ], context={'active_test': False})
            if not presentaciones:
                self.log_error(cr, uid, u"Se intentó procesar un detalle de variante de artículo con una presentación no existente",
                    tabla, datos, 'W')
                return

        # Existencia de la marca
        if 'marc_cod' in datos:
            marcas = mar_obj.search(cr, uid, [("cod", "=", datos['marc_cod']), ], context={'active_test': False})
            if not marcas:
                self.log_error(cr, uid, u"Se intentó procesar un detalle de variante de artículo con una marca no existente",
                    tabla, datos, 'W')
                return


        # Existencia del detalle de variante
        art_det_variantes = art_det_var_obj.search(cr, uid, [("cod", "=", datos['cod']), ], context={'active_test': False})

        art_det_variante_dat = {}

        if 'fecha_baja' in datos:
            if art_det_variantes:
                # Verifico que no esté dado de baja
                art_det_variante = art_det_var_obj.browse(cr, uid, art_det_variantes[0])

                if not art_det_variante.fecha_baja or art_det_variante.active:

                    art_det_variante_dat['fecha_baja'] = datos['fecha_baja']
                    art_det_variante_dat['active'] = False
                    if 'motivo_baja' in datos:
                        art_det_variante_dat['motivo_baja'] = datos['motivo_baja']

                    prod_ids = prod_prod_obj.search(cr, uid, [('det_variante_id', '=', art_det_variante.id),
                                                     ('product_tmpl_id.grp_sice_cod', '=', art_det_variante.arse_cod)])
                    if prod_ids:
                        prod_prod_obj.write(cr, uid, prod_ids, {'active': False})

                    art_det_var_obj.write(cr, uid, art_det_variantes[0], art_det_variante_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - DETALLE VARIANTE', 'B')
        else:
            if tabla['operacion'] == 'A':
                if not art_det_variantes:

                    # Existencia de medida de variante del articulo
                    art_med_variantes = art_med_var_obj.search(cr, uid, [("arse_cod", "=", datos['arse_cod']),
                                                                         ("med_cod_variante", "=",
                                                                          datos['med_cod_variante']),
                                                                         ("pres_cod", "=", datos['pres_cod']),
                                                                         ("med_cod_pres", "=", datos['med_cod_pres'])],
                                                               context={'active_test': False})
                    if not art_med_variantes:
                        self.log_error(cr, uid,
                                       u"NOVEDAD SICE (det_variante): Se intentó agregar un detalle de variante de artículo con una medida de variante no existente",
                                       tabla, datos, 'W')
                    else:
                        art_det_variante_dat['cod'] = datos['cod']
                        art_det_variante_dat['articulo_id'] = articulos[0]
                        art_det_variante_dat['med_cod_id'] = un_med_variantes[0]
                        art_det_variante_dat['pres_id'] = presentaciones[0]
                        art_det_variante_dat['med_cod_pres_id'] = un_med_pres[0]
                        art_det_variante_dat['marc_id'] = marcas[0]
                        art_det_variante_dat['descripcion'] = datos['descripcion']
                        art_det_variante_dat['med_variante_id'] = art_med_variantes[0]

                        # Creo detalle de variante
                        art_det_var_obj.create(cr, uid, art_det_variante_dat)
                        self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - DETALLE VARIANTE', 'A')

            elif tabla['operacion'] == 'M':
                if art_det_variantes:
                    # Si existe lo unico que actualizo es la descripcion
                    art_det_variante_dat['descripcion'] = datos['descripcion']
                    art_det_var_obj.write(cr, uid, art_det_variantes[0], art_det_variante_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO - DETALLE VARIANTE', 'M')
                else:
                    self.log_error(cr, uid,
                                   u"Se intentó modificar un detalle de variante de artículo no existente", tabla, datos, 'W')
        return


    # -
    # - Proceso de novedad de tipo: sinonimo
    # -
    def procesar_sinonimo(self, cr, uid, tabla, datos):
        """
        Procesa la novedad de la relacion entre "Articulo" e "Impuesto"
        """
        art_obj = self.pool.get('grp.sice_art_serv_obra')
        art_sin_obj = self.pool.get('grp.sice_sinonimo')
        art_sinonimo_dat = {}

        # Existencia del articulo
        articulos = art_obj.search(cr, uid, [("cod", "=", datos['arse_cod']), ], context={'active_test': False})
        if not articulos:
            self.log_error(cr, uid, u"Se intentó procesar un sinónimo para un artículo no existente", tabla, datos, 'W')
            return

        # Existencia de la relacion articulo - sinonimo
        art_sinonimos = art_sin_obj.search(cr, uid,
                                      [("arse_cod", "=", datos['arse_cod']), ("descripcion", "=", datos['descripcion'])],
                                      context={'active_test': False})
        if 'fecha_baja' in datos:
            if art_sinonimos:
                # Verifico que no esté dado de baja
                art_sinonimo = art_sin_obj.browse(cr, uid, art_sinonimos[0])

                if not art_sinonimo.fecha_baja or art_sinonimo.active:

                    art_sinonimo_dat['fecha_baja'] = datos['fecha_baja']
                    art_sinonimo_dat['active'] = False
                    if 'motivo_baja' in datos:
                        art_sinonimo_dat['motivo_baja'] = datos['motivo_baja']

                    art_sin_obj.write(cr, uid, art_sinonimos[0], art_sinonimo_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'SINONIMO', 'B')
        else:
            if tabla['operacion'] == 'A' or tabla['operacion'] == 'M':
                if not art_sinonimos:
                    art_sinonimo_dat['articulo_id'] = articulos[0]
                    art_sinonimo_dat['descripcion'] = datos['descripcion']
                    art_sin_obj.create(cr, uid, art_sinonimo_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'SINONIMO', 'A')
        return

    # -
    # - Proceso de novedad de tipo: art_serv_obra
    # -
    def procesar_art_serv_obra(self, cr, uid, tabla, datos):
        """
        Procesa la novedad detalle de variante del articulo
        """
        art_obj = self.pool.get('grp.sice_art_serv_obra')
        fam_obj = self.pool.get('grp.sice_familia')
        subf_obj = self.pool.get('grp.sice_subflia')
        cla_obj = self.pool.get('grp.sice_clase')
        subc_obj = self.pool.get('grp.sice_subclase')
        unme_obj = self.pool.get('grp.sice_unidades_med')
        imp_obj = self.pool.get('grp.sice_impuesto')
        prop_obj = self.pool.get('grp.sice_propiedad')
        odg_obj = self.pool.get('grp.sice_odg')
        col_obj = self.pool.get('grp.sice_color')
        prod_tmpl_obj = self.pool.get('product.template')

        # Existencia de familia
        familias = fam_obj.search(cr, uid, [("cod", "=", datos['fami_cod']), ], context={'active_test': False})
        if not familias:
            self.log_error(cr, uid, u"Se intentó procesar un artículo para una familia no existente", tabla, datos, 'W')
            return

        # Existencia de subfamilia
        subflias = subf_obj.search(cr, uid, [("cod", "=", datos['subf_cod']), ("fami_cod", "=", datos['fami_cod']), ],
                                   context={'active_test': False})
        if not subflias:
            self.log_error(cr, uid, u"Se intentó procesar un artículo para una subfamilia no existente", tabla, datos, 'W')
            return

        # Existencia de clase
        clases = cla_obj.search(cr, uid, [("cod", "=", datos['clas_cod']), ("subf_cod", "=", datos['subf_cod']),
                                          ("fami_cod", "=", datos['fami_cod']), ], context={'active_test': False})
        if not clases:
            self.log_error(cr, uid, u"Se intentó procesar un artículo para una clase no existente", tabla, datos, 'W')
            return

        # Existencia de subclase
        subclases = subc_obj.search(cr, uid, [("cod", "=", datos['subc_cod']), ("clas_cod", "=", datos['clas_cod']),
                                              ("subf_cod", "=", datos['subf_cod']),
                                              ("fami_cod", "=", datos['fami_cod']), ], context={'active_test': False})
        if not subclases:
            self.log_error(cr, uid, u"Se intentó procesar un artículo para una subclase no existente", tabla, datos, 'W')
            return

        # Existencia de la Unidad de Medida
        un_meds = unme_obj.search(cr, uid, [("cod", "=", datos['unme_cod']), ], context={'active_test': False})
        if not un_meds:
            self.log_error(cr, uid, u"Se intentó procesar un artículo para una unidad de medida no existente", tabla, datos, 'W')
            return

        # Existencia de la Unidad de Medida de la Variante del Articulo
        var_un_meds = unme_obj.search(cr, uid, [("cod", "=", datos['var_unme_cod']), ], context={'active_test': False})
        if not var_un_meds:
            self.log_error(cr, uid, u"Se intentó procesar un artículo para una unidad de medida de variante no existente", tabla, datos, 'W')
            return

        # Existencia del impuesto
        if 'imp_cod' in datos:
            impuestos = imp_obj.search(cr, uid, [("cod", "=", datos['imp_cod']), ], context={'active_test': False})
            if not impuestos:
                self.log_error(cr, uid, u"Se intentó procesar un artículo para un impuesto no existente", tabla, datos, 'W')
                return
        else:
            self.log_error(cr, uid, u"La novedad de artículo no tenía impuesto", tabla, datos, 'W')
            impuestos = False

        # Existencia de la variante
        propiedades = prop_obj.search(cr, uid, [("cod", "=", datos['var_cod']), ], context={'active_test': False})
        if not propiedades:
            self.log_error(cr, uid, u"Se intentó agregar un artículo con una variante no existente", tabla, datos, 'W')
            return

        # Existencia de ODG
        if 'odg' in datos:
            odgs = odg_obj.search(cr, uid, [("odg", "=", datos['odg']), ], context={'active_test': False})
            if not odgs:
                self.log_error(cr, uid, u"Se intentó procesar un artículo para un ODG no existente", tabla, datos, 'W')
                return
        else:
            self.log_error(cr, uid, u"La novedad de artículo no tenía odg", tabla, datos, 'W')
            odgs = False



        # Existencia del artículo
        articulos = art_obj.search(cr, uid, [("cod", "=", datos['cod']), ], context={'active_test': False})

        art_dat = {}

        if 'fecha_baja' in datos:
            if articulos:
                # Verifico que no esté dado de baja
                articulo = art_obj.browse(cr, uid, articulos[0])

                if not articulo.fecha_baja or articulo.active:

                    art_dat['fecha_baja'] = datos['fecha_baja']
                    art_dat['active'] = False
                    if 'motivo_baja' in datos:
                        art_dat['motivo_baja'] = datos['motivo_baja']

                    prod_ids = prod_tmpl_obj.search(cr, uid, [('grp_sice_cod', '=', articulo.cod)])

                    if prod_ids:
                        prod_tmpl_obj.write(cr, uid, prod_ids, {'active': False})

                    art_obj.write(cr, uid, articulos[0], art_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO', 'B')
        else:
            if tabla['operacion'] == 'A' or tabla['operacion'] == 'M':

                for dato in datos:
                    if dato == 'fami_cod':
                        art_dat['fami_id'] = familias[0]
                    elif dato == 'subf_cod':
                        art_dat['subf_id'] = subflias[0]
                    elif dato == 'clas_cod':
                        art_dat['clas_id'] = clases[0]
                    elif dato == 'subc_cod':
                        art_dat['subc_id'] = subclases[0]
                    elif dato == 'unme_cod':
                        art_dat['unme_id'] = un_meds[0]
                    elif dato == 'imp_cod':
                        art_dat['imp_id'] = impuestos[0] if impuestos else False
                    elif dato == 'var_cod':
                        art_dat['var_id'] = propiedades[0]
                    elif dato == 'var_unme_cod':
                        art_dat['var_unme_id'] = var_un_meds[0]
                    elif dato == 'odg':
                        art_dat['odg_id'] = odgs[0] if odgs else False
                    else:
                        if dato in art_obj._columns:
                            art_dat[dato] = datos[dato]

                if not articulos:
                    art_dat['cod'] = datos['cod']
                    colores = col_obj.search(cr, uid, [("cod", "=", -1), ], context={'active_test': False})
                    art_dat['art_color_ids'] = [(4, colores[0])]
                    art_obj.create(cr, uid, art_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO', 'A')
                else:
                    art_obj.write(cr, uid, articulos[0], art_dat)
                    self.registar_historico(cr, uid, datos, tabla, 'ARTICULO', 'M')
        return


    # -
    # - Método principal de la recepción de novedades
    # -
    def recibir_novedades_sice(self, cr, uid, ids=None, context=None):

        def novedad_str_to_dic(self, novedad_str):
            """
            Transforma la novedad en dos diccionarios con los datos pertinentes
            """
            novedad_list = novedad_str.split("\n")
            tabla = {}
            datos = {}

            # _logger.info('novedad_list: %s', novedad_list)

            for linea in novedad_list:
                # _logger.info('LINEA: %s', linea)
                if 'Arr' in linea:
                    pass

                elif 'Proxy' in linea:
                    pass

                elif 'FECHA =' in linea:
                    cols = linea.strip().split(' = ')
                    tabla['fecha'] = cols[1].replace('"', '')

                elif 'OPERACION' in linea:
                    cols = linea.strip().split(' = ')
                    tabla['operacion'] = cols[1].replace('"', '')

                elif 'Type' in linea:
                    tabla['nombre'] = linea.strip().replace('(','').replace('Type){','').lower()

                elif '=' in linea:
                    cols = linea.strip().split(' = ')
                    if len(cols) == 2:
                        if '"' in cols[1]:
                            valor = cols[1].replace('"', '')
                        elif '-' in cols[1]:
                            valor = cols[1]
                        else:
                            if cols[1] != 'None':
                                valor = float(cols[1])
                        if cols[1] != 'None':
                            datos[cols[0].lower()] = valor
            return tabla, datos

        _logger.info('Novedades Articulos SICE: INICIO')
        # _logger.info('Novedades Articulos SICE: Estableciendo conexion')

        # Establecer la conexión
        if not self.conectar_sice(cr, uid):
            # self.log_error(cr, uid, u"No se pudo establecer conexión", tabla, datos, 'E')
            return False

        # _logger.info('Novedades Articulos SICE: Conexion establecida')

        # Determinar fecha a partir de la cual se solicitarán las novedades
        sys_cfg = self.pool.get('ir.config_parameter')
        dias_atras = sys_cfg.get_param(cr, uid, self.key_dias_atras)

        if not dias_atras:
            raise osv.except_osv('Error!',u'No se encuentra configurada la cantidad de días atrás para consumir el servicio de Novedades SICE')
        fecha_inicio_novedades = date.today() - timedelta(days=int(dias_atras))

        _logger.info('Novedades Articulos SICE: Fecha de Inicio de Novedades %s', fecha_inicio_novedades.strftime("%Y-%m-%d"))

        # Consumo de novedades
        try:
            pool_novedades = self.ws_novedades.service['ActualizacionCatalogoServiceHttpSoap12Endpoint'].findActualizacionesCatalogo(fecha_inicio_novedades.strftime("%Y-%m-%d"))
        except:
            # self.log_error(cr, uid, u"No se pudo obtener la novedad SICE", tabla, datos, 'E')
            raise osv.except_osv('Error!', u'No se pudo obtener la novedad SICE')

        # Segmentamos en una lista
        list_novedades = str(pool_novedades).replace('},','}*').split('*')

        # Proceso cada novedad
        for novedad_str in list_novedades:

            # Convertimos la cadena a diccionario
            tabla, datos = novedad_str_to_dic(self, novedad_str)

            # Derivo a métodos especializados en cada tipo de novedad
            if 'nombre' in tabla:
                if tabla['nombre'] == 'familia':
                    self.procesar_familia(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'subflia':
                    self.procesar_subflia(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'clase':
                    self.procesar_clase(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'subclase':
                    self.procesar_subclase(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'unidad_med':
                    self.procesar_unidad_med(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'impuesto':
                    self.procesar_impuesto(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'marca':
                    self.procesar_marca(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'medida':
                    self.procesar_medida(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'propiedad':
                    self.procesar_propiedad(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'prop_unidad_med':
                    self.procesar_prop_unidades_med(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'art_color':
                    self.procesar_art_color(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'art_impuesto':
                    self.procesar_art_impuesto(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'art_atributo':
                    self.procesar_art_atributo(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'art_unidad_med':
                    self.procesar_art_unidad_med(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'med_variante':
                    self.procesar_med_variante(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'det_variante':
                    self.procesar_det_variante(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'art_serv_obra':
                    self.procesar_art_serv_obra(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'sinonimo':
                    self.procesar_sinonimo(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'objetodelgasto':
                    self.procesar_odg(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'presentacion':
                    self.procesar_presentacion(cr, uid, tabla, datos)

                elif tabla['nombre'] == 'color':
                    self.procesar_color(cr, uid, tabla, datos)

                else:
                    self.log_error(cr, uid, u"Tipo de novedad no contemplado", tabla, datos, 'E')

        _logger.info('Novedades Articulos SICE: FIN')
        return

wizard_novedades_sice()


