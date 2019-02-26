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

from openerp.osv import fields, osv

class obligacion_fr_anulaciones_siif_log(osv.osv):
    _name = 'obligacion.fr.anulacion.siif.log'
    _description = "Log obligacion fondo rotatorio anulaciones"

    _columns = {
        'fondo_rotatorio_id': fields.many2one('grp.fondo.rotatorio', 'Fondo rotatorio', required=True,ondelete='cascade'),
        'fecha': fields.date('Fecha', required=True),
        'nro_afectacion_siif': fields.integer(u'Nro Afectación SIIF'),
        'nro_compromiso': fields.char(u'Nro Compromiso'),
        'nro_obligacion': fields.char(u'Nro Obligación'),
        'nro_obl_sist_aux': fields.char(u'Nro Obligación Sistema Aux'),
    }

    _defaults = {
        'fecha': fields.date.context_today,
    }
obligacion_fr_anulaciones_siif_log()
