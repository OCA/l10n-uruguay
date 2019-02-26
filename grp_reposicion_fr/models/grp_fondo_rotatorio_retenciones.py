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

import openerp.addons.decimal_precision as dp
from openerp import fields, models


class grp_fondo_rotarios_retencion(models.Model):
    _name = 'grp.fondo.rotarios.retencion'

    fr_id = fields.Many2one('grp.fondo.rotatorio', 'Fondo rotatorio', required=True, ondelete='cascade')
    creditor_id = fields.Many2one('account.retention.creditors', 'Acreedor', required=True)
    group_id = fields.Many2one('account.group.creditors', 'Grupo', required=True)
    tipo_retencion = fields.Selection([('siif', 'Siif'),
                                       ('manual', 'Manual')], 'Tipo de retención', required=True)
    iva = fields.Char('Retenciones', required=True)

    base_linea = fields.Float(string=u'Importe sin impuestos', digits=(16, 0), help=u'Base línea')
    base_linea_pesos = fields.Float(string=u'Importe sin impuestos en UYU', digits=(16, 0))
    base_impuesto = fields.Float(string=u'Impuesto', digits=(16, 0), help=u'Base Impuesto')
    base_impuesto_pesos = fields.Float(string=u'Impuesto en UYU', digits=(16, 0))
    monto_retencion = fields.Float(u'Monto retención', digits=(16, 0),
                                   help=u'Monto retención redondeado y calculado a partir de base impuesto sin redondear.')
    monto_retencion_unround = fields.Float(u'Monto retención', digits_compute=dp.get_precision('Account'),
                                           help=u'Monto retención sin redondear')
    monto_retencion_pesos = fields.Float(digits=(16, 0), string=u'Monto retención pesos')
    ret_amount_round = fields.Float(string=u'Retención redondeado ME', digits=(16, 0),
                                    help=u'Monto retención redondeado y calculado a partir de base impuesto redondeado.')
    ret_amount_pesos_round = fields.Float(string=u'Retención redondeado', digits=(16, 0),
                                          help=u'Monto retención pesos redondeado y calculado a partir de base impuesto redondeado')
    # campo para integracion siif, enlace
    retention_id = fields.Many2one('account.retention', string=u'Retención')
