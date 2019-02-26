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

class grp_integracion_pagas_totalmente(models.Model):
    _inherit = 'grp.integracion.pagas_totalmente'

    # columns
    fondo_rot_grp_id = fields.Many2one('grp.fondo.rotatorio', 'Fondo Rotatorio')

    @api.model
    def success_fondo_paga(self, vals, fondo, paga):
        config_fondo_rotatorio_obj = self.env['config.recuperacion.fondo.rotatorio']
        config_fondo_rotatorio = config_fondo_rotatorio_obj.search([('unidad_ejecutora_id', '=', fondo.operating_unit_id.id)], limit=1)
        if fondo.state == 'pagado':
            vals['state'] = 'error'
            vals['resultado'] = 'El documento %s ya se encuentra en estado Pago.' % (fondo.name,)
        elif config_fondo_rotatorio:
            period = self.env['account.period'].find(dt=vals['fecha_enviado'])
            referencia = u'Recuperación FR. Afec. %s, Comp. %s, Oblg. %s' % (paga.nroDocAfectacion, paga.nroDocCompromiso, paga.nroDocObligacion)
            recuperacion_move = self.env['account.move'].create(
                {
                'ref': referencia,
                'period_id': period[0].id,
                'operating_unit_id': config_fondo_rotatorio.unidad_ejecutora_id.id,
                'journal_id': config_fondo_rotatorio.journal_id.id,
                'date': vals['fecha_enviado'],
                'line_id': [(0, 0, {
                    'name': referencia,
                    'operating_unit_id': config_fondo_rotatorio.unidad_ejecutora_id.id,
                    'account_id': config_fondo_rotatorio.journal_id.default_debit_account_id.id,
                    'debit': fondo.liquido_pagable,
                }), (0, 0, {
                    'name': referencia,
                    'operating_unit_id': config_fondo_rotatorio.unidad_ejecutora_id.id,
                    'account_id': config_fondo_rotatorio.cuenta_credito_id.id,
                    'credit': fondo.liquido_pagable,
                })]
            })
            vals['state'] = 'processed'
            vals['resultado'] = 'Procesada'
            fondo.write({'state': 'pagado', 'recuperacion_move_id': recuperacion_move.id})
        else:
            vals['state'] = 'error'
            vals['resultado'] = 'Error de configuración, debe configurar la recuperación de fondo rotatorio para la unidad ejecutora %s' % (fondo.operating_unit_id.name,)
        self.create(vals)

    # @api.model
    # def failed_fondo_paga(self, vals, paga):
    #     vals['state'] = 'error'
    #     vals['resultado'] = u'No se encontró factura en GRP correspondiente a este registro'
    #     self.create(vals)

    @api.model
    def failed_paga(self, vals, paga):
        #Si llega a esta función es porque pasó por grp_factura_siif > Pagas Totalmenmte > factura > clearing... sin obtener resultados
        condiciones_fondo = []
        condiciones_fondo.append(('nro_afectacion', '=', paga.nroDocAfectacion))
        condiciones_fondo.append(('nro_compromiso', '=', paga.nroDocCompromiso))
        condiciones_fondo.append(('nro_obligacion', '=', paga.nroDocObligacion))
        condiciones_fondo.append(('fiscal_year_id.code', '=', str(paga.anioFiscal)))
        condiciones_fondo.append(('ue_siif_llp_id.ue', '=', str(paga.unidadEjecutadora).zfill(3)))
        condiciones_fondo.append(('inciso_siif_llp_id.inciso', '=', str(paga.inciso).zfill(2)))


        fondo = self.env['grp.fondo.rotatorio'].search(condiciones_fondo, limit=1)
        if fondo:
            vals['fondo_rot_grp_id'] = fondo.id
            self.success_fondo_paga(vals, fondo, paga)
        else:
            super(grp_integracion_pagas_totalmente,self).failed_paga(vals, paga)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
