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

from openerp import models, fields, api, exceptions
from openerp.tools.translate import _
import logging

_logger = logging.getLogger(__name__)


class GrpCombinacionesContables(models.Model):
    _name = "grp.combinaciones_contables"
    _description = u'Combinación con Cuentas Contables'
    _order = "cuenta_contable_id"

    name = fields.Char(string='Nombre', required=True, size=80)
    cuenta_contable_id = fields.Many2one('account.account', 'Cuenta contable', required=True)
    unidad_organizativa_ids = fields.Many2many('hr.department', 'hr_department_comb_cont_rel', 'comb_cont_id',
                                               'hr_department_id', string='Unidad organizativa')
    cuenta_analitica_ids = fields.Many2many('account.analytic.account', 'account_analytic_account_comb_cont_rel',
                                            'comb_cont_id', 'account_analytic_account_id', u'Cuenta analítica')
    dimension_multiproposito_ids = fields.Many2many('grp.dimension_multiproposito',
                                                    'grp_dimen_multiproposito_comb_cont_rel', 'comb_cont_id',
                                                    'grp_dimen_multiproposito_id', string=u'Multipropósito')
    active = fields.Boolean(string='Activo', default=True)

    @api.constrains('cuenta_contable_id', 'unidad_organizativa_ids', 'cuenta_analitica_ids', 'dimension_multiproposito_ids')
    def _check_combinacion(self):
        for cuenta in self:
            if not cuenta.cuenta_contable_id:
                raise exceptions.ValidationError(_(u'Debe ingresar la cuenta contable.'))
            elif not cuenta.unidad_organizativa_ids:
                raise exceptions.ValidationError(_(u'Debe ingresar al menos una Unidad organizativa.'))
            elif not cuenta.cuenta_analitica_ids:
                raise exceptions.ValidationError(_(u'Debe ingresar al menos una Cuenta analítica.'))
            elif not cuenta.dimension_multiproposito_ids:
                raise exceptions.ValidationError(_(u'Debe ingresar al menos una Multipropósito.'))

            query = '''
                SELECT count(*)
                FROM grp_combinaciones_contables comb, hr_department_comb_cont_rel rel, account_analytic_account_comb_cont_rel acre, grp_dimen_multiproposito_comb_cont_rel multire
                WHERE comb.id = rel.comb_cont_id AND comb.id =acre.comb_cont_id AND comb.id =multire.comb_cont_id
                AND comb.active = true AND comb.cuenta_contable_id = %s
                group by comb.cuenta_contable_id, rel.hr_department_id, acre.account_analytic_account_id, multire.grp_dimen_multiproposito_id
                order by count(*) desc
                limit 1
            '''

            self._cr.execute(query, (cuenta.cuenta_contable_id.id,))
            cant = self._cr.fetchone()[0] or 0
            if cant > 1:
                raise exceptions.ValidationError(_(u'Ya hiciste un registro para alguna de las combinaciones ingresadas.'))


    @api.model
    def combinacion_valida(self, cuenta_contable, unidad_organizativa, cuenta_analitica, dimension_multiproposito):
        valida = False

        if not cuenta_contable:
            raise exceptions.ValidationError(_(u'Falta Cuenta contable.'))

        self._cr.execute(
            "SELECT count(comb.id) FROM grp_combinaciones_contables comb WHERE comb.cuenta_contable_id = %s ",
            (cuenta_contable,))
        exist = self._cr.fetchone()[0] or 0
        if exist > 0:
            if not unidad_organizativa or not cuenta_analitica or not dimension_multiproposito:
                raise exceptions.ValidationError(_(u'Faltan parámetros para validar la combinación.'))

            query = "SELECT count(comb.id)" \
                    "FROM grp_combinaciones_contables comb, hr_department_comb_cont_rel rel," \
                    "account_analytic_account_comb_cont_rel acre,grp_dimen_multiproposito_comb_cont_rel multire " \
                    "WHERE  comb.id = rel.comb_cont_id AND comb.id =acre.comb_cont_id AND comb.id =multire.comb_cont_id " \
                    "AND comb.cuenta_contable_id = %s AND hr_department_id = %s AND acre.account_analytic_account_id  = %s" \
                    "AND multire.grp_dimen_multiproposito_id = %s "

            self._cr.execute(query, (cuenta_contable, unidad_organizativa, cuenta_analitica, dimension_multiproposito))
            cant = self._cr.fetchone()[0] or 0

            if cant > 0:
                valida = True
        else:
            valida = True

        return valida
