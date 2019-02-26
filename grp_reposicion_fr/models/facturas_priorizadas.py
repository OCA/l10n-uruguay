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

from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)


class grp_integracion_priorizadas(osv.osv):
    _inherit = 'grp.integracion.priorizadas'

    _columns = {
        'fondo_rotatorio_id': fields.many2one('grp.fondo.rotatorio', 'Fondo Rotatorio', readonly=True)
    }

    def success_fondo_prioritized(self, cr, uid, vals, fondo, priorizada, context=None):
        if fondo.state not in ['obligado','confirmado','intervenido']:
            vals['state'] = 'error'
            vals['resultado'] = 'El Fondo Rotatorio debe estar en estado Obligado, Abierto o Intervenido. El estado es: ' + fondo.state.capitalize()
        else:
            vals['state'] = 'processed'
            vals['resultado'] = 'Fondo Rotatorio procesado con un monto priorizado de %s.' % (str(priorizada.montoPriorizado),)
            self.pool.get('grp.fondo.rotatorio.prioritized.line').create(cr, uid, {
                'fondo_grp_id': fondo.id,
                'fecha_confirmado': priorizada.fechaConfirmado,
                'monto_priorizado': priorizada.montoPriorizado
            }, context=context)
            _amount = 0
            for inv_p in fondo.fondo_prioritized_line:
                _amount += inv_p.monto_priorizado
            if _amount > 0 and _amount >= fondo.liquido_pagable:
                vals['resultado'] = 'Fondo Rotatorio procesado con un monto priorizado de %s. Se pasa a Priorizado.' % (str(priorizada.montoPriorizado),)
                fondo.write({'state': 'priorizado'})
        #Create Log
        self.create(cr, uid, vals, context=context)

    def failed_prioritized(self, cr, uid, vals, priorizada, context=None):
        condiciones_fondo = []
        condiciones_fondo.append(('nro_afectacion', '=', priorizada.nroDocAfectacion))
        condiciones_fondo.append(('nro_compromiso', '=', priorizada.nroDocCompromiso))
        condiciones_fondo.append(('nro_obligacion', '=', priorizada.nroDocObligacion))
        condiciones_fondo.append(('fiscal_year_id.code', '=', str(priorizada.anioFiscal)))
        condiciones_fondo.append(('ue_siif_llp_id.ue', '=', str(priorizada.unidadEjecutora).zfill(3)))
        condiciones_fondo.append(('inciso_siif_llp_id.inciso', '=', str(priorizada.inciso).zfill(2)))

        fondo_obj = self.pool.get('grp.fondo.rotatorio')
        fondo_ids = fondo_obj.search(cr, uid, condiciones_fondo, context=context)
        if fondo_ids:
            vals['fondo_rotatorio_id'] = fondo_ids[0]
            fondo = fondo_obj.browse(cr, uid, fondo_ids[0], context=context)
            self.success_fondo_prioritized(cr, uid, vals, fondo, priorizada, context=context)
        else:
            super(grp_integracion_priorizadas, self).failed_prioritized(cr, uid, vals, priorizada, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
