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

from openerp import models, fields, api, exceptions, _
from openerp.exceptions import ValidationError
from lxml import etree

class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'

    hr_department_id = fields.Many2one('hr.department', string='Unidad organizativa')
    account_id = fields.Many2one('account.analytic.account', u'Cuenta analítica', required=False, ondelete='restrict', select=True, domain=[('type','<>','view')])
    dim_multi_id = fields.Many2one('grp.dimension_multiproposito', string=u'Multipropósito')

class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'journal_id': self.invoice_id.journal_id.id,
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True # Trigger error?

    @api.model
    def create(self, vals):
        _line = super(account_invoice_line, self).create(vals)
        if _line.analytics_id:
            for instance in _line.analytics_id.account_ids:
                if not instance.account_id or instance.account_id.id != _line.account_id.id:
                    instance.write({'account_id': _line.account_id.id})
        return _line

    @api.multi
    def write(self, vals):
        _r = super(account_invoice_line, self).write(vals)
        for _line in self:
            if _line.analytics_id:
                for instance in _line.analytics_id.account_ids:
                    if not instance.account_id or instance.account_id.id != _line.account_id.id:
                        instance.write({'account_id': _line.account_id.id})
        return _r

class account_analytic_plan(models.Model):
    _inherit = "account.analytic.plan"

    plan_instance_ids = fields.One2many('account.analytic.plan.instance', 'plan_id', 'Distribución analítica', copy=True)

class account_analytic_plan_instance(models.Model):
    _inherit = "account.analytic.plan.instance"

    @api.constrains('account_ids')
    def _check_amount(self):
        form_amount = self.env.context.get('form_amount', False)
        form_currency_id = self.env.context.get('form_currency_id', False)
        if form_amount and form_currency_id:
            form_currency_id = self.env['res.currency'].search([('id','=',form_currency_id)])
            for row in self:
                if row.plan_id:
                    continue # ?
                _amount = 0
                for line in row.account_ids:
                    if line.amount > 0:
                        _amount += line.amount
                    elif line.rate > 0:
                        _amount += (line.rate * form_amount) / 100
                _diff = form_amount - _amount
                if form_currency_id.name=='UYU':
                    if _diff < 1 and _diff >= 0:
                        continue
                elif _diff < 0.1 and _diff >= 0:
                    continue
                raise ValidationError('El importe de distribución no coincide con el importe de la línea')

    def remove_field_view(self, xml_view, field_view):
        xml_view = etree.XML(xml_view)
        for node in xml_view.xpath("//field[@name='%s']"%(field_view,)):
            xml_view.remove(node)
        return etree.tostring(xml_view)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(account_analytic_plan_instance, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = res.get('fields',{}).get('account_ids',{}).get('views',{}).get('tree',{}).get('arch',False)
        if doc:
            if self._context.get('analytics_id', False):
                dim = self.search([('id','=',self._context['analytics_id'])])
                #Cuando tiene plan_id entonces solo debe mostrar el compute
                if dim.plan_id:
                    res['fields']['account_ids']['views']['tree']['arch'] = self.remove_field_view(doc, 'amount')
                else:
                    res['fields']['account_ids']['views']['tree']['arch'] = self.remove_field_view(doc, 'amount_cmp')
            else:
                res['fields']['account_ids']['views']['tree']['arch'] = self.remove_field_view(doc, 'amount_cmp')
        return res

class account_analytic_plan_instance_line(models.Model):
    _inherit = "account.analytic.plan.instance.line"

    @api.onchange('amount')
    def _onchange_amount(self):
        form_amount = self.env.context.get('form_amount', False)
        if form_amount:
            self.rate = 0.00
            self.rate = (self.amount * 100)/form_amount

    @api.onchange('rate')
    def _onchange_rate(self):
        self.amount = 0.00
        form_amount = self.env.context.get('form_amount', False)
        if form_amount:
            self.amount = (self.rate * form_amount) / 100

    @api.depends('rate','amount')
    def _compute_amount_cmp(self):
        for row in self:
            form_amount = row.env.context.get('form_amount', False)
            if form_amount:
                row.amount_cmp = (row.rate * form_amount) / 100

    @api.depends('account_id')
    def _compute_account_id(self):
        for row in self:
            row.account_id_cmp = row.account_id

    @api.onchange('hr_department_id_not_apply', 'dim_multi_id_not_apply', 'analytic_account_id_not_apply')
    def _onchange_apply(self):
        if self.hr_department_id_not_apply:
            self.hr_department_id = False
        if self.dim_multi_id_not_apply:
            self.dim_multi_id = False
        if self.analytic_account_id_not_apply:
            self.analytic_account_id = False

    hr_department_id = fields.Many2one('hr.department', string='Unidad organizativa')
    hr_department_id_not_apply = fields.Boolean('No aplica Unidad organizativa', default=False, help="No aplicar Unidad organizativa")
    dim_multi_id = fields.Many2one('grp.dimension_multiproposito', string=u'Multipropósito')
    dim_multi_id_not_apply = fields.Boolean(u'No aplica Multipropósito', default=False, help=u"No aplicar Multipropósito")
    account_id = fields.Many2one('account.account', string='Cuenta')
    account_id_cmp = fields.Many2one('account.account', string='Cuenta', compute='_compute_account_id')
    analytic_account_id = fields.Many2one('account.analytic.account', u'Cuenta analítica', required=False, domain=[('type','<>','view')])
    analytic_account_id_not_apply = fields.Boolean(u'No aplica Cuenta analítica', default=False, help=u"No aplicar Cuenta analítica")
    amount = fields.Float('Importe')
    amount_cmp = fields.Float('Importe', compute='_compute_amount_cmp')

class grp_compras_solicitud_recursos_line_sr(models.Model):
    _inherit = 'grp.compras.solicitud.recursos.line.sr'

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'amount_invisible': True,
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True

    analytics_id = fields.Many2one('account.analytic.plan.instance','Dimensiones')
    account_id = fields.Many2one(string='Cuenta', related='product_id.property_account_expense', store=True, readonly=True)
    parent_state = fields.Selection(related='grp_id.state', store=True, readonly=True)

class grp_solicitud_compra(models.Model):
    _inherit = 'grp.solicitud.compra'

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'amount_invisible': True,
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True

    @api.model
    def _prepare_crear_solicitud_linea(self, browse_id):
        _res = super(grp_solicitud_compra, self)._prepare_crear_solicitud_linea(browse_id)
        _res.update({
            'analytics_id': browse_id.analytics_id and browse_id.analytics_id.id or False,
            'account_id': browse_id.account_id and browse_id.account_id.id or False
        })
        return _res

    analytics_id = fields.Many2one('account.analytic.plan.instance', 'Dimensiones')
    account_id = fields.Many2one(string='Cuenta', related='product_id.property_account_expense', store=True, readonly=True)

class grp_pedido_compra(models.Model):
    _inherit = 'grp.pedido.compra'

    @api.multi
    def _prepare_merge_line(self, line, taxes=[]):
        _res = super(grp_pedido_compra, self)._prepare_merge_line(line, taxes=taxes)
        _res.update({
            'analytics_id': line.analytics_id and line.analytics_id.id or False,
            'account_id': line.account_id and line.account_id.id or False
        })
        return _res

    @api.multi
    def _prepare_resumir_linea(self, pedido, line):
        _res = super(grp_pedido_compra, self)._prepare_resumir_linea(pedido, line)
        if isinstance(line, list):
            linea_pedido = line[0]
        else:
            linea_pedido = line
        _res.update({
            'analytics_id': linea_pedido.analytics_id and linea_pedido.analytics_id.id or False,
            'account_id': linea_pedido.account_id and linea_pedido.account_id.id or False
        })
        return _res

class grp_linea_pedido_compra(models.Model):
    _inherit = 'grp.linea.pedido.compra'

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'amount_invisible': True,
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True

    analytics_id = fields.Many2one('account.analytic.plan.instance','Dimensiones')
    account_id = fields.Many2one(string='Cuenta', related='product_id.property_account_expense', store=True, readonly=True)
    parent_state = fields.Selection(related='pedido_compra_id.state', store=True, readonly=True)

class grp_resumen_pedido_compra(models.Model):
    _inherit = 'grp.resumen.pedido.compra'

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'amount_invisible': True,
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True

    analytics_id = fields.Many2one('account.analytic.plan.instance','Dimensiones')
    account_id = fields.Many2one(string='Cuenta', related='product_id.property_account_expense', store=True, readonly=True)
    parent_state = fields.Selection(related='pedido_compra_id.state', store=True, readonly=True)

class grp_cotizaciones_lineas_aceptadas(models.Model):
    _inherit = 'grp.cotizaciones.lineas.aceptadas'

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'amount_invisible': True,
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True

    analytics_id = fields.Many2one('account.analytic.plan.instance','Dimensiones')
    account_id = fields.Many2one(string='Cuenta', related='product_id.property_account_expense', store=True, readonly=True)
    parent_state = fields.Selection(related='pedido_cot_id.state', store=True, readonly=True)

class account_asset_asset(models.Model):
    _inherit = 'account.asset.asset'

    analytics_id = fields.Many2one('account.analytic.plan.instance','Dimensiones')
    account_id = fields.Many2one(string='Cuenta', related='category_id.account_expense_depreciation_id', store=True, readonly=True)

class account_asset_depreciation_line(models.Model):
    _inherit = 'account.asset.depreciation.line'

    @api.multi
    def _prepare_deb_move_line(self, line, move_id, depreciation_date, period_ids=[]):
        res = super(account_asset_depreciation_line, self)._prepare_deb_move_line(line, move_id, depreciation_date, period_ids=period_ids)
        res.update({
            'analytics_id': line.asset_id.analytics_id and line.asset_id.analytics_id.id or False,
            'account_id': line.asset_id.account_id and line.asset_id.account_id.id or False
        })
        return res

class grp_asset_depreciation_confirmation_wizard(models.TransientModel):
    _inherit = 'asset.depreciation.confirmation.wizard'

    @api.multi
    def _prepare_deb_move_line(self, lines, asset_categ, debit, operating_unit):
        res = super(grp_asset_depreciation_confirmation_wizard, self)._prepare_deb_move_line(lines, asset_categ, debit, operating_unit)
        if lines:
            _res=[]
            for asset_line in lines:
                if not asset_line.asset_id.analytics_id:
                    continue
                for dline in asset_line.asset_id.analytics_id.account_ids:
                    _found = False
                    for r in _res:
                        if (r['account_id'], r['hr_department_id'], r['dim_multi_id'], r['analytic_account_id']) == \
                            (dline.account_id and dline.account_id.id or False, dline.hr_department_id and dline.hr_department_id.id or False, \
                            dline.dim_multi_id and dline.dim_multi_id.id or False, dline.analytic_account_id and dline.analytic_account_id.id or False):
                            r['amount'] += (dline.rate * asset_line.amount) / 100
                            _found = True
                            break
                    if not _found:
                        _res.append({
                            #'asset_line_id': asset_line.id,
                            'account_id': dline.account_id and dline.account_id.id or False,
                            'hr_department_id': dline.hr_department_id and dline.hr_department_id.id or False,
                            'hr_department_id_not_apply': dline.hr_department_id_not_apply,
                            'dim_multi_id': dline.dim_multi_id and dline.dim_multi_id.id or False,
                            'dim_multi_id_not_apply': dline.dim_multi_id_not_apply,
                            'analytic_account_id': dline.analytic_account_id and dline.analytic_account_id.id or False,
                            'analytic_account_id_not_apply': dline.analytic_account_id_not_apply,
                            'amount': (dline.rate * asset_line.amount) / 100
                        })
            if _res:
                _record = {
                    'account_ids': []
                }
                for r in _res:
                    _record['account_ids'].append((0, 0, {
                        'account_id': r['account_id'],
                        'hr_department_id': r['hr_department_id'],
                        'hr_department_id_not_apply': r['hr_department_id_not_apply'],
                        'dim_multi_id': r['dim_multi_id'],
                        'dim_multi_id_not_apply': r['dim_multi_id_not_apply'],
                        'analytic_account_id': r['analytic_account_id'],
                        'analytic_account_id_not_apply': r['analytic_account_id_not_apply'],
                        'rate': (r['amount'] * 100) / debit
                    }))
                res['analytics_id'] = self.env['account.analytic.plan.instance'].create({
                                                                                            'account_ids': _record['account_ids']
                                                                                        }).id
        return res

class account_move_line(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'amount_invisible': False,
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True

    # Sobreescritura del metodo create_analytic_lines de account_analytic_plans
    # Las lineas analiticas deben tomar la UO a partir de las lineas de la distribucion del asiento generado
    @api.multi
    def create_analytic_lines(self):
        super(account_move_line, self).create_analytic_lines()
        analytic_line_obj = self.env['account.analytic.line']
        for line in self:
           if line.analytics_id:
               if not line.journal_id.analytic_journal_id:
                   raise exceptions.ValidationError(_('No Analytic Journal!'),
                                                    _("You have to define an analytic journal on the '%s' journal.")
                                                    % (line.journal_id.name,))

               toremove = analytic_line_obj.search([('move_id','=',line.id)])
               if toremove:
                    toremove.unlink()
               for line2 in line.analytics_id.account_ids:
                   val = (line.credit or  0.0) - (line.debit or 0.0)
                   amt=val * (line2.rate/100)
                   al_vals={
                       'name': line.name,
                       'date': line.date,
                       'account_id': line2.analytic_account_id.id,
                       'unit_amount': line.quantity,
                       'product_id': line.product_id and line.product_id.id or False,
                       'product_uom_id': line.product_uom_id and line.product_uom_id.id or False,
                       'amount': amt,
                       'general_account_id': line.account_id.id,
                       'move_id': line.id,
                       'journal_id': line.journal_id.analytic_journal_id.id,
                       'ref': line.ref,
                       'percentage': line2.rate
                   }
                   # Si la linea de la distribucion tiene UO agregarle la UO a la linea analitica
                   if line2.hr_department_id:
                       al_vals.update({'hr_department_id': line2.hr_department_id.id})
                   if line2.dim_multi_id:
                       al_vals.update({'dim_multi_id': line2.dim_multi_id.id})
                   analytic_line_obj.create(al_vals)
        return True

class account_move(models.Model):
    _inherit = "account.move"

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'amount_invisible': False,
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True

class hr_expense_line(models.Model):
    _inherit = "hr.expense.line"

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'amount_invisible': False,
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True

    analytics_id = fields.Many2one('account.analytic.plan.instance','Dimensiones')
    account_id = fields.Many2one(string='Cuenta', related='product_id.property_account_expense', store=True, readonly=True)
    parent_state = fields.Selection(related='expense_id.state', store=True, readonly=True)

class stock_move(models.Model):
    _inherit = "stock.move"

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'amount_invisible': True,
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True

    @api.model
    def _get_invoice_line_vals(self, move, partner, inv_type):
        _res = super(stock_move, self)._get_invoice_line_vals(move, partner, inv_type)
        #if inv_type in ('in_invoice', 'in_refund'): ?
        if not _res['account_id']:
            _res['account_id'] = move.account_id and move.account_id.id or False
        _res['analytics_id'] = move.analytics_id and move.analytics_id.id or False
        return _res

    analytics_id = fields.Many2one('account.analytic.plan.instance','Dimensiones')
    account_id = fields.Many2one(string='Cuenta', related='product_id.property_account_expense', store=True, readonly=True)

class grp_compras_solicitud_recursos_almacen(models.Model):
    _inherit = 'grp.compras.solicitud.recursos.almacen'

    @api.multi
    def _prepare_move_line(self, cabezal, line, location_dest_id, pick_type_id):
        _res = super(grp_compras_solicitud_recursos_almacen, self)._prepare_move_line(cabezal, line, location_dest_id, pick_type_id)
        _res.update({
            'analytics_id': line.analytics_id and line.analytics_id.id or False,
            'account_id': line.account_id and line.account_id.id or False
        })
        return _res

class account_bank_statement_line(models.Model):
    _inherit = 'account.bank.statement.line'

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'amount_invisible': True,
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True

class purchase_order(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _prepare_order_line_move(self, order, order_line, picking_id, group_id):
        _res = super(purchase_order, self)._prepare_order_line_move(order, order_line, picking_id, group_id)
        for _r in _res:
            _r['account_id'] = order_line.account_id and order_line.account_id.id or False
            _r['analytics_id'] = order_line.analytics_id and order_line.analytics_id.id or False
        return _res

    @api.model
    def _prepare_inv_line(self, account_id, order_line):
        _r = super(purchase_order, self)._prepare_inv_line(account_id, order_line)
        _r.update({
            'account_id': order_line.account_id and order_line.account_id.id or account_id,
            'analytics_id': order_line.analytics_id and order_line.analytics_id.id or False
        })
        return _r

class purchase_order_line(models.Model):
    _inherit='purchase.order.line'

    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, state='draft', context=None):
        _r = super(purchase_order_line, self).onchange_product_id(cr, uid, ids, pricelist_id, product_id, qty, uom_id,
                                                partner_id, date_order=date_order, fiscal_position_id=fiscal_position_id, date_planned=date_planned,
                                                name=name, price_unit=price_unit, state=state, context=context)
        if _r.get('value',False):
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            _r['value']['account_id'] = prod.property_account_expense and prod.property_account_expense.id or False
        return _r

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'journal_id': self.order_id.journal_id.id,
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True # Trigger error?

    @api.model
    def create(self, vals):
        _line = super(purchase_order_line, self).create(vals)
        if _line.analytics_id:
            for instance in _line.analytics_id.account_ids:
                if not instance.account_id or instance.account_id.id != _line.account_id.id:
                    instance.write({'account_id': _line.account_id.id})
        return _line

    @api.multi
    def write(self, vals):
        _r = super(purchase_order_line, self).write(vals)
        for _line in self:
            if _line.analytics_id:
                for instance in _line.analytics_id.account_ids:
                    if not instance.account_id or instance.account_id.id != _line.account_id.id:
                        instance.write({'account_id': _line.account_id.id})
        return _r

    account_id = fields.Many2one('account.account','Cuenta')

class account_model(models.Model):
    _inherit = "account.model"

    @api.multi
    def generate(self, data=None):
        move_ids = super(account_model, self).generate(data=data)
        if move_ids:
            AccountMoveLine = self.env['account.move.line']
            for move_id in move_ids:
                for model in self:
                    for line in model.lines_id:
                        if line.analytics_id:
                            move_lines = AccountMoveLine.search([('move_id','=',move_id),('name','=',line.name),
                                                                 ('quantity','=',line.quantity),('debit','=',line.debit),
                                                                 ('credit','=',line.credit),('account_id','=',line.account_id.id),
                                                                 ('partner_id','=',line.partner_id.id),
                                                                 ('date','=',self._context.get('date', fields.Date.context_today(self)))])
                            move_lines.write({'analytics_id': line.analytics_id.id})
        return move_ids

class account_model_line(models.Model):
    _inherit = "account.model.line"

    @api.multi
    def open_analytics(self):
        if self.analytics_id:
            return {
                'type': 'ir.actions.act_window',
                'name': u'Distribución analítica',
                'res_model': 'account.analytic.plan.instance',
                'domain': [('plan_id','&lt;&gt;',False)],
                'view_type': 'form',
                'view_mode': 'form',
                'context': {
                        'form_view_ref': 'grp_account_distribution.account_analytic_plan_instance_form2_readonly',
                        'amount_invisible': False,
                        'analytics_id': self.analytics_id.plan_id and self.analytics_id.id or False
                },
                'target': 'new',
                'res_id': self.analytics_id.id
            }
        return True

    analytics_id = fields.Many2one('account.analytic.plan.instance', 'Dimensiones')

class GrpCajaChicaTesoreria(models.Model):
    _inherit = 'grp.caja.chica.tesoreria'

    @api.depends('box_id','box_id.currency_id')
    def compute_currency_id(self):
        for row in self:
            row.currency_id = row.box_id.currency_id and row.box_id.currency_id or False

    currency_id = fields.Many2one('res.currency', 'Moneda', compute="compute_currency_id", readonly=True)

class GrpCajaChicaTesoreriaMovEfectivo(models.Model):
    _inherit = 'grp.caja.chica.movimiento.efectivo'

    @api.depends('concept_cc_id','concept_cc_id.cuenta_id')
    def compute_concept_account(self):
        for row in self:
            row.account_id = row.concept_cc_id and row.concept_cc_id.cuenta_id or False

    @api.onchange('concept_cc_id')
    def onchange_concept(self):
        self.dimension_id = False

    account_id = fields.Many2one('account.account','Cuenta', compute="compute_concept_account", readonly=True)

class GrpCajaChicaTesoreriaLine(models.Model):
    _inherit = 'grp.caja.chica.tesoreria.line'

    @api.multi
    def edit_transaction(self):
        mod_obj = self.env['ir.model.data']
        for rec in self:
            if rec.is_catch_mov:
                res = mod_obj.get_object_reference('grp_tesoreria', 'view_grp_caja_chica_mov_efectivo_form')
                return {
                    'name': 'Movimiento en efectivo',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_id': [res and res[1] or False],
                    'view_mode': 'form',
                    'res_model': 'grp.caja.chica.movimiento.efectivo',
                    'res_id': rec.catch_mov_id.id,
                    'target': 'new',
                    'nodestroy': True,
                    'context': {
                        'journal_id': self.env.context.get('journal_id', False),
                        'currency_id': self.env.context.get('currency_id', False)
                    }
                }
            mod_obj.get_object_reference('grp_tesoreria', 'view_grp_caja_chica_line_form')
            return {
                'name': 'Valor en custodia',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_id': False,
                'view_mode': 'form',
                'res_model': 'grp.caja.chica.tesoreria.line',
                'res_id': rec.id,
                'target': 'new',
                'nodestroy': True,
                'context': {'custody': True}
            }