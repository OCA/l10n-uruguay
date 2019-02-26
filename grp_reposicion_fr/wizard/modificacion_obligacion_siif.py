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

from openerp.osv import osv, fields

_logger = logging.getLogger(__name__)


class wiz_modificacion_obligacion_fr_siif(osv.osv_memory):
    _name = 'wiz.modificacion_obligacion_fr_siif'
    _description = "Wizard modificacion de obligacion SIIF"
    _columns = {
        'fondo_rotatorio_w_id': fields.integer('fondo_rotatorio_id', invisible=False),
        'tipo': fields.selection(
            (('A', 'A - Aumento'),
             ('R', u'R - Reducción')),
             # ('C', u'C - Corrección'),
             # ('N', u'N - Anulación'),
             # ('D', u'D - Devolución')),
            'Tipo', required=True),
        'fecha': fields.date('Fecha', required=True),
        'importe': fields.integer('Importe', required=True),
        'motivo': fields.char('Motivo', required=True),
        'financiamiento': fields.related('fin_id', 'ff', type='char', string='Fin related', store=True, readonly=True),
        'programa': fields.related('programa_id', 'programa', type='char', string='Programa related', store=True, readonly=True),
        'proyecto': fields.related('proyecto_id', 'proyecto', type='char', string='Proyecto related', store=True, readonly=True),
        'objeto_gasto': fields.related('odg_id', 'odg', type='char', string='ODG related', store=True, readonly=True),
        'auxiliar' : fields.related('auxiliar_id', 'aux', type='char', string='Auxiliar related', store=True, readonly=True),
        'moneda' : fields.related('mon_id', 'moneda', type='char', string='Mon related', store=True, readonly=True),
        'tipo_credito' : fields.related('tc_id', 'tc', type='char', string='TC related', store=True, readonly=True),
        'ue_id': fields.many2one('grp.estruc_pres.ue', 'Unidad ejecutora'),
        'fin_id' : fields.many2one ('grp.estruc_pres.ff', 'Fin', required=True),
        'programa_id' : fields.many2one ('grp.estruc_pres.programa', 'Programa', required=True),
        'proyecto_id' : fields.many2one ('grp.estruc_pres.proyecto', 'Proyecto', required=True),
        'odg_id' : fields.many2one ('grp.estruc_pres.odg', 'ODG', required=True),
        'auxiliar_id' : fields.many2one ('grp.estruc_pres.aux', 'Auxiliar', required=True),
        'mon_id' : fields.many2one ('grp.estruc_pres.moneda', 'Mon', required=True),
        'tc_id' : fields.many2one ('grp.estruc_pres.tc', 'TC', required=True),
    }

    _defaults = {
        'fecha': fields.date.context_today,
    }

    #Consumir SIIF aca
    def send_modif(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, [], context=context)[0]
        fondo_rotatorio_obj = self.pool.get("grp.fondo.rotatorio")

        ctx = dict(context)
        ctx.update({
            'es_modif': True,
            'fondo_rotatorio_w_id': data['fondo_rotatorio_w_id'],
            'tipo_modificacion': data['tipo'],
            'fecha': data['fecha'],
            'programa': data['programa'],
            'proyecto': data['proyecto'],
            'moneda': data['moneda'],
            'tipo_credito': data['tipo_credito'],
            'financiamiento': data['financiamiento'],
            'objeto_gasto': data['objeto_gasto'],
            'auxiliar': data['auxiliar'],
            'importe': data['importe'] if data['tipo']=='A' else data['importe']*-1,
            'motivo': data['motivo'],
        })

        return fondo_rotatorio_obj.enviar_modificacion_siif(cr, uid, id=data['fondo_rotatorio_id'], context=ctx)

wiz_modificacion_obligacion_fr_siif()

# class ws_modif_obligacion_siif_fr_log(osv.osv):
#     _name = 'wiz.modif_obligacion_siif_fr_log'
#     _description = "Log de modificaciones de obligacion SIIF"
#     _columns = {
#         'fondo_rotatorio_w_id': fields.many2one('grp.fondo.rotatorio', '3en1 Fondo Rotacion', required=True,ondelete='cascade'),
#         'tipo': fields.selection(
#             (('A', 'A - Aumento'),
#              ('R', u'R - Reducción'),
#              # ('C', u'C - Corrección'),
#              ('N', u'N - Anulación')),
#              # ('D', u'D - Devolución')),
#              'Tipo'),
#         'fecha': fields.date('Fecha', required=True),
#         'importe': fields.float('Importe', required=True),
#         'programa': fields.char('Programa', size=3, required=True),
#         'proyecto': fields.char('Proyecto', size=3, required=True),
#         'moneda': fields.char('MON', size=2, required=True),
#         'tipo_credito': fields.char('TC', size=1, required=True),
#         'financiamiento': fields.char('FF', size=2, required=True),
#         'objeto_gasto': fields.char('ODG', size=3, required=True),
#         'auxiliar': fields.char('AUX', size=3, required=True),
#         'siif_sec_obligacion': fields.char(u'Secuencial obligación'),
#         'siif_ult_modif': fields.integer(u'Última modificación'),
#     }
# ws_modif_obligacion_siif_fr_log()

# class obligacion_anulaciones_siif_fr_log(osv.osv):
#     _name = 'obligacion.anulacion.siif.fr.log'
#     _description = "Log obligacion anulaciones"
#
#     _columns = {
#         'fondo_rotatorio_w_id': fields.many2one('grp.fondo.rotatorio', '3en1 Fondo Rotacion', required=True, ondelete='cascade'),
#         'fecha': fields.date('Fecha', required=True),
#         'nro_afectacion_siif': fields.integer(u'Nro Afectación SIIF'),
#         'nro_compromiso': fields.char(u'Nro Compromiso'),
#         'nro_obligacion': fields.char(u'Nro Obligación'),
#         'nro_obl_sist_aux': fields.char(u'Nro Obligación Sistema Aux'),
#     }
#
#     _defaults = {
#         'fecha': fields.date.context_today,
#     }
# obligacion_anulaciones_siif_fr_log()


