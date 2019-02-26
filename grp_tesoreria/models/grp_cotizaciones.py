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

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
from openerp.osv import osv

class grp_cotizaciones(models.Model):
    _inherit = 'grp.cotizaciones'

    requiere_presentacion_garantia = fields.Boolean(string=u'Requiere presentación de garantía', default=False)

    def action_cotizaciones_send_email(self, cr, uid, ids, context=None):
        data = self.pool.get('ir.model.data')
        context = context or {}
        local_context = context.copy()
        template = data.get_object(cr,uid,'grp_tesoreria', 'grp_cotizaciones_alert_mail')
        _model, group_id = data.get_object_reference(cr, uid, 'grp_tesoreria', 'group_grp_tesoreria')
        r = self.browse(cr, uid, ids[0], context=context)
        users = self.pool.get('res.users').search(cr, uid, [('groups_id', 'in', group_id),('operating_unit_ids','in',r.operating_unit_id.id)])
        if users:
            for user in self.pool.get('res.users').browse(cr, uid, users, context=context):
                local_context['partner'] = user.partner_id
                self.pool.get('email.template').send_mail(cr, uid, template.id, ids[0], force_send=True,
                                                     raise_exception=False, context=local_context)

    def act_cot_aprobar_sice(self, cr, uid, ids, context=None):
        super(grp_cotizaciones, self).act_cot_aprobar_sice(cr, uid, ids, context=context)
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
                   u"Número de adjudicación (%s)." % (number)
            context = dict(context)
            context.update({'mail_notify_noemail': True})
            self.pool['mail.thread'].message_post(cr, uid, 0, body=body, subject='Inicio de procedimiento de compra', partner_ids=partner_ids, context=context, subtype='mail.mt_comment')
            self.action_cotizaciones_send_email(cr, uid, ids)
        return True

    @api.multi
    def cotizaciones_authorized(self):
        for rec in self:
            if rec.requiere_presentacion_garantia:
                model, group_id = self.env['ir.model.data'].get_object_reference('grp_tesoreria',
                                                                                 'group_grp_tesoreria')
                users = self.env['res.users'].search([('groups_id', 'in', group_id),('operating_unit_ids','in',rec.operating_unit_id.id)])
                partner_ids = []

                if users:
                    partner_ids = [user.partner_id.id for user in users]

                for proveedor in self.sice_page_aceptadas:
                    prov = proveedor.proveedor_cot_id or ''
                    msg = _(
                        """Es necesario que el proveedor %s presente una garantía para el procedimiento de compra <a href="#action=mail.action_mail_redirect&amp;model=grp.pedido.compra&amp;res_id=%s">%s<a/>.""") % (
                              prov.name, rec.pedido_compra_id.id, rec.pedido_compra_id.name)

                    self.pool.get('mail.thread').message_post(self._cr, self._uid, self.id, type="notification",
                                                              subtype='mt_comment', body=msg,
                                                              partner_ids=partner_ids)

        return super(grp_cotizaciones, self).cotizaciones_authorized()