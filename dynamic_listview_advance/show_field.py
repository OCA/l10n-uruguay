# -*- coding: utf-8 -*-
# __author__ = 'irabaza <ismel.rabaza@gmail.com>'
# __contributors__ = 'truongdung'

from openerp import fields, api, models, _

class ShowFieldS(models.Model):
    _name = "show.fields"
    _order = "create_date desc, id desc"

    user_id = fields.Many2one(comodel_name="res.users", string="User")
    name = fields.Char(string="Name")
    model_name = fields.Char(string="Model Name")
    color = fields.Char(string="Color", default="check-base")
    fields_show = fields.Char(string="Fields Show")
    all_user = fields.Boolean(string="Fix header List View")
    fields_sequence = fields.Char(string="Sequence")
    color_for_list = fields.Boolean(string="Use Color/bgcolor for listview")
    fields_string = fields.Char(string="Fields String", translate=True)
    # background_color = fields.Char(string="Background Color of ListView")
    # color_list_view = fields.Char(string="Color of ListView")

    view_id = fields.Many2one('ir.ui.view', string="View", help="View ID. A model may have multiple views")
    view_type = fields.Char(string="View Type")
    action_id = fields.Integer(string="Action", help="Action ID not relational. A model may use the same view definition (same view_id) for diferent actions")

    @api.model
    def action(self, vals, action):
        show_button_col = False
        if self.user_has_groups('dynamic_listview_advance.group_show_fields,dynamic_listview_advance.group_show_fields_manager'):
            show_button_col = True

        if 'user_id' in vals and 'model_name' in vals:
            context = self._context or {}
            view_type = vals.get('view_type', 'tree')
            view_id = vals.get('view_id', False)
            if not view_id:
                # <view_type>_view_ref in context can be used to overrride the default view
                view_ref_key = view_type + '_view_ref'
                view_ref = context.get(view_ref_key)
                if view_ref:
                    if '.' in view_ref:
                        module, view_ref = view_ref.split('.', 1)
                        self._cr.execute("SELECT res_id FROM ir_model_data WHERE model='ir.ui.view' AND module=%s AND name=%s", (module, view_ref))
                        view_ref_res = self._cr.fetchone()
                        if view_ref_res:
                            view_id = view_ref_res[0]
                    else:
                        pass # ignore?

                if not view_id:
                    # otherwise try to find the lowest priority matching ir.ui.view
                    view_id = self.pool['ir.ui.view'].default_view(self._cr, self._uid, vals['model_name'], view_type, context=context)

            vals.update({'view_id': view_id, 'action_id': context.get('params', {}).get('action', False) })


            data = self.search([('user_id', '=', vals['user_id']),
                                ('model_name', '=', vals['model_name']),
                                ('view_type','=',vals['view_type']),
                                ('view_id','=',vals['view_id']),
                                ('action_id','=',vals['action_id'])])
            if not data:
                data = self.search([('all_user', '=', True),
                                    ('model_name', '=', vals['model_name']),
                                    ('view_type','=',vals['view_type']),
                                    ('view_id','=',vals['view_id']),
                                    ('action_id','=',vals['action_id'])])
            if not vals['action_id'] and not data:
                # Si se recarga el navegador context puede no traer action
                datas = self.search([('user_id', '=', vals['user_id']),
                                    ('model_name', '=', vals['model_name']),
                                    ('view_type','=',vals['view_type']),
                                    ('view_id','=',vals['view_id'])])
                if not datas:
                    datas = self.search([('all_user', '=', True),
                                        ('model_name', '=', vals['model_name']),
                                        ('view_type','=',vals['view_type']),
                                        ('view_id','=',vals['view_id'])])
                if datas and len(datas)==1:
                    data = datas[0]

            show_all_user = self.user_has_groups('dynamic_listview_advance.group_show_fields_manager')
            if action == 'delete':
                if data and data[0].user_id.id == vals['user_id'] or vals.get('all_user', False):
                    data.unlink()
            elif action == 'update':
                if 'fields_show' in vals:
                    vals['fields_show'] = str(vals['fields_show']) # TODO: Is this neccessary??
                    if len(data) > 0 and (data[0].user_id.id == vals['user_id'] or vals.get('all_user', False)):
                        data[0].write({ 'fields_show': vals['fields_show'], 'all_user': vals.get('all_user', False),
                                        'fields_sequence': vals.get('fields_sequence', False),
                                        'fields_string': vals.get('fields_string', False) })
                    else:
                        self.create(vals)
                else:
                    if len(data) > 0 and (data[0].user_id.id == vals['user_id'] or vals.get('all_user', False)):
                        data[0].write({'color': vals.get('color', False), 'all_user': vals.get('all_user', False),
                                       'color_for_list': vals.get('color_for_list', False), 'view_id': view_id})
                    else:
                        self.create(vals)

            elif action == 'select':
                model_all_fields = self.env[vals['model_name']].fields_get()

                if len(data) > 0:
                    data = data[0]
                    return {'data': {'user_id': data.user_id.id, 'color': data.color, 'model_name': data.model_name,
                                     'fields_show': data.fields_show, 'id': data.id, 'name': data.name,
                                     'fields_sequence': data.fields_sequence,
                                     'all_user': data.all_user,
                                     'color_for_list': data.color_for_list,
                                     'fields_string': data.fields_string },
                            'fields': model_all_fields,
                            'show_button_col': show_button_col,
                            'show_all_user': show_all_user }
                else:
                    return {'data': {}, 'fields': model_all_fields, 'show_button_col': show_button_col, 'show_all_user': show_all_user }
            return { 'show_button_col': show_button_col, 'show_all_user': show_all_user }

ShowFieldS()
