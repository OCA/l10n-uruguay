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

class grp_pedido_compra(models.Model):
    _inherit = 'grp.pedido.compra'

    requiere_presentacion_garantia = fields.Boolean(string=u'Requiere presentación de garantía', default=False)

    def action_pedido_compra_send_email(self, cr, uid, ids, context=None):
        data = self.pool.get('ir.model.data')
        context = context or {}
        local_context = context.copy()
        template = data.get_object(cr,uid,'grp_tesoreria', 'grp_pedido_compra_alert_mail')
        _model, group_id = data.get_object_reference(cr, uid, 'grp_tesoreria', 'group_grp_tesoreria')
        r = self.browse(cr, uid, ids[0], context=context)
        users = self.pool.get('res.users').search(cr, uid, [('groups_id', 'in', group_id),('operating_unit_ids','in',r.operating_unit_id.id)])
        if users:
            for user in self.pool.get('res.users').browse(cr, uid, users, context=context):
                local_context['partner'] = user.partner_id
                self.pool.get('email.template').send_mail(cr, uid, template.id, ids[0], force_send=True,
                                                     raise_exception=False, context=local_context)

    def trans_pc_confirmado_sice(self, cr, uid, ids, context=None):
        r = self.browse(cr, uid, ids[0], context=context)
        if r.requiere_presentacion_garantia == True:
            env = api.Environment(cr, 1, {})
            ir_model_data = env['ir.model.data']
            _model, group_id = ir_model_data.get_object_reference('grp_tesoreria', 'group_grp_tesoreria')
            users = env['res.users'].search([('groups_id', 'in', group_id),('operating_unit_ids','in',r.operating_unit_id.id)])
            partner_ids = []
            number = r.name or ''
            if users:
                partner_ids = [user.partner_id.id for user in users]
            body = u"Se inició un procedimiento de compra que requiere presentación de garantía. \n\n" \
                   u"Número de pedido de compra (%s)." % (number)
            self.pool['mail.thread'].message_post(cr, uid, 0, body=body, subject='Inicio de procedimiento de compra', partner_ids=partner_ids, context=context, subtype='mail.mt_comment')
            self.action_pedido_compra_send_email(cr, uid, ids)
        return True

    def act_pc_sice(self, cr, uid, ids, context=None):
        super(grp_pedido_compra, self).act_pc_sice(cr, uid, ids, context=context)
        return self.trans_pc_confirmado_sice(cr, uid, ids, context=context)
