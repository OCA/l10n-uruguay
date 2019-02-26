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

class grp_art_serv_busqueda(osv.osv):
    """Búsqueda de artículos del SICE"""

    def default_description(self, cr, uid, context=None):
        """La descripción de la búsqueda"""
        hoy   = datetime.now()
        fecha = "%02s/%02s/%s" % (hoy.day, hoy.month, hoy.year)
        hora  = "%02s:%02s" % (hoy.hour, hoy.minute)
        return "Seleccionados el %s a las %s" % (fecha, hora)

    _name = 'grp.sice_art_serv_busqueda'
    _columns = {
        'name': fields.char(string=u'Descripción', size=200, required=True),
        'cod': fields.integer(string=u'Código'),
        'descripcion': fields.char(string=u'Descripción', size=200),
        'fami_id': fields.many2one('grp.sice_familia','Familia'),
        'subf_id': fields.many2one('grp.sice_subflia','Sub Familia'),
        'clas_id': fields.many2one('grp.sice_clase','Clase'),
        'subc_id': fields.many2one('grp.sice_subclase','Sub Clase'),
        'odg': fields.char('ODG', size=200),
        'ind_art_serv': fields.selection((('A', u'Artículo'), ('S', 'Servicio'), ('O', 'Obra')), string='Tipo'),
        'articulo_ids': fields.one2many('grp.sice_art_serv_obra','search_id',u'Artículos'),
        # 'unme_cod': fields.char('Unidad', size=200),
        # 'descripcion': fields.char('Descripción', size=200),
    }

    _defaults = {
        'name': default_description,
    }

    def grp_art_buscar(self, cr, uid, ids, context=None):
        """Al disparar el boton de búsqueda se efectúa la consulta"""

        # El código del ODG apartir de la descricpión
        def get_odg_cod(cr,odg):
            cr.execute("select odg from grp_sice_odg where descripcion ilike %(odg)s",{'odg': odg})
            res = cr.fetchone()
            return int(res[0]) if res else 0

        # Construir la consulta
        condicion = ""
        datos = {}
        for record in self.browse(cr, uid, ids):
            if record.cod:
                condicion += "cod = %(cod)s"
                datos['cod'] = record.cod

            if record.descripcion:
                if condicion: condicion += " and "
                condicion += "descripcion ilike %(descripcion)s"
                datos['descripcion'] = record.descripcion

            if record.fami_id:
                if condicion: condicion += " and "
                condicion += "fami_id = %(fami_id)s"
                datos['fami_id'] = record.fami_id.id

            if record.subf_id:
                if condicion: condicion += " and "
                condicion += "subf_id = %(subf_id)s"
                datos['subf_id'] = record.subf_id.id

            if record.clas_id:
                if condicion: condicion += " and "
                condicion += "clas_id = %(clas_id)s"
                datos['clas_id'] = record.clas_id.id

            if record.subc_id:
                if condicion: condicion += " and "
                condicion += "subc_id = %(subc_id)s"
                datos['subc_id'] = record.subc_id.id

            if record.odg:
                if condicion: condicion += " and "
                condicion += "odg = %(odg)s"
                if record.odg.isdigit():
                    datos['odg'] = record.odg
                else:
                    datos['odg'] = get_odg_cod(cr, record.odg)

            if record.ind_art_serv:
                if condicion: condicion += " and "
                condicion += "ind_art_serv = %(ind_art_serv)s"
                datos['ind_art_serv'] = record.ind_art_serv

        # En caso de que no haya ningún valor ...
        if not condicion:
            raise osv.except_osv('Por favor', 'Ingrese al menos un criterio.')
            return False

        # La consulta
        consulta = "select id from grp_sice_art_serv_obra where " + condicion

        # Buscar
        cr.execute(consulta, datos)
        res = cr.fetchall()
        if cr.rowcount > 0:
            # Desvincular los artículos que haya de una consulta anterior
            self.write(cr, uid, ids, {'articulo_ids':[(5,)] }, context)

            # Grabar los nuevos vínculos con artículos
            art_list = []
            for an_art in res:
                art_list.append((4,an_art[0]))
            self.write(cr, uid, ids, {'articulo_ids': art_list}, context)
        else:
            raise osv.except_osv('No hay resultados', 'Intente otros valores.')

        # Retornar True para actualicar la vista o False si no hay resultados
        return cr.rowcount


    def onchange_familia(self, cr, uid, ids, fami_id, context=None):
        """Limpia la lista hija"""
        values = {}
        values['subf_id'] = None
        return {'value': values}

    def onchange_subfamilia(self, cr, uid, ids, subf_id, context=None):
        """Limpia la lista hija"""
        values = {}
        values['clas_id'] = None
        return {'value': values}

    def onchange_clase(self, cr, uid, ids, clas_id, context=None):
        """Limpia la lista hija"""
        values = {}
        values['subc_id'] = None
        return {'value': values}

grp_art_serv_busqueda()

