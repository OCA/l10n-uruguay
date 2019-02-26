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

from openerp.osv import osv, fields
from lxml import etree
import openerp.exceptions
import datetime
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)
from openerp import tools, api

# 001-Inicio
class grp_valores_custodia(osv.osv):
    _name = "grp.valores_custodia"
    _inherit = ['mail.thread']
    _description = "Valores en custodia"

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'name': False
        })
        return super(grp_valores_custodia, self).copy(cr, uid, id, default, context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        valores = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []

        for t in valores:
            if t['state'] not in ('borrador'):
                raise openerp.exceptions.Warning(_('No puede eliminar un valor en custodia que no esté en borrador.'))
                return False
            else:
                unlink_ids.append(t['id'])

        osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        return True

    def _check_fechas(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.fecha_vencimiento >= obj.fecha:
                return True
        return False

    def get_fecha_entregado(self, cr, uid, ids, fieldname, args, context=None):
        res = {}
        for garantia in self.browse(cr, uid, ids, context=context):
            if garantia.state in 'entregado':
                fecha_id = self.pool.get('grp.fecha_entrega_garantia').search(cr, uid,
                                                                              [('garantia_id', '=', garantia.id)])
                if len(fecha_id) > 0:
                    for fecha in self.pool.get('grp.fecha_entrega_garantia').browse(cr, uid, fecha_id):
                        res[garantia.id] = fecha.name
        return res

    def _get_company_id(self, cr, uid, context=None):
        res = self.pool.get('res.users').read(cr, uid, [uid], ['company_id'], context=context)
        if res and res[0]['company_id']:
            return res[0]['company_id'][0]
        return False

    def _es_tesoreria(self, cr, uid, ids, name, arg, context=None):
        res = {}
        users_obj = self.pool.get('res.users')
        for rec in self.browse(cr, uid, ids, context=context):
            es_grupo_tesoreria = users_obj.has_group(cr, uid, 'grp_tesoreria.group_grp_tesoreria')
            res[rec.id] = es_grupo_tesoreria
        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(grp_valores_custodia, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
                                                                context=context,
                                                                toolbar=toolbar, submenu=submenu)
        model_data_obj = self.pool.get('ir.model.data')
        pc_obj = self.pool.get('grp.pedido.compra')
        # tipo_compra_obj = self.pool.get('sicec.tipo.compra')

        # domain_ids = []
        # pc_ids = []

        # if len(tipo_compra_abreviada_id) > 0:
        #     for id_p in tipo_compra_abreviada_id:
        #         domain_ids.append(id_p)
        #
        # if len(tipo_compra_publica_id) > 0:
        #     for id_p in tipo_compra_publica_id:
        #         domain_ids.append(id_p)  # tipo_compra_abreviada_id = tipo_compra_obj.search(cr, uid, [('idTipoCompra', '=', 'LA')])
        # # tipo_compra_publica_id = tipo_compra_obj.search(cr, uid, [('idTipoCompra', '=', 'LP')])
        #
        #
        # pc_ids = pc_obj.search(cr, uid, [('tipo_compra', 'in', domain_ids)])
        # domain_user = str([('id', 'in', pc_ids),('state', 'in', ['sice'])]) , se quita para cumplir con requerimiento de gap 303
        domain_user = str([('state', 'in', ['sice'])])

        if domain_user:
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='nro_licitacion']"):
                node.set('domain', domain_user)
            res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'fecha': fields.date('Fecha documento', required=True),
        'fecha_vencimiento': fields.date('Fecha vencimiento', required=True),
        'fecha_recepcion': fields.date(u'Fecha de recepción'),
        'requerido': fields.boolean('Requerir'),
        'monto': fields.float('Monto'),
        'currency_id': fields.many2one('res.currency', 'Moneda', readonly=True),
        'fecha_entregado': fields.function(get_fecha_entregado, type='date', string='Fecha de entrega'),
        'partner_id': fields.many2one('res.partner', 'Proveedor'),
        'descripcion': fields.char(u'Descripción'),
        'state': fields.selection((('borrador', 'Borrador'), ('entregado', u'Entregar a Tesorería'),
                                   ('recibido', u'Recibido Tesorería'), ('vencido', u'Vencido en Tesorería'),
                                   ('entrega_autorizada', u'Entrega Autorizada'),
                                   ('entrega_tesoreria', u'Entregado por Tesorería'), ('baja', 'Baja')),
                                  'Estado', track_visibility='onchange'),
        'company_id': fields.many2one('res.company', u'Compañia'),
        'observaciones_tesoreria': fields.char(u'Observaciones Tesorería', size=40),
        'es_tesoreria': fields.function(_es_tesoreria, method=True, type='boolean', string=u'Es grupo tesoreria?'),
        'nro_licitacion': fields.many2one('grp.pedido.compra', u'Nro. Procedimiento', required=True),
        # #
        # 'tipo_de_compra' : fields.related('nro_licitacion', 'tipo_compra', type='many2one', relation='sicec.tipo.compra', readonly=True, string='Tipo de compra', store=True),
    }

    # def action_entregado(self, cr, uid, ids, context):
    #     return self.write(cr, uid, ids, {'state':'entregado'}, context=context)

    def action_recibido(self, cr, uid, ids, context):
        return self.write(cr, uid, ids, {'state': 'recibido'}, context=context)

    def action_entrega_autorizada(self, cr, uid, ids, context):
        return self.write(cr, uid, ids, {'state': 'entrega_autorizada'}, context=context)

    def action_entrega_tesoreria(self, cr, uid, ids, context):
        return self.write(cr, uid, ids, {'state': 'entrega_tesoreria'}, context=context)

    def action_devolucion_aprobada(self, cr, uid, ids, context):
        return self.write(cr, uid, ids, {'state': 'devolucion_aprobada'}, context=context)

    _defaults = {
        'state': 'borrador',
        'requerido': False,
        'company_id': _get_company_id
    }

    _constraints = [
        (_check_fechas, u'La fecha de vencimiento debe ser mayor o igual a la fecha', ['fecha_vencimiento', 'fecha'])]

    def action_entregado(self, cr, uid, ids, context=None):
        if not ids: return []
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'grp_tesoreria',
                                                                             'view_grp_fecha_entrega_garantia_form')
        # dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_dialog_form')
        garantia = self.browse(cr, uid, ids[0], context=context)

        return {
            'name': _("Fecha de entrega"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'grp.fecha_entrega_garantia',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'default_garantia_id': garantia.id,

            }
        }

    def cambiar_estado_cron(self, cr, uid, context=None):
        fecha_hoy = datetime.datetime.now()
        today = fecha_hoy.strftime('%Y') + '-' + fecha_hoy.strftime('%m') + '-' + fecha_hoy.strftime('%d')
        garantias_ids = self.search(cr, uid, [('fecha_vencimiento', '<=', today), ('state', '=', 'recibido')])
        if len(garantias_ids) > 0:
            self.write(cr, uid, garantias_ids, {'state': 'vencido'}, context=context)

    def enviar_notificacion_fin_contrato(self, cr, uid, ids, context=None):
        r = self.browse(cr, uid, ids[0], context=context)
        env = api.Environment(cr, 1, {})
        ir_model_data = env['ir.model.data']
        _model, group_id1 = ir_model_data.get_object_reference('grp_tesoreria', 'group_grp_tesoreria')
        _model, group_id2 = ir_model_data.get_object_reference('grp_seguridad', 'grp_compras_pc_Comprador')
        users1 = env['res.users'].search([('groups_id', 'in', group_id1)])
        users2 = env['res.users'].search([('groups_id', 'in', group_id2)])
        partner_ids = []
        nombre = r.name or ''
        fec_ven = r.fecha_vencimiento or ''
        proveedor = r.partner_id.name or ''
        if users1:
            partner_ids = [user.partner_id.id for user in users1]
        if users2:
            partner_ids.extend([user.partner_id.id for user in users2])
        body = u"Se informa del fin del contrato del siguiente valor: \n\n" \
               u"%s \n\n" \
               u"Fecha Vencimiento %s \n\n" \
               u"Proveedor %s \n\n"
        msg = _(body) % \
              (nombre, fec_ven, proveedor)
        self.pool['mail.thread'].message_post(cr, uid, 0, body=msg, subject='Fin de contrato', partner_ids=partner_ids, context=context, subtype='mail.mt_comment')
        return True

grp_valores_custodia()


class grp_fecha_entrega_garantia(osv.osv):
    _name = 'grp.fecha_entrega_garantia'

    # def button_entregado(self, cr, uid, ids, context):
    #     for fecha in self.browse(cr, uid, ids):
    #         self.pool.get('grp_valores_').write(cr, uid, [fecha.garantia_id.id], {'state': 'entregado'},
    #                                                     context=context)

    _columns = {
        'name': fields.date('Fecha de entrega', required=1),
        'garantia_id': fields.many2one('grp.valores_custodia', 'Garantia id'),
    }

    _defaults = {

        'name': lambda *a: datetime.date.today().strftime('%Y-%m-%d'),
    }


grp_fecha_entrega_garantia()
# 001-Fin
