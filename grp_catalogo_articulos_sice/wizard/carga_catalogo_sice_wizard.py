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

class grpCargaCatalogoSice(models.TransientModel):

    _name = 'grp.carga_catalogo_sice_wizard'
    _description = u"Wizard de carga de modelos grp del catálogo de artículos SICE"

    procesar_familias = fields.Boolean('Familias',
                                      help=u"Marque esta casilla si desea cargar el modelo GRP de Familias SICE",
                                      default=False)

    @api.multi
    def cargar_familias(self):

        grp_sice_familia_obj = self.env['grp.sice_familia']

        self._cr.execute("select * from sice_familias")
        for familia in self._cr.dictfetchall():
            if familia['fecha_baja']:
                familia['active'] = False

            grp_sice_familia_obj.create(familia)

        return True

    @api.multi
    def cargar_subflias(self):
        grp_sice_familia_obj = self.env['grp.sice_familia']
        grp_sice_subflia_obj = self.env['grp.sice_subflia']

        self._cr.execute("select * from sice_subflias")
        for subflia in self._cr.dictfetchall():

            _logger.info('subflia[fami_cod]: %s', subflia['fami_cod'])

            # Obtengo id de familia
            familia = grp_sice_familia_obj.search([('cod', '=', subflia['fami_cod'])])
            if not familia:
                _logger.info('ERROR: No se encontró familia para la subfamilia: %s', subflia)
                continue

            if subflia['fecha_baja']:
                subflia['active'] = False

            subflia['fami_id'] = familia.id
            grp_sice_subflia_obj.create(subflia)

        return True


    @api.multi
    def cargar_clases(self):
        grp_sice_familia_obj = self.env['grp.sice_familia']
        grp_sice_subflia_obj = self.env['grp.sice_subflia']
        grp_sice_clase_obj = self.env['grp.sice_clase']

        self._cr.execute("select * from sice_clases")
        for clase in self._cr.dictfetchall():

            # Obtengo id de familia
            familia = grp_sice_familia_obj.search([('cod', '=', clase['fami_cod'])])
            if not familia:
                _logger.info('ERROR: No se encontró familia para la clase: %s', clase)
                continue

            # Obtengo id de subfamilia
            subfamilia = grp_sice_subflia_obj.search([('fami_cod', '=', clase['fami_cod']),('cod', '=', clase['subf_cod'])])
            if not subfamilia:
                _logger.info('ERROR: No se encontró subfamilia para la clase: %s', clase)
                continue

            if clase['fecha_baja']:
                clase['active'] = False

            clase['fami_id'] = familia.id
            clase['subf_id'] = subfamilia.id
            grp_sice_clase_obj.create(clase)

        return True


    @api.multi
    def cargar_subclases(self):
        grp_sice_familia_obj = self.env['grp.sice_familia']
        grp_sice_subflia_obj = self.env['grp.sice_subflia']
        grp_sice_clase_obj = self.env['grp.sice_clase']
        grp_sice_subclase_obj = self.env['grp.sice_subclase']

        i = 0

        self._cr.execute("select * from sice_subclases")
        for subclase in self._cr.dictfetchall():

            i += 1
            _logger.info('Subclase nro: %s',i)

            # Obtengo id de familia
            domain = [('cod','=',subclase['fami_cod'])]
            familia = grp_sice_familia_obj.with_context(active_test=False).search(domain)
            if not familia:
                _logger.info('ERROR: No se encontró familia para la subclase: %s', subclase)
                continue

            # Obtengo id de subfamilia
            domain = [('fami_cod','=',subclase['fami_cod']),('cod','=',subclase['subf_cod'])]
            subfamilia = grp_sice_subflia_obj.with_context(active_test=False).search(domain)
            if not subfamilia:
                _logger.info('ERROR: No se encontró subfamilia para la subclase: %s', subclase)
                continue

            # Obtengo id de clase
            domain = [('fami_cod','=',subclase['fami_cod']),('subf_cod','=',subclase['subf_cod']),('cod','=',subclase['clas_cod'])]
            clase = grp_sice_clase_obj.with_context(active_test=False).search(domain)
            if not clase:
                _logger.info('ERROR: No se encontró clase para la subclase: %s', subclase)
                continue

            if subclase['fecha_baja']:
                subclase['active'] = False

            subclase['fami_id'] = familia.id
            subclase['subf_id'] = subfamilia.id
            subclase['clas_id'] = clase.id

            grp_sice_subclase_obj.create(subclase)

        return True

    @api.multi
    def cargar_impuestos(self):
        grp_sice_impuesto_obj = self.env['grp.sice_impuesto']

        self._cr.execute("select * from sice_impuestos")

        for impuesto in self._cr.dictfetchall():
            if impuesto['fecha_baja']:
                impuesto['active'] = False

            grp_sice_impuesto_obj.create(impuesto)
        return True

    @api.multi
    def cargar_porcentajes_impuestos(self):

        grp_sice_porc_impuesto_obj = self.env['grp.sice_porc_impuesto']
        grp_sice_impuesto_obj = self.env['grp.sice_impuesto']

        self._cr.execute("select * from sice_porcs_impuestos order by imp_cod, fecha_vigencia desc")

        for porc_impuesto in self._cr.dictfetchall():

            # Obtengo id de impuesto
            domain = ['|', ('active', '=', False), ('active', '=', True),('cod','=',porc_impuesto['imp_cod'])]
            impuesto = grp_sice_impuesto_obj.with_context(active_test=False).search(domain)
            if not impuesto:
                _logger.info('ERROR: No se encontró impuesto para porc_impuesto: %s', porc_impuesto)
                continue

            porc_impuesto['imp_id'] = impuesto.id
            grp_sice_porc_impuesto_obj.create(porc_impuesto)
        return True


    @api.multi
    def cargar_medidas(self):

        grp_sice_medida_obj = self.env['grp.sice_medida']

        self._cr.execute("select * from sice_medidas")

        for medida in self._cr.dictfetchall():
            if medida['fecha_baja']:
                medida['active'] = False

            grp_sice_medida_obj.create(medida)
        return True


    @api.multi
    def cargar_unidades_med(self):

        grp_sice_unidades_med_obj = self.env['grp.sice_unidades_med']

        self._cr.execute("select * from sice_unidades_med")

        for unidad_med in self._cr.dictfetchall():
            if unidad_med['fecha_baja']:
                unidad_med['active'] = False

            grp_sice_unidades_med_obj.create(unidad_med)
        return True


    @api.multi
    def cargar_marcas(self):
        grp_sice_marca_obj = self.env['grp.sice_marca']

        self._cr.execute("select * from sice_marcas")

        for marca in self._cr.dictfetchall():
            if marca['fecha_baja']:
                marca['active'] = False

            grp_sice_marca_obj.create(marca)
        return True


    @api.multi
    def cargar_odg(self):
        grp_sice_odg_obj = self.env['grp.sice_odg']

        self._cr.execute("select * from sice_odgs")

        for odg in self._cr.dictfetchall():
            if odg['fecha_baja']:
                odg['active'] = False

            grp_sice_odg_obj.create(odg)
        return True


    @api.multi
    def cargar_colores(self):
        grp_sice_color_obj = self.env['grp.sice_color']

        self._cr.execute("select * from sice_colores")

        for color in self._cr.dictfetchall():
            if color['fecha_baja']:
                color['active'] = False

            grp_sice_color_obj.create(color)
        # Agrego color NINGUNO para creacion de productos sin especificacion de color
        color = {
            'cod': -1,
            'descripcion': 'NINGUNO',
        }
        grp_sice_color_obj.create(color)

        return True


    @api.multi
    def cargar_presentaciones(self):
        grp_sice_presentacion_obj = self.env['grp.sice_presentacion']
        grp_sice_unidades_med_obj = self.env['grp.sice_unidades_med']

        self._cr.execute("select * from sice_presentaciones")
        for presentacion in self._cr.dictfetchall():

            # Obtengo id de unidad de medida
            domain = [('cod','=',presentacion['unme_cod'])]
            unme = grp_sice_unidades_med_obj.with_context(active_test=False).search(domain)
            if not unme:
                _logger.info('ERROR: No se encontró Unidad de medida para la presentacion: %s', presentacion)
                continue

            if presentacion['fecha_baja']:
                presentacion['active'] = False

            presentacion['unme_id'] = unme.id
            grp_sice_presentacion_obj.create(presentacion)

        return True


    @api.multi
    def cargar_propiedades(self):
        grp_sice_propiedad_obj = self.env['grp.sice_propiedad']
        grp_sice_unidades_med_obj = self.env['grp.sice_unidades_med']

        self._cr.execute("select * from sice_propiedades")
        for propiedad in self._cr.dictfetchall():

            # Obtengo id de unidad de medida
            domain = [('cod', '=', propiedad['unme_cod'])]
            unme = grp_sice_unidades_med_obj.with_context(active_test=False).search(domain)
            if not unme:
                _logger.info('ERROR: No se encontró Unidad de medida para la propiedad: %s', propiedad)
                continue

            if propiedad['fecha_baja']:
                propiedad['active'] = False

            propiedad['unme_id'] = unme.id
            grp_sice_propiedad_obj.create(propiedad)

        return True


    @api.multi
    def cargar_articulos(self):
        # grp_sice_familia_obj = self.env['grp.sice_familia']
        # grp_sice_subflia_obj = self.env['grp.sice_subflia']
        # grp_sice_clase_obj = self.env['grp.sice_clase']
        # grp_sice_subclase_obj = self.env['grp.sice_subclase']
        # grp_sice_unidades_med_obj = self.env['grp.sice_unidades_med']
        # grp_sice_odg_obj = self.env['grp.sice_odg']

        grp_sice_art_serv_obra_obj = self.env['grp.sice_art_serv_obra']

        i = 0

        self._cr.execute("select * from sice_art_serv_obra order by cod")
        for art in self._cr.dictfetchall():

            i += 1
            _logger.info('Articulo nro: %s', i)

            # # Obtengo id de familia
            # familia = grp_sice_familia_obj.search([('cod', '=', art['fami_cod'])])
            # if not familia:
            #     _logger.info('ERROR: No se encontró familia para el articulo: %s', art)
            #     continue

            # # Obtengo id de subfamilia
            # subfamilia = grp_sice_subflia_obj.search(
            #     [('fami_cod', '=', art['fami_cod']), ('cod', '=', art['subf_cod'])])
            # if not subfamilia:
            #     _logger.info('ERROR: No se encontró subfamilia para el articulo: %s', art)
            #     continue

            # # Obtengo id de clase
            # clase = grp_sice_clase_obj.search(
            #     [('fami_cod', '=', art['fami_cod']), ('subf_cod', '=', art['subf_cod']),
            #      ('cod', '=', art['clas_cod'])])
            # if not clase:
            #     _logger.info('ERROR: No se encontró clase para el articulo: %s', art)
            #     continue

            # # Obtengo id de subclase
            # subclase = grp_sice_subclase_obj.search(
            #     [('fami_cod', '=', art['fami_cod']), ('subf_cod', '=', art['subf_cod']),
            #      ('clas_cod', '=', art['clas_cod']), ('cod', '=', art['subc_cod'])])
            # if not subclase:
            #     _logger.info('ERROR: No se encontró subclase para el articulo: %s', art)
            #     continue

            # # Obtengo id de unidad de medida de la variante
            # var_unme = grp_sice_unidades_med_obj.search([('cod', '=', art['var_unme_cod'])])
            # if not var_unme:
            #     _logger.info('ERROR: No se encontró unidad de medida de la variante para el articulo: %s', art)
            #     continue

            # # Obtengo id de unidad de medida del articulo
            # unme = grp_sice_unidades_med_obj.search([('cod', '=', art['unme_cod'])])
            # if not unme:
            #     _logger.info('ERROR: No se encontró unidad de medida para el articulo: %s', art)
            #     continue

            # # Obtengo id de Odg
            # odg = grp_sice_odg_obj.search([('odg', '=', art['odg'])])
            # if not odg:
            #     _logger.info('ERROR: No se encontró odg para el articulo: %s', art)
            #     continue


            # if art['fecha_baja']:
            #     art['active'] = False

            # art['fami_id'] = familia.id
            # art['subf_id'] = subfamilia.id
            # art['clas_id'] = clase.id
            # art['subc_id'] = subclase.id
            # art['var_unme_id'] = var_unme.id
            # art['unme_id'] = unme.id
            # art['odg_id'] = odg.id

            grp_sice_art_serv_obra_obj.create(art)

        return True


    @api.multi
    def cargar_atributos_de_articulos(self):

        # grp_sice_art_serv_obra_obj = self.env['grp.sice_art_serv_obra']
        # grp_sice_propiedad_obj = self.env['grp.sice_propiedad']
        # grp_sice_unidades_med_obj = self.env['grp.sice_unidades_med']

        grp_sice_art_atributo_obj = self.env['grp.sice_art_atributo']

        self._cr.execute("select * from sice_art_atributos")

        i = 0

        for atributo in self._cr.dictfetchall():

            i+=1
            _logger.info('Atributo nro: %s',i)
            # _logger.info('Atributo: %s', atributo)


            # Obtengo id de articulo
            # domain = [('cod', '=', atributo['arse_cod'])]
            # articulo = grp_sice_art_serv_obra_obj.with_context(active_test=False).search(domain)
            # if not articulo:
            #     _logger.info('ERROR: No se encontró Articulo para art_atributo: %s', atributo)
            #     continue

            # _logger.info('articulo: %s', articulo)


            # Obtengo id de propiedad
            # domain = [('cod', '=', atributo['prop_cod'])]
            # propiedad = grp_sice_propiedad_obj.with_context(active_test=False).search(domain)
            # if not propiedad:
            #     _logger.info('ERROR: No se encontró Propiedad para art_atributo: %s', atributo)
            #     continue

            # _logger.info('propiedad: %s', propiedad)

            # Obtengo id de unidad de medida
            # domain = [('cod', '=', atributo['prop_unme_cod'])]
            # unmed = grp_sice_unidades_med_obj.with_context(active_test=False).search(domain)
            # if not unmed:
            #     _logger.info('ERROR: No se encontró Unidad de medida para art_atributo: %s', atributo)
            #     continue

            # _logger.info('unidad de medida: %s', unmed)

            # atributo['articulo_id'] = articulo.id
            # atributo['prop_id'] = propiedad.id
            # atributo['prop_unme_id'] = unmed.id

            # _logger.info('ATRIBUTO: %s', atributo)

            grp_sice_art_atributo_obj.create(atributo)
        return True


    # @api.multi
    # def cargar_colores_de_articulos(self):
    #     grp_sice_art_serv_obra_obj = self.env['grp.sice_art_serv_obra']
    #     grp_sice_color_obj = self.env['grp.sice_color']
    #
    #     grp_sice_art_color_obj = self.env['grp.sice_art_color']
    #
    #
    #     self._cr.execute("select * from sice_art_colores")
    #     i = 0
    #     for art_color in self._cr.dictfetchall():
    #
    #         i+=1
    #         _logger.info('Color nro: %s',i)
    #
    #         # Obtengo id de articulo
    #         domain = [('cod', '=', art_color['arse_cod'])]
    #         articulo = grp_sice_art_serv_obra_obj.with_context(active_test=False).search(domain)
    #         if not articulo:
    #             _logger.info('ERROR: No se encontró Articulo para art_color: %s', art_color)
    #             continue
    #
    #         _logger.info('articulo: %s', articulo)
    #
    #
    #         # Obtengo id de color
    #         domain = [('cod', '=', art_color['colo_cod'])]
    #         color = grp_sice_color_obj.with_context(active_test=False).search(domain)
    #         if not color:
    #             _logger.info('ERROR: No se encontró Color para art_color: %s', art_color)
    #             continue
    #
    #         _logger.info('color: %s', color)
    #
    #         art_color['articulo_id'] = articulo.id
    #         art_color['colo_id'] = color.id
    #         if art_color['fecha_baja']:
    #             art_color['active'] = False
    #
    #         grp_sice_art_color_obj.create(art_color)
    #     return True


    @api.multi
    def cargar_variantes(self):
        # grp_sice_art_serv_obra_obj = self.env['grp.sice_art_serv_obra']
        # grp_sice_medida_obj = self.env['grp.sice_medida']
        # grp_sice_presentacion_obj = self.env['grp.sice_presentacion']

        grp_sice_med_variante_obj = self.env['grp.sice_med_variante']

        self._cr.execute("select * from sice_med_variantes")

        i = 0

        for variante in self._cr.dictfetchall():

            i += 1
            _logger.info('Variante nro: %s', i)
            _logger.info('Variante: %s', variante)

            # Obtengo id de articulo
            # domain = [('cod', '=', variante['arse_cod'])]
            # articulo = grp_sice_art_serv_obra_obj.with_context(active_test=False).search(domain)
            # if not articulo:
            #     _logger.info('ERROR: No se encontró Articulo para variante: %s', variante)
            #     continue

            # _logger.info('articulo: %s', articulo)

            # Obtengo id de medida (variante)
            # domain = [('cod', '=', variante['med_cod_variante'])]
            # medida_variante = grp_sice_medida_obj.with_context(active_test=False).search(domain)
            # if not medida_variante:
            #     _logger.info('ERROR: No se encontró Medida para variante: %s', variante)
            #     continue

            # _logger.info('propiedad: %s', propiedad)

            # Obtengo id de presentacion
            # domain = [('cod', '=', variante['pres_cod'])]
            # presentacion = grp_sice_presentacion_obj.with_context(active_test=False).search(domain)
            # if not presentacion:
            #     _logger.info('ERROR: No se encontró Presentacion para variante: %s', variante)
            #     continue

            # _logger.info('unidad de medida: %s', unmed)

            # Obtengo id de medida (presentacion)
            # domain = [('cod', '=', variante['med_cod_pres'])]
            # medida_presentacion = grp_sice_medida_obj.with_context(active_test=False).search(domain)
            # if not medida_presentacion:
            #     _logger.info('ERROR: No se encontró Medida de la Presentacion para variante: %s', variante)
            #     continue


            # variante['articulo_id'] = articulo.id
            # variante['med_cod_id'] = medida_variante.id
            # variante['pres_id'] = presentacion.id
            # variante['med_cod_pres_id'] = medida_presentacion.id

            # _logger.info('ATRIBUTO: %s', atributo)

            grp_sice_med_variante_obj.create(variante)

        return True


    @api.multi
    def cargar_detalle_variantes(self):
        # grp_sice_art_serv_obra_obj = self.env['grp.sice_art_serv_obra']
        # grp_sice_medida_obj = self.env['grp.sice_medida']
        # grp_sice_presentacion_obj = self.env['grp.sice_presentacion']
        # grp_sice_marca_obj = self.env['grp.sice_marca']

        grp_sice_det_variante_obj = self.env['grp.sice_det_variante']

        self._cr.execute("select * from sice_det_variantes")

        i = 0

        for det_variante in self._cr.dictfetchall():

            i += 1
            if i%10 == 0:
                _logger.info('det_Variante nro: %s', i)


            # Obtengo id de articulo
            # domain = [('cod', '=', det_variante['arse_cod'])]
            # articulo = grp_sice_art_serv_obra_obj.with_context(active_test=False).search(domain)
            # if not articulo:
            #     _logger.info('ERROR: No se encontró Articulo para detalle de variante: %s', det_variante)
            #     continue

            # Obtengo id de marca
            # domain = [('cod', '=', det_variante['marc_cod'])]
            # marca = grp_sice_marca_obj.with_context(active_test=False).search(domain)
            # if not marca:
            #     _logger.info('ERROR: No se encontró Marca para detalle de variante: %s', det_variante)
            #     continue

            # Obtengo id de medida (variante)
            # domain = [('cod', '=', det_variante['med_cod_variante'])]
            # medida_variante = grp_sice_medida_obj.with_context(active_test=False).search(domain)
            # if not medida_variante:
            #     _logger.info('ERROR: No se encontró Medida para detalle de variante: %s', det_variante)
            #     continue


            # Obtengo id de presentacion
            # domain = [('cod', '=', det_variante['pres_cod'])]
            # presentacion = grp_sice_presentacion_obj.with_context(active_test=False).search(domain)
            # if not presentacion:
            #     _logger.info('ERROR: No se encontró Presentacion para detalle de variante: %s', det_variante)
            #     continue


            # Obtengo id de medida (presentacion)
            # domain = [('cod', '=', det_variante['med_cod_pres'])]
            # medida_presentacion = grp_sice_medida_obj.with_context(active_test=False).search(domain)
            # if not medida_presentacion:
            #     _logger.info('ERROR: No se encontró Medida de la Presentacion para detalle de variante: %s', det_variante)
            #     continue

            # det_variante['articulo_id'] = articulo.id
            # det_variante['med_cod_id'] = medida_variante.id
            # det_variante['pres_id'] = presentacion.id
            # det_variante['med_cod_pres_id'] = medida_presentacion.id
            # det_variante['marc_id'] = marca.id


            grp_sice_det_variante_obj.create(det_variante)
        return True


    # Carga de Catalogo de Atributos y Valores de Atributos con las dimensiones SICE:
    # - COLOR
    # - PRESENTACION
    # - VARIANTE
    # - DETALLE DE VARIANTE

    @api.multi
    def cargar_atributos_colores(self):
        # Carga el catalgo de atributos con las dimensiones de los articulos SICE
        product_attribute_obj = self.env['product.attribute']
        product_attribute_val_obj = self.env['product.attribute.value']

        # Carga de Colores
        # -----------------------------------------------------------------
        atributo = {}
        atributo['name'] = 'COLOR'
        atributo['dimension_sice'] = True
        atributo_ref = product_attribute_obj.create(atributo)

        self._cr.execute("select * from grp_sice_color where active")
        for color in self._cr.dictfetchall():
            atributo_valor = {}

            atributo_valor['attribute_id'] = atributo_ref.id
            atributo_valor['sice_color_id'] = color['id']
            atributo_valor['name'] = color['descripcion']

            product_attribute_val_obj.create(atributo_valor)
        return True

    @api.multi
    def cargar_product_attribute_variantes(self):

        product_attribute_obj = self.env['product.attribute']

        # Carga de Variantes
        # -----------------------------------------------------------------
        self._cr.execute("select * from grp_sice_propiedad")
        for propiedad in self._cr.dictfetchall():
            atributo = {}
            atributo['sice_propiedad_id'] = propiedad['id']
            atributo['name'] = 'VARIANTE: ' + propiedad['descripcion']
            atributo['dimension_sice'] = True

            atributo_ref = product_attribute_obj.create(atributo)
        return True


    @api.multi
    def cargar_product_attribute_value_medida(self):

        product_attribute_obj = self.env['product.attribute']
        product_attribute_val_obj = self.env['product.attribute.value']
        grp_sice_art_serv_obra_obj = self.env['grp.sice_art_serv_obra']
        grp_sice_medida_obj = self.env['grp.sice_medida']
        grp_sice_presentacion_obj = self.env['grp.sice_presentacion']

        med_var = 0

        # Cargo valores de atributo con las Medidas de Variantes
        self._cr.execute("select * from grp_sice_med_variante")
        for med_variante in self._cr.dictfetchall():
            atributo_valor = {}

            med_var += 1
            if med_var % 100 == 0:
                _logger.info('Medida nro: %s', med_var)

            # Obtengo id de variante del articulo
            domain = [('cod', '=', med_variante['arse_cod'])]
            articulo = grp_sice_art_serv_obra_obj.with_context(active_test=False).search(domain)
            if not articulo:
                _logger.info('ERROR: No se encontró Articulo con cod : %s', med_variante['arse_cod'])
                continue

            # Obtengo id de propiedad (variante)
            var_id = articulo.var_id.id

            # Obtengo id de atributo
            domain = [('sice_propiedad_id', '=', var_id)]
            atributo = product_attribute_obj.search(domain)
            if not atributo:
                _logger.info('ERROR: No se encontró Product Attribute con sice_propiedad_id : %s', var_id)
                continue
            product_attribute_id = atributo.id

            # Obtengo medida
            domain = [('id', '=', med_variante['med_cod_id'])]
            medida = grp_sice_medida_obj.with_context(active_test=False).search(domain)
            if not medida:
                _logger.info('ERROR: No se encontró Medida con id : %s', med_variante['med_cod_id'])
                continue

            # Obtengo presentacion
            domain = [('cod', '=', med_variante['pres_cod'])]
            presentacion = grp_sice_presentacion_obj.with_context(active_test=False).search(domain)
            if not presentacion:
                _logger.info('ERROR: No se encontró Presentacion para variante: %s', med_variante)
                continue

            # Obtengo medida de presentacion
            domain = [('cod', '=', med_variante['med_cod_pres'])]
            medida_presentacion = grp_sice_medida_obj.with_context(active_test=False).search(domain)
            if not medida_presentacion:
                _logger.info('ERROR: No se encontró Medida de la Presentacion para variante: %s', med_variante)
                continue

            # Verifico que no exista un valor de atributo ya creado
            domain = [('attribute_id', '=', product_attribute_id),('articulo_id', '=', articulo.id),('med_cod_id', '=', med_variante['med_cod_id']),('pres_id', '=', med_variante['pres_id']),('med_cod_pres_id', '=', med_variante['med_cod_pres_id'])]
            valor_atributo = product_attribute_val_obj.with_context(active_test=False).search(domain)
            if valor_atributo:
                _logger.info('Ya existe valor de atributo para el atributo: %s, medida de variante: %s', product_attribute_id, med_variante)
                continue

            atributo_valor['attribute_id'] = product_attribute_id
            atributo_valor['articulo_id'] = articulo.id
            atributo_valor['med_cod_id'] = med_variante['med_cod_id']
            atributo_valor['pres_id'] = med_variante['pres_id']
            atributo_valor['med_cod_pres_id'] = med_variante['med_cod_pres_id']
            atributo_valor['name'] = articulo.descripcion + ' [' + str(articulo.cod) + '] '\
                         + ' - ' + medida.descripcion + ' [' + str(medida.cod) + '] '\
                            + ' - ' + presentacion.descripcion + ' [' + str(presentacion.cod) + '] '\
                         + ' - ' + medida_presentacion.descripcion + ' [' + str(medida_presentacion.cod) + ']'
            product_attribute_val_obj.create(atributo_valor)
        return True

    @api.multi
    def cargar_product_attribute_value_detalle(self):

        product_attribute_obj = self.env['product.attribute']
        product_attribute_val_obj = self.env['product.attribute.value']
        grp_sice_art_serv_obra_obj = self.env['grp.sice_art_serv_obra']
        grp_sice_medida_obj = self.env['grp.sice_medida']
        grp_sice_presentacion_obj = self.env['grp.sice_presentacion']
        grp_sice_marca_obj = self.env['grp.sice_marca']

        det_var = 0

        # Cargo valores de atributo con los Detalle de Variantes
        self._cr.execute("select * from grp_sice_det_variante")
        for det_variante in self._cr.dictfetchall():
            atributo_valor = {}

            det_var += 1
            if det_var % 100 == 0:
                _logger.info('Detalle nro: %s', det_var)

            # Obtengo id de variante del articulo
            domain = [('cod', '=', det_variante['arse_cod'])]
            articulo = grp_sice_art_serv_obra_obj.with_context(active_test=False).search(domain)
            if not articulo:
                _logger.info('ERROR: No se encontró Articulo con cod : %s', det_variante['arse_cod'])
                continue

            # Obtengo id de propiedad (variante)
            var_id = articulo.var_id.id

            # Obtengo id de atributo
            domain = [('sice_propiedad_id', '=', var_id)]
            atributo = product_attribute_obj.search(domain)
            if not atributo:
                _logger.info('ERROR: No se encontró Product Attribute con sice_propiedad_id : %s', var_id)
                continue
            product_attribute_id = atributo.id

            # Obtengo medida de variante
            domain = [('id', '=', det_variante['med_cod_id'])]
            medida = grp_sice_medida_obj.with_context(active_test=False).search(domain)
            if not medida:
                _logger.info('ERROR: No se encontró Medida con id : %s', det_variante['med_cod_id'])
                continue

            # Obtengo presentacion
            domain = [('cod', '=', det_variante['pres_cod'])]
            presentacion = grp_sice_presentacion_obj.with_context(active_test=False).search(domain)
            if not presentacion:
                _logger.info('ERROR: No se encontró Presentacion para variante: %s', det_variante)
                continue

            # Obtengo medida de presentacion
            domain = [('cod', '=', det_variante['med_cod_pres'])]
            medida_presentacion = grp_sice_medida_obj.with_context(active_test=False).search(domain)
            if not medida_presentacion:
                _logger.info('ERROR: No se encontró Presentacion: %s', det_variante)
                continue

            # Obtengo marca
            domain = [('cod', '=', det_variante['marc_cod'])]
            marca = grp_sice_marca_obj.with_context(active_test=False).search(domain)
            if not marca:
                _logger.info('ERROR: No se encontró Marca: %s', det_variante)
                continue


            # Verifico que no exista un valor de atributo ya creado
            domain = [('attribute_id', '=', product_attribute_id), ('articulo_id', '=', articulo.id),
                      ('med_cod_id', '=', det_variante['med_cod_id']), ('pres_id', '=', det_variante['pres_id']),
                      ('med_cod_pres_id', '=', det_variante['med_cod_pres_id']),('det_variante_id', '=', det_variante['id']) ]

            valor_atributo = product_attribute_val_obj.with_context(active_test=False).search(domain)
            if valor_atributo:
                _logger.info('Ya existe valor de atributo para el atributo: %s, detalle de variante: %s',
                             product_attribute_id, det_variante)
                continue

            atributo_valor['attribute_id'] = product_attribute_id
            atributo_valor['articulo_id'] = articulo.id
            atributo_valor['med_cod_id'] = det_variante['med_cod_id']
            atributo_valor['pres_id'] = det_variante['pres_id']
            atributo_valor['med_cod_pres_id'] = det_variante['med_cod_pres_id']
            atributo_valor['det_variante_id'] = det_variante['id']

            atributo_valor['name'] = articulo.descripcion + ' [' + str(articulo.cod) + '] ' \
                                     + ' - ' + medida.descripcion + ' [' + str(medida.cod) + '] ' \
                                     + ' - ' + presentacion.descripcion + ' [' + str(
                presentacion.cod) + '] ' \
                                     + ' - ' + medida_presentacion.descripcion + ' [' + str(medida_presentacion.cod) + ']' \
                                     + ' - ' + marca.descripcion + ' [' + str(marca.cod) + ']' \
                                     + ' - ' + det_variante['descripcion'].replace("'","''")

            product_attribute_val_obj.create(atributo_valor)

        return True



            # @api.multi
    # def cargar_atributos_detalle_variantes(self):
        # product_attribute_obj = self.env['product.attribute']
        # product_attribute_val_obj = self.env['product.attribute.value']
        #
        # # Carga el catalgo de atributos con las dimensiones de los articulos SICE
        # # Carga de Detalle de Variantes
        # # -----------------------------------------------------------------
        # atributo = {}
        # atributo['name'] = 'DETALLE DE VARIANTE'
        # atributo['dimension_sice'] = True
        # atributo_ref = product_attribute_obj.create(atributo)
        #
        # self._cr.execute("""select distinct d.marc_id, m.descripcion marca, d.descripcion
        #                     from grp_sice_det_variante d,
        #                          grp_sice_marca m
        #                     where m.id = d.marc_id
        #                     order by marca, descripcion""")
        #
        # det_var  = 0
        #
        # for detalle in self._cr.dictfetchall():
        #
        #     det_var += 1
        #     _logger.info('Detallea: %s', det_var)
        #
        #
        #     atributo_valor = {}
        #
        #     atributo_valor['attribute_id'] = atributo_ref.id
        #     atributo_valor['sice_marc_id'] = detalle['marc_id']
        #     atributo_valor['sice_detalle_variante_desc'] = detalle['descripcion']
        #     atributo_valor['name'] = detalle['marca'] + ' - ' + detalle['descripcion']
        #
        #     product_attribute_val_obj.create(atributo_valor)
        #
        # return True


    @api.multi
    def cargar_sinonimos_de_articulos(self):

        grp_sice_art_serv_obra_obj = self.env['grp.sice_art_serv_obra']
        grp_sice_sinonimo_obj = self.env['grp.sice_sinonimo']

        self._cr.execute("select * from sice_sinonimos")

        i = 0

        for sinonimo in self._cr.dictfetchall():
            i += 1
            _logger.info('Sinonimo nro: %s', i)

            # Obtengo id de articulo
            domain = [('cod', '=', sinonimo['arse_cod'])]
            articulo = grp_sice_art_serv_obra_obj.with_context(active_test=False).search(domain)
            if not articulo:
                _logger.info('ERROR: No se encontró Articulo para sinonimo: %s', sinonimo)
                continue

            sinonimo['articulo_id'] = articulo.id

            grp_sice_sinonimo_obj.create(sinonimo)
        return True

grpCargaCatalogoSice()











