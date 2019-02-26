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

from datetime import datetime
from openerp.osv import osv, fields

class grp_art_impuestos(osv.osv):
    """Relación de Impuestos"""

    def _get_sice_imp(self, cr, uid, context=None):
        #Si no existe la tabla devuelvo vacio para que no de error
        cr.execute("SELECT * FROM pg_class WHERE relname = 'grp_sice_impuesto'")
        if cr.rowcount > 0:
            cr.execute("select cod, descripcion from grp_sice_impuesto where active")
            res = cr.fetchall()
            imp_list = ()
            for a_imp in res:
                imp_list += ((str(a_imp[0]), a_imp[1]),)
            return imp_list
        else:
            return ()

    _name = 'grp.art.impuestos'
    _columns = {
        'imp_sice': fields.selection(_get_sice_imp, 'Impuesto SICE', required=True),
        'imp_grp': fields.many2one('account.tax','Impuesto GRP', required=True),
    }
    _sql_constraints = [
        ('sice_imp_uniq','unique(imp_sice)', 'Impuesto SICE ya relacionado'),
        ('grp_imp_uniq','unique(imp_grp)', 'Impuesto GRP ya relacionado'),
    ]

grp_art_impuestos()
