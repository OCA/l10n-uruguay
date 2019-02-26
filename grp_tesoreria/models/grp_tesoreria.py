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

from openerp.osv import osv, fields
import time
from openerp import tools, exceptions
from lxml import etree
from openerp.tools.translate import _

from openerp import models, api


import logging
_logger = logging.getLogger(__name__)


#002-Inicio
class grp_relacion_llave_contable(osv.osv):
    _name="grp_relacion_llave_contable"

    def is_account_ids_unique(self, cr, uid, ids, account_ids, fiscal_year, context=None):
        for a in account_ids:
            if len(self.search(cr,uid,[('fiscalyear_siif_id','=',fiscal_year.id),('account_ids','in',a.id)])) > 1:
                return False
        return True

    def _check_account_ids_on_relation_llave(self, cr, uid, ids, context=None):
        for relation_llave in self.browse(cr, uid, ids):
            if relation_llave.account_ids:
                return self.is_account_ids_unique(cr, uid, ids, relation_llave.account_ids, relation_llave.fiscalyear_siif_id)
        return True

    def onchange_presupuesto(self, cr, uid, ids, name, context=None):
        value = {}
        domain_ids=[]
        pres_inciso_obj = self.pool.get('grp.estruc_pres.inciso')
        pres_ue_obj = self.pool.get('grp.estruc_pres.ue')

        if name:
            obj = self.pool.get('presupuesto.presupuesto').browse(cr, uid, name)
            value = {
                'start_date':obj.start_date,'end_date':obj.end_date,'fiscalyear_siif_id': obj.fiscal_year.id
            }
            fiscal_year_id = obj.fiscal_year.id
            if fiscal_year_id:
                ids_pres_inciso = pres_inciso_obj.search(cr, uid, [('fiscal_year_id','=', fiscal_year_id)])
            inciso = len(ids_pres_inciso) == 1 and ids_pres_inciso[0] or False
            ue = False
            if inciso:
                ids_pres_ue = pres_ue_obj.search(cr, uid, [('inciso_id','=', ids_pres_inciso[0])])
                ue = len(ids_pres_ue) == 1 and ids_pres_ue[0] or False
            value.update({'inciso_siif_id':inciso}) and inciso
            value.update({'ue_siif_id':ue}) and ue
        else:
            value = {'start_date':False,'end_date':False,'fiscalyear_siif_id': False, 'inciso_siif_id': False, 'ue_siif_id': False}
        return {'value': value}

    #006 - Cambios en onchange llaves y valores
    def onchange_inciso(self, cr, uid, ids, inciso_siif_id, context=None):
            return {'value': {
                              'ue_siif_id': False,
                              'fin_id': False,
                              'programa_id': False,
                              'proyecto_id': False,
                              'odg_id': False,
                              'auxiliar_id': False,
                              'mon_id': False,
                              'tc_id': False,
                              }}

    def onchange_unidad_ejecutora(self, cr, uid, ids, ue_siif_id, context=None):
            return {'value': {
                              'fin_id': False,
                              'programa_id': False,
                              'proyecto_id': False,
                              'odg_id': False,
                              'auxiliar_id': False,
                              'mon_id': False,
                              'tc_id': False,
                              }}

    def onchange_fuente_de_financiamiento(self, cr, uid, ids, fin_id, context=None):
            return {'value': {
                              'programa_id': False,
                              'proyecto_id': False,
                              'odg_id': False,
                              'auxiliar_id': False,
                              'mon_id': False,
                              'tc_id': False,
                              }}

    def onchange_programa(self, cr, uid, ids, programa_id, context=None):
            return {'value': {
                              'proyecto_id': False,
                              'odg_id': False,
                              'auxiliar_id': False,
                              'mon_id': False,
                              'tc_id': False,
                            }}

    def onchange_proyecto(self, cr, uid, ids, proyecto_id, context=None):
            return {'value': {
                              'odg_id': False,
                              'auxiliar_id': False,
                              'mon_id': False,
                              'tc_id': False,
                              }}

    def onchange_objeto_del_gasto(self, cr, uid, ids, odg_id, context=None):
            return {'value': {
                              'auxiliar_id': False,
                              'mon_id': False,
                              'tc_id': False,
                              }}

    def onchange_auxiliar(self, cr, uid, ids, auxiliar_id, context=None):
            return {'value': {
                              'mon_id': False,
                              'tc_id': False
                              }}

    def onchange_moneda(self, cr, uid, ids, mon_id, context=None):
            return {'value': {
                              'tc_id': False
                              }}

    def get_descripcion(self, cr, uid, ids, name, args, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = ('%s-%s-%s%s-%s-%s%s-%s-%s') % (rec.inciso_siif_id.inciso, rec.ue_siif_id.ue, rec.programa_id.programa,
                                             rec.proyecto_id.proyecto, rec.fin_id.ff, rec.tc_id.tc,
                                             rec.mon_id.moneda, rec.odg_id.odg, rec.auxiliar_id.aux)
        return res

    _columns={
        'name': fields.many2one('presupuesto.presupuesto','Presupuesto',required=True),
        'start_date': fields.related('name','start_date', type='date',string='Fecha inicio',readonly=True),
        'end_date': fields.related('name','end_date',type='date',string='Fecha fin',readonly=True),
        # 'fiscal_year': fields.related('name','fiscal_year',type='many2one', relation='account.fiscalyear', string=u'Año fiscal'),
        'fiscalyear_siif_id': fields.related('name','fiscal_year',type='many2one', relation='account.fiscalyear', string=u'Año fiscal', readonly=True),
        'active': fields.boolean('Activo'),
        'create_date': fields.datetime(u'Fecha de creación', readonly=True),
        'account_ids': fields.many2many('account.account', 'account_account_llavep_rel','relacion_id', 'account_id', string='Cuentas Contables'),
        #005 Cambios
        'inciso_siif_id': fields.many2one('grp.estruc_pres.inciso', 'Inciso', required=True),
        'ue_siif_id': fields.many2one('grp.estruc_pres.ue', 'Unidad ejecutora', required=True),
        # llave presupuestal
        'fin_id' : fields.many2one ('grp.estruc_pres.ff', 'Fin', required=True),
        'programa_id' : fields.many2one ('grp.estruc_pres.programa', 'Programa', required=True),
        'proyecto_id' : fields.many2one ('grp.estruc_pres.proyecto', 'Proyecto', required=True),
        'odg_id' : fields.many2one ('grp.estruc_pres.odg', 'ODG', required=True),
        'auxiliar_id' : fields.many2one ('grp.estruc_pres.aux', 'Auxiliar', required=True),
        'mon_id' : fields.many2one ('grp.estruc_pres.moneda', 'Mon', required=True),
        'tc_id' : fields.many2one ('grp.estruc_pres.tc', 'TC', required=True),
        # 'descripcion': fields.char(u'Descripción'),
        'descripcion': fields.function(get_descripcion, type='char', size=200, string=u'Descripción', store=True),
    }

    _defaults = {
        'active': True,
    }

    _sql_constraints = [('unique_fiscal_year_config_llaves', 'unique(name,inciso_siif_id,ue_siif_id,fin_id,programa_id,proyecto_id,odg_id,auxiliar_id,mon_id,tc_id)', u'Ya existe un registro para el año fiscal seleccionado y el presupuesto indicado.')]
    _constraints = [(_check_account_ids_on_relation_llave,u'Una de las cuentas contables ingresada ya esta asociada a una llave presupuestal.',['account_ids'])]

grp_relacion_llave_contable()

class grp_vista_tree_llavep_cc(osv.osv):
    _name = 'grp_vista_tree_llavep_cc'
    _auto = False
    _rec_name = 'presupuesto_id'
    _order = 'presupuesto_id asc'
    _columns = {
        'relacion_id': fields.many2one('grp_relacion_llave_contable', u'Relación'),
        'presupuesto_id': fields.many2one('presupuesto.presupuesto', 'Presupuesto'),
        'fiscal_year': fields.many2one('account.fiscalyear', string=u'Año fiscal'),
        'inciso_siif_id': fields.many2one('grp.estruc_pres.inciso','Inciso'),
        'ue_siif_id': fields.many2one('grp.estruc_pres.ue','UE'),
        'financiamiento_id': fields.many2one('grp.estruc_pres.ff','Financiamiento'),
        'programa_id': fields.many2one('grp.estruc_pres.programa','Programa'),
        'proyecto_id': fields.many2one('grp.estruc_pres.proyecto','Proyecto'),
        'odg_id': fields.many2one('grp.estruc_pres.odg','ODG'),
        'auxiliar_id': fields.many2one('grp.estruc_pres.aux','AUX'),
        'moneda_id': fields.many2one('grp.estruc_pres.moneda','MON'),
        'tipo_credito': fields.many2one('grp.estruc_pres.tc','TC'),
        'descripcion': fields.char(u'Descripción'),
        'account_id': fields.many2one('account.account', 'Cuenta contable'),
        # 'cuenta_contable_id': fields.many2one('account.account', 'Cuenta contable'),
    }

    #cambio en la query 18/11
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'grp_vista_tree_llavep_cc')
        cr.execute("""
            CREATE OR REPLACE VIEW grp_vista_tree_llavep_cc AS (
            SELECT DISTINCT row_number() over() as id, rel.account_id,rel.relacion_id, l.name as presupuesto_id, p.fiscal_year, l.inciso_siif_id, l.ue_siif_id,
                l.fin_id as financiamiento_id, l.programa_id, l.proyecto_id, l.odg_id, l.auxiliar_id,
                l.mon_id as moneda_id, l.tc_id as tipo_credito, l.descripcion
                 from account_account_llavep_rel rel
                inner join grp_relacion_llave_contable l on rel.relacion_id = l.id
                inner join presupuesto_presupuesto p on p.id = l.name
                order by l.name asc)
          """)
grp_vista_tree_llavep_cc()
#002-Fin

class grp_concepto_gasto_cc_viaticos(osv.osv):
    _name = 'grp_concepto_gasto_cc_viaticos'
    _description='Conceptos de gastos a utilizar en caja chica y viaticos'

    # def onchange_fiscal_year(self, cr, uid, ids, fiscal_year, context=None):
    #     inciso_siif_id = False
    #     if fiscal_year:
    #         inciso_siif_ids = self.pool.get('grp.estruc_pres.inciso').search(cr, uid, [('fiscal_year_id', '=', fiscal_year)])
    #         if len(inciso_siif_ids) == 1:
    #             inciso_siif_id = inciso_siif_ids[0]
    #
    #         return {'value': {'inciso_siif_id': inciso_siif_id,
    #                           'ue_siif_id': False,
    #                           'fin_id': False,
    #                           'programa_id': False,
    #                           'proyecto_id': False,
    #                           'odg_id': False,
    #                           'auxiliar_id': False,
    #                           'mon_id': False,
    #                           'tc_id': False,
    #                           }}
    #
    # def onchange_inciso(self, cr, uid, ids, inciso_siif_id, context=None):
    #     ue_siif_id = False
    #     if inciso_siif_id:
    #         ue_siif_ids = self.pool.get('grp.estruc_pres.ue').search(cr, uid, [('inciso_id', '=', inciso_siif_id)])
    #         if len(ue_siif_ids) == 1:
    #             ue_siif_id = ue_siif_ids[0]
    #     return {'value': {
    #         'ue_siif_id': ue_siif_id,
    #         'odg_id': False,
    #         'auxiliar_id': False,
    #         'fin_id': False,
    #         'programa_id': False,
    #         'proyecto_id': False,
    #         'mon_id': False,
    #         'tc_id': False,
    #     }}
    #
    # def onchange_unidad_ejecutora(self, cr, uid, ids, ue_siif_id, context=None):
    #     odg_id = False
    #     if ue_siif_id:
    #         odg_ids = self.pool.get('grp.estruc_pres.odg').search(cr, uid, [('ue_id', '=', ue_siif_id)])
    #         if len(odg_ids) == 1:
    #             odg_id = odg_ids[0]
    #     return {'value': {
    #         'odg_id': odg_id,
    #         'auxiliar_id': False,
    #         'fin_id': False,
    #         'programa_id': False,
    #         'proyecto_id': False,
    #         'mon_id': False,
    #         'tc_id': False,
    #     }}
    #
    # def onchange_objeto_del_gasto(self, cr, uid, ids, odg_id, context=None):
    #     auxiliar_id = False
    #     if odg_id:
    #         auxiliar_ids = self.pool.get('grp.estruc_pres.aux').search(cr, uid, [('odg_id', '=', odg_id)])
    #         if len(auxiliar_ids) == 1:
    #             auxiliar_id = auxiliar_ids[0]
    #     return {'value': {
    #         'auxiliar_id': auxiliar_id,
    #         'fin_id': False,
    #         'programa_id': False,
    #         'proyecto_id': False,
    #         'mon_id': False,
    #         'tc_id': False,
    #     }}
    #
    # def onchange_auxiliar(self, cr, uid, ids, auxiliar_id, context=None):
    #     fin_id = False
    #     if auxiliar_id:
    #         fin_ids = self.pool.get('grp.estruc_pres.ff').search(cr, uid, [('aux_id', '=', auxiliar_id)])
    #         if len(fin_ids) == 1:
    #             fin_id = fin_ids[0]
    #     return {'value': {
    #         'fin_id': fin_id,
    #         'programa_id': False,
    #         'proyecto_id': False,
    #         'mon_id': False,
    #         'tc_id': False
    #     }}
    #
    # def onchange_fuente_de_financiamiento(self, cr, uid, ids, fin_id, context=None):
    #     programa_id = False
    #     if fin_id:
    #         programa_ids = self.pool.get('grp.estruc_pres.programa').search(cr, uid, [('ff_id', '=', fin_id)])
    #         if len(programa_ids) == 1:
    #             programa_id = programa_ids[0]
    #     return {'value': {
    #         'programa_id': programa_id,
    #         'proyecto_id': False,
    #         'mon_id': False,
    #         'tc_id': False,
    #     }}
    #
    # def onchange_programa(self, cr, uid, ids, programa_id, context=None):
    #     proyecto_id = False
    #     if programa_id:
    #         proyecto_ids = self.pool.get('grp.estruc_pres.proyecto').search(cr, uid,[('programa_id', '=', programa_id)])
    #         if len(proyecto_ids) == 1:
    #             proyecto_id = proyecto_ids[0]
    #     return {'value': {
    #         'proyecto_id': proyecto_id,
    #         'mon_id': False,
    #         'tc_id': False,
    #     }}
    #
    # def onchange_proyecto(self, cr, uid, ids, proyecto_id, context=None):
    #     mon_id = False
    #     if proyecto_id:
    #         mon_ids = self.pool.get('grp.estruc_pres.moneda').search(cr, uid, [('proyecto_id', '=', proyecto_id)])
    #         if len(mon_ids) == 1:
    #             mon_id = mon_ids[0]
    #     return {'value': {
    #         'mon_id': mon_id,
    #         'tc_id': False,
    #     }}
    #
    # def onchange_moneda(self, cr, uid, ids, mon_id, context=None):
    #     tc_id = False
    #     if mon_id:
    #         tc_ids = self.pool.get('grp.estruc_pres.tc').search(cr, uid, [('moneda_id', '=', mon_id)])
    #         if len(tc_ids) == 1:
    #             tc_id = tc_ids[0]
    #     return {'value': {
    #         'tc_id': tc_id
    #     }}

    def _check_concepto_sacar_dinero(self, cr, uid, ids, context=None):
        for concepto in self.browse(cr, uid, ids):
            sacar_dinero_ids= self.search(cr,uid,[('sacar_dinero','=',True)])
            if len(sacar_dinero_ids) >1:
                return False
        return True

    def _check_concepto_poner_dinero(self, cr, uid, ids, context=None):
        for concepto in self.browse(cr, uid, ids):
            poner_dinero_ids= self.search(cr,uid,[('poner_dinero','=',True)])
            if len(poner_dinero_ids) >1:
                return False
        return True

    def _check_concepto_perdida_diferencia(self, cr, uid, ids, context=None):
        for concepto in self.browse(cr, uid, ids):
            perdida_diferencia_ids= self.search(cr,uid,[('perdida_diferencia','=',True)])
            if len(perdida_diferencia_ids) >1:
                return False
        return True

    def _check_concepto_ganancia_diferencia(self, cr, uid, ids, context=None):
        for concepto in self.browse(cr, uid, ids):
            ganancia_diferencia_ids= self.search(cr,uid,[('ganancia_diferencia','=',True)])
            if len(ganancia_diferencia_ids) >1:
                return False
        return True

    def _check_concepto_a_rendir(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.a_rendir and rec.signo != 'neg':
                return False
        return True

    def buscar_partner_ids(self, cr, uid, ids, name, args, context=None):
        result = {}
        partner_domain_ids = []
        part_ids = self.pool.get('res.partner').search(cr, uid,[('es_inciso_default','=',True)], context=context)
        if part_ids:
            for id_p in part_ids:
                partner_domain_ids.append(id_p)
        for rec in self.browse(cr,uid,ids):
            pid = rec.partner_id and rec.partner_id.id
            if pid:
                partner_domain_ids.append(pid)
            if partner_domain_ids:
                result[rec.id]= partner_domain_ids
        return result

    _columns={
        'name': fields.char('Concepto', size=64),
        'active': fields.boolean('Activo', default=True),
        'caja_chica': fields.boolean('Caja chica'),
        'viaticos': fields.boolean(u'Vales'),
        'a_rendir': fields.boolean('A rendir'),
        'fiscal_year': fields.many2one('account.fiscalyear', 'Ejercicio fiscal'),
        # 'inciso_siif_id': fields.many2one('grp.estruc_pres.inciso', 'Inciso'),
        # 'ue_siif_id': fields.many2one('grp.estruc_pres.ue', 'Unidad ejecutora'),
        # llave presupuestal
        # 'fin_id' : fields.many2one ('grp.estruc_pres.ff', 'Fin'),
        # 'programa_id' : fields.many2one ('grp.estruc_pres.programa', 'Programa'),
        # 'proyecto_id' : fields.many2one ('grp.estruc_pres.proyecto', 'Proyecto'),
        # 'odg_id' : fields.many2one ('grp.estruc_pres.odg', 'ODG'),
        # 'auxiliar_id' : fields.many2one ('grp.estruc_pres.aux', 'Auxiliar'),
        # 'mon_id' : fields.many2one ('grp.estruc_pres.moneda', 'Mon'),
        # 'tc_id' : fields.many2one ('grp.estruc_pres.tc', 'TC'),
        # 'fin_id' : fields.many2one ('grp.estruc_pres.ff', 'Fin'),
        'programa_id' : fields.char('Programa'),
        'proyecto_id' : fields.char('Proyecto'),
        'odg_id' : fields.char('ODG'),
        'auxiliar_id' : fields.char('Auxiliar'),
        'mon_id' : fields.char('Mon'),
        'tc_id' : fields.char('TC'),
        'fin': fields.char('FIN'),
        'descripcion': fields.char(u'Descripción'),
        'siif_tipo_ejecucion':fields.many2one('tipo.ejecucion.siif', u'Tipo de ejecución SIIF'),
        'siif_concepto_gasto':fields.many2one('presupuesto.concepto', 'Concepto de gasto SIIF'),
        'siif_financiamiento': fields.many2one('financiamiento.siif', 'Financiamiento SIIF'),
        'siif_codigo_sir': fields.many2one('codigo.sir.siif',u'Código SIR SIIF'),
        'siif_tipo_documento': fields.many2one('tipo.documento.siif', 'Tipo documento SIIF'),
        'cuenta_id': fields.many2one('account.account','Cuenta'),
        'partner_id': fields.many2one('res.partner', 'Empresa'),
        'poner_dinero':fields.boolean('Poner dinero'),
        'sacar_dinero': fields.boolean('Sacar dinero'),
        'perdida_diferencia': fields.boolean(u'Pérdida por diferencia'),
        'ganancia_diferencia': fields.boolean(u'Ganancia por diferencia'),
        'beneficiario_siif':fields.many2one('res.partner', string=u'Beneficiario SIIF', change_default=True, track_visibility='always'),
        'domain_beneficiario_ids': fields.function(buscar_partner_ids, method=True, type='many2many', relation='res.partner', string='Lista domain partners'),
        # 007-Inicio
        'otros': fields.boolean('Otros'),
        'signo': fields.selection([
            ('pos', u'Positivo'),
            ('neg', u'Negativo'),
            ], string=u'Signo'),
        # 007-Fin
        'caja_recaudadora': fields.boolean(u'Caja recaudadora'),  # TODO: SPRING 10 GAP 474 M
        'caja_chica_t': fields.boolean(u'Caja chica Tesorería'),  # TODO: SPRING 10 GAP 474 M
        'opi': fields.boolean(u'OPI'),  # TODO: SPRING 10 GAP 474 M
        'ajuste_caja': fields.boolean(u'Ajuste revisión caja'),  # TODO: SPRING 11 GAP 292 M
        'devolucion_vc': fields.boolean(u'Devolución VC', default=False),  # TODO: M SPRING 11 GAP 474
        #'ingreso_vc': fields.boolean(u'Ingreso VC', default=False),   TODO: M SPRING 11 GAP 292
    }

    _constraints = [(_check_concepto_perdida_diferencia,u'Sólo puede existir un concepto de pérdida',['perdida_diferencia']),
                    (_check_concepto_ganancia_diferencia,u'Sólo puede existir un concepto de ganancia',['ganancia_diferencia']),
                    (_check_concepto_poner_dinero,u'Sólo puede existir un concepto de poner dinero',['poner_dinero']),
                    (_check_concepto_sacar_dinero,u'Sólo puede existir un concepto de sacar dinero',['sacar_dinero']),
                    (_check_concepto_a_rendir,u'Si el concepto está marcado "A rendir" el signo debe ser negativo.',['a_rendir','signo']),

        ]

    # TODO: SPRING 10 GAP 474 M
    _default = {
        'caja_recaudadora': False,
        'caja_chica_t': False,
        'opi': False,
    }

    @api.onchange('a_rendir')
    def _onchange_a_rendir(self):
        if self.a_rendir:
            self.signo = 'neg'

    @api.constrains('fiscal_year', 'odg_id', 'auxiliar_id', 'programa_id',
                    'proyecto_id', 'mon_id', 'tc_id','fin','a_rendir')
    def check_combinacion_llave(self):
        for rec in self:
            if rec.a_rendir:
                search_objs = self.env['presupuesto.linea'].search([
                    ('budget_fiscal_year', '=', rec.fiscal_year.id),
                    ('objeto_gasto', '=', rec.odg_id),
                    ('auxiliar', '=', rec.auxiliar_id),
                    ('programa', '=', rec.programa_id),
                    ('proyecto', '=', rec.proyecto_id),
                    ('moneda', '=', rec.mon_id),
                    ('tipo_credito', '=', rec.tc_id),
                    ('financiamiento', '=', rec.fin),
                ])
                if len(search_objs) == 0:
                    raise exceptions.ValidationError(u'No existe combinación de presupuesto para los datos ingresados.')
        return True

    # @api.multi
    # def name_get(self):
    #     res = []
    #     for value in self:
    #         # pasar por context la clave 'show_name_by_odg' en True si se quiere que muestre el odg
    #         if self._context.get('show_name_by_odg', False):
    #             res.append((value.id, value.odg_id and value.odg_id.odg or value.name))
    #         else:
    #             res.append((value.id, value.name))
    #     return res

grp_concepto_gasto_cc_viaticos()


class account_invoice_ext_api(models.Model):
    _inherit='grp_concepto_gasto_cc_viaticos'

    @api.multi
    def onchange_partner(self, partner_id):
        result = {
            'domain':{},
            'value': {
            'beneficiario_siif': False,
        }}
        domain = []
        part_ids = self.env['res.partner'].search([('es_inciso_default','=',True)])
        if part_ids:
            for idp in part_ids:
                domain.append(idp.id)
        if partner_id:
            domain.append(partner_id)
        if domain:
            result_add = {'beneficiario_siif':[('id','in',domain)]}
            result.update({'domain': result_add})
        return result

account_invoice_ext_api()

