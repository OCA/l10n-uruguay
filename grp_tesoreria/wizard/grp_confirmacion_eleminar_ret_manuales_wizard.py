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

from openerp import fields, models, api, _
from openerp.exceptions import ValidationError
import logging
import openerp.addons.decimal_precision as dp
from lxml import etree

_logger = logging.getLogger(__name__)


class GrpConfirmacionEleminarRetManualesWizard(models.TransientModel):
    _name = 'grp.confirmacion.eleminar.ret.manuales.wizard'

    @api.multi
    def eliminar_lineas(self):
        if self._context.get('eliminar_lineas_retenciones_manuales_ids', False):
            eliminar_lineas_retenciones_manuales_ids = self._context.get('eliminar_lineas_retenciones_manuales_ids', False)
            lineas_retenciones_manuales_obj = self.env['grp.lineas.retenciones.manuales']
            invoice_lines = []
            retencion_manual = False
            lineas_retenciones_manuales_ids = eliminar_lineas_retenciones_manuales_ids
            invoice_lines += [x.invoice_ret_global_line_id.invoice_id for x in lineas_retenciones_manuales_obj.browse(eliminar_lineas_retenciones_manuales_ids)]
            for linea in lineas_retenciones_manuales_obj.browse(eliminar_lineas_retenciones_manuales_ids):
                retencion_manual = linea.retencion_manual_id
            for invoice in invoice_lines:
                if invoice.ret_sueldo == True:
                    invoice.write({'ret_sueldo':False})
            if retencion_manual:
                retencion_manual.with_context(eliminar_lineas_retenciones_manuales_ids=lineas_retenciones_manuales_ids).onchange_lineas_retenciones_manuales_ids()

                mod_obj = self.env['ir.model.data']
                res = mod_obj.get_object_reference('grp_tesoreria', 'view_form_grp_retenciones_manuales')
                res_id = res and res[1] or False
                value =  {
                    'name': "Retenciones de Sueldos de Habilitaciones",
                    'view_mode': 'form',
                    'view_id': res_id,
                    'view_type': 'form',
                    'res_model': 'grp.retenciones.manuales',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': retencion_manual.id,
                }
                return value
        return True

