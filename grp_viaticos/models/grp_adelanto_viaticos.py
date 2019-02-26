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

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class utec_adelanto_viaticos(osv.osv):
    _inherit = 'account.voucher'

    _columns = {
        'solicitud_viatico_id': fields.many2one('grp.solicitud.viaticos', string=u'Solicitud de viajes',
                                                domain=[('lleva_adelanto', '=', True), ('state', '=', 'autorizado')],
                                                readonly=True, states={'draft': [('readonly', False)]},
                                                ondelete='restrict', required=False),  # TODO: SPRING 11 GAP 28 L
        'moneda_solicitud': fields.related('solicitud_viatico_id', 'currency_id', type='many2one', relation='res.currency',
                                      string='Moneda de solicitud', readonly=True),
        'adelanto_solicitud': fields.related('solicitud_viatico_id', 'total_adelanto', type='float',
                                           string='Total adelanto', readonly=True),
    }

    def onchange_solicitud_viatico_id(self, cr, uid, ids, solicitud_viatico_id, context=None):
        value = {}
        if solicitud_viatico_id:
            solicitud = self.pool.get('grp.solicitud.viaticos').browse(cr, uid, solicitud_viatico_id, context=context)
            value.update({'moneda_solicitud': solicitud.currency_id.id, 'adelanto_solicitud': solicitud.total_adelanto})
        else:
            value.update({'moneda_solicitud': False, 'adelanto_solicitud': False})
        return {'value': value}

    def _check_montos(self, cr, uid, ids, context=None):
        for adelanto in self.browse(cr, uid, ids, context=context):
            # Si el voucher es un adelanto de viatico
            if adelanto.solicitud_viatico_id.id and adelanto.type == 'payment':  # TODO: SPRING 11 GAP 28 L
                #calculo la moneda del metodo de pago
                if adelanto.journal_id.currency.id:
                    moneda_diario = adelanto.journal_id.currency.id
                else:
                    moneda_diario = adelanto.journal_id.company_id.currency_id.id
                # Si la moneda de la solicitud es la misma que la del metodo de pago
                if adelanto.solicitud_viatico_id.currency_id.id == moneda_diario:
                    # Si los montos no coinciden
                    if round(adelanto.solicitud_viatico_id.total_adelanto,2) != adelanto.amount:
                        return False
        return True

    _constraints = [
        (_check_montos, 'Si la moneda de la solicitud es la misma que la del adelanto, los montos deben coincidir', ['amount','adelanto_solicitud'])
    ]

