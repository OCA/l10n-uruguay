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

_logger = logging.getLogger(__name__)
import sys
reload(sys)
sys.setdefaultencoding('utf8')


class grpSiceArtServObra(models.Model):

    # Atributos privados
    _name = 'grp.sice_art_serv_obra'
    _order = "cod"
    _rec_name = 'descripcion'
    _description = u'Artículos SICE'

    # Declaración de campos

    # Campos requeridos
    cod = fields.Integer(string=u'Código', required=True, index=True)
    descripcion = fields.Char(string=u'Descripción', size=200, required=True, index=True)

    fami_id = fields.Many2one('grp.sice_familia', string='Familia', required=True)
    subf_id = fields.Many2one('grp.sice_subflia', string='Subfamilia', required=True)
    clas_id = fields.Many2one('grp.sice_clase', string='Clase', required=True)
    subc_id = fields.Many2one('grp.sice_subclase', string='Subclase', required=True)

    fami_cod = fields.Integer(related='fami_id.cod', string=u'Código de Familia', store=True, index=True)
    subf_cod = fields.Integer(related='subf_id.cod', string=u'Código de Subfamilia', store=True, index=True)
    clas_cod = fields.Integer(related='clas_id.cod', string=u'Código de Clase', store=True, index=True)
    subc_cod = fields.Integer(related='subc_id.cod', string=u'Código de Subclase', store=True, index=True)

    # fami_cod = fields.Integer(related='fami_id.cod', string=u'Código de Familia')
    # subf_cod = fields.Integer(related='subf_id.cod', string=u'Código de Subfamilia')
    # clas_cod = fields.Integer(related='clas_id.cod', string=u'Código de Clase')
    # subc_cod = fields.Integer(related='subc_id.cod', string=u'Código de Subclase')

    # Variante
    var_id = fields.Many2one('grp.sice_propiedad', string='Variante', required=True)
    var_cod = fields.Integer(related='var_id.cod', string=u'Código de variante', store=True, index=True)
    # var_cod = fields.Integer(related='var_id.cod', string=u'Código de variante')

    # Indica el tipo: articulo, servicio u obra
    ind_art_serv = fields.Selection([('A',u'Artículo'),('S','Servicio'),('O','Obra')], string='Tipo', required=True)

    # Indicador de dificil fraccionamiento
    ind_fraccion = fields.Selection([('S','Si'),('N','No')], string=u'Difícil fraccionamiento', required=True)

    # Indica si cualquiera puede iniciar la compra o hay alguien encargado
    ind_gestionable = fields.Selection([('S','Si'),('N','No')], string='Gestionable', required=True)

    # Indica si el articulo se compra mediante compra agrupadda (en forma conjunta para varias reparticiones)
    ind_agrupable  = fields.Selection([('S','Si'),('N','No')], string='Agrupable', required=True)

    comprable = fields.Selection([('S', 'Si'), ('N', 'No')], string='Comprable', required=True)

    # Campos no requeridos
    var_unme_cod = fields.Integer(related='var_unme_id.cod', string=u'Código de unidad de medida de la variante',
                                  store=True, index=True)
    # var_unme_cod = fields.Integer(related='var_unme_id.cod', string=u'Código de unidad de medida de la variante')
    var_unme_id = fields.Many2one('grp.sice_unidades_med', string='Unidad de medida de la variante')

    unme_cod = fields.Integer(related='unme_id.cod', string=u'Código de unidad de medida', store=True, index=True)
    # unme_cod = fields.Integer(related='unme_id.cod', string=u'Código de unidad de medida')
    unme_id  = fields.Many2one('grp.sice_unidades_med', string='Unidad de medida')

    imp_cod = fields.Integer(related='imp_id.cod', string=u'Código de impuesto', store=True, index=True)
    # imp_cod = fields.Integer(related='imp_id.cod', string=u'Código de impuesto')
    imp_id  = fields.Many2one('grp.sice_impuesto', string='Impuesto')

    # Indica si el articulo es stockeable
    stockeable = fields.Selection([('S','Si'),('N','No')], string='Stockeable')

    # Indica en caso de ser stockeable, si dicho stock debe reflejarse contablemente o simplemente interesa llevarse su inventario
    stock_contable = fields.Selection([('S','Si'),('N','No')], string='Stock Contable')

    # Indica el tipo de detalle de la variante del articulo (medicamento, repuesto)
    ind_tipo_detalle = fields.Selection([('M','Medicamento'),('R','Repuesto')], string='Tipo de detalle')

    odg = fields.Integer(related='odg_id.odg', string=u'Código Odg', store=True, index=True)
    # odg = fields.Integer(related='odg_id.odg', string=u'Código Odg')
    odg_id = fields.Many2one('grp.sice_odg', string='Odg')
    odg_desc = fields.Char(related='odg_id.descripcion', string=u'Descripción Odg')

    esp_tecnicas = fields.Char(string=u'Especificación técnica', size=2000)

    fecha_baja = fields.Date(string='Fecha de baja')
    motivo_baja = fields.Char(string='Motivo de baja', size=200)

    active = fields.Boolean(string='Activo', default=True)

    art_impuesto_ids = fields.Many2many(comodel_name="grp.sice_impuesto",
                                        relation="grp_sice_art_impuesto",
                                        column1="articulo_id", column2="impuesto_id",
                                        string=u'Impuestos del artículo')

    art_color_ids = fields.Many2many(comodel_name="grp.sice_color",
                                        relation="grp_sice_art_color",
                                        column1="articulo_id", column2="color_id",
                                        string=u'Colores del artículo')

    unidades_med_ids = fields.Many2many(comodel_name="grp.sice_unidades_med",
                                        relation="grp_sice_art_unidades_med",
                                        column1="articulo_id", column2="unme_id",
                                        string=u'Unidades de medida del artículo')


    atributo_ids = fields.One2many('grp.sice_art_atributo', 'articulo_id', u'Atributos del artículo')

    variante_ids = fields.One2many('grp.sice_med_variante', 'articulo_id', u'Variantes del artículo')
    det_variante_ids  = fields.One2many('grp.sice_det_variante', 'articulo_id', u'Detalle de variantes del artículo')

    search_id = fields.Many2one('grp.sice_art_serv_busqueda', string=u'Búsqueda asociada')
    modificado = fields.Boolean(string='Modificado', default=False)

    sinonimo_ids = fields.One2many('grp.sice_sinonimo', 'articulo_id', u'Sinónimos del artículo')

    # Restricciones SQL
    _sql_constraints = [
        ("unique_sice_art_serv_obra_cod", "unique(cod)", u"Ya existe un artículo con el mismo código"),
    ]

    # Métodos CRUD (y sobreescrituras de name_get, name_search, etc)
    @api.multi
    def set_attrib(self):
        """Dispara la ventana de product para completar atributos"""

        def get_uom_id(self):
            """Retorna id de la unidad de medida"""

            unme_id = self.unme_id.id
            uom_id = False

            # Si existe la unidad, retornamos su id
            self.env.cr.execute("select id from product_uom where sice_uom_id = %(unme_id)s and active",{'unme_id': unme_id})

            if self.env.cr.rowcount > 0:
                res = self.env.cr.fetchone()
                uom_id = res[0]

            return uom_id

        def get_tax_id(self):
            """Retorna id del impuesto correspondiente al mapeo"""

            imp_cod = self.imp_cod
            tax_id = False

            self.env.cr.execute("select imp_grp from grp_art_impuestos where cast (imp_sice as float) = %(imp_sice)s",{'imp_sice': imp_cod})
            if self.env.cr.rowcount > 0:
                res = self.env.cr.fetchone()
                tax_id = res[0]
            else:
                tax_id = 0

            return tax_id


        # Mapeo de los datos del Artículo SICE
        for object in self:

            context = {}
            prod_uom_id = get_uom_id(self)
            prod_imp_id = get_tax_id(self)

            # Valores por defecto a traves del 'context'
            context['default_grp_objeto_del_gasto'] = object.odg
            context['default_cost_method'] = 'real'
            context['default_grp_sice_cod'] = object.cod
            context['default_uom_po_id'] = prod_uom_id
            context['default_uom_id'] = prod_uom_id
            context['default_name'] = object.descripcion
            context['default_description'] = "Nombre SICE: " + object.descripcion
            if prod_imp_id:
                context['default_supplier_taxes_id'] = [prod_imp_id]

        context['hide_grp_buttons'] = False
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.product',
            'target': 'new',
            'context': context,
        }

    # metodo que corrige valores de atributo mal cargados
    # y crea los que no fueron creados
    def check_data(self, articulo_id):
        pool_art = self.env['grp.sice_art_serv_obra']
        pool_det_var = self.env['grp.sice_det_variante']
        pool_med_var = self.env['grp.sice_med_variante']
        pool_prod_att_value = self.env['product.attribute.value']
        pool_prod_att = self.env['product.attribute']
        pool_temp = self.env['product.template']
        pool_prod_prod = self.env['product.product']
        sel_var_lines = self.env['grp.seleccion.variantes.lineas']
        attribute_val = pool_prod_att_value.search([('articulo_id', '=', articulo_id),
                                                    ('sice_color_id', '=', False)])
        art_obj = pool_art.search([('id', '=', articulo_id)])
        if len(art_obj) > 0:
            art_obj = art_obj[0]

        for line in attribute_val:
            new_vals = {}

            if line.det_variante_id:
                if line.det_variante_id.med_cod_pres_id.id != line.med_cod_pres_id.id:
                    new_vals.update({'med_cod_pres_id': line.det_variante_id.med_cod_pres_id.id})
                if line.det_variante_id.pres_id.id != line.pres_id.id:
                    new_vals.update({'pres_id': line.det_variante_id.pres_id.id})
                if line.det_variante_id.med_cod_id.id != line.med_cod_id.id:
                    new_vals.update({'med_cod_id': line.det_variante_id.med_cod_id.id})
                pool_prod_att_value.browse([line.id]).write(new_vals)

        # chequeo de colores
        self.env.cr.execute("""
        select id as id from product_attribute_value where sice_color_id is not null
        and sice_color_id in (
        select id from grp_sice_color where not active
        )""")
        res = self.env.cr.dictfetchall()
        for rec in res:
            pool_prod_att_value.browse([rec['id']]).write({'active': False})

        atributo_color = pool_prod_att.search([('name', '=', 'COLOR')])
        self.env.cr.execute("""
        select color_id as color_id
        from grp_sice_art_color ac
        where ac.articulo_id = %(art_id)s and ac.color_id not in
        (select id from grp_sice_color where not active)
        and not exists (select id from product_attribute_value where
        sice_color_id = ac.color_id and attribute_id = %(attr_color)s)
        """, {'art_id': articulo_id, 'attr_color': atributo_color.id})
        res = self.env.cr.dictfetchall()
        for rec in res:
            sice_color_id = rec['color_id']
            color_obj = self.env['grp.sice_color'].browse(sice_color_id)
            vals = {
                'attribute_id': atributo_color.id,
                'sice_color_id': sice_color_id,
                'name': color_obj.descripcion,
            }
            pool_prod_att_value.create(vals)
        # Insertar linea de atributo en el producto, con atributo COLOR y valores los correspondientes al articulo
        prod_tmp = self.env['product.template'].search([('grp_sice_cod', '=', art_obj.cod)])


        # chequeo de la propiedad sice del articulo
        atributo = pool_prod_att.search([('sice_propiedad_id', '=', art_obj.var_id.id)])
        if len(atributo) > 0:
            atributo = atributo[0]
        else:
            vals = {
                'name': art_obj.var_id.descripcion,
                'sice_propiedad_id': art_obj.var_id.id,
                'dimension_sice': True,
            }
            atributo = pool_prod_att.create(vals)
        if prod_tmp and not prod_tmp.attribute_id.id:
            prod_tmp.write({'attribute_id': atributo.id})
        att_lines = self.env['product.attribute.line'].search([('product_tmpl_id', '=', prod_tmp.id),
                                                               ('attribute_id', '=', atributo.id)])
        if prod_tmp and not att_lines:
            att_line = {
                'product_tmpl_id': prod_tmp.id,
                'attribute_id': atributo.id,
            }
            att_line_id = self.env['product.attribute.line'].create(att_line)
            line_id = self.env['product.attribute.value'].search([('articulo_id', '=', art_obj.id),
                                                                  ('attribute_id', '=', atributo.id)])
            for val in line_id:
                self.env.cr.execute("""
                insert into product_attribute_line_product_attribute_value_rel (line_id, val_id) values (%(line_id)s, %(val_id)s)
                """, {'line_id': att_line_id.id, 'val_id': val.id})

        self.env.cr.execute("""
        select id as id from product_attribute_value where articulo_id = %(art_id)s and det_variante_id in (
        select id from grp_sice_det_variante where active = false
        )""", {'art_id': articulo_id})
        res = self.env.cr.dictfetchall()
        for rec in res:
            pool_prod_att_value.browse([rec['id']]).write({'active': False})

        self.env.cr.execute("""
        select dv.id as id
        from grp_sice_det_variante dv
        where dv.articulo_id = %(art_id)s and dv.active and
        not exists (select id from product_attribute_value av where av.det_variante_id = dv.id)
        """, {'art_id': articulo_id})
        res = self.env.cr.dictfetchall()
        for rec in res:
            det_var_obj = pool_det_var.search([('id', '=', rec['id'])])
            if len(det_var_obj) > 0:
                det_var_obj = det_var_obj[0]
            if det_var_obj.med_cod_pres_id and det_var_obj.pres_id and det_var_obj.med_cod_id and det_var_obj.marc_id:
                atributo_valor = {}
                atributo_valor['attribute_id'] = atributo.id
                atributo_valor['articulo_id'] = articulo_id
                atributo_valor['med_cod_id'] = det_var_obj.med_cod_id.id
                atributo_valor['pres_id'] = det_var_obj.pres_id.id
                atributo_valor['med_cod_pres_id'] = det_var_obj.med_cod_pres_id.id
                atributo_valor['name'] = 'DET_VARIANTE: ART: ' + art_obj.descripcion + ' [' + str(art_obj.cod) + '] ' \
                                                 + ' - ' + 'MEDVAR: ' + det_var_obj.med_cod_id.descripcion + ' [' + str(det_var_obj.med_cod_id.cod) + '] ' \
                                                 + ' - ' + 'PRE: ' + det_var_obj.pres_id.descripcion + ' [' + \
                                                    str(det_var_obj.pres_id.cod) + '] ' \
                                                 + ' - ' + 'MEDPRE: ' + det_var_obj.med_cod_pres_id.descripcion + ' [' + str(det_var_obj.med_cod_pres_id.cod) + ']' \
                                                 + ' - ' + 'DETMARC: ' + det_var_obj.marc_id.descripcion + ' [' + str(det_var_obj.marc_id.cod) + ']' \
                                                 + ' - ' + 'DETDESC: ' + det_var_obj.descripcion

                atributo_valor['det_variante_id'] = det_var_obj.id
                new_med_variante = pool_prod_att_value.create(atributo_valor)
                prod_tmp = self.env['product.template'].search([('grp_sice_cod', '=', art_obj.cod)])
                if prod_tmp:
                    line_id = self.env['product.attribute.line'].search([('product_tmpl_id', '=', prod_tmp.id), ('attribute_id', '=', atributo.id)])
                    self.env.cr.execute("""
                    insert into product_attribute_line_product_attribute_value_rel (line_id, val_id) values (%(line_id)s, %(val_id)s)
                    """, {'line_id': line_id.id, 'val_id': new_med_variante.id})
                variantes = self.env['grp.seleccion.variantes.lineas'].search([('product_id', '=', prod_tmp.id)])
                para_borrar = []
                for sel_var in variantes:
                    if sel_var.det_variante_id and not sel_var.det_variante_id.active:
                        para_borrar.append(sel_var.id)
                if para_borrar:
                    self.env['grp.seleccion.variantes.lineas'].browse(para_borrar).unlink()

        att_values = self.env['product.attribute.value'].search([('articulo_id', '=', art_obj.id)])
        for atv in att_values:
            med_objs = pool_med_var.search([('articulo_id', '=', art_obj.id),
                                            ('med_cod_id', '=', atv.med_cod_id.id),
                                            ('pres_id', '=', atv.pres_id.id),
                                            ('med_cod_pres_id', '=', atv.med_cod_pres_id.id),
                                            ('active', '=', False)])
            if med_objs:
                self.env.cr.execute("""
                select p.id as id
                from product_product p, product_attribute_value_product_product_rel rel
                where p.id = rel.prod_id and rel.att_id = %(att_id)s
                """, {'att_id': atv.id})
                res = self.env.cr.dictfetchall()
                for rec in res:
                    pool_prod_prod.browse([rec['id']]).write({'active': False})
                self.env['product.attribute.value'].browse([atv.id]).write({'active': False})

        self.env.cr.execute("""
        select dv.id as id
        from grp_sice_med_variante dv
        where dv.articulo_id = %(art_id)s and dv.active and
        not exists (select id from product_attribute_value av where av.med_cod_id = dv.med_cod_id
        and articulo_id = %(art_id)s and pres_id = dv.pres_id and med_cod_pres_id = dv.med_cod_pres_id)
        """, {'art_id': articulo_id})
        res = self.env.cr.dictfetchall()
        for rec in res:
            det_var_obj = pool_med_var.search([('id', '=', rec['id'])])
            if len(det_var_obj) > 0:
                det_var_obj = det_var_obj[0]
            if det_var_obj.med_cod_pres_id and det_var_obj.pres_id and det_var_obj.med_cod_id:
                atributo_valor = {}
                atributo_valor['attribute_id'] = atributo.id
                atributo_valor['articulo_id'] = articulo_id
                atributo_valor['med_cod_id'] = det_var_obj.med_cod_id.id
                atributo_valor['pres_id'] = det_var_obj.pres_id.id
                atributo_valor['med_cod_pres_id'] = det_var_obj.med_cod_pres_id.id
                atributo_valor['name'] = 'MED_VARIANTE: ART: ' + art_obj.descripcion + ' [' + str(art_obj.cod) + '] ' \
                                                 + ' - ' + 'MEDVAR: ' + det_var_obj.med_cod_id.descripcion + ' [' + str(det_var_obj.med_cod_id.cod) + '] ' \
                                                 + ' - ' + 'PRE: ' + det_var_obj.pres_id.descripcion + ' [' + \
                                                    str(det_var_obj.pres_id.cod) + '] ' \
                                                 + ' - ' + 'MEDPRE: ' + det_var_obj.med_cod_pres_id.descripcion + ' [' + str(det_var_obj.med_cod_pres_id.cod) + ']'

                new_det_variante = pool_prod_att_value.create(atributo_valor)
                prod_tmp = self.env['product.template'].search([('grp_sice_cod', '=', art_obj.cod)])
                if prod_tmp:
                    line_id = self.env['product.attribute.line'].search([('product_tmpl_id', '=', prod_tmp.id), ('attribute_id', '=', atributo.id)])
                    self.env.cr.execute("""
                    insert into product_attribute_line_product_attribute_value_rel (line_id, val_id) values (%(line_id)s, %(val_id)s)
                    """, {'line_id': line_id.id, 'val_id': new_det_variante.id})
                variantes = self.env['grp.seleccion.variantes.lineas'].search([('product_id', '=', prod_tmp.id)])
                para_borrar = []
                for sel_var in variantes:
                    if sel_var.det_variante_id and not sel_var.det_variante_id.active:
                        para_borrar.append(sel_var.id)
                if para_borrar:
                    self.env['grp.seleccion.variantes.lineas'].browse(para_borrar).unlink()
        cant = 1
        if prod_tmp:
            att_lines = self.env['product.attribute.line'].search([('product_tmpl_id', '=', prod_tmp.id),
                                                                 ('attribute_id', '=', atributo_color.id)])
            colors_list = [color.id for color in art_obj.art_color_ids]
            if not att_lines:

                att_values = pool_prod_att_value.search([('attribute_id', '=', atributo_color.id),
                                                         ('sice_color_id', 'in', colors_list)])
                att_line = {
                    'product_tmpl_id': prod_tmp.id,
                    'attribute_id': atributo_color.id,
                    # 'value_ids': [(6, 0, att_values.ids)]
                }
                if not att_values:
                    ninguno = self.env['grp.sice_color'].search([('descripcion', '=', 'NINGUNO')])
                    val_ninguno = pool_prod_att_value.search([('attribute_id', '=', atributo_color.id),
                                                              ('sice_color_id', '=', ninguno.id)])
                    att_line.update({'value_ids': [(6, 0, [val_ninguno.id])]})
                else:
                    att_line.update({'value_ids': [(6, 0, att_values.ids)]})
                att_line_id = self.env['product.attribute.line'].create(att_line)
            else:
                line_id = self.env['product.attribute.value'].search([('sice_color_id', 'in', colors_list)])
                self.env.cr.execute("""
                select val_id as val_id from product_attribute_line_product_attribute_value_rel
                where line_id = %(line_id)s
                """, {'line_id': att_lines.id})
                values = []
                for r in self._cr.dictfetchall():
                    values.append(r['val_id'])
                for val in line_id:
                    if val.id not in values:
                        self.env.cr.execute("""
                        insert into product_attribute_line_product_attribute_value_rel (line_id, val_id) values (%(line_id)s, %(val_id)s)
                        """, {'line_id': att_lines.id, 'val_id': val.id})
            for at_line in prod_tmp.attribute_line_ids:
                cant *= len(at_line.value_ids)
        if prod_tmp and len(prod_tmp.seleccion_variantes_ids) < cant:
            # Crear combinaciones de variantes para la grilla Variantes a Crear
            para_borrar = sel_var_lines.search([('product_id', '=', prod_tmp.id)])
            if para_borrar:
                sel_var_lines.browse(para_borrar.ids).unlink()
            colors_list = [color.id for color in art_obj.art_color_ids]
            ninguno = self.env['grp.sice_color'].search([('descripcion', '=', 'NINGUNO')])
            if not colors_list:
                colors_list.append(ninguno.id)
            lineas = []
            lista_variantes = []
            list_lineas = []
            attribute_id = False
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
                    att_values = self.env['product.attribute.value'].search([('articulo_id', '=', art_obj.id)])
                    for atv in att_values:
                        values = {
                            'product_id': prod_tmp.id,
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
                            'det_variante_id': det_var_id
                        })
                        domain = [
                            ('product_tmpl_id', '=', prod_tmp.id),
                            ('med_cod_id', '=', values['med_cod_id']),
                            ('pres_id', '=', values['pres_id']),
                            ('med_cod_pres_id', '=', values['med_cod_pres_id'])
                        ]
                        if atv.sice_color_id:
                            domain.append(('sice_color_id', '=', values['sice_color_id']))
                        else:
                            domain.append(('sice_color_id', '=', False))
                        if atv.det_variante_id:
                            domain.append(('det_variante_id', '=', values['det_variante_id']))
                        else:
                            domain.append(('det_variante_id', '=', False))
                        prod_variante = pool_prod_prod.search(domain)
                        if prod_variante.id:
                            values.update({'creado': True})
                        attribute_id = atv.attribute_id.id
                        if not atv.det_variante_id or atv.det_variante_id.active:
                            sel_var_lines.create(values)

        return True

    @api.multi
    def set_attrib_template_parcial(self):

        def get_uom_id(self):
            """Retorna id de la unidad de medida"""

            unme_id = self.unme_id.id
            uom_id = False

            # Si existe la unidad, retornamos su id
            self.env.cr.execute("select id from product_uom where sice_uom_id = %(unme_id)s and active",{'unme_id': unme_id})

            if self.env.cr.rowcount > 0:
                res = self.env.cr.fetchone()
                uom_id = res[0]

            return uom_id

        def get_tax_id(self):
            """Retorna id del impuesto correspondiente al mapeo"""

            imp_cod = self.imp_cod
            tax_id = False

            self.env.cr.execute("select imp_grp from grp_art_impuestos where cast (imp_sice as float) = %(imp_sice)s",{'imp_sice': imp_cod})
            if self.env.cr.rowcount > 0:
                res = self.env.cr.fetchone()
                tax_id = res[0]
            else:
                tax_id = 0

            return tax_id

        # Mapeo de los datos del Artículo SICE
        for object in self:
            # Valores por defecto a traves del 'context'
            context = {}
            context['from_articulo_sice']=True #Bandera para reconocer el origen de lanzamiento de product.template
            prod_uom_id = get_uom_id(self)
            prod_imp_id = get_tax_id(self)
            self.check_data(object.id)

            prod_tmp = self.env['product.template'].search([('grp_sice_cod', '=', object.cod)])
            self._cr.execute("""
                select unme_id as id
                from grp_sice_art_unidades_med
                where articulo_id = %s
            """, [object.id])
            uom_ids = []
            for res in self._cr.dictfetchall():
                uom_ids.append(res['id'])
            context['uom_ids'] = uom_ids
            self._cr.execute("""
                select art_im.imp_grp as id
                from grp_sice_art_impuesto sice_im, grp_art_impuestos art_im
                where sice_im.articulo_id = %s and cast (art_im.imp_sice as int) = sice_im.impuesto_id
            """, [object.id])
            tax_ids = []
            for res in self._cr.dictfetchall():
                tax_ids.append(res['id'])
            context['tax_ids'] = tax_ids
            if prod_tmp:
                context['only_variants_parcial'] = True
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'product.template',
                    'res_id': prod_tmp.id,
                    'target': 'new',
                    'context': context,
                }

            colors_list = [color.id for color in object.art_color_ids]
            ninguno = self.env['grp.sice_color'].search([('descripcion', '=', 'NINGUNO')])
            if not colors_list:
                colors_list.append(ninguno.id)
            _logger.info("Colores ids: %s", colors_list)
            lineas = []
            lista_variantes = []
            list_lineas = []
            attribute_id = False
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
                    att_values = self.env['product.attribute.value'].search([('articulo_id', '=', object.id)]
                                                                            )
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
                            'det_variante_id': det_var_id
                        })
                        attribute_id = atv.attribute_id.id
                        if not atv.det_variante_id or atv.det_variante_id.active:
                            lista_variantes.append((0, 0, values))
                dicc.update({'value_ids': [(6, 0, lineas)],
                            'solo_lectura': True})
                list_lineas.append((0, 0, dicc))

            variante_id = object.var_id.id
            att_obj = self.env['product.attribute'].search([('sice_propiedad_id', '=', variante_id)])
            variantes_list = [med.med_cod_id.id for med in object.variante_ids]
            att_values = self.env['product.attribute.value'].search([('articulo_id', '=', object.id),
                                                                     ('attribute_id', '=', att_obj.id)])
            if att_values:
                lista_activos = []
                for at in att_values:
                    if not at.det_variante_id or at.det_variante_id.active:
                        lista_activos.append(at.id)
                dicc = {
                    'attribute_id': att_obj.id,
                    # 'value_ids': att_values.ids,
                    'value_ids': [(6, 0, lista_activos)],
                    'solo_lectura': True
                }
                list_lineas.append((0, 0, dicc))

            context['default_attribute_line_ids'] = list_lineas

            context['default_seleccion_variantes_ids'] = lista_variantes
            context['default_attribute_id'] = attribute_id

            # 002-Fin

            context['default_is_multi_variants'] = True
            context['default_type'] = ''
            context['default_cost_method'] = 'real'
            context['default_uom_po_id'] = prod_uom_id
            context['default_uom_id'] = prod_uom_id
            context['default_categ_id']=''
            context['default_grp_objeto_del_gasto'] = object.odg
            context['default_grp_sice_cod'] = object.cod
            context['default_name'] = object.descripcion
            context['default_description'] = "Nombre SICE: " + object.descripcion
            if prod_imp_id:
                context['default_supplier_taxes_id'] = [(6, 0, [prod_imp_id])]

            campos = {
                'is_multi_variants': True,
                'type': 'product',
                'cost_method': 'real',
                'uom_po_id': prod_uom_id or 1,
                'uom_id': prod_uom_id or 1,
                'categ_id': 1,
                'grp_objeto_del_gasto': object.odg,
                'grp_sice_cod': object.cod,
                'name': object.descripcion,
                'description': "Nombre SICE: " + object.descripcion,
                'attribute_line_ids': list_lineas,
                'seleccion_variantes_ids': lista_variantes,
                'attribute_id': attribute_id,
                'sale_ok': False,
            }
            if prod_imp_id:
                campos.update({'supplier_taxes_id': [(6, 0, [prod_imp_id])]})
            context['hide_grp_buttons'] = True
            context['creacion_inicial'] = True
            context['only_variants_parcial'] = True
            created_id = self.env['product.template'].with_context(context).create(campos)

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.template',
            'res_id': created_id.id,
            'target': 'new',
            'context': context,
        }

    @api.multi
    def set_attrib_template(self):

        def get_uom_id(self):
            """Retorna id de la unidad de medida"""

            unme_id = self.unme_id.id
            uom_id = False

            # Si existe la unidad, retornamos su id
            self.env.cr.execute("select id from product_uom where sice_uom_id = %(unme_id)s and active",{'unme_id': unme_id})

            if self.env.cr.rowcount > 0:
                res = self.env.cr.fetchone()
                uom_id = res[0]

            return uom_id

        def get_tax_id(self):
            """Retorna id del impuesto correspondiente al mapeo"""

            imp_cod = self.imp_cod
            tax_id = False

            self.env.cr.execute("select imp_grp from grp_art_impuestos where cast (imp_sice as float) = %(imp_sice)s",{'imp_sice': imp_cod})
            if self.env.cr.rowcount > 0:
                res = self.env.cr.fetchone()
                tax_id = res[0]
            else:
                tax_id = 0

            return tax_id

        # Mapeo de los datos del Artículo SICE
        for object in self:
            # Valores por defecto a traves del 'context'
            context = {}
            context['from_articulo_sice']=True #Bandera para reconocer el origen de lanzamiento de product.template
            prod_uom_id = get_uom_id(self)
            prod_imp_id = get_tax_id(self)
            self.check_data(object.id)

            prod_tmp = self.env['product.template'].search([('grp_sice_cod', '=', object.cod)])
            self._cr.execute("""
                select unme_id as id
                from grp_sice_art_unidades_med
                where articulo_id = %s
            """, [object.id])
            uom_ids = []
            for res in self._cr.dictfetchall():
                uom_ids.append(res['id'])
            context['uom_ids'] = uom_ids
            self._cr.execute("""
                select art_im.imp_grp as id
                from grp_sice_art_impuesto sice_im, grp_art_impuestos art_im
                where sice_im.articulo_id = %s and cast (art_im.imp_sice as int) = sice_im.impuesto_id
            """, [object.id])
            tax_ids = []
            for res in self._cr.dictfetchall():
                tax_ids.append(res['id'])
            context['tax_ids'] = tax_ids
            if prod_tmp:
                context['only_variants_total'] = True
                return {
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'product.template',
                    'res_id': prod_tmp.id,
                    'target': 'new',
                    'context': context,
                }
            # 002-Inicio
            # buscar variantes y valores de variantes del articulo
            # y cargarlas en la grilla de product.template
            colors_list = [color.id for color in object.art_color_ids]
            ninguno = self.env['grp.sice_color'].search([('descripcion', '=', 'NINGUNO')])
            if not colors_list:
                colors_list.append(ninguno.id)
            _logger.info("Colores ids: %s", colors_list)
            lineas = []
            dicc = {}
            lista_variantes = []
            list_lineas = []
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
                    att_values = self.env['product.attribute.value'].search([('articulo_id', '=', object.id)])
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
                            'det_variante_id': det_var_id
                        })
                        attribute_id = atv.attribute_id.id
                        if not atv.det_variante_id or atv.det_variante_id.active:
                            lista_variantes.append((0, 0, values))
                dicc.update({'value_ids': [(6, 0, lineas)],
                            'solo_lectura': True})
                list_lineas.append((0, 0, dicc))

            variante_id = object.var_id.id
            att_obj = self.env['product.attribute'].search([('sice_propiedad_id', '=', variante_id)])
            variantes_list = [med.med_cod_id.id for med in object.variante_ids]
            att_values = self.env['product.attribute.value'].search([('articulo_id', '=', object.id),
                                                                     ('attribute_id', '=', att_obj.id)])
            if att_values:
                lista_activos = []
                for at in att_values:
                    if not at.det_variante_id or at.det_variante_id.active:
                        lista_activos.append(at.id)
                dicc = {
                    'attribute_id': att_obj.id,
                    # 'value_ids': att_values.ids,
                    # 'value_ids': lista_activos,
                    'value_ids': [(6, 0, lista_activos)],
                    'solo_lectura': True
                }
                list_lineas.append((0, 0, dicc))
                context['default_attribute_id'] = att_obj.id

            context['default_attribute_line_ids'] = list_lineas
            context['default_seleccion_variantes_ids'] = lista_variantes

            # 002-Fin

            context['default_is_multi_variants'] = True
            context['default_type'] = ''
            context['default_cost_method'] = 'real'
            context['default_uom_po_id'] = prod_uom_id
            context['default_uom_id'] = prod_uom_id
            context['default_categ_id']=''
            context['default_grp_objeto_del_gasto'] = object.odg
            context['default_grp_sice_cod'] = object.cod
            context['default_name'] = object.descripcion
            context['default_description'] = "Nombre SICE: " + object.descripcion
            context['default_sale_ok'] = False
            if prod_imp_id:
                context['default_supplier_taxes_id'] = [(6, 0, [prod_imp_id])]
            context['hide_grp_buttons'] = True

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.template',
            'target': 'new',
            'context': context,
        }



class grpSiceArtAtributo(models.Model):

    # Atributos privados
    _name = 'grp.sice_art_atributo'
    _description = u'Atributo de artículo'

    # Declaración de campos
    articulo_id = fields.Many2one('grp.sice_art_serv_obra', string=u'Artículo', required=True)
    # arse_cod = fields.Integer(related='articulo_id.cod', string=u'Código de artículo')
    prop_id = fields.Many2one('grp.sice_propiedad', string='Propiedad', required=True)
    # prop_cod = fields.Integer(related='prop_id.cod', string=u'Código de propiedad')
    prop_unme_id = fields.Many2one('grp.sice_unidades_med', string='Unidad de medida de la propiedad', required=True)
    # prop_unme_cod = fields.Integer(related='prop_unme_id.cod', string=u'Código de unidad de medida de la propiedad')

    arse_cod = fields.Integer(related='articulo_id.cod', string=u'Código de artículo', store=True, index=True)
    prop_cod = fields.Integer(related='prop_id.cod', string=u'Código de propiedad', store=True, index=True)
    prop_unme_cod = fields.Integer(related='prop_unme_id.cod', string=u'Código de unidad de medida de la propiedad', store=True, index=True)

    patron = fields.Char(string=u'Patrón', size=150)
    fecha_baja = fields.Date(string='Fecha de baja')
    motivo_baja = fields.Char(string='Motivo de baja', size=200)

    active = fields.Boolean(string='Activo', default=True)

    # Restricciones SQL
    _sql_constraints = [
        ("unique_sice_art_atributo", "unique(articulo_id, prop_id, prop_unme_id)", u"Ya existe la tupla artículo, propiedad, unidad de medida"),
    ]


class grpSiceMedVariante(models.Model):

    # Atributos privados
    _name = 'grp.sice_med_variante'
    _description = u'Variante de artículo'

    # Declaración de campos
    articulo_id = fields.Many2one('grp.sice_art_serv_obra', string=u'Artículo', required=True)
    # arse_cod = fields.Integer(related='articulo_id.cod', string=u'Código de artículo')

    # Medida de la variante
    med_cod_id = fields.Many2one('grp.sice_medida', string=u'Medida de la variante', required=True)
    # med_cod_variante = fields.Integer(related='med_cod_id.cod', string=u'Código de medida de la variante')

    # Presentacion
    pres_id = fields.Many2one('grp.sice_presentacion', string='Presentacion', required=True)
    # pres_cod = fields.Integer(related='pres_id.cod', string=u'Código de presentación')

    # Medida de la presentacion
    med_cod_pres_id = fields.Many2one('grp.sice_medida', string=u'Medida de la presentación', required=True)
    # med_cod_pres = fields.Integer(related='med_cod_pres_id.cod', string=u'Código de medida de la prresentación')

    det_variante_ids = fields.One2many('grp.sice_det_variante', 'med_variante_id', u'Detalles de variante del artículo')

    fecha_baja = fields.Date(string='Fecha de baja')
    motivo_baja = fields.Char(string='Motivo de baja', size=200)

    active = fields.Boolean(string='Activo', default=True)

    arse_cod = fields.Integer(related='articulo_id.cod', string=u'Código de artículo', store=True, index=True)
    med_cod_variante = fields.Integer(related='med_cod_id.cod', string=u'Código de medida de la variante', store=True, index=True)
    pres_cod = fields.Integer(related='pres_id.cod', string=u'Código de presentación', store=True, index=True)
    med_cod_pres = fields.Integer(related='med_cod_pres_id.cod', string=u'Código de medida de la prresentación', store=True, index=True)

    # Restricciones SQL
    _sql_constraints = [
        ("unique_sice_med_variante", "unique(articulo_id, med_cod_id, pres_id, med_cod_pres_id)", u"Ya existe la tupla artículo, unidad de medida de la variante, presentación, unidad de medida de la presentación"),
    ]



class grpSiceDetVariante(models.Model):

    # Atributos privados
    _name = 'grp.sice_det_variante'
    _description = u'Detalle de variante de artículo'

    cod = fields.Integer(string=u'Código de detalle de variante', required=True, index=True)
    descripcion = fields.Char(string=u'Descripción', size=300, required=True)

    # Marca
    marc_id = fields.Many2one('grp.sice_marca', string='Marca', required=True)
    # marc_cod = fields.Integer(related='marc_id.cod', string=u'Código de marca')

    med_variante_id = fields.Many2one('grp.sice_med_variante', string='Medida de variante')

    # Articulo
    articulo_id = fields.Many2one('grp.sice_art_serv_obra', string=u'Artículo', required=True)
    # arse_cod = fields.Integer(related='articulo_id.cod', string=u'Código de artículo')

    # Unidad de medida de la variante
    med_cod_id = fields.Many2one('grp.sice_medida', string=u'Medida de la variante', required=True)
    # med_cod_variante = fields.Integer(related='med_cod_id.cod', string=u'Código de medida de la variante')

    # Presentacion
    pres_id = fields.Many2one('grp.sice_presentacion', string='Presentacion', required=True)
    # pres_cod = fields.Integer(related='pres_id.cod', string=u'Código de prresentación')

    # Unidad de medida de la presentacion
    med_cod_pres_id = fields.Many2one('grp.sice_medida', string=u'Medida de la presentación', required=True)
    # med_cod_pres = fields.Integer(related='med_cod_pres_id.cod', string=u'Código de medida de la prresentación')

    fecha_baja = fields.Date(string='Fecha de baja')
    motivo_baja = fields.Char(string='Motivo de baja', size=200)

    active = fields.Boolean(string='Activo', default=True)

    marc_cod = fields.Integer(related='marc_id.cod', string=u'Código de marca', store=True, index=True)
    arse_cod = fields.Integer(related='articulo_id.cod', string=u'Código de artículo', store=True, index=True)
    med_cod_variante = fields.Integer(related='med_cod_id.cod', string=u'Código de medida de la variante', store=True, index=True)
    pres_cod = fields.Integer(related='pres_id.cod', string=u'Código de prresentación', store=True, index=True)
    med_cod_pres = fields.Integer(related='med_cod_pres_id.cod', string=u'Código de medida de la prresentación', store=True, index=True)


    # Restricciones SQL
    _sql_constraints = [
        ("unique_sice_det_variante", "unique(cod)", u"Ya existe un detalle de variante con el mismo código"),
    ]


class grpSiceSinonimo(models.Model):
    _name = 'grp.sice_sinonimo'
    _rec_name = 'descripcion'
    _description = u'Sinónimo de artículo'
    _order = 'descripcion'

    articulo_id = fields.Many2one('grp.sice_art_serv_obra', string=u'Artículo', required=True)
    # arse_cod = fields.Integer(related='articulo_id.cod', string=u'Código de artículo')
    arse_cod = fields.Integer(related='articulo_id.cod', string=u'Código de artículo', store=True, index=True)
    descripcion = fields.Char(string=u'Descripción', size=200, required=True, index=True)
    fecha_baja = fields.Date(string='Fecha de baja')
    motivo_baja = fields.Char(string='Motivo de baja', size=200)
    active = fields.Boolean(string='Activo', default=True)
