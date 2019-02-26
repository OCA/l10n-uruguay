# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Enterprise Management Solution
#    GRP Estado Uruguay
#    Copyright (C) 2018 ATOS Uruguay
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

from openerp import fields as fields_new, models, api, _
from openerp.osv import osv, fields, orm
from openerp.exceptions import Warning
import logging

from ..library import validaciones_contra_pep_operations as validacion_ops

_logger = logging.getLogger(__name__)

class account_invoice_extention_api_nueva(models.Model):
    _inherit = "account.invoice"

    @api.multi
    @api.depends('factura_original')
    def _domain_conceptos_domain(self):
        _logger.info('Se carga el Dominio para el Concepto')
        print 'Se carga el Dominio para el Concepto'

        return validacion_ops.obtener_conceptos_del_plan_activo(self)


    concepto_id = fields_new.Many2one('grp.pep.concepto', string=u"Concepto de Ejecución Presupuestal", store=True, domain=_domain_conceptos_domain)
    concepto_de_modificacion_id = fields_new.Many2one('grp.pep.concepto', string=u"Concepto de Ejecución Presupuestal", store=True, compute='compute_concepto_de_modificacion_id')
    ver_campos_pep = fields_new.Boolean(string=u"Ver campos PEP?", default=False, compute='compute_ver_campos_pep')


    def continuar_envio_a_siif(self):
        _logger.info('### Acciones que llaman a SIIF ###')
        print '### Acciones que llaman a SIIF ###'

        resultado_siif = False
        es_factura_fondo_rotatorio = self.nro_factura_grp and 'Factura' in self.nro_factura_grp

        if es_factura_fondo_rotatorio:  
            resultado_siif = self.signal_workflow('invoice_open')
        else:
            resultado_siif = self.btn_obligar()

        if resultado_siif:
            codigo_identificador_documento = self.nro_factura_grp if not self.factura_original else self.factura_original.nro_factura_grp
            validacion_ops.ejecutar_pep_para_proceso_origen(self, codigo_identificador_documento, validacion_ops.PROCESO_ORIGEN_3EN1)


    @api.multi
    @api.depends('factura_original')
    def compute_concepto_de_modificacion_id(self):
        _logger.info('Se carga el Concepto en le Concepto del Modificacion.')
        print 'Se carga el Concepto en le Concepto del Modificacion.'

        for record in self:
            mi_factura_original = record.factura_original

            if mi_factura_original and not record.concepto_de_modificacion_id:
                concepto_origen = mi_factura_original.concepto_id
                record.concepto_de_modificacion_id = concepto_origen.id

            if record.concepto_de_modificacion_id:
                _logger.info('Se cargan las Llaves del Concepto en la Tabla')
                print 'Se cargan las Llaves del Concepto en la Tabla'

                record.llpapg_ids = validacion_ops.obtener_llaves_a_mostrar_en_la_tabla(record)

    @api.multi
    @api.depends('doc_type', 'factura_original')
    def compute_ver_campos_pep(self):
        _logger.info('Se valida si mostrar los campos para PEP')
        print 'Se valida si mostrar los campos para PEP'
  
        for record in self:
            mi_factura_original = record.factura_original

            es_documento_3en1 = record.doc_type == '3en1_invoice'
            es_factura_original_3en1 = '3en1' in mi_factura_original
            es_documento_fondo_rotatorio = record.siif_tipo_ejecucion.codigo == 'P'

            if es_documento_3en1 or es_factura_original_3en1 or es_documento_fondo_rotatorio:
                record.ver_campos_pep = True

    @api.multi
    @api.onchange('concepto_id')
    def onchange_concepto_id(self):
        _logger.info('Se cargan las Llaves del Concepto en la Tabla')
        print 'Se cargan las Llaves del Concepto en la Tabla'

        for record in self:
            record.llpapg_ids = validacion_ops.obtener_llaves_a_mostrar_en_la_tabla(record)

account_invoice_extention_api_nueva()

class account_invoice_extention(osv.osv):
    _inherit = "account.invoice"

    def validar_contra_pep(self, cr, uid, ids, context=None):
        _logger.info('### Validando contra PEP ###')
        print '### Validando contra PEP ###'

        for record in self.browse(cr, uid, ids):
            return validacion_ops.realizar_validacion_contra_pep(record)

    def cancelar_ejecucion_pep(self, cr, uid, ids,context=None):
        _logger.info('### Cancelar Ejecucion PEP ###')
        print '### Cancelar Ejecucion PEP ###'

        for record in self.browse(cr, uid, ids):
            if record.state != 'open':
                raise Warning('No se puede Borrar la obligación si no esta en estado Abierto')

            resultado_siif = False
            es_factura_fondo_rotatorio = record.nro_factura_grp and 'Factura' in record.nro_factura_grp

            if es_factura_fondo_rotatorio:
                resultado_siif = record.signal_workflow('invoice_cancel')
            else:
                resultado_siif = record.btn_borrar_obligacion()

            if resultado_siif:
                codigo_identificador_documento = record.nro_factura_grp if not record.factura_original else record.factura_original.nro_factura_grp
                validacion_ops.realizar_cancelacion_de_pep(record, codigo_identificador_documento, validacion_ops.PROCESO_ORIGEN_3EN1)

account_invoice_extention()
