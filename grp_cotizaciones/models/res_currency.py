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

from datetime import date, timedelta, datetime
from openerp.osv import osv, fields
from suds.client import Client
import logging
import time

_logger = logging.getLogger(__name__)

class grp_res_currency(osv.osv):
    _inherit = 'res.currency'

    _columns = {
        'codigo_siif': fields.integer(u'Código moneda SIIF'),
        'porcentaje_aumento_tipo_cambio_siif': fields.integer(u'% aumento tipo cambio presupuesto'),
    }

    # Objetos SOAP para la conexión
    ws_siif = None

    # Las lineas siguientes permiten controlar que en caso de cargar valor en codigo_siif, se deba cargar tambien en porcentaje aumento TC para presupuesto
    # Se quita este control para permitir que el porcentaje mencionado pueda ser 0
    # def _check_porcentaje_aumento(self, cr, uid, ids, context=None):
    #     for moneda in self.browse(cr, uid, ids, context=context):
    #         if moneda.codigo_siif and not moneda.porcentaje_aumento_tipo_cambio_siif:
    #             return False
    #     return True
    #
    # _constraints = [
    #     (_check_porcentaje_aumento,'Debe ingresar el valor correspondiente al porcentaje de aumento para el tipo de cambio del presupuesto',
    #      ['codigo_siif','porcentaje_aumento_tipo_cambio_siif'])
    # ]

    def conectar_siif(self, cr, uid):
        """
        Establece la conexión con los WS y crea los objetos SOAP clientes de dicha conexión.
        """
        # Obtener las URLs necesarias de los parámetros del sistema
        wsdl_siif = self.pool.get('ir.config_parameter').get_param(cr, uid, 'url_ws.siif')

        if not wsdl_siif:
            raise osv.except_osv('Error!',
                                 u'No se encuentra configurada la ruta del WSDL para consumir los servicios SiiF')

        _logger.info("wsdl_siif: " + wsdl_siif)

        # Establecer la conexión
        try:
            self.ws_siif = Client(wsdl_siif, cache=None)
            _logger.info("WS_SIIF: %s", self.ws_siif)
        except Exception as e:
            return False

        return True


    def get_cotizaciones(self, cr, uid, ids=None, context=None):

        currency_rate_obj = self.pool.get('res.currency.rate')

        _logger.info('Servicio Web SIIF - obtenerTasaCambioPorMoneda: Inicio')

        # Establecer la conexión con SIIF
        if not self.conectar_siif(cr, uid):
            _logger.info('Servicio Web SIIF - obtenerTasaCambioPorMoneda: No se pudo conectar con el servicio')
            return False

        # Fecha de fin de consulta
        fecha_fin = datetime.now().date()

        # Recorro las monedas que tienen definido 'Codigo Moneda SiiF'
        moneda_ids = self.search(cr, uid, [('codigo_siif','>',0)])
        for moneda in self.browse(cr, uid, moneda_ids, context=context):

            factor_presupuesto = 1 + moneda.porcentaje_aumento_tipo_cambio_siif/float(100)

            _logger.info('Servicio Web SIIF - obtenerTasaCambioPorMoneda: Moneda: %s', moneda.name)
            _logger.info('Servicio Web SIIF - obtenerTasaCambioPorMoneda: Codigo SIIF: %s', moneda.codigo_siif)

            # Obtengo la fecha maxima para la cual se registro tipo de cambio
            rate_ids = currency_rate_obj.search(cr, uid, [('currency_id','=',moneda.id)], order='name desc')

            # Determino fecha de inicio de consulta
            if rate_ids:
                rate_last_date = currency_rate_obj.browse(cr, uid, rate_ids[0], context=context).name
                rate_last_date_datetime = datetime.strptime(rate_last_date, "%Y-%m-%d")
                fecha_ini_datetime = rate_last_date_datetime + timedelta(days=1)
                fecha_ini = fecha_ini_datetime.date()

                fecha = fecha_ini
                while (fecha <= fecha_fin):
                    _logger.info('Servicio Web SIIF - obtenerTasaCambioPorMoneda: Fecha consulta: %s', fecha)

                    try:
                        tasaCambioConsulta = self.ws_siif.factory.create('tasaCambioRequest')
                        tasaCambioConsulta['moneda'] = moneda.codigo_siif
                        tasaCambioConsulta['fecha'] = fecha
                        _logger.info('Servicio Web SIIF - obtenerTasaCambioPorMoneda: Parametros consulta: %s', tasaCambioConsulta)

                        tasaCambio = self.ws_siif.service.obtenerTasaCambioPorMoneda(tasaCambioConsulta)
                        _logger.info('Servicio Web SIIF - obtenerTasaCambioPorMoneda: Respuesta: %s', tasaCambio)

                        if tasaCambio.resultado == 1:
                            # fecha_dt = datetime(fecha.year, fecha.month, fecha.day, 3, 0)
                            fecha_dt = fecha
                            values = {
                                'name': fecha_dt,
                                'currency_id': moneda.id,
                                'rate': tasaCambio.tasaDeCambio,
                                'rate_sell': tasaCambio.tasaDeCambio,
                                'rate_presupuesto': float(tasaCambio.tasaDeCambio) * factor_presupuesto
                            }
                            currency_rate_obj.create(cr, uid, values)  # Se crea el nuevo registro

                    except Exception as e:
                        _logger.info("Error en obtenerTasaCambioPorMoneda: %s", str(e))
                        return False

                    fecha = fecha + timedelta(days=1)

        _logger.info('Servicio Web SIIF - obtenerTasaCambioPorMoneda: Fin')
        return True

grp_res_currency()

