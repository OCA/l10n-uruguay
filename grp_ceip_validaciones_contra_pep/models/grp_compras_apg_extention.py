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

class grp_compras_apg_extention_api_nueva(models.Model):
    _inherit = "grp.compras.apg"

    def _cargar_conceptos_domain(self):
        return validacion_ops.obtener_conceptos_del_plan_activo(self)

    concepto_id = fields_new.Many2one('grp.pep.concepto', string=u"Concepto de Ejecución Presupuestal", domain=_cargar_conceptos_domain)

    def continuar_envio_a_siif(self):
        _logger.info('### Acciones que llaman a SIIF ###')
        print '### Acciones que llaman a SIIF ###'

        resultado_siif = self.act_apg_afectado()

        if resultado_siif:
            validacion_ops.ejecutar_pep_para_proceso_origen(self, self.name, validacion_ops.PROCESO_ORIGEN_APG)


    @api.multi
    @api.onchange('concepto_id')
    def onchange_concepto_id(self):
        _logger.info('Se cargan las Llaves del Concepto en la Tabla')
        print 'Se cargan las Llaves del Concepto en la Tabla'

        for record in self:
            record.llpapg_ids = validacion_ops.obtener_llaves_a_mostrar_en_la_tabla(record)

grp_compras_apg_extention_api_nueva()

class grp_compras_apg_extention(osv.osv):
    _inherit = "grp.compras.apg"

    def validar_contra_pep(self, cr, uid, ids, context=None):
        _logger.info('### Validando contra PEP ###')
        print '### Validando contra PEP ###'

        for record in self.browse(cr, uid, ids):
            return validacion_ops.realizar_validacion_contra_pep(record)

    def cancelar_ejecucion_pep(self, cr, uid, ids,context=None):
        _logger.info('### Cancelar Ejecucion PEP ###')
        print '### Cancelar Ejecucion PEP ###'

        for record in self.browse(cr, uid, ids):
            if record.state != 'afectado':
                raise Warning('No se puede Borrar la obligación si no esta en estado Abierto')

            resultado_siif = record.act_apg_desafectado()

            if resultado_siif:
                codigo_identificador_documento = record.name
                validacion_ops.realizar_cancelacion_de_pep(record, codigo_identificador_documento, validacion_ops.PROCESO_ORIGEN_APG)

    def abrir_wizard_modif_siif(self, cr, uid, ids, context=None):
        _logger.info('Se abre el Wizard de Nueva Modificacion en APG.')
        print 'Se abre el Wizard de Nueva Modificacion en APG.'

        for record in self.browse(cr, uid, ids):
            resultado = super(grp_compras_apg_extention, record).abrir_wizard_modif_siif()

            resultado['context'].update({
                'default_factura_original': record.id
            })

        return resultado

grp_compras_apg_extention()

class grp_compras_apg_wizard_extention_api_nueva(models.TransientModel):
    _inherit = "wiz.modificacion_apg_siif"

    factura_original = fields_new.Many2one('grp.compras.apg', string=u"Factura Original")

grp_compras_apg_wizard_extention_api_nueva()

class grp_compras_apg_wizard_extention(osv.osv_memory):
    _inherit = 'wiz.modificacion_apg_siif'

    def continuar_envio_a_siif(self, cr, uid, ids, context=None):
        _logger.info('### Acciones que llaman a SIIF ###')
        print '### Acciones que llaman a SIIF ###'

        for record in self.browse(cr, uid, ids):
            resultado_siif = record.send_modif()

            if resultado_siif:
                apg_origen = record.env['grp.compras.apg'].browse(record.apg_id)

                id_concepto = apg_origen.concepto_id.id
                inciso = apg_origen.inciso_siif_id
                unidad_ejecutora = apg_origen.ue_siif_id
                codigo_identificador_documento = apg_origen.name

                validacion_ops.ejecutar_pep_para_proceso_origen_en_modificacion(record, {
                    'id_concepto': id_concepto,
                    'inciso': inciso,
                    'unidad_ejecutora': unidad_ejecutora,
                    'llave_a_utilizar': record,
                    'codigo_identificador_documento': codigo_identificador_documento,
                    'proceso_origen': validacion_ops.PROCESO_ORIGEN_APG_MODIFICACION
                })

    def validar_contra_pep(self, cr, uid, ids, context=None):
        _logger.info('### Validando contra PEP ###')
        print '### Validando contra PEP ###'

        for record in self.browse(cr, uid, ids):
            apg_origen = record.env['grp.compras.apg'].browse(record.apg_id)

            id_concepto = apg_origen.concepto_id.id
            tiene_un_concepto_de_modificacion = 'concepto_de_modificacion_id' in apg_origen

            if tiene_un_concepto_de_modificacion:
                if apg_origen.concepto_de_modificacion_id:
                    id_concepto = apg_origen.concepto_de_modificacion_id.id

            inciso = apg_origen.inciso_siif_id
            unidad_ejecutora = apg_origen.ue_siif_id

            return validacion_ops.realizar_validacion_contra_pep_en_modificacion(record, id_concepto, inciso, unidad_ejecutora, record)

grp_compras_apg_wizard_extention()
