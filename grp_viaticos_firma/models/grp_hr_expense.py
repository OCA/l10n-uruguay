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

from openerp.osv  import osv
from openerp import models, fields, api, _
import logging


_logger = logging.getLogger(__name__)

class GrpHrExpenseExpense(models.Model):
    _inherit = 'hr.expense.expense'

    x_doc_firmado = fields.Boolean(string='Documento firmado')
    firma_electronica = fields.Boolean(string=u'Firma Electrónica', compute='_firma_electronica', store=False)

    def _firma_electronica(self):
        usuario = self.env['res.users'].browse(self._uid)
        usuario_firma = usuario.firma_electronica
        for rec in self:
            if usuario_firma and rec.company_id.firma_electronica:
                rec.firma_electronica = True
            else:
                rec.firma_electronica = False



class GrpHrExpense(osv.osv):
    _inherit = 'hr.expense.expense'


    def boton_firmar_y_autorizar(self, cr, uid, ids, context=None):
        nombre_reporte = 'Rendición por persona'
        #x_firma_obj = self.env['x_firma']
        x_firma_obj = self.pool.get('x_firma')
        adjunto = 'False'
        result = {}

        result = x_firma_obj.firmar_documento(cr, uid, ids, self._name, nombre_reporte, adjunto, context=None)

        return result

