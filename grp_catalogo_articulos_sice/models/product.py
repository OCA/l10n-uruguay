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
from openerp.osv import osv, fields, expression
from openerp import models, fields, api, _, exceptions
from openerp import tools
import psycopg2
from openerp import SUPERUSER_ID
import re
import logging
from lxml import etree
_logger = logging.getLogger(__name__)

class grp_product(osv.osv):
    _name = "product.product"
    _inherit = "product.product"

    def crear_producto_grp(self, cr, uid, ids, context=None):
        return True

    # PCAR 04 07 2017 inicio
    @api.depends('det_variante_id')
    def _get_marca_desc(self):
        for rec in self:
            if rec.det_variante_id:
                marc_cod = rec.det_variante_id.marc_cod
                marc_obj = self.env['grp.sice_marca'].search([('cod', '=', marc_cod)])
                rec.marca_desc = marc_obj.descripcion
            else:
                rec.marca_desc = False

    def _get_es_admin(self):
        for rec in self:
            rec.es_admin = self.env.user.id == SUPERUSER_ID

    @api.model
    def _def_es_admin(self):
        return self.env.user.id == SUPERUSER_ID

    med_cod_id = fields.Many2one('grp.sice_medida', string=u'Medida de la variante')
    pres_id = fields.Many2one('grp.sice_presentacion', string='Presentacion')
    med_cod_pres_id = fields.Many2one('grp.sice_medida', string=u'Medida de la presentación')
    det_variante_id = fields.Many2one('grp.sice_det_variante', string='Detalle de variante')
    sice_color_id = fields.Many2one('grp.sice_color', string='Color SICE')

    med_cod_desc = fields.Char(related='med_cod_id.descripcion', string=u'Medida variante descripción')
    pres_desc = fields.Char(related='pres_id.descripcion', string=u'Presentación descripción')
    med_cod_pres_desc = fields.Char(related='med_cod_pres_id.descripcion', string=u'Medida presentación descripción')
    det_variante_desc = fields.Char(related='det_variante_id.descripcion', string=u'Detalle variante descripción')
    sice_color_desc = fields.Char(related='sice_color_id.descripcion', string=u'Color descripción')
    marca_desc = fields.Char(compute='_get_marca_desc', string=u'Marca descripción', store=True)
    es_admin = fields.Boolean(compute='_get_es_admin', string=u'Es superusuario', default=_def_es_admin)
    # PCAR 04 07 2017 fin

    # 002-Inicio
    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []
        result = []
        for product in self.browse(cr, SUPERUSER_ID, ids, context=context):
            if not product.grp_sice_cod:
                result.append((product.id, product.name))
            else:
                name = product.name
                color = False
                det_variante_desc = False
                marc_desc = False

                #COLOR
                name += " /"
                if product.sice_color_id:
                    color = product.sice_color_id.descripcion
                    name += " " + color

                #MEDIDA DE VARIANTE
                att_desc = ""
                med_cod_desc = ""
                if product.attribute_id and product.attribute_id.name != '-----':
                    att_desc = product.attribute_id.name
                if product.med_cod_id and product.med_cod_id.descripcion != "-----":
                    med_cod_desc = product.med_cod_id.descripcion
                datos_attr = att_desc
                if med_cod_desc:
                    if datos_attr:
                        datos_attr += " " + med_cod_desc
                    else:
                        datos_attr = med_cod_desc
                if datos_attr:
                    name += " (" + datos_attr + ")"

                # PRESENTACION Y MEDIDA DE PRESENTACION
                pres_desc = ""
                med_cod_pres_desc = ""
                unme_desc = ""
                if product.pres_id and product.pres_id.descripcion != "-----":
                    pres_desc = product.pres_id.descripcion
                if product.med_cod_pres_id and product.med_cod_pres_id.descripcion != "-----":
                    med_cod_pres_desc = product.med_cod_pres_id.descripcion
                if product.pres_id.unme_id and product.pres_id.unme_id.descripcion != "-----":
                    unme_desc = product.pres_id.unme_id.descripcion

                datos_pres = pres_desc
                # if pres_desc:
                if med_cod_pres_desc:
                    if datos_pres:
                        datos_pres += " " + med_cod_pres_desc
                    else:
                        datos_pres = med_cod_pres_desc
                if unme_desc:
                    if datos_pres:
                        datos_pres += " " + unme_desc
                    else:
                        datos_pres = unme_desc
                if datos_pres:
                    name += " (" + datos_pres + ")"

                #DETALLE DE VARIANTE
                if product.det_variante_id:
                    marc_obj = self.pool.get('grp.sice_marca').search(cr, SUPERUSER_ID, [('cod', '=',
                                                                                  product.det_variante_id.marc_cod)])
                    if len(marc_obj) > 0:
                        marc_obj = marc_obj[0]
                    marc_obj = self.pool.get('grp.sice_marca').browse(cr, SUPERUSER_ID, marc_obj)
                    det_variante_desc = product.det_variante_id.descripcion if product.det_variante_id.descripcion != '-----' else ""
                    marc_desc = marc_obj.descripcion if marc_obj.descripcion != '-----' else ""

                    datos_var = marc_desc
                    if det_variante_desc:
                        if datos_var:
                            datos_var += " " + det_variante_desc
                        else:
                            datos_var = det_variante_desc
                    if datos_var:
                        name += " (" + datos_var + ")"

                result.append((product.id, name))
        return result

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            ids = False
            if name.isdigit():
                ids = self.search(cr, user, [('grp_sice_cod', '=', name)] + args, limit=limit, context=context)
            if not ids and operator not in expression.NEGATIVE_TERM_OPERATORS:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                ids = self.search(cr, user, args + [('default_code', operator, name)], limit=limit, context=context)
                if not limit or len(ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    limit2 = (limit - len(ids)) if limit else False
                    ids += self.search(cr, user, args + [('name', operator, name), ('id', 'not in', ids)], limit=limit2, context=context)
            elif not ids and operator in expression.NEGATIVE_TERM_OPERATORS:
                ids = self.search(cr, user, args + ['&', '|',('default_code', operator, name),('default_code','=',False), ('name', operator, name)], limit=limit, context=context)
            elif not ids and operator in positive_operators:
                # Se agrega la busqueda por los campos descripcion de atributos SICE
                ids = self.search(cr, user, [('med_cod_desc', 'ilike', '%' + name + '%')] + args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user, [('pres_desc', 'ilike', '%' + name + '%')]+ args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user, [('med_cod_pres_desc', 'ilike', '%' + name + '%')]+ args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user, [('det_variante_desc', 'ilike', '%' + name + '%')]+ args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user, [('sice_color_desc', 'ilike', '%' + name + '%')]+ args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user, [('marca_desc', 'ilike', '%' + name + '%')]+ args, limit=limit, context=context)
                # fin
                if not ids:
                    ids = self.search(cr, user, [('default_code','=', name)]+ args, limit=limit, context=context)
                if not ids:
                    ids = self.search(cr, user, [('ean13', '=', name)]+ args, limit=limit, context=context)
            if not ids and operator in positive_operators:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, user, [('default_code','=', res.group(2))] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result
    # 002-Fin

    @api.multi
    def unlink(self):
        for product in self:
            pool_sel_var = self.env['grp.seleccion.variantes.lineas']
            tmpl_id = product.product_tmpl_id.id
            sel_var_borrar = pool_sel_var.search([('product_id', '=', tmpl_id)])
            for variante in sel_var_borrar:
                if variante.med_cod_id.id == product.med_cod_id.id and\
                   variante.med_cod_pres_id.id == product.med_cod_pres_id.id and\
                   variante.pres_id.id == product.pres_id.id and\
                   variante.det_variante_id.id == product.det_variante_id.id:
                   variante.write({'creado': False, 'para_crear': False})
            art_serv_obra_pool = self.env['grp.sice_art_serv_obra']
        return super(grp_product, self).unlink()

grp_product()

class grp_product_template(models.Model):
    _name = "product.template"
    _inherit = "product.template"

    @api.multi
    def crear_producto_grp(self):
        for object in self:
            cant = 0
            for line in object.attribute_line_ids:
                if line.attribute_id.dimension_sice:
                    cant += 1
            if cant < 2:
                raise exceptions.ValidationError(_(u"Error! No se deben eliminar "
                                                   u"las lineas de atributos de dimensión SICE."))
        return True

    @api.multi
    def write(self, vals):
        # res = super(grp_product_template, self).write(vals)
        # sobreescritura del write estandar para modificar un control
        for product in self:
            if 'categ_id' in vals:
                categ_new = vals['categ_id']
                categ_new_obj = self.env['product.category'].browse([vals['categ_id']])
                if not categ_new_obj.parent_id or categ_new_obj.type in ['view']:
                    raise exceptions.ValidationError(_(u"Error! No se debe seleccionar "
                                                       u"una categoría padre, o de tipo Vista."))
            elif not product.categ_id.parent_id or product.categ_id.type in ['view']:
                raise exceptions.ValidationError(_(u"Error! No se debe seleccionar "
                                                   u"una categoría padre, o de tipo Vista."))
        if 'uom_po_id' in vals:
            new_uom = self.env['product.uom'].browse(vals['uom_po_id'])
            for product in self:
                old_uom = product.uom_po_id
                variantes = self.env['product.product'].search([('product_tmpl_id', '=', product.id)])
                # Solo se verifica la categoria del producto si no cargo el articulo desde la carga masiva por CSV
                if (not self._context.get('chequeo_categorias', False)) and old_uom.category_id.id != \
                        new_uom.category_id.id:
                    if variantes:
                        raise osv.except_osv(_('Unit of Measure categories Mismatch!'),
                                             _("New Unit of Measure '%s' must belong to same Unit of Measure category"
                                               " '%s' as of old Unit of Measure '%s'. If you need to change the unit of"
                                               " measure, you may deactivate this product from the 'Procurements' tab"
                                               " and create a new one.") % (new_uom.name, old_uom.category_id.name,
                                                                            old_uom.name,))
        if 'standard_price' in vals:
            for prod_template_id in self._ids:
                self._set_standard_price(prod_template_id, vals['standard_price'])
        res = models.Model.write(self, vals)
        if 'attribute_line_ids' in vals or vals.get('active'):
            self.create_variant_ids()
        if 'active' in vals and not vals.get('active'):
            ctx = self._context and self._context.copy() or {}
            ctx.update(active_test=False)
            product_ids = []
            for product in self:
                product_ids += map(int, product.product_variant_ids)
            self.env["product.product"].browse(product_ids).write({'active': vals.get('active')})
        # PCAR 24 07 2017 inicio
        if 'only_variants_total' in self._context or 'only_variants_parcial' in self._context:
            self.create_variant_ids()
        # PCAR 24 07 2017 fin
        if self._context.get('from_articulo_sice', False):
            for rec in self:
                sice_cod = False
                if 'grp_sice_cod' in vals:
                    sice_cod = vals['grp_sice_cod']
                else:
                    sice_cod = rec.grp_sice_cod
                articulo = self.env['grp.sice_art_serv_obra'].search([('cod', '=', sice_cod)])
                self._cr.execute("""
                    select art_im.imp_grp as id
                    from grp_sice_art_impuesto sice_im, grp_art_impuestos art_im
                    where sice_im.articulo_id = %s and cast (art_im.imp_sice as int) = sice_im.impuesto_id
                """, [articulo.id])
                tax_ids = []
                for res in self._cr.dictfetchall():
                    tax_ids.append(res['id'])
                if not rec.supplier_taxes_id:
                    raise exceptions.ValidationError(_(u'Error! Debe cargar un impuesto '
                                                       u'en el campo Impuestos proveedor.'))
                for line in rec.supplier_taxes_id:
                    if line.id not in tax_ids:
                        raise exceptions.ValidationError(_(u'Error! No se deben seleccionar impuestos no'
                                                           u' asociados al artículo SICE %s.') % articulo.descripcion)
                self._cr.execute("""
                select unme_id as id
                from grp_sice_art_unidades_med
                where articulo_id = %s
                """, [articulo.id])
                uom_ids = []
                for res in self._cr.dictfetchall():
                    uom_ids.append(res['id'])
                uom_id = False
                if 'uom_id' in vals:
                    uom_id = vals['uom_id']
                    uom_obj = self.env['product.uom'].search([('id', '=', uom_id)])
                    if isinstance(uom_obj, list):
                        uom_obj = uom_obj[0]
                    uom_id = uom_obj.sice_uom_id.id
                else:
                    uom_id = rec.uom_id.sice_uom_id.id
                if uom_id not in uom_ids:
                    raise exceptions.ValidationError(_(u'Error! No se debe seleccionar una unidad de medida no'
                                                       u' asociada al artículo SICE.'))
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(grp_product_template, self).fields_view_get(view_id=view_id,
                                                                view_type=view_type,
                                                                context=context,
                                                                toolbar=toolbar,
                                                                submenu=submenu)
        doc = etree.XML(res['arch'])

        if 'from_articulo_sice' in self._context:
            domain_user = str([('sice_uom_id', 'in', self._context.get('uom_ids', []))])
            domain_taxes = str([('id', 'in', self._context.get('tax_ids', []))])

            for node_tree in doc.xpath("//field[@name='uom_id']"):
                node_tree.set('domain', domain_user)

            for node_tree in doc.xpath("//field[@name='supplier_taxes_id']"):
                node_tree.set('domain', domain_taxes)

            res['arch'] = etree.tostring(doc)

        return res

    @api.model
    def create(self, vals):
        if not self._context.get('from_articulo_sice', False):
            if 'categ_id' in vals:
                categ_new = vals['categ_id']
                categ_new_obj = self.env['product.category'].browse([vals['categ_id']])
                if not categ_new_obj.parent_id or categ_new_obj.type in ['view']:
                    raise exceptions.ValidationError(_(u"Error! No se debe seleccionar "
                                                       u"una categoría padre, o de tipo Vista."))
        ''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
        product_template_id = super(grp_product_template, self).create(vals)
        if not self._context.get("hide_grp_buttons", False):
            if not self._context or "create_product_product" not in self._context:
                # self.create_variant_ids(cr, uid, [product_template_id.id], context=context)
                self.create_variant_ids()
        self._set_standard_price(product_template_id.id, vals.get('standard_price', 0.0))

        # TODO: this is needed to set given values to first variant after creation
        # these fields should be moved to product as lead to confusion
        related_vals = {}
        if vals.get('ean13'):
            related_vals['ean13'] = vals['ean13']
        if vals.get('default_code'):
            related_vals['default_code'] = vals['default_code']
        if related_vals:
            self.browse([product_template_id.id]).write(related_vals)

        return product_template_id

    @api.one
    def copy(self, default=None):
        if default is None:
            default = {}
        if self.grp_sice_cod:
            raise exceptions.ValidationError(_(u'Error! No es posible duplicar un artículo SICE.'))
        default.update({
            'attribute_line_ids': [(6, 0, self.attribute_line_ids.ids)]
        })
        return super(grp_product_template, self).copy(default=default)

    @api.multi
    def create_variant_parcial(self):
        product_obj = self.env["product.product"]
        ctx = self._context and self._context.copy() or {}

        if ctx.get("create_product_variant"):
            return None

        ctx.update(active_test=False, create_product_variant=True)

        for tmpl_id in self:
            # create new product
            product_att_val_obj = self.env["product.attribute.value"]
            lista_combinaciones = []
            if ctx.get("only_variants_total", False):
                lista_combinaciones = [l for l in tmpl_id.seleccion_variantes_ids if not l.creado]
            else:
                lista_combinaciones = [l for l in tmpl_id.seleccion_variantes_ids if l.para_crear and not l.creado]
            # if len(lista_combinaciones) == 0 and ctx.get('creacion_inicial', False):
            #     raise exceptions.ValidationError(_(u'Error! Debe seleccionar al menos una variante a crear.'))
            if len(lista_combinaciones) > 20:
                raise exceptions.ValidationError(_(u'Error! No es posible crear más de 20 variantes de un producto'
                                                   u' a la vez. Producto: %s') % tmpl_id.name)
            for variant in tmpl_id.seleccion_variantes_ids:
                condicion = variant.para_crear and not variant.creado
                if ctx.get("only_variants_total", False):
                    condicion = not variant.creado
                # if variant.para_crear and not variant.creado:
                if condicion:
                    art_obj = self.env["grp.sice_art_serv_obra"].search([('cod', '=', tmpl_id.grp_sice_cod)])
                    domain = [('sice_color_id', '=', variant.sice_color_id.id)]
                    variant_ids = []
                    variant_color_id = product_att_val_obj.search(domain)
                    if len(variant_color_id) > 0:
                        variant_color_id = variant_color_id[0]
                    if variant_color_id.id:
                        variant_ids.append(variant_color_id.id)
                    domain = [
                        ('attribute_id', '=', tmpl_id.attribute_id.id),
                        ('articulo_id', '=', art_obj.id),
                        ('sice_color_id', '=', False),
                        ('med_cod_id', '=', variant.med_cod_id.id),
                        ('pres_id', '=', variant.pres_id.id),
                        ('med_cod_pres_id', '=', variant.med_cod_pres_id.id),
                    ]
                    if variant.det_variante_id:
                        domain.append(('det_variante_id', '=', variant.det_variante_id.id))
                    else:
                        domain.append(('det_variante_id', '=', False))
                    variant_sin_color_id = product_att_val_obj.search(domain)
                    if len(variant_sin_color_id) > 0:
                        variant_sin_color_id = variant_sin_color_id[0]
                    if variant_sin_color_id.id:
                        variant_ids.append(variant_sin_color_id.id)

                    if variant.valor_id:
                        variant_no_sice_id = product_att_val_obj.browse(variant.valor_id.id)
                        if variant_no_sice_id.id:
                            variant_ids.append(variant_no_sice_id.id)
                    values = {
                        'product_tmpl_id': tmpl_id.id,
                        'attribute_value_ids': [(6, 0, variant_ids)],
                    }

                    for var in variant_ids:
                        val = product_att_val_obj.browse(var)
                        if val.attribute_id.name == 'COLOR':
                            if val.name != 'NINGUNO':
                                values.update({
                                    'sice_color_id': val.sice_color_id.id
                                })
                        elif tmpl_id.attribute_id and val.attribute_id.id == tmpl_id.attribute_id.id:
                            values.update({
                                'med_cod_id': val.med_cod_id.id,
                                'pres_id': val.pres_id.id,
                                'med_cod_pres_id': val.med_cod_pres_id.id,
                                'det_variante_id': val.det_variante_id.id
                            })
                    id = product_obj.with_context(ctx).create(values)
                    variant.write({'creado': True})
        return True

    @api.multi
    def create_variant_ids(self):
        product_obj = self.env["product.product"]
        product_tmpl_obj = self.env["product.template"]
        ctx = self._context and self._context.copy() or {}

        if not ctx.get('from_articulo_sice', False):
            return super(grp_product_template, self).create_variant_ids()

        if not ctx.get("cargar_variantes", False):
            return self.create_variant_parcial()

        if ctx.get("only_variants_total", False):
            return self.create_variant_parcial()

        if ctx.get("create_product_variant"):
            return None

        ctx.update(active_test=False, create_product_variant=True)

        for tmpl_id in self:

            # list of values combination
            variant_alone = []
            all_variants = [[]]
            for variant_id in tmpl_id.attribute_line_ids:
                if len(variant_id.value_ids) == 1:
                    variant_alone.append(variant_id.value_ids[0])
                temp_variants = []
                for variant in all_variants:
                    for value_id in variant_id.value_ids:
                        temp_variants.append(sorted(variant + [int(value_id)]))
                if temp_variants:
                    all_variants = temp_variants

            # adding an attribute with only one value should not recreate product
            # write this attribute on every product to make sure we don't lose them
            for variant_id in variant_alone:
                product_ids = []
                for product_id in tmpl_id.product_variant_ids:
                    if variant_id.id not in map(int, product_id.attribute_value_ids):
                        product_ids.append(product_id.id)
                product_obj.browse(product_ids).with_context(ctx).write({
                    'attribute_value_ids': [(4, variant_id.id)]
                })

            # check product
            variant_ids_to_active = []
            variants_active_ids = []
            variants_inactive = []
            for product_id in tmpl_id.product_variant_ids:
                variants = sorted(map(int, product_id.attribute_value_ids))
                if variants in all_variants:
                    variants_active_ids.append(product_id.id)
                    all_variants.pop(all_variants.index(variants))
                    if not product_id.active:
                        variant_ids_to_active.append(product_id.id)
                else:
                    variants_inactive.append(product_id)
            if variant_ids_to_active:
                product_obj.browse(variant_ids_to_active).with_context(ctx).write(variant_ids_to_active,
                                                                                  {'active': True})

            # create new product
            product_att_val_obj = self.env["product.attribute.value"]
            # if len(all_variants) == 0:
            #     raise exceptions.ValidationError(_(u'Error! Debe seleccionar al menos una variante a crear.'))
            if len(all_variants) > 20:
                raise exceptions.ValidationError(_(u'Error! No es posible crear más de 20 variantes de un producto'
                                                   u' a la vez. Producto: %s') % tmpl_id.name)
            for variant_ids in all_variants:
                values = {
                    'product_tmpl_id': tmpl_id.id,
                    'attribute_value_ids': [(6, 0, variant_ids)],
                }
                attribute_id = False
                for var in variant_ids:
                    val = product_att_val_obj.browse(var)
                    if val.attribute_id.name == 'COLOR':
                        if val.name != 'NINGUNO':
                            values.update({
                                'sice_color_id': val.sice_color_id.id
                            })
                    elif tmpl_id.attribute_id and val.attribute_id.id == tmpl_id.attribute_id.id:
                        values.update({
                            'med_cod_id': val.med_cod_id.id,
                            'pres_id': val.pres_id.id,
                            'med_cod_pres_id': val.med_cod_pres_id.id,
                            'det_variante_id': val.det_variante_id.id
                        })
                        attribute_id = val.attribute_id.id
                id = product_obj.with_context(ctx).create(values)
                variants_active_ids.append(id)
                product_tmpl_obj.browse([tmpl_id.id]).write({'attribute_id': attribute_id})
            tmpl_id.seleccion_variantes_ids.write({'creado': True})

            # unlink or inactive product
            for variant_id in map(int,variants_inactive):
                try:
                    with self._cr.savepoint(), tools.mute_logger('openerp.sql_db'):
                        product_obj.browse([variant_id]).with_context(ctx).unlink([variant_id])
                except (psycopg2.Error, osv.except_osv):
                    product_obj.browse([variant_id]).with_context(ctx).write({'active': False})
                    pass
        return True

    @api.multi
    def cargar_combinaciones(self):
        for rec in self:
            combinaciones = [svar for svar in rec.seleccion_variantes_ids]
            for line in rec.attribute_line_ids:
                if not line.attribute_id.dimension_sice:
                    for v in line.value_ids:
                        att_vals = [s.valor_id.id for s in rec.seleccion_variantes_ids if s.valor_id and v.id == s.valor_id.id]
                        if len(att_vals) == 0:
                            for svar in combinaciones:
                                values = {
                                    'product_id': svar.product_id.id,
                                    'atributo_id': line.attribute_id.id,
                                    'valor_id': v.id,
                                    'atributo_name': line.attribute_id.name,
                                    'valor_name': v.name,

                                    'sice_color_id': svar.sice_color_id and svar.sice_color_id.id or False,
                                    'med_cod_id': svar.med_cod_id and svar.med_cod_id.id or False,
                                    'pres_id': svar.pres_id and svar.pres_id.id or False,
                                    'med_cod_pres_id': svar.med_cod_pres_id and svar.med_cod_pres_id.id or False,
                                    'det_variante_id': svar.det_variante_id and svar.det_variante_id.id or False,

                                    'med_cod_desc': svar.med_cod_id and svar.med_cod_desc or '',
                                    'pres_desc': svar.pres_id and svar.pres_desc or '',
                                    'med_cod_pres_desc': svar.med_cod_pres_id and svar.med_cod_pres_desc or '',
                                    'det_variante_desc': svar.det_variante_id and svar.det_variante_desc or '',
                                    'sice_color_desc': svar.sice_color_id and svar.sice_color_desc or '',
                                    'marca_desc': svar.det_variante_id and svar.marca_desc or '',
                                }
                                self.env['grp.seleccion.variantes.lineas'].create(values)
            sel_var_borrar = [sel for sel in rec.seleccion_variantes_ids if not sel.creado]
            for variante in sel_var_borrar:
                domain = [('product_tmpl_id', '=', rec.id),
                          ('med_cod_id', '=', variante.med_cod_id.id),
                          ('pres_id', '=', variante.pres_id.id),
                          ('med_cod_pres_id', '=', variante.med_cod_pres_id.id)]
                if variante.sice_color_id:
                    domain.append(('sice_color_id', '=', variante.sice_color_id.id))
                else:
                    domain.append(('sice_color_id', '=', False))
                if variante.det_variante_id:
                    domain.append(('det_variante_id', '=', variante.det_variante_id.id))
                else:
                    domain.append(('det_variante_id', '=', False))
                prod = self.env['product.product'].search(domain)
                if prod:
                    prod.unlink()

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.template',
            'res_id': rec.id,
            'target': 'new',
            'context': self._context,
        }

    @api.multi
    def unlink(self):
        for tmpl_obj in self:
            if tmpl_obj.seleccion_variantes_ids:
                tmpl_obj.seleccion_variantes_ids.unlink()
        return super(grp_product_template, self).unlink()

    attribute_id = fields.Many2one(
        comodel_name='product.attribute',
        string=u'Atributo'
    )
    seleccion_variantes_ids = fields.One2many(
        comodel_name='grp.seleccion.variantes.lineas',
        inverse_name='product_id',
        string=u'Combinaciones para crear'
    )

grp_product_template()

#  Clase para la carga de las combinaciones validas para seleccionar en la creacion de un producto
class GrpSeleccionVariantesLineas(models.Model):
    _name = 'grp.seleccion.variantes.lineas'

    product_id = fields.Many2one(
        comodel_name='product.template',
        string=u'Producto'
    )
    para_crear = fields.Boolean(u'Para Crear', default=False)
    creado = fields.Boolean(u'Creado', default=False)
    med_cod_id = fields.Many2one('grp.sice_medida', string=u'Medida de la variante')
    pres_id = fields.Many2one('grp.sice_presentacion', string='Presentacion')
    med_cod_pres_id = fields.Many2one('grp.sice_medida', string=u'Medida de la presentación')
    det_variante_id = fields.Many2one('grp.sice_det_variante', string='Detalle de variante')
    sice_color_id = fields.Many2one('grp.sice_color', string='Color SICE')
    atributo_id = fields.Many2one('product.attribute', string='Atributo')
    valor_id = fields.Many2one('product.attribute.value', string='Valor atributo')

    atributo_name = fields.Char(string=u'Atributo')
    valor_name = fields.Char(string=u'Valor atributo')
    med_cod_desc = fields.Char(string=u'Medida variante')
    pres_desc = fields.Char(string=u'Presentación')
    med_cod_pres_desc = fields.Char(string=u'Medida presentación')
    det_variante_desc = fields.Char(string=u'Detalle variante')
    sice_color_desc = fields.Char(string=u'Color')
    marca_desc = fields.Char(string=u'Marca')


#----------------------------------------------------------
# Product Attributes
#----------------------------------------------------------
class grp_product_attribute(models.Model):
    _inherit = "product.attribute"

    sice_propiedad_id = fields.Many2one('grp.sice_propiedad', string='Variante SICE')
    sice_propiedad_cod = fields.Integer(related='sice_propiedad_id.cod', string=u'Código de variante SICE')
    dimension_sice = fields.Boolean(string=u'Es dimensión SICE', default=False)


class grp_product_attribute_value(models.Model):
    _inherit = "product.attribute.value"

    articulo_id = fields.Many2one('grp.sice_art_serv_obra', string=u'Artículo')
    med_cod_id = fields.Many2one('grp.sice_medida', string=u'Medida de la variante')
    pres_id = fields.Many2one('grp.sice_presentacion', string='Presentacion')
    med_cod_pres_id = fields.Many2one('grp.sice_medida', string=u'Medida de la presentación')
    det_variante_id = fields.Many2one('grp.sice_det_variante', string='Detalle de variante')
    sice_color_id = fields.Many2one('grp.sice_color', string='Color SICE')
    active = fields.Boolean(string=u'Activo', default=True)

    @api.multi
    def name_get(self):
        if self._context and not self._context.get('show_attribute', True):
            return super(grp_product_attribute_value, self).name_get()
        res = []
        for value in self:
            if not value.articulo_id:
                res.append((value.id, value.name))
            else:
                name = ""
                color = False
                det_variante_desc = False
                marc_desc = False

                if value.sice_color_id:
                    color = value.sice_color_id.descripcion
                    name += " " + color
                att_desc = False
                if value.attribute_id:
                    att_desc = value.attribute_id.name
                    name += " (" + att_desc
                else:
                    name += " (-----"
                med_cod_desc = value.med_cod_id.descripcion
                name += ": " + med_cod_desc + ")"
                med_cod_pres_desc = value.med_cod_pres_id.descripcion
                pres_desc = value.pres_id.descripcion
                if value.pres_id.unme_id:
                    name += " (" + pres_desc + ": " + med_cod_pres_desc + " " + value.pres_id.unme_id.descripcion + ")"
                else:
                    name += " (" + pres_desc + ": " + med_cod_pres_desc + ")"
                if value.det_variante_id:
                    marc_obj = self.env['grp.sice_marca'].search([('cod', '=',
                                                                  value.det_variante_id.marc_cod)])
                    if len(marc_obj) > 0:
                        marc_obj = marc_obj[0]
                    det_variante_desc = value.det_variante_id.descripcion
                    marc_desc = marc_obj.descripcion
                    if marc_desc:
                        name += " (" + marc_desc + ", "
                    else:
                        name += " ( False, "
                    if det_variante_desc:
                        name += det_variante_desc + ")"
                    else:
                        name += "False)"
                    # name += " (" + marc_desc + ", " + det_variante_desc + ")"
                res.append((value.id, name))
        return res

class GrpProductAttributeLine(models.Model):
    _inherit = 'product.attribute.line'

    solo_lectura = fields.Boolean(string=u'Sólo lectura', default=False)

