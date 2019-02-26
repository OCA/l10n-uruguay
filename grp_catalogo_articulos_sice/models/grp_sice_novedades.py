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

def servicio_novedades_sice2grp(self, cr, uid, ids=None, context=None):
    # La tarea planificada
    tarea = {}
    tarea['name'] = 'Servicio Novedades SICE-GRP'
    tarea['model'] = 'grp.art.serv.obra'
    tarea['function'] = 'copiar_novedades_sice2grp'
    tarea['args'] = '()'
    tarea['interval_number'] = '1'
    tarea['interval_type'] = 'days'
    tarea['numbercall'] = -1
    tarea['doall'] = False
    tarea['active'] = False

    cr.execute("select id from ir_cron where name = %(name)s", {'name': tarea['name']})
    if not cr.rowcount:
        self.pool.get('ir.cron').create(cr, uid, tarea, context=context)
