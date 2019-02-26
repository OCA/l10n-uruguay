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

import logging
import openerp
from openerp import api, exceptions, fields, models
from openerp.tools.translate import _
import csv
import base64
import codecs, os
_logger = logging.getLogger(__name__)


class GrpImportarArticulos(models.Model):
    _name = 'grp.importar.articulos'
    _rec_name = 'csv_filename'

    csv_file = fields.Binary(u'Archivo')
    csv_filename = fields.Char(
        string=u'Nombre de archivo',
        size=256
    )

    @api.multi
    def cargar_articulos(self):

        def get_uom_id(self, obj):
            """Retorna id de la unidad de medida"""

            unme_id = obj.unme_id.id
            uom_id = False

            # Si existe la unidad, retornamos su id
            self.env.cr.execute("select id from product_uom where sice_uom_id = %(unme_id)s", {'unme_id': unme_id})

            if self.env.cr.rowcount > 0:
                res = self.env.cr.fetchone()
                uom_id = res[0]

            return uom_id

        def get_tax_id(self, obj):
            """Retorna id del impuesto correspondiente al mapeo"""

            imp_cod = obj.imp_cod
            tax_id = False

            self.env.cr.execute("select imp_grp from grp_art_impuestos where cast (imp_sice as float) = %(imp_sice)s",
                                {'imp_sice': imp_cod})
            if self.env.cr.rowcount > 0:
                res = self.env.cr.fetchone()
                tax_id = res[0]
            else:
                tax_id = 0

            return tax_id

        for rec in self:
            decoded_binary_data = self.csv_file.decode('base64').decode('UTF-8')
            data_splitted = decoded_binary_data.split("\n")
            vals = {}
            i = 1
            if (len(data_splitted) - 1) > 100:
                raise exceptions.ValidationError(u'El archivo CSV no debe contener más de 100 filas.')
            for row in data_splitted:
                if i == 1:
                    i += 1
                    continue
                row_splitted = []
                row_splitted_comma = row.split(",")
                row_splitted_dot_comma = row.split(";")
                if len(row_splitted_comma) <= 22 and len(row_splitted_dot_comma) > 22:
                    row_splitted = row_splitted_dot_comma
                elif len(row_splitted_dot_comma) <= 22 and len(row_splitted_comma) > 22:
                    row_splitted = row_splitted_comma
                else:
                    continue
                # if len(row_splitted) <= 1:
                #     continue
                cantidad = 0
                vals.update({
                    'name': row_splitted[2],
                    'grp_sice_cod': row_splitted[1],
                    'uom_desc': row_splitted[5],
                    'var_desc': row_splitted[6],
                    'med_var_desc': row_splitted[7],
                    'pres_desc': row_splitted[9],
                    'med_pres_desc': row_splitted[10],
                    'uom_pres_desc': row_splitted[11],
                    'color_desc': (row_splitted[12] != '') and row_splitted[12] or u'NINGUNO',
                    'imp_desc': row_splitted[16],
                    'stockeable': row_splitted[21],
                    'cat_desc': row_splitted[22],
                    'grp_objeto_del_gasto': row_splitted[15],
                    'tipo_art': row_splitted[13],
                })
                pool_sice_art_serv_obra = self.env['grp.sice_art_serv_obra']
                articulo = pool_sice_art_serv_obra.search([('cod', '=', vals['grp_sice_cod'])])
                context = {}
                context['from_articulo_sice'] = True
                prod_uom_id = get_uom_id(self, articulo)
                prod_imp_id = get_tax_id(self, articulo)
                prod_tmp = self.env['product.template'].search([('grp_sice_cod', '=', articulo.cod)])
                self._cr.execute("""
                    select unme_id as id
                    from grp_sice_art_unidades_med
                    where articulo_id = %s
                """, [articulo.id])
                uom_ids = []
                for res in self._cr.dictfetchall():
                    uom_ids.append(res['id'])
                context['uom_ids'] = uom_ids
                self._cr.execute("""
                    select art_im.imp_grp as id
                    from grp_sice_art_impuesto sice_im, grp_art_impuestos art_im
                    where sice_im.articulo_id = %s and cast (art_im.imp_sice as int) = sice_im.impuesto_id
                """, [articulo.id])
                tax_ids = []
                for res in self._cr.dictfetchall():
                    tax_ids.append(res['id'])
                context['tax_ids'] = tax_ids

                colors_list = [color.id for color in articulo.art_color_ids]
                _logger.info("Colores ids: %s", colors_list)
                lineas = []
                lista_variantes = []
                lista_variantes_write = []
                list_lineas = []
                attribute_id = False
                if vals['uom_desc'] == '':
                    raise exceptions.ValidationError(u'No se especificó unidad de medida para el artículo %s.'
                                                     % vals['name'])
                if vals['cat_desc'] == '':
                    raise exceptions.ValidationError(u'No se especificó categoría para el artículo %s.'
                                                     % vals['name'])
                desc_uom = vals['uom_desc']
                unidades_med_sice = self.env['grp.sice_unidades_med'].search([('descripcion', '=', desc_uom)])
                if len(unidades_med_sice) > 0:
                    unidades_med_sice = unidades_med_sice[0]
                unidades_grp = self.env['product.uom'].search([('sice_uom_id', '=', unidades_med_sice.id)])
                if len(unidades_grp) > 0:
                    unidades_grp = unidades_grp[0]
                parent_split = vals['cat_desc'].split(' /')
                categs = []
                if len(parent_split) > 1:
                    parent_name = parent_split[0]
                    child_name = vals['cat_desc'].split('/ ')[1]
                    if child_name[-1] == '\r':
                        child_name = child_name[:-1]
                    categs = self.env['product.category'].search([('parent_id.name', '=', parent_name),
                                                                  ('name', '=', child_name)])
                else:
                    categs = self.env['product.category'].search([('name', '=', parent_split[0])])
                if len(categs) > 0:
                    categs = categs[0]
                prod_uom_id = unidades_grp.id if unidades_grp else False
                categ_id = categs.id if categs else False
                if not prod_uom_id:
                    raise exceptions.ValidationError(u'La unidad de medida %s no está mapeada en GRP.'
                                                     % desc_uom)
                if not categ_id:
                    raise exceptions.ValidationError(u'La categoría de nombre %s no existe en GRP.'
                                                     % vals['cat_desc'])
                tipo = 'consu'
                if vals['stockeable'] in [u'Sí', u'Si']:
                    tipo = 'product'
                elif vals['tipo_art'] in ['Servicio', 'Obra']:
                    tipo = 'service'
                if colors_list:
                    colors_list = tuple(colors_list)
                    self._cr.execute("""
                        select patv.id as id, pat.id as attribute_id from product_attribute pat, product_attribute_value patv
                        where patv.attribute_id = pat.id and pat.dimension_sice
                        and patv.sice_color_id in %s
                    """, [colors_list])
                    primero = True
                    for res in self._cr.dictfetchall():
                        if primero:
                            value_id = res['attribute_id']
                            dicc = {'attribute_id': value_id}
                            primero = False
                        att_id = res['id']
                        lineas.append(att_id)
                        atv_color = self.env['product.attribute.value'].browse(att_id)
                        att_values = self.env['product.attribute.value'].search([('articulo_id', '=', articulo.id)])
                        for atv in att_values:
                            values = {
                                'sice_color_id': atv_color.sice_color_id.id,
                                'med_cod_id': atv.med_cod_id.id,
                                'pres_id': atv.pres_id.id,
                                'med_cod_pres_id': atv.med_cod_pres_id.id,
                            }
                            det_var_id = False
                            if atv.det_variante_id:
                                det_var_id = atv.det_variante_id.id
                            med_cod_desc = ""
                            if atv.med_cod_id:
                                med_cod_desc = atv.med_cod_id.descripcion
                            pres_desc = ""
                            if atv.pres_id:
                                pres_desc = atv.pres_id.descripcion
                            med_cod_pres_desc = ""
                            if atv.med_cod_pres_id:
                                med_cod_pres_desc = atv.med_cod_pres_id.descripcion
                            sice_color_desc = ""
                            if atv_color.sice_color_id:
                                sice_color_desc = atv_color.sice_color_id.descripcion
                            det_var_desc = ""
                            marca = ""
                            if atv.det_variante_id:
                                det_var_desc = atv.det_variante_id.descripcion
                                med_pool = self.env['grp.sice_marca']
                                marca_obj = med_pool.search([('cod', '=', atv.det_variante_id.marc_cod)])
                                marca = marca_obj.descripcion
                            values.update({
                                'med_cod_desc': med_cod_desc,
                                'pres_desc': pres_desc,
                                'med_cod_pres_desc': med_cod_pres_desc,
                                'sice_color_desc': sice_color_desc,
                                'marca_desc': marca,
                                'det_variante_desc': det_var_desc,
                                'det_variante_id': det_var_id,
                                'creado': False,
                                'para_crear': False,
                            })
                            variante_creada = []
                            if prod_tmp:
                                variante_creada = self.env['grp.seleccion.variantes.lineas'].search([
                                    ('product_id', '=', prod_tmp.id),
                                    ('med_cod_desc', '=', vals['med_var_desc']),
                                    ('pres_desc', '=', vals['pres_desc']),
                                    ('med_cod_pres_desc', '=', vals['med_pres_desc']),
                                    ('sice_color_desc', '=', vals['color_desc']),
                                    ('creado', '=', True),
                                ])
                            if vals['med_var_desc'] == values['med_cod_desc'] and\
                               vals['pres_desc'] == values['pres_desc'] and\
                               vals['med_pres_desc'] == values['med_cod_pres_desc'] and\
                               vals['color_desc'] == values['sice_color_desc'] and not len(variante_creada):
                                cantidad += 1
                                values.update({
                                    'creado': False,
                                    'para_crear': True
                                })
                            elif len(variante_creada):
                                values.update({
                                    'creado': True,
                                    'para_crear': True
                                })
                                # correccion de datos erroneos
                                campos = {
                                    'purchase_ok': True,
                                    'valuation': 'real_time',
                                    'property_account_income': categs.property_account_income_categ.id,
                                    'property_account_expense': categs.property_account_expense_categ.id,
                                    'type': tipo,
                                    'uom_po_id': prod_uom_id,
                                    'uom_id': prod_uom_id,
                                    'categ_id': categ_id,
                                }
                                if (not prod_tmp.purchase_ok or prod_tmp.valuation != 'real_time' or
                                        prod_tmp.property_account_income.id != categs.property_account_income_categ.id or
                                        prod_tmp.property_account_expense.id != categs.property_account_expense_categ.id
                                        or prod_tmp.type != tipo or prod_tmp.uom_id.id != prod_uom_id or
                                        prod_tmp.uom_po_id.id != prod_uom_id or prod_tmp.categ_id.id != categ_id):
                                    ctx = self._context.copy()
                                    ctx = dict(ctx)
                                    ctx.update({'chequeo_categorias': True})
                                    _logger.info("UPDATE PROD TEMPLATE")
                                    prod_tmp.with_context(ctx).write(campos)
                                # fin correccion de datos erroneos
                            attribute_id = atv.attribute_id.id
                            lista_variantes.append((0, 0, values))
                    dicc.update({'value_ids': [(6, 0, lineas)],
                                'solo_lectura': True})
                    list_lineas.append((0, 0, dicc))

                variante_id = articulo.var_id.id
                att_obj = self.env['product.attribute'].search([('sice_propiedad_id', '=', variante_id)])
                # variantes_list = [med.med_cod_id.id for med in articulo.variante_ids]
                att_values = self.env['product.attribute.value'].search([('articulo_id', '=', articulo.id)])
                if att_values:
                    dicc = {
                        'attribute_id': att_obj.id,
                        'value_ids': [(6, 0, att_values.ids)],
                        'solo_lectura': True
                    }
                    list_lineas.append((0, 0, dicc))

                # if vals['uom_desc'] == '':
                #     raise exceptions.ValidationError(u'No se especificó unidad de medida para el artículo %s.'
                #                                      % vals['name'])
                # if vals['cat_desc'] == '':
                #     raise exceptions.ValidationError(u'No se especificó categoría para el artículo %s.'
                #                                      % vals['name'])
                # desc_uom = vals['uom_desc']
                # unidades_med_sice = self.env['grp.sice_unidades_med'].search([('descripcion', '=', desc_uom)])
                # if len(unidades_med_sice) > 0:
                #     unidades_med_sice = unidades_med_sice[0]
                # unidades_grp = self.env['product.uom'].search([('sice_uom_id', '=', unidades_med_sice.id)])
                # if len(unidades_grp) > 0:
                #     unidades_grp = unidades_grp[0]
                # parent_split = vals['cat_desc'].split(' /')
                # categs = []
                # if len(parent_split) > 1:
                #     parent_name = parent_split[0]
                #     child_name = vals['cat_desc'].split('/ ')[1]
                #     categs = self.env['product.category'].search([('parent_id.name', '=', parent_name),
                #                                                   ('name', '=', child_name)])
                # else:
                #     categs = self.env['product.category'].search([('name', '=', parent_split[0])])
                # if len(categs) > 0:
                #     categs = categs[0]
                # prod_uom_id = unidades_grp.id if unidades_grp else False
                # categ_id = categs.id if categs else False
                # if not prod_uom_id:
                #     raise exceptions.ValidationError(u'La unidad de medida %s no está mapeada en GRP.'
                #                                      % desc_uom)
                # if not categ_id:
                #     raise exceptions.ValidationError(u'La categoría de nombre %s no existe en GRP.'
                #                                      % vals['cat_desc'])
                # tipo = 'consu'
                # if vals['stockeable'] in [u'Sí', u'Si']:
                #     tipo = 'product'
                # elif vals['tipo_art'] in ['Servicio', 'Obra']:
                #     tipo = 'service'
                campos = {
                    'is_multi_variants': True,
                    'type': tipo,
                    'cost_method': 'real',
                    'uom_po_id': prod_uom_id,
                    'uom_id': prod_uom_id,
                    'categ_id': categ_id,
                    'grp_objeto_del_gasto': articulo.odg,
                    'grp_sice_cod': articulo.cod,
                    'name': articulo.descripcion,
                    'description': "Nombre SICE: " + articulo.descripcion,
                    'attribute_line_ids': list_lineas,
                    'seleccion_variantes_ids': lista_variantes,
                    'attribute_id': attribute_id,
                    'sale_ok': False,
                    'purchase_ok': True,
                    'valuation': 'real_time',
                    'property_account_income': categs.property_account_income_categ.id,
                    'property_account_expense': categs.property_account_expense_categ.id,
                }
                impuestos = self.env['account.tax'].search([('name', '=', vals['imp_desc'])])
                if len(impuestos) > 0:
                    impuestos = impuestos[0]
                if impuestos.id:
                    campos['supplier_taxes_id'] = [(6, 0, [impuestos.id])]
                else:
                    raise exceptions.ValidationError(u'El impuesto de nombre %s no existe en GRP.'
                                                     % vals['imp_desc'])
                # property_account_income = categs.property_account_income_categ.id
                # property_account_expense = categs.property_account_expense_categ.id
                # duda: supplier_taxes_id para tomarlo de columna Impuesto busco por descripcion ?
                # if prod_imp_id:
                #     campos.update({'supplier_taxes_id': [(6, 0, [prod_imp_id])]})
                context['hide_grp_buttons'] = True
                context['creacion_inicial'] = True
                context['cargar_variantes'] = False
                context['generar_variantes'] = True
                context['chequeo_categorias'] = True
                if not prod_tmp:
                    created_id = self.env['product.template'].with_context(context).create(campos)
                    # context['creacion_inicial'] = False
                    # created_id.with_context(context).create_variant_ids()
                else:
                    context['creacion_inicial'] = False
                    pool_seleccion_variantes = self.env['grp.seleccion.variantes.lineas']
                    variantes = pool_seleccion_variantes.search([
                        ('product_id', '=', prod_tmp.id),
                        ('para_crear', '=', False),
                        ('med_cod_desc', '=', vals['med_var_desc']),
                        ('pres_desc', '=', vals['pres_desc']),
                        ('med_cod_pres_desc', '=', vals['med_pres_desc']),
                        ('sice_color_desc', '=', vals['color_desc']),
                    ])
                    if len(variantes) > 0:
                        pool_seleccion_variantes.browse(variantes.ids).write({'para_crear': True, 'creado': False})
                        prod_tmp.with_context(context).create_variant_ids()
        return True

