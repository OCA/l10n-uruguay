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

from openerp import fields, models, api
from openerp import tools
from openerp.exceptions import ValidationError
import logging
import openerp.addons.decimal_precision as dp
from lxml import etree

class grp_control_credito_fondo_rotarios(models.Model):
    _name = 'grp.control.credito.fondo.rotarios'
    _auto = False

    nro_afectacion = fields.Integer(u'Nro Afectación')
    date_invoice = fields.Date('Fecha')
    siif_descripcion = fields.Text(u"Descripción SIIF", size=100)
    ue_siif_id = fields.Many2one('grp.estruc_pres.ue', 'Unidad ejecutora' )
    odg_id = fields.Many2one('grp.estruc_pres.odg', 'ODG', required=True)
    auxiliar_id = fields.Many2one('grp.estruc_pres.aux', 'Auxiliar', required=True, default=False)
    fin_id =  fields.Many2one('grp.estruc_pres.ff', 'Fin')
    programa_id = fields.Many2one('grp.estruc_pres.programa', 'Programa')
    proyecto_id = fields.Many2one('grp.estruc_pres.proyecto', 'Proyecto')
    mon_id =fields.Many2one('grp.estruc_pres.moneda', 'Mon')
    tc_id = fields.Many2one('grp.estruc_pres.tc', 'TC')
    importe = fields.Integer('Importe')
    procesado = fields.Boolean(string='Procesado')
    fecha_procesado = fields.Date('Fecha Procesado')
    fr_id = fields.Integer('Id FR')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'grp_control_credito_fondo_rotarios')
        cr.execute("""
            create or replace view grp_control_credito_fondo_rotarios as (
                select
                    frl.id,
                    fr.nro_afectacion,
                    fr.date_invoice,
                    fr.siif_descripcion,
                    fr.ue_siif_llp_id as ue_siif_id,
                    frl.odg_id,
                    frl.auxiliar_id,
                    frl.fin_id,
                    frl.programa_id,
                    frl.proyecto_id,
                    frl.mon_id,
                    frl.tc_id,
                    frl.importe,
                    fr.procesado,
                    fr.fecha_procesado,
                    fr.id as fr_id
                from
                    grp_fondo_rotatorio fr
                    left join grp_fondo_rotatorio_llavep frl on (frl.fondo_rotatorios_llp_id = fr.id)
                    where fr.state in ('obligado', 'intervenido', 'priorizado', 'pagado')
            )
        """)

    @api.multi
    def write(self, vals):
        fondo_rotatorio_obj =  self.env['grp.fondo.rotatorio']
        control_credito_obj =  self.pool.get('grp.control.credito.fondo.rotarios')
        for line in self:
            fondo_rotatorio = fondo_rotatorio_obj.search([('id', '=', line.fr_id)])[0]
            if fondo_rotatorio:
                if vals.get('procesado', False) and vals.get('fecha_procesado', False):
                    fondo_rotatorio.write({'procesado': vals.get('procesado'), 'fecha_procesado': vals.get('fecha_procesado')})
                else:
                    if vals.get('procesado', False):
                        fondo_rotatorio.write({'procesado': vals.get('procesado')})
                    if vals.get('fecha_procesado', False):
                        fondo_rotatorio.write({'fecha_procesado': vals.get('fecha_procesado')})
        control_credito_obj.init(self._cr)
        return True
