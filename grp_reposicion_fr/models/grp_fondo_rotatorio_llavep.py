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

from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp
import time

# TODO: SPRING 8 GAP 111.228.339 K
class grp_fondo_rotatorio_llavep(models.Model):
    _name = 'grp.fondo.rotatorio.llavep'

    def _check_linea_llavep_programa(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.programa:
                if not llp.programa.isdigit():
                    return False
        return True

    def _check_linea_llavep_odg(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.odg:
                if not llp.odg.isdigit():
                    return False
        return True

    def _check_linea_llavep_auxiliar(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.auxiliar:
                if not llp.auxiliar.isdigit():
                    return False
        return True

    def _check_linea_llavep_disponible(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.disponible:
                if not llp.disponible.isdigit():
                    return False
        return True

    def _check_linea_llavep_proyecto(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.proyecto:
                if not llp.proyecto.isdigit():
                    return False
        return True

    def _check_linea_llavep_fin(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.fin:
                if not llp.fin.isdigit():
                    return False
        return True

    def _check_linea_llavep_mon(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.mon:
                if not llp.mon.isdigit():
                    return False
        return True

    def _check_linea_llavep_tc(self, cr, uid, ids):
        for llp in self.browse(cr, uid, ids):
            if llp.tc:
                if not llp.tc.isdigit():
                    return False
        return True

    fondo_rotatorios_llp_id = fields.Many2one('grp.fondo.rotatorio', string=u'3-1 Fondo Rotarorio', ondelete='cascade')
    #Campos de la estructura
    odg_id = fields.Many2one('grp.estruc_pres.odg', 'ODG', required=True)
    auxiliar_id = fields.Many2one('grp.estruc_pres.aux', 'Auxiliar', required=True, default=False)
    fin_id =  fields.Many2one('grp.estruc_pres.ff', 'Fin')
    programa_id = fields.Many2one('grp.estruc_pres.programa', 'Programa')
    proyecto_id = fields.Many2one('grp.estruc_pres.proyecto', 'Proyecto')
    mon_id =fields.Many2one('grp.estruc_pres.moneda', 'Mon')
    tc_id = fields.Many2one('grp.estruc_pres.tc', 'TC')
    # Campos related
    fin = fields.Char(related='fin_id.ff',string='Fin related', store=True, readonly=True)
    programa = fields.Char(related='programa_id.programa', string='Programa related', store=True, readonly=True)
    proyecto = fields.Char(related='proyecto_id.proyecto', string='Proyecto related', store=True, readonly=True)
    odg = fields.Char(related='odg_id.odg', string='ODG related', store=True, readonly=True)
    auxiliar = fields.Char(related='auxiliar_id.aux', string='Auxiliar related', store=True, readonly=True)
    mon = fields.Char(related='mon_id.moneda', string='Mon related', store=True, readonly=True)
    tc = fields.Char(related='tc_id.tc', string='TC related', store=True, readonly=True)
    #montos
    disponible = fields.Char('Disponible', size=3)
    importe = fields.Integer('Importe')
    parent_state = fields.Selection(related='fondo_rotatorios_llp_id.state', readonly=True)

    # 001 - On_change llaves presupuestal
    def onchange_objeto_del_gasto(self, cr, uid, ids, odg_id, context=None):
        auxiliar_id = False
        if odg_id:
            auxiliar_ids = self.pool.get('grp.estruc_pres.aux').search(cr, uid, [('odg_id', '=', odg_id)])
            if len(auxiliar_ids) == 1:
                auxiliar_id = auxiliar_ids[0]
        return {'value': {
            'auxiliar_id': auxiliar_id,
            'fin_id': False,
            'programa_id': False,
            'proyecto_id': False,
            'mon_id': False,
            'tc_id': False,
        }}

    def onchange_auxiliar(self, cr, uid, ids, auxiliar_id, context=None):
        fin_id = False
        if auxiliar_id:
            fin_ids = self.pool.get('grp.estruc_pres.ff').search(cr, uid, [('aux_id', '=', auxiliar_id)])
            if len(fin_ids) == 1:
                fin_id = fin_ids[0]
        return {'value': {
            'fin_id': fin_id,
            'programa_id': False,
            'proyecto_id': False,
            'mon_id': False,
            'tc_id': False
        }}

    def onchange_fuente_de_financiamiento(self, cr, uid, ids, fin_id, context=None):
        programa_id = False
        if fin_id:
            programa_ids = self.pool.get('grp.estruc_pres.programa').search(cr, uid, [('ff_id', '=', fin_id)])
            if len(programa_ids) == 1:
                programa_id = programa_ids[0]
        return {'value': {
            'programa_id': programa_id,
            'proyecto_id': False,
            'mon_id': False,
            'tc_id': False,
        }}

    def onchange_programa(self, cr, uid, ids, programa_id, context=None):
        proyecto_id = False
        if programa_id:
            proyecto_ids = self.pool.get('grp.estruc_pres.proyecto').search(cr, uid,[('programa_id', '=', programa_id)])
            if len(proyecto_ids) == 1:
                proyecto_id = proyecto_ids[0]
        return {'value': {
            'proyecto_id': proyecto_id,
            'mon_id': False,
            'tc_id': False,
        }}

    def onchange_proyecto(self, cr, uid, ids, proyecto_id, context=None):
        mon_id = False
        if proyecto_id:
            mon_ids = self.pool.get('grp.estruc_pres.moneda').search(cr, uid, [('proyecto_id', '=', proyecto_id)])
            if len(mon_ids) == 1:
                mon_id = mon_ids[0]
        return {'value': {
            'mon_id': mon_id,
            'tc_id': False,
        }}

    def onchange_moneda(self, cr, uid, ids, mon_id, context=None):
        tc_id = False
        if mon_id:
            tc_ids = self.pool.get('grp.estruc_pres.tc').search(cr, uid, [('moneda_id', '=', mon_id)])
            if len(tc_ids) == 1:
                tc_id = tc_ids[0]
        return {'value': {
            'tc_id': tc_id
        }}

    def _check_llavep_unica(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            lineas_duplicadas = self.search(cr, uid, [('fondo_rotatorios_llp_id', '=', line.fondo_rotatorios_llp_id.id),
                                                      ('fin_id', '=', line.fin_id.id),
                                                      ('programa_id', '=', line.programa_id.id),
                                                      ('proyecto_id', '=', line.proyecto_id.id),
                                                      ('odg_id', '=', line.odg_id.id),
                                                      ('auxiliar_id', '=', line.auxiliar_id.id),
                                                      ('mon_id', '=', line.mon_id.id),
                                                      ('tc_id', '=', line.tc_id.id),
                                                      ('id', 'not in', ids)
                                                      ], context=context)
            if lineas_duplicadas:
                raise exceptions.ValidationError(_(u'No se pueden ingresar 2 líneas iguales para el mismo registro.'))
        return True


    _constraints = [
        (_check_llavep_unica, u'Línea duplicada',
         ['fondo_rotatorios_llp_id', 'fin_id', 'programa_id', 'proyecto_id', 'odg_id', 'auxiliar_id'
          'mon_id', 'tc_id']),
        (_check_linea_llavep_programa, u'Campo no es numérico', ['programa']),
        (_check_linea_llavep_odg, u'Campo no es numérico', ['odg']),
        (_check_linea_llavep_auxiliar, u'Campo no es numérico', ['auxiliar']),
        (_check_linea_llavep_disponible, u'Campo no es numérico', ['disponible']),
        # incidencias
        (_check_linea_llavep_proyecto, u'Campo no es numérico', ['proyecto']),
        (_check_linea_llavep_fin, u'Campo no es numérico', ['fin']),
        (_check_linea_llavep_mon, u'Campo no es numérico', ['mon']),
        (_check_linea_llavep_tc, u'Campo no es numérico', ['tc']),
    ]




