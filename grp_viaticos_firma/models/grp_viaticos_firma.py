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

class grp_viaticos_firma(osv.osv):
    _inherit= 'x_firma'


    def utiles (self, cr, uid, modelo, id_registro, context = None):

        if modelo == 'hr.expense.expense':
            modelo_obj = self.pool.get(modelo)
            estado = modelo_obj.browse (cr, uid, id_registro, context).state
            # if estado == 'in_approved':
            #     modelo_obj.btn_aprobar(cr, uid, [id_registro], context)
            if estado == 'en_autorizacion':
                modelo_obj.action_autorizar(cr, uid, [id_registro], context)
        return super (grp_viaticos_firma, self). utiles (cr, uid, modelo, id_registro, context )

grp_viaticos_firma()