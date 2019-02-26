# -*- encoding: utf-8 -*-
from openerp import models, fields, api, tools
from openerp.exceptions import Warning, ValidationError
from grp_pep_concepto import get_odg_aux_ff


class grp_linea_monto_compra(models.Model):
    _inherit = 'grp.linea.monto.compra'

    @api.multi
    def name_get(self):
        data = []
        for linea in self:
            display_name = "%s (%s) %s - %s" % (linea.tipo_compra_id.display_name,
                                                linea.monto_compra_id.anio_vigencia,
                                                linea.desde,
                                                linea.hasta)
            data.append((linea.id, display_name))
        return data

grp_linea_monto_compra()


# LINEA ADQUISICIONES
class grp_pep_anual_linea_adquisicion(models.Model):
    _name = 'grp.pep.anual.linea.adquisicion'

    TDO_BIEN = 'bien'
    TDO_SERVICIO = 'servicio'
    TDO_OBRA = 'obra'
    TDO_CONCEPTO = 'concepto'
    TDO_NE = 'no_existe'
    TIPOS_DE_OBJETO = [
        (TDO_BIEN, 'bien'),
        (TDO_SERVICIO, 'servicio'),
        (TDO_OBRA, 'obra'),
        (TDO_CONCEPTO, 'concepto'),
        (TDO_NE, 'no existe')
    ]

    SI_NO = [
        ('Si', 'Si'),
        ('No', 'No')
    ]

    def _domain_procedimiento_contratacion(self):
        lista_ids = []
        if self.env.context.get('active_model') == self._name:
            plan_anual_id = self.browse(self.env.context['active_id']).plan_anual_id
            if plan_anual_id:
                # Obtengo el año anterior al fiscal
                anio = int(plan_anual_id.anio_fiscal.code) - 1

                # filtro los valores de montos de compra
                monto_compra = self.env['grp.monto.compras'].search([('anio_vigencia', '=', anio), ('activo_compras', '=', True)])
                if monto_compra:
                    monto_compra = monto_compra[0]

                lista_ids = monto_compra.linea_ids.ids
        return [('id', 'in', lista_ids)]

    def _obtener_monto_y_cantidad(self, dict_producto_y_sus_conceptos):
        """
            Obtiene el monto asociado a la linea del plan
        """

        # Dependiendo si es concepto o producto se obtiene el monto de forma diferente
        if self.concepto_id:
            monto = self.concepto_id.get_monto_por_odg_aux_ff(self.odg_id.id, self.aux_id.id, self.ff_id.id)
            cantidad = 0
        else:
            # Obtengo los ids de Concepto en los que está el producto
            set_concepto_ids = dict_producto_y_sus_conceptos.get(self.product_id.id, [])

            # Si no hay conceptos que tengan el producto no se puede calcular un monto
            if not set_concepto_ids:
                return 0.0, 0

            # Obtengo la ddistribución de cantidades y montos en las llaves
            concepto_ids = self.env['grp.pep.concepto'].browse(set_concepto_ids)
            distribucion_del_gasto, distribucion_de_cantidaes = concepto_ids.get_distribucion_gasto_producto(self.product_id.id)

            # Calculo la llave que me interesa y la utilizo para obtener monto y cantidad
            llave = get_odg_aux_ff(self.odg_id, self.aux_id, self.ff_id)
            monto = distribucion_del_gasto.get(llave, 0.0)
            cantidad = distribucion_de_cantidaes.get(llave, 0)
        return monto, cantidad

    @api.multi
    def set_procedimiento_contratacion_y_cantidad_estimada(self, dict_producto_y_sus_conceptos):
        """ Setea el procedimiento de compra correcto según el monto """

        # Obtengo las lineas validas de montos de compra TOCAF
        # Obtengo el año anterior al fiscal del plan de la primer linea
        if len(self) > 0:
            anio = int(self[0].plan_anual_id.anio_fiscal.code) - 1

            # filtro los valores de montos de compra, debería haber solo 1 activo
            monto_compra = self.env['grp.monto.compras'].search([('anio_vigencia', '=', anio),
                                                                 ('activo_compras', '=', True)])
            if monto_compra:
                monto_compra = monto_compra[0]
            else:
                raise ValidationError(u"No se encontraron montos TOCAF para el año %s (año anterior al año "
                                      u"fiscal del plan). No se permite la creación del Plan de Adquisiciones."
                                      % str(anio))

            # Creo estructuras auxiliares para el algoritmo de pertenencia a rangos de montos
            lista_ids = monto_compra.linea_ids.ids
            lista_desde = []
            lista_hasta = []
            for linea in monto_compra.linea_ids:
                lista_desde.append(linea.desde)
                lista_hasta.append(lista_hasta)

            for rec in self:
                monto, cantidad = rec._obtener_monto_y_cantidad(dict_producto_y_sus_conceptos)
                # Comparo el monto contra los segmentos desde hasta, cuando monto está contenido en uno,
                # seteo el procedimiento de contratación correpondiente según la lista_ids
                for i in range(len(lista_ids)):
                    if lista_desde[i] <= monto <= lista_hasta[i]:
                        rec.procedimiento_contratacion = lista_ids[i]
                        break
                # Seteo cantidad estimada
                rec.write({'cantidad_estimada': cantidad,
                           'importe_estimado': monto})

    # Campos basicos para generar las lineas
    plan_anual_id = fields.Many2one(comodel_name='grp.pep.anual')
    plan_state = fields.Selection(related='plan_anual_id.state', string=u'Estado', readonly=True)
    concepto_id = fields.Many2one(comodel_name='grp.pep.concepto')
    product_id = fields.Many2one(comodel_name='product.product')
    cantidad_estimada = fields.Integer(string=u"Cantidad Estimada")
    importe_estimado = fields.Float(string=u'Importe Estimado')
    compras_innovadoras = fields.Boolean(string=u"Compras Innovadoras",
                                         related='concepto_id.es_compra_innovadora')
    odg_id = fields.Many2one(comodel_name='grp.estruc_pres.odg',
                             string=u'Código ODG')
    aux_id = fields.Many2one(comodel_name='grp.estruc_pres.aux',
                             string=u'Auxiliar')
    ff_id = fields.Many2one(comodel_name='grp.estruc_pres.ff',
                            string=u"Fuente de Financiamiento")

    # Campos extra
    id_planificacion = fields.Integer(string=u"Id de Planificación")
    descripcion_objeto = fields.Char(string=u"Descripción General del Objeto")
    procedimiento_contratacion = fields.Many2one(comodel_name='grp.linea.monto.compra',
                                                 string=u"Procedimiento de Contratación",
                                                 domain=_domain_procedimiento_contratacion)
    fecha_estimada_convocatoria = fields.Date(string=u"Fecha Estimada de Convocatoria")
    fecha_estimada_recepcion = fields.Date(string=u"Fecha Estimada de Recepción")
    estimacion_renovacion = fields.Selection(string=u"Estimación de Renovación", selection=SI_NO)
    destino_adquisicion = fields.Char(string=u"Destino de la adquisición")
    sujeto_autorizacion_externa = fields.Selection(string=u"Sujeto a Autorización Externa de Fondos",
                                                   selection=SI_NO)
    compras_innovadoras_desc = fields.Char(string=u"Descripción Compras Innovadoras")
    observaciones = fields.Text(string=u"Observaciones")

    # Campos calculados
    tipo_de_objeto = fields.Selection(string=u'Tipo de Objeto',
                                      selection=TIPOS_DE_OBJETO,
                                      compute='_compute_campos_calculados')
    identificacion_objeto = fields.Char(string=u"Identificación del objeto", compute='_compute_campos_calculados')

    codigo_odg = fields.Char(string=u'Código ODG.Aux', compute='_compute_campos_calculados')
    descripcion_odg = fields.Char(string=u'Descripción ODG', compute='_compute_campos_calculados')
    product_uom = fields.Char(string=u"Unidad de Medida", related='product_id.uom_id.name')

    @api.multi
    def _compute_campos_calculados(self):
        for rec in self:
            es_concepto = True if rec.concepto_id else False
            rec.identificacion_objeto = rec.concepto_id.name if es_concepto else rec.product_id.display_name

            str_odg = rec.odg_id.odg if rec.odg_id else u''
            str_aux = rec.aux_id.aux if rec.aux_id else u''
            rec.codigo_odg = str_odg + '.' + str_aux

            odg = self.env['presupuesto.objeto.gasto'].search([('name', '=', str_odg),
                                                               ('auxiliar', '=', str_aux)])
            rec.descripcion_odg = odg.descripcion if odg else u''

            # Si es Concepto seteo el tipo concepto
            rec.tipo_de_objeto = self.TDO_NE
            if es_concepto:
                rec.tipo_de_objeto = self.TDO_CONCEPTO
            else:
                # Si es Producto busco el articulo SICE y seteo el tipo que corresponda
                sice_cod = rec.product_id.grp_sice_cod
                art_sice = self.env['grp.sice_art_serv_obra'].search([('cod', '=', sice_cod)])

                if len(art_sice) == 1:
                    tipo = art_sice.ind_art_serv
                    if tipo == 'A':
                        rec.tipo_de_objeto = self.TDO_BIEN
                    elif tipo == 'S':
                        rec.tipo_de_objeto = self.TDO_SERVICIO
                    elif tipo == 'O':
                        rec.tipo_de_objeto = self.TDO_OBRA

    @api.multi
    def obtener_presupuesto(self):
        """
            Calcula la suma de la plata de todos los conceptos que se incluyen
            en el plan de adquisiciones
        """
        presup = 0
        # TODO: Implementar
        for rec in self:
            # presup+=
            pass

        return presup

    @api.multi
    def abrir_detalle(self):
        """ Boton para abrir detalle de linea """
        self.ensure_one()
        xml_id_obj = self.env['ir.model.data']

        # Si tiene el grupo pep_adquisiciones abro la vista editable
        if self.env.user.has_group('grp_plan_ejecucion_presupuestal.pep_adquisiciones'):
            form_id = xml_id_obj.get_object_reference('grp_plan_ejecucion_presupuestal',
                                                      'view_grp_pep_anual_adquisicion_detalle_form')[1]
        # Sinó abro la vista readonly
        else:
            form_id = xml_id_obj.get_object_reference('grp_plan_ejecucion_presupuestal',
                                                      'view_grp_pep_anual_adquisicion_detalle_readonly_form')[1]
        return {
            'name': u"Detalle Adquisición",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.anual.linea.adquisicion',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(form_id, 'form')],
            'target': 'new',
            'domain': [('', )]
        }

grp_pep_anual_linea_adquisicion()


# EXPORT ADQUISICIONES
class grp_pep_export_adquisiciones(models.TransientModel):
    """ Wizard para descarga de Export de plan de adquisiciones """
    _name = 'grp.pep.export.adquisiciones'
    archivo_nombre = fields.Char(string='Nombre del archivo')
    archivo_contenido = fields.Binary(string="Archivo")

grp_pep_export_adquisiciones()