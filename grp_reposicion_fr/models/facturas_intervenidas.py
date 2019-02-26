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

from openerp import models, fields, api

class grp_integracion_intervenidas(models.Model):
    _inherit = 'grp.integracion.intervenidas'

    # columns
    fondo_rot_grp_id = fields.Many2one('grp.fondo.rotatorio', 'Fondo Rotatorio')

    @api.model
    def success_fondo_intervened(self, vals, fondo, intervenida):
        if fondo.siif_tipo_ejecucion.codigo == 'P':
            if fondo.state == 'obligado':
                vals['state'] = 'processed'
                vals['resultado'] = 'Procesada'
                fondo.write({'state': 'intervenido'})
            else:
                vals['state'] = 'error'
                estado = dict(self.env['grp.fondo.rotatorio'].fields_get(allfields=['state'])['state']['selection'])[fondo.state]
                vals['resultado'] = 'El documento debe estar en estado Obligado. El estado es: %s' % (estado,)
        else:
            if fondo.state in ['obligado','confirmado']:
                vals['state'] = 'processed'
                vals['resultado'] = 'Procesada'
                fondo.write({'state': 'intervenido'})
            else:
                vals['state'] = 'error'
                estado = dict(self.env['grp.fondo.rotatorio'].fields_get(allfields=['state'])['state']['selection'])[fondo.state]
                vals['resultado'] = 'El documento debe estar en estado Obligado o Abierto. El estado es: %s' % (estado,)
        self.create(vals)

    @api.model
    def failed_fondo_intervened(self, vals, intervenida):
        vals['state'] = 'error'
        vals['resultado'] = u'No se encontró factura en GRP correspondiente a este registro'
        self.create(vals)

    @api.model
    def failed_intervened(self, vals, intervenida):
        #Si llega a esta función es porque pasó por grp_factura_siif>Intervenidas > factura > clearing... sin obtener resultados
        condiciones_fondo = []
        condiciones_fondo.append(('nro_afectacion', '=', intervenida.nroDocAfectacion))
        condiciones_fondo.append(('nro_compromiso', '=', intervenida.nroDocCompromiso))
        condiciones_fondo.append(('nro_obligacion', '=', intervenida.nroDocObligacion))
        condiciones_fondo.append(('fiscal_year_id.code', '=', str(intervenida.anioFiscal)))
        condiciones_fondo.append(('ue_siif_llp_id.ue', '=', str(intervenida.unidadEjecutora).zfill(3)))
        condiciones_fondo.append(('inciso_siif_llp_id.inciso', '=', str(intervenida.inciso).zfill(2)))


        fondo = self.env['grp.fondo.rotatorio'].search(condiciones_fondo, limit=1)
        if fondo:
            vals['fondo_rot_grp_id'] = fondo.id
            self.success_fondo_intervened(vals, fondo, intervenida)
        else:
            self.failed_fondo_intervened(vals, intervenida)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
