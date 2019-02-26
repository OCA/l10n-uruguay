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

from openerp import models, fields, api, modules, _, SUPERUSER_ID
from datetime import datetime

FIELDS_BLACKLIST = [
    'id', 'create_uid', 'create_date', 'write_uid', 'write_date',
    'display_name', '__last_update',
]

EMPTY_DICT = {}

class AuditTrackedFieldsRule(models.Model):
    _name = 'audit.tracked_fields.rule'
    _description = "Audit Tracked Fields - Settings"
    _rec_name = "model_id"

    @api.one
    @api.depends('field_ids')
    def _compute_field_names(self):
        field_names = [ f.name for f in self.field_ids ]
        self.field_names = str(field_names or [])

    model_id = fields.Many2one('ir.model', "Model", required=True, ondelete='cascade', help="Select model for which you want to track a field.")
    model = fields.Char("Model Technical Name", related='model_id.model', store=True, readonly=True)
    field_ids = fields.Many2many('ir.model.fields', 'audit_tracked_fields_rule_ir_fields_rel', 'field_id', 'rule_id',
                                  string="Tracking Fields", required=True, domain="[('model_id','=',model_id)]")
    field_names = fields.Char('Fields Names List', compute='_compute_field_names', store=True)
    log_create = fields.Boolean("Log Creates", default=True)
    log_write = fields.Boolean("Log Writes", default=True)
    log_unlink = fields.Boolean("Log Deletes", default=True)
    state = fields.Selection([('draft', "Draft"), ('subscribed', "Subscribed")],
        string="State", required=True, default='subscribed')


    _sql_constraints = [
        ('model_uniq', 'unique(model_id)',
         ("There is already a configuration defined on this model\n"
          "You cannot define another: please edit the existing one."))
    ]

    def _register_hook(self, cr, ids=None):
        super(AuditTrackedFieldsRule, self)._register_hook(cr)
        if not hasattr(self.pool, '_audit_tracked_field_cache'):
            self.pool._audit_tracked_field_cache = {}
        if not hasattr(self.pool, '_audit_tracked_field_model_cache'):
            self.pool._audit_tracked_field_model_cache = {}
        if ids is None:
            ids = self.search(cr, SUPERUSER_ID, [('state', '=', 'subscribed')])
        return self._patch_methods(cr, SUPERUSER_ID, ids)

    @api.multi
    def _patch_methods(self):
        """ Patch ORM methods of models defined in rules to log their calls. """
        updated = False
        model_cache = self.pool._audit_tracked_field_model_cache
        for rule in self:
            if rule.state != 'subscribed':
                continue
            if not self.pool.get(rule.model_id.model):
                # ignore rules for models not loadable currently
                continue
            model_cache[rule.model_id.model] = rule.model_id.id
            model_model = self.env[rule.model_id.model]
            #   -> create
            check_attr = 'audit_tracked_fields_ruled_create'
            if getattr(rule, 'log_create') \
                    and not hasattr(model_model, check_attr):
                model_model._patch_method('create', rule._make_create())
                setattr(model_model, check_attr, True)
                updated = True
            #   -> write
            check_attr = 'audit_tracked_fields_ruled_write'
            if getattr(rule, 'log_write') \
                    and not hasattr(model_model, check_attr):
                model_model._patch_method('write', rule._make_write())
                setattr(model_model, check_attr, True)
                updated = True
            #   -> unlink
            check_attr = 'audit_tracked_fields_ruled_unlink'
            if getattr(rule, 'log_unlink') \
                    and not hasattr(model_model, check_attr):
                model_model._patch_method('unlink', rule._make_unlink())
                setattr(model_model, check_attr, True)
                updated = True
        return updated

    @api.multi
    def _revert_methods(self):
        """Restore original ORM methods of models defined in rules."""
        updated = False
        for rule in self:
            model_model = self.env[rule.model_id.model]
            for method in ['create','write','unlink']:
                if getattr(rule, 'log_%s' % method) and hasattr(
                        getattr(model_model, method), 'origin'):
                    model_model._revert_method(method)
                    updated = True
        if updated:
            modules.registry.RegistryManager.signal_registry_change(
                self.env.cr.dbname)

    @api.model
    def create(self, vals):
        """ Update the registry when a new rule is created. """
        new_record = super(AuditTrackedFieldsRule, self).create(vals)
        if self._model._register_hook(self.env.cr, new_record.ids):
            modules.registry.RegistryManager.signal_registry_change(
                self.env.cr.dbname)
        return new_record

    @api.multi
    def write(self, vals):
        """ Update the registry when existing rules are updated. """
        super(AuditTrackedFieldsRule, self).write(vals)
        if self._model._register_hook(self.env.cr, self.ids):
            modules.registry.RegistryManager.signal_registry_change(
                self.env.cr.dbname)
        return True

    @api.multi
    def unlink(self):
        """ Unsubscribe rules before removing them. """
        self.unsubscribe()
        return super(AuditTrackedFieldsRule, self).unlink()

    @api.multi
    def _make_create(self):
        self.ensure_one()

        @api.model
        @api.returns('self', lambda value: value.id)
        def do_create(self, vals, **kwargs):
            rule_model = self.env['audit.tracked_fields.rule']
            do_logging = rule_model.search([('model','=',self._name)], limit=1)
            if do_logging:
                self = self.with_context(audit_tracked_fields_disabled=True)
            new_record = do_create.origin(self, vals, **kwargs)
            if do_logging:
                new_values = dict(
                    (d['id'], d) for d in new_record.sudo()
                    .with_context(prefetch_fields=False).read(eval(do_logging.field_names)))
                rule_model.sudo().create_logs(
                    self.env.uid, self._name, new_record.ids,
                    'create', None, new_values)
            return new_record

        return do_create

    @api.multi
    def _make_write(self):
        self.ensure_one()

        @api.multi
        def do_write(self, vals, **kwargs):
            rule_model = self.env['audit.tracked_fields.rule']
            record = rule_model.search([('model','=',self._name)], limit=1)
            read_fields = record and [ f for f in vals.keys() if f in eval(record.field_names)] or []
            do_logging = bool(read_fields)
            if do_logging:
                self = self.with_context(audit_tracked_fields_disabled=True)
                old_values = dict(
                    (d['id'], d) for d in self.sudo()
                    .with_context(prefetch_fields=False).read(read_fields))
            result = do_write.origin(self, vals, **kwargs)
            if do_logging:
                new_values = dict(
                    (d['id'], d) for d in self.sudo()
                    .with_context(prefetch_fields=False).read(read_fields))
                rule_model.sudo().create_logs(
                    self.env.uid, self._name, self.ids,
                    'write', old_values, new_values)
            return result

        return do_write

    @api.multi
    def _make_unlink(self):
        self.ensure_one()

        @api.multi
        def do_unlink(self, **kwargs):
            do_logging = self.env['audit.tracked_fields.log'].sudo().search_count([('model','=',self._name),('res_id','in',self.ids)])
            if do_logging:
                rule_model = self.env['audit.tracked_fields.rule']
                self = self.with_context(audit_tracked_fields_disabled=True)
                rule_model.sudo().create_logs(
                    self.env.uid, self._name, self.ids, 'unlink', {}, {})
            return do_unlink.origin(self, **kwargs)

        return do_unlink

    def create_logs(self, uid, res_model, res_ids, method,
                    old_values=None, new_values=None):
        """Create logs. `old_values` and `new_values` are dictionaries, e.g:
            {RES_ID: {'FIELD': VALUE, ...}}
        """
        if 'lang' not in (self._context or {}):
            self = self.with_context(lang=self.env.user.lang)

        if old_values is None:
            old_values = EMPTY_DICT
        if new_values is None:
            new_values = EMPTY_DICT

        def _get_field_value_text(value, field_def):
            field_type = field_def.get('ttype', False)
            if field_type == 'many2one':
                return value[1] if (isinstance(value, tuple) and len(value)==2) else value
            if field_type == 'selection':
                try:
                    return _(dict(self.env[field_def.get('model')]._fields[field_def['name']].selection).get(value, '')) or value
                except:
                    return value
            return value

        log_model = self.env['audit.tracked_fields.log'].sudo()
        IrModel = self.env['ir.model']
        model_model = self.env[res_model]
        for res_id in res_ids:
            name = model_model.browse(res_id).name_get()
            res_name = name and name[0] and name[0][1]
            vals = {
                'name': res_name,
                'model_id': self.pool._audit_tracked_field_model_cache[res_model],
                'res_id': res_id,
                'user_id': uid,
            }
            if method == 'create':
                fields_list = new_values.get(res_id, EMPTY_DICT).keys()
                for field_name in fields_list:
                    if field_name in FIELDS_BLACKLIST:
                        continue
                    field = self._get_field(IrModel.browse(vals['model_id']), field_name)
                    if field:
                        if field['relation'] and '2many' in field['ttype']:
                            continue
                        log_vals = vals.copy()
                        log_vals.update({
                            'field_id': field['id'],
                            'new_value': new_values[res_id][field['name']],
                            'new_value_text': _get_field_value_text(new_values[res_id][field['name']], field),
                            'description': _('Record Created')
                        })
                        log_model.create(log_vals)
            if method == 'write':
                fields_list = old_values.get(res_id, EMPTY_DICT).keys()
                for field_name in fields_list:
                    if field_name in FIELDS_BLACKLIST:
                        continue
                    field = self._get_field(IrModel.browse(vals['model_id']), field_name)
                    if field:
                        if field['relation'] and '2many' in field['ttype']:
                            continue
                        log_vals = vals.copy()
                        log_vals.update({
                            'field_id': field['id'],
                            'old_value': old_values[res_id][field['name']],
                            'new_value': new_values[res_id][field['name']],
                            'old_value_text': _get_field_value_text(old_values[res_id][field['name']], field),
                            'new_value_text': _get_field_value_text(new_values[res_id][field['name']], field),
                            'description': _('Record Updated')
                        })
                        previous_log = log_model.search([('model_id','=',vals['model_id']),
                                                         ('res_id','=',res_id),
                                                         ('field_id','=',field['id'])], limit=1)
                        new_log = log_model.create(log_vals)
                        if previous_log:
                            elapsed_time = (datetime.strptime(new_log.create_date, '%Y-%m-%d %H:%M:%S') - datetime.strptime(previous_log.create_date, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600.0
                            previous_log.write({'elapsed_time': elapsed_time, 'elapsed_time_set': True})
            if method == 'unlink':
                log_vals = vals.copy()
                log_vals.update({
                    'old_value': False,
                    'old_value_text': False,
                    'new_value': False,
                    'new_value_text': False,
                    'field_id': False,
                    'description': _('Record Deleted')
                })
                previous_logs = log_model.search([('model_id','=',vals['model_id']),('res_id','=',res_id),('elapsed_time_set','=',False)])
                if previous_logs:
                    new_log = previous_logs[0].copy(log_vals)
                    updated_field_ids = []
                    for log in previous_logs:
                        if log.field_id.id not in updated_field_ids:
                            updated_field_ids.append(log.field_id.id)
                            elapsed_time = (datetime.strptime(new_log.create_date, '%Y-%m-%d %H:%M:%S') - datetime.strptime(log.create_date, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600.0
                            log.write({'elapsed_time': elapsed_time, 'elapsed_time_set': True})

    def _get_field(self, model, field_name):
        cache = self.pool._audit_tracked_field_cache
        if field_name not in cache.get(model.model, {}):
            cache.setdefault(model.model, {})
            rule_model = self.env['audit.tracked_fields.rule'].sudo()
            record = rule_model.search([('model_id','=',model.id)], limit=1)
            do_logging = record and field_name in eval(record.field_names)
            if not do_logging:
                cache[model.model][field_name] = False
            else:
                # - search the field in the current model and those it inherits
                field_model = self.env['ir.model.fields'].sudo()
                all_model_ids = [model.id]
                all_model_ids.extend(model.inherited_model_ids.ids)
                field = field_model.search(
                    [('model_id', 'in', all_model_ids), ('name', '=', field_name)])
                # The field can be a dummy one
                if not field:
                    cache[model.model][field_name] = False
                else:
                    field_data = field.read(load='_classic_write')[0]
                    cache[model.model][field_name] = field_data
        return cache[model.model][field_name]

    @api.multi
    def unsubscribe(self):
        """Unsubscribe Auditing Rule on model."""
        # Revert patched methods
        self._revert_methods()
        self.write({'state': 'draft'})
        return True


class AuditTrackedFieldsLog(models.Model):
    _name = 'audit.tracked_fields.log'
    _description = "Audit Tracked Fields - Log"
    _order = "create_date desc"

    @api.one
    @api.depends('elapsed_time_set')
    def _compute_elapsed_time(self):
        elapsed_time_computed = 0.0
        if self.field_id:
            if not self.elapsed_time_set:
                elapsed_time_computed = (datetime.now() - datetime.strptime(self.create_date, '%Y-%m-%d %H:%M:%S')).total_seconds() / 3600.0
            else:
                elapsed_time_computed = self.elapsed_time
        self.elapsed_time_computed = elapsed_time_computed

    name = fields.Char("Resource Name")
    model_id = fields.Many2one('ir.model', string="Model", required=True, index=True, ondelete='cascade')
    model = fields.Char("Model Technical Name", related='model_id.model', store=True, readonly=True)
    field_id = fields.Many2one('ir.model.fields', string="Field", required=False, index=True, ondelete='cascade')
    field_name = fields.Char("Field Technical Name", related='field_id.name', readonly=True)
    old_value = fields.Text("Old Value")
    new_value = fields.Text("New Value")
    old_value_text = fields.Text("Old Value")
    new_value_text = fields.Text("New Value")
    elapsed_time = fields.Float('Elapsed Time', default=0.0, help="Elapsed time in hours with the field value of record.")
    elapsed_time_computed = fields.Float('Elapsed Time', compute="_compute_elapsed_time", help="Elapsed time in hours with the field value of record.")
    elapsed_time_set = fields.Boolean("Elapsed Time Set", readonly=True, default=False)
    res_id = fields.Integer("Related Resource ID")
    user_id = fields.Many2one('res.users', string="User", help="User that makes field modification")
    description = fields.Text("Additional Information")

    def fields_get(self, cr, uid, allfields=None, context=None, write_access=True, attributes=None):
        res = super(AuditTrackedFieldsLog, self).fields_get(cr, uid, allfields=allfields, context=context, write_access=write_access, attributes=attributes)
        if 'res_id' in res:
            res['res_id'].update({'type': 'char', 'searchable': False})
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        result = super(AuditTrackedFieldsLog, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if 'elapsed_time_computed' in fields or 'elapsed_time' in fields:
            cr = self.env.cr
            for line in result:
                line_domain = line.get('__domain', domain)
                line_domain_ets = line_domain + [('elapsed_time_set','=',True)]
                line_domain_no_ets = line_domain + [('elapsed_time_set','=',False)]
                tables = 'audit_tracked_fields_log'
                where_clause = ""
                where_clause_params = []
                if line_domain:
                    query = self._where_calc(line_domain_ets)
                    tables, where_clause, where_clause_params = query.get_sql()

                query = """ SELECT sum(elapsed_time) as et
                            FROM %s """ % (tables,)
                if where_clause:
                    query += " WHERE %s " % (where_clause,)
                    cr.execute(query, tuple(where_clause_params))
                else:
                    cr.execute(query)
                __res = cr.fetchone()
                elapsed_time = __res and __res[0] or 0
                for row in self.search(line_domain_no_ets):
                    elapsed_time += row.elapsed_time_computed

                if 'elapsed_time' in fields:
                    line['elapsed_time'] = elapsed_time
                if 'elapsed_time_computed' in fields:
                    line['elapsed_time_computed'] = elapsed_time

        return result

    @api.multi
    def open_related_record(self):
        self.ensure_one()
        return self.pool[self.model].get_formview_action(self._cr, self._uid, self.res_id, context=self._context)
