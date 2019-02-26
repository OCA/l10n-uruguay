##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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


import openerp
from openerp import SUPERUSER_ID

import pprint
import werkzeug
import openerp.addons.web.http as http
from openerp.http import request

import logging

_logger = logging.getLogger(__name__)

class firmaController(http.Controller):

    # Punto de entrada para procesar la respuesta del applet de firma
    @http.route('/x_firma', type='http', auth="none", methods=['POST'])
    def respuesta_applet(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        _logger.info('post %s',post)
        _logger.info('request %s',request)
        """ resultado del llamado"""
        _logger.debug('TRACE: firmaController POST: %s', pprint.pformat(post))
        id_transaction = post['id_transaction']
        try:
            uid = int(post['uid'])
        except:
            uid = SUPERUSER_ID
        #db_name = openerp.tools.config['db_name']
        #cr = openerp.pooler.get_db(db_name).cursor()

        _logger.info("Antes de instanciar firma_obj")
        firma_obj = request.registry.get('x_firma')
        _logger.info("Luego de instanciar firma_obj")

        id_firma = firma_obj.search(cr, SUPERUSER_ID, [('id_transaction', 'in', [id_transaction])], context=None)
        _logger.info('id_firma: %s', id_firma)

        registro = firma_obj.read(cr, SUPERUSER_ID, id_firma, ['id_registro'], context=None)
        _logger.info('registro: %s', registro)

        rec_id = registro[0]['id']
        id_registro = registro[0]['id_registro']

        modelo = post['model']
        adjunto = post['attachment']



        documento = firma_obj.invocar_ws_obtenerDocumentosFirmados(cr, SUPERUSER_ID, [id_registro, id_transaction])
        if documento:
            firma_obj.adjuntar_documento(cr, uid, [id_registro, rec_id, documento, modelo, adjunto])
            firma_obj.utiles(cr, uid, modelo, id_registro)

        firma_obj.unlink(cr, SUPERUSER_ID, id_firma, context = None)

        return werkzeug.utils.redirect('/web')

firmaController()
