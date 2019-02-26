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

    fami_cod = fields.Integer(string=u'Código de Familia', index=True)
    subf_cod = fields.Integer(string=u'Código de Subfamilia', index=True)
    clas_cod = fields.Integer(string=u'Código de Clase', index=True)
    subc_cod = fields.Integer(string=u'Código de Subclase', index=True)

    # Variante
    var_id = fields.Many2one('grp.sice_propiedad', string='Variante')
    var_cod = fields.Integer(string=u'Variante', required=True, index=True)

    # Indica el tipo: articulo, servicio u obra
    ind_art_serv = fields.Selection([('A',u'Artículo'),('S','Servicio'),('O','Obra')], string='Tipo', required=True)

    # Indicador de dificil fraccionamiento
    ind_fraccion = fields.Selection([('S','Si'),('N','No')], string=u'Difícil fraccionamiento', required=True)

    # Indica si cualquiera puede iniciar la compra o hay alguien encargado
    ind_gestionable = fields.Selection([('S','Si'),('N','No')], string='Gestionable', required=True)

    # Indica si el articulo se compra mediante compra agrupadda (en forma conjunta para varias reparticiones)
    ind_agrupable  = fields.Selection([('S','Si'),('N','No')], string='Agrupable', required=True)

    comprable = fields.Selection([('S', 'Si'), ('N', 'No')], string='Comprable', required=True)

    fami_id = fields.Many2one('grp.sice_familia', string='Familia')
    subf_id = fields.Many2one('grp.sice_subflia', string='Subfamilia')
    clas_id = fields.Many2one('grp.sice_clase', string='Clase')
    subc_id = fields.Many2one('grp.sice_subclase', string='Subclase')

    # Campos no requeridos
    var_unme_cod = fields.Integer(string=u'Código de unidad de medida de la variante', store=True, index=True)
    var_unme_id = fields.Many2one('grp.sice_unidades_med', string='Unidad de medida de la variante')

    unme_cod = fields.Integer(string=u'Código de unidad de medida', store=True, index=True)
    unme_id  = fields.Many2one('grp.sice_unidades_med', string='Unidad de medida')

    imp_cod = fields.Integer(string=u'Código de impuesto', store=True, index=True)
    imp_id  = fields.Many2one('grp.sice_impuesto', string='Impuesto')

    # Indica si el articulo es stockeable
    stockeable = fields.Selection([('S','Si'),('N','No')], string='Stockeable')

    # Indica en caso de ser stockeable, si dicho stock debe reflejarse contablemente o simplemente interesa llevarse su inventario
    stock_contable = fields.Selection([('S','Si'),('N','No')], string='Stock Contable')

    # Indica el tipo de detalle de la variante del articulo (medicamento, repuesto)
    ind_tipo_detalle = fields.Selection([('M','Medicamento'),('R','Repuesto')], string='Tipo de detalle')

    odg = fields.Integer(string=u'Código Odg', store=True, index=True)
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
            self.env.cr.execute("select id from product_uom where sice_uom_id = %(unme_id)s",{'unme_id': unme_id})

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


    @api.multi
    def set_attrib_template(self):

        def get_uom_id(self):
            """Retorna id de la unidad de medida"""

            unme_id = self.unme_id.id
            uom_id = False

            # Si existe la unidad, retornamos su id
            self.env.cr.execute("select id from product_uom where sice_uom_id = %(unme_id)s",{'unme_id': unme_id})

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
                context['default_supplier_taxes_id'] = [prod_imp_id]

        context['hide_grp_buttons'] = False
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

    articulo_id = fields.Integer(string=u'Artículo')
    arse_cod = fields.Integer(string=u'Código de artículo')
    prop_id = fields.Integer(string='Propiedad')
    prop_cod = fields.Integer(string=u'Código de propiedad')
    prop_unme_id = fields.Integer(string='Unidad de medida de la propiedad')
    prop_unme_cod = fields.Integer(string=u'Código de unidad de medida de la propiedad')

    patron = fields.Char(string=u'Patrón', size=150)
    fecha_baja = fields.Date(string='Fecha de baja')
    motivo_baja = fields.Char(string='Motivo de baja', size=200)


class grpSiceMedVariante(models.Model):

    # Atributos privados
    _name = 'grp.sice_med_variante'
    _description = u'Variante de artículo'

    # Declaración de campos
    articulo_id = fields.Integer(string=u'Artículo')
    arse_cod = fields.Integer(string=u'Código de artículo')

    # Medida de la variante
    med_cod_id = fields.Integer(string=u'Medida de la variante')
    med_cod_variante = fields.Integer(string=u'Código de medida de la variante')

    # Presentacion
    pres_id = fields.Integer(string=u'Prresentacion')
    pres_cod = fields.Integer(string=u'Código de prresentación')

    # Medida de la presentacion
    med_cod_pres_id = fields.Integer(string=u'Medida de la presentación')
    med_cod_pres = fields.Integer(string=u'Código de medida de la prresentación')


    det_variante_ids = fields.One2many('grp.sice_det_variante', 'med_variante_id', u'Detalles de variante del artículo')

    fecha_baja = fields.Date(string='Fecha de baja')
    motivo_baja = fields.Char(string='Motivo de baja', size=200)



class grpSiceDetVariante(models.Model):

    # Atributos privados
    _name = 'grp.sice_det_variante'
    _description = u'Detalle de variante de artículo'

    cod = fields.Integer(string=u'Código de detalle de variante', required=True, index=True)
    descripcion = fields.Char(string=u'Descripción', size=300, required=True)

    # Marca
    marc_id = fields.Integer(string=u'Marca')
    marc_cod = fields.Integer(string=u'Código de marca')

    med_variante_id = fields.Many2one('grp.sice_med_variante', string='Medida de variante')

    # Articulo
    articulo_id = fields.Integer(string=u'Artículo')
    arse_cod = fields.Integer(string=u'Código de artículo')

    # Unidad de medida de la variante
    med_cod_id = fields.Integer(string=u'Medida de la variante')
    med_cod_variante = fields.Integer(string=u'Código de medida de la variante')

    # Presentacion
    pres_id = fields.Integer(string=u'Prresentacion')
    pres_cod = fields.Integer(string=u'Código de prresentación')

    # Unidad de medida de la presentacion
    med_cod_pres_id = fields.Integer(string=u'Medida de la presentación')
    med_cod_pres = fields.Integer(string=u'Código de medida de la prresentación')

    fecha_baja = fields.Date(string='Fecha de baja')
    motivo_baja = fields.Char(string='Motivo de baja', size=200)


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
