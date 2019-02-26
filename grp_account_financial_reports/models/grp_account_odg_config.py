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
from openerp.exceptions import ValidationError

class GrpAccountODGConfig(models.Model):
    _name = 'grp.account.odg.config'
    _description = 'Combinaciones Cuenta - ODGs'
    _rec_name = 'account_id'

    account_id = fields.Many2one('account.account', 'Cuenta contable', required=True)
    odg_ids = fields.Many2many('grp.estruc_pres.odg', 'grp_account_odg_config_odg_rel', 'config_id', 'odg_id', string='Objetos de Gasto', required=True)
    company_id = fields.Many2one('res.company', u'Compañía', required=True, default=lambda self: self.env['res.company']._company_default_get('account.account'))

    _sql_constraints = [
        ('unique_account', 'UNIQUE (account_id, company_id)', u'Ya existe una combinación con esta Cuenta contable.'),
    ]

    @api.one
    @api.constrains('odg_ids')
    def _check_odgs(self):
        if self.odg_ids:
            self.env.cr.execute("SELECT count(*) FROM grp_account_odg_config_odg_rel r WHERE r.odg_id in %s and r.config_id != %s AND r.config_id is not null", (tuple(self.odg_ids.ids), self.id))
            if self.env.cr.fetchone()[0]:
                raise ValidationError('Ya existe una combinación que contiene uno o varios objetos de gasto configurados en este registro.')


