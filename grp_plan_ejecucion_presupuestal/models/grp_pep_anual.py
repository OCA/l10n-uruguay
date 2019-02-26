# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2018 Datamatic All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from collections import defaultdict
from lxml import etree

from openerp import models, fields, api, tools
from openerp.exceptions import Warning, ValidationError
import base64
from cStringIO import StringIO
from xlwt import Workbook, easyxf


class grp_pep_anual(models.Model):
    _name = 'grp.pep.anual'

    # Tipos de control
    ALERTA_NO_BLOQUEANTE = 'alerta_no_bloqueante'
    ALERTA_BLOQUEANTE    = 'alerta_bloqueante'
    DEFINIDO_EN_CONCEPTO = 'definido_en_concepto'
    TIPO_CONTROL_CONCEPTOS = [
        (ALERTA_NO_BLOQUEANTE, 'Alerta para todos'),
        (ALERTA_BLOQUEANTE, 'Bloquear para todos'),
        (DEFINIDO_EN_CONCEPTO,'Definido en el concepto')
    ]

    # Periodicidad
    MENSUAL = '12'
    BIMENSUAL = '6'
    TRIMESTRAL = '4'
    CUATRIMESTRAL = '3'
    SEMESTRAL = '2'
    periodos = [
        (MENSUAL, 'Mes'),
        (BIMENSUAL, 'Bimestre'),
        (TRIMESTRAL, 'Trimestre'),
        (CUATRIMESTRAL, 'Cuatrimestre'),
        (SEMESTRAL, 'Semestre'),
    ]

    # Estados
    BORRADOR = 'borrador'
    CONFECCION = 'confeccion'
    ANALISIS = 'analisis'
    ACTUALIZACION = 'actualizacion'
    VERIFICACION = 'verificacion'
    APROBADO = 'aprobado'
    EN_EJECUCION = 'en_ejecucion'
    CIERRE = 'cierre'
    FINALIZADO = 'finalizado'
    estados = [
        (BORRADOR, u'Borrador'),
        (CONFECCION, u'Confección'),
        (ANALISIS, u'Análisis'),
        (ACTUALIZACION, u'Actualización'),
        (VERIFICACION, u'Verificación'),
        (APROBADO, u'Aprobado'),
        (EN_EJECUCION, u'En ejecución'),
        (CIERRE, u'Cierre'),
        (FINALIZADO, u'Finalizado')
    ]

    RA_APROBADO = 'aprobado'
    RA_RECHAZADO = 'rechazado'
    resultados_aprobacion = [
        (RA_APROBADO, 'Aprobado'),
        (RA_RECHAZADO, 'Rechazado')
    ]

    # Expreso los estados como lista para tener facilmente una relación de orden entre ellos
    LISTA_ESTADOS = [e[0] for e in estados]

    state = fields.Selection(string=u'Estado', selection=estados, default=BORRADOR)
    plan_activo = fields.Boolean(string=u'Activo', default=False)
    name = fields.Char(string=u'Nombre')
    plan_base_id = fields.Many2one(string='Plan base', comodel_name='grp.pep.anual')
    estructura_de_servicios_id = fields.Many2one(string=u'Estructura de servicios', comodel_name='grp.pep.estructura')
    numero_inciso = fields.Integer(related='inciso_id.idInciso', string=u'N° Inciso')
    inciso_id = fields.Many2one(string=u'Descripción Inciso', comodel_name='sicec.inciso', required=True)
    numero_unidad_ejecutora = fields.Integer(related='unidad_ejecutora_id.idUE', string=u'N° Unidad Ejecutora')
    unidad_ejecutora_id = fields.Many2one(string=u'Unidad ejecutora', comodel_name='sicec.ue', required=True)
    jerarca_id = fields.Many2one(string='Nombre Apellido', comodel_name='hr.employee', required=True)
    cargo_jerarca = fields.Many2one(related='jerarca_id.job_id', string='Cargo', readonly=True)
    telefono_jerarca = fields.Char(related='jerarca_id.work_phone', string=u'Teléfono', readonly=True)
    correo_jerarca = fields.Char(related='jerarca_id.work_email', string=u'Correo electrónico', readonly=True)
    responsable_id = fields.Many2one(string='Nombre Apellido', comodel_name='hr.employee', required=True)
    telefono_responsable = fields.Char(related='responsable_id.work_phone', string=u'Teléfono', readonly=True)
    correo_responsable = fields.Char(related='responsable_id.work_email', string=u'Correo electrónico', readonly=True)
    periodicidad = fields.Selection(string=u'Periodicidad', selection=periodos, required=True)
    periodo_activo = fields.Integer(string=u'Período activo', default=0)
    presupuesto_anual = fields.Float(string=u'Presupuesto anual', compute='_compute_presupuesto_anual')
    anio_fiscal = fields.Many2one(string=u'Año fiscal', comodel_name='account.fiscalyear', required=True)
    tipo_control_conceptos = fields.Selection(string=u'Tipo de control de los conceptos', selection=TIPO_CONTROL_CONCEPTOS, required=True)
    tiene_productos = fields.Boolean(string=u"Tiene Productos", compute='_compute_tiene_productos')

    # Plan de Adquisiciones
    unidad_de_compra = fields.Char(string=u"Descripción Unidad de Compra")
    responsable_adqui_id = fields.Many2one(string='Nombre Apellido', comodel_name='hr.employee')
    telefono_responsable_adqui = fields.Char(related='responsable_adqui_id.work_phone', string=u'Teléfono', readonly=True)
    correo_responsable_adqui = fields.Char(related='responsable_adqui_id.work_email', string=u'Correo electrónico', readonly=True)
    presupuesto_anual_adqui = fields.Float(string=u'Presupuesto anual adquisiciones', compute='_compute_presupuesto_anual_adqui')
    fecha_actualizacion_adqui = fields.Date(string=u"Fecha de actualización del plan")

    # Aprobación
    aprobacion_resultado = fields.Selection(selection=resultados_aprobacion, string=u'Resultado Aprobación')
    aprobacion_observaciones = fields.Text(string=u'Observaciones')

    lineas_concepto = fields.One2many(string=u'Conceptos', comodel_name='grp.pep.anual.linea.concepto', inverse_name='plan_anual_id')
    lineas_gasto = fields.One2many(string=u'Distribución del gasto', comodel_name='grp.pep.anual.linea.gasto', inverse_name='plan_anual_id')
    lineas_receta = fields.One2many(string='Recetas', comodel_name='grp.pep.receta', inverse_name='plan_id')
    lineas_actualizacion = fields.One2many(string=u'Actualización de existencias', comodel_name='grp.pep.anual.linea.actualizacion', inverse_name='plan_anual_id')
    lineas_existencia = fields.One2many(string=u'Análisis de Existencias',
                                        comodel_name='grp.pep.anual.linea.existencia',
                                        inverse_name='plan_anual_id')
    lineas_adquisicion = fields.One2many(string=u'Plan de Adquisiciones',
                                         comodel_name='grp.pep.anual.linea.adquisicion',
                                         inverse_name='plan_anual_id')
    lineas_comparar_credito = fields.One2many(string='Comparación con crédito SIIF',
                                              comodel_name='grp.pep.comparar.credito.siif', inverse_name='plan_id')
    lineas_ejecucion = fields.One2many(string=u'Ejecución del plan',
                                       comodel_name='grp.pep.anual.linea.ejecucion', inverse_name='plan_id')

    lineas_aprobacion = fields.One2many(string=u"Historico de Aprobación",
                                        comodel_name='grp.pep.anual.linea.aprobacion',
                                        inverse_name='plan_anual_id')
    # -------------------------------------------------------------------------------------------------------- #
    # Campos duplicados de los originales version compute (Necesarios para modelar la casuistica de seguridad) #
    # -------------------------------------------------------------------------------------------------------- #
    fn_plan_activo = fields.Boolean(string=u'Activo', default=False, compute='_compute_fn_plan_activo')
    fn_name = fields.Char(string=u'Nombre', compute='_compute_fn_name')
    fn_plan_base_id = fields.Many2one(string='Plan base', comodel_name='grp.pep.anual', compute='_compute_fn_plan_base_id')
    fn_estructura_de_servicios_id = fields.Many2one(string=u'Estructura de servicios', comodel_name='grp.pep.estructura', compute='_compute_fn_estructura_de_servicios_id')
    fn_numero_inciso = fields.Integer(related='inciso_id.idInciso', string=u'N° Inciso', readonly=True)
    fn_inciso_id = fields.Many2one(string=u'Descripción Inciso', comodel_name='sicec.inciso', compute='_compute_fn_inciso_id')
    fn_numero_unidad_ejecutora = fields.Integer(related='unidad_ejecutora_id.idUE', string=u'N° Unidad Ejecutora', readonly=True)
    fn_unidad_ejecutora_id = fields.Many2one(string=u'Unidad ejecutora', comodel_name='sicec.ue', compute='_compute_fn_unidad_ejecutora_id')
    fn_jerarca_id = fields.Many2one(string='Nombre Apellido', comodel_name='hr.employee', compute='_compute_fn_jerarca_id')
    fn_cargo_jerarca = fields.Many2one(related='jerarca_id.job_id', string='Cargo', readonly=True)
    fn_telefono_jerarca = fields.Char(related='jerarca_id.work_phone', string=u'Teléfono', readonly=True)
    fn_correo_jerarca = fields.Char(related='jerarca_id.work_email', string=u'Correo electrónico', readonly=True)
    fn_responsable_id = fields.Many2one(string='Nombre Apellido', comodel_name='hr.employee', compute='_compute_fn_responsable_id')
    fn_telefono_responsable = fields.Char(related='responsable_id.work_phone', string=u'Teléfono', readonly=True)
    fn_correo_responsable = fields.Char(related='responsable_id.work_email', string=u'Correo electrónico', readonly=True)
    fn_periodicidad = fields.Selection(string=u'Periodicidad', selection=periodos, compute='_compute_fn_periodicidad')
    fn_periodo_activo = fields.Integer(string=u'Período activo', default=0, compute='_compute_fn_periodo_activo')
    fn_presupuesto_anual = fields.Float(string=u'Presupuesto anual', compute='_compute_fn_presupuesto_anual')
    fn_anio_fiscal = fields.Many2one(string=u'Año fiscal', comodel_name='account.fiscalyear', compute='_compute_fn_anio_fiscal')
    fn_tipo_control_conceptos = fields.Selection(string=u'Tipo de control de los conceptos',
                                                 selection=TIPO_CONTROL_CONCEPTOS,
                                                 compute='_compute_fn_tipo_control_conceptos')
    fn_tiene_productos = fields.Boolean(string=u"Tiene Productos", compute='_compute_fn_tiene_productos')
    fn_fecha_creacion = fields.Datetime(string=u"Fecha de Creación", compute='_compute_fn_fecha_creacion')

    # Plan de Adquisiciones
    fn_unidad_de_compra = fields.Char(string=u"Descripción Unidad de Compra", compute='_compute_fn_unidad_de_compra')
    fn_responsable_adqui_id = fields.Many2one(string='Nombre Apellido', compute='_compute_fn_responsable_adqui_id')
    fn_telefono_responsable_adqui = fields.Char(string=u'Teléfono',
                                                compute='_compute_fn_telefono_responsable_adqui')
    fn_correo_responsable_adqui = fields.Char(string=u'Correo electrónico',
                                              compute='_compute_fn_correo_responsable_adqui')
    fn_presupuesto_anual_adqui = fields.Float(string=u'Presupuesto anual adquisiciones',
                                              compute='_compute_fn_presupuesto_anual_adqui')
    fn_fecha_actualizacion_adqui = fields.Date(string=u"Fecha de actualización del plan",
                                               compute='_compute_fn_fecha_actualizacion_adqui')

    # Aprobación
    # fn_aprobacion_resultado = fields.Selection(selection=resultados_aprobacion,
    #                                            string=u'Resultado Aprobación',
    #                                            compute='_compute_fn_aprobacion_resultado')
    # fn_aprobacion_observaciones = fields.Text(string=u'Observaciones',
    #                                           compute='_compute_fn_aprobacion_observaciones')

    # -------------------------------------- #
    # Funciones compute de campos duplicados #
    # -------------------------------------- #
    @api.depends('plan_activo')
    def _compute_fn_plan_activo(self):
        for rec in self:
            rec.fn_plan_activo = rec.plan_activo

    @api.depends('name')
    def _compute_fn_name(self):
        for rec in self:
            rec.fn_name = rec.name

    @api.depends('plan_base_id')
    def _compute_fn_plan_base_id(self):
        for rec in self:
            rec.fn_plan_base_id = rec.plan_base_id.id

    @api.depends('estructura_de_servicios_id')
    def _compute_fn_estructura_de_servicios_id(self):
        for rec in self:
            rec.fn_estructura_de_servicios_id = rec.estructura_de_servicios_id.id

    @api.depends('inciso_id')
    def _compute_fn_inciso_id(self):
        for rec in self:
            rec.fn_inciso_id = rec.inciso_id

    @api.depends('unidad_ejecutora_id')
    def _compute_fn_unidad_ejecutora_id(self):
        for rec in self:
            rec.fn_unidad_ejecutora_id = rec.unidad_ejecutora_id.id

    @api.depends('jerarca_id')
    def _compute_fn_jerarca_id(self):
        for rec in self:
            rec.fn_jerarca_id = rec.jerarca_id.id

    @api.depends('responsable_id')
    def _compute_fn_responsable_id(self):
        for rec in self:
            rec.fn_responsable_id = rec.responsable_id.id

    @api.depends('telefono_responsable')
    def _compute_fn_telefono_responsable(self):
        for rec in self:
            rec.fn_telefono_responsable = rec.telefono_responsable

    @api.depends('periodicidad')
    def _compute_fn_periodicidad(self):
        for rec in self:
            rec.fn_periodicidad = rec.periodicidad

    @api.depends('periodo_activo')
    def _compute_fn_periodo_activo(self):
        for rec in self:
            rec.fn_periodo_activo = rec.periodo_activo

    @api.depends('presupuesto_anual')
    def _compute_fn_presupuesto_anual(self):
        for rec in self:
            rec.fn_presupuesto_anual = rec.presupuesto_anual

    @api.depends('anio_fiscal')
    def _compute_fn_anio_fiscal(self):
        for rec in self:
            rec.fn_anio_fiscal = rec.anio_fiscal

    @api.depends('tipo_control_conceptos')
    def _compute_fn_tipo_control_conceptos(self):
        for rec in self:
            rec.fn_tipo_control_conceptos = rec.tipo_control_conceptos

    @api.depends('tiene_productos')
    def _compute_fn_tiene_productos(self):
        for rec in self:
            rec.fn_tiene_productos = rec.tiene_productos

    @api.depends('unidad_de_compra')
    def _compute_fn_unidad_de_compra(self):
        for rec in self:
            rec.fn_unidad_de_compra = rec.unidad_de_compra

    @api.depends('responsable_adqui_id')
    def _compute_fn_responsable_adqui_id(self):
        for rec in self:
            rec.fn_responsable_adqui_id = rec.responsable_adqui_id.id

    @api.depends('telefono_responsable_adqui')
    def _compute_fn_telefono_responsable_adqui(self):
        for rec in self:
            rec.fn_telefono_responsable_adqui = rec.telefono_responsable_adqui

    @api.depends('correo_responsable_adqui')
    def _compute_fn_correo_responsable_adqui(self):
        for rec in self:
            rec.fn_correo_responsable_adqui = rec.correo_responsable_adqui

    @api.depends('presupuesto_anual_adqui')
    def _compute_fn_presupuesto_anual_adqui(self):
        for rec in self:
            rec.fn_presupuesto_anual_adqui = rec.presupuesto_anual_adqui

    @api.depends('fecha_actualizacion_adqui')
    def _compute_fn_fecha_actualizacion_adqui(self):
        for rec in self:
            rec.fn_fecha_actualizacion_adqui = rec.fecha_actualizacion_adqui

    # @api.depends('aprobacion_resultado')
    # def _compute_fn_aprobacion_resultado(self):
    #     self.fn_aprobacion_resultado = self.aprobacion_resultado

    # @api.depends('aprobacion_observaciones')
    # def _compute_fn_aprobacion_observaciones(self):
    #     for rec in self:
    #         rec.fn_aprobacion_observaciones = rec.aprobacion_observaciones

    @api.depends('create_date')
    def _compute_fn_fecha_creacion(self):
        for rec in self:
            rec.fn_fecha_creacion = rec.create_date

    # -------------------------------------- #
    # -------------------------------------- #

    @api.multi
    def _compute_tiene_productos(self):
        """
            Devuelve True si el plan tiene al menos un producto
        """
        metodo_receta = self.env['grp.pep.concepto'].METODO_RECETA
        for rec in self:
            tiene_productos = False
            for linea in rec.lineas_concepto:
                if linea.concepto_id.compuesto_por_productos or linea.concepto_id.metodo_calculo == metodo_receta:
                    tiene_productos = True
                    break
            rec.tiene_productos = tiene_productos

    """
    Interfaz para procesos del GEP.

    Todos los métods operan sobre el plan activo

        - Obtener Conceptos del plan
        - Obtener llaves de un concepto
        - Consultar Saldo de Plan-Concepto-Llave segun Importe
        - Ejecutar Fondo Presupuestal
    """

    # Resultados de consulta de saldo
    CONCEPTO_LLAVE_CON_SALDO = 1
    CONCEPTO_LLAVE_SIN_SALDO_ADVERTENCIA = 2
    CONCEPTO_LLAVE_SIN_SALDO_BLOQUEO = 3

    # Resultados de ejecución
    EJECUCION_OK = 'OK'
    EJECUCION_ERROR = 'ERROR'

    def obtener_plan_activo(self):
        plan_activo = self.search([('plan_activo', '=', True)])
        # Si hay uno o ninguno retorno un plan o un plan vacio
        if len(plan_activo) <= 1:
            return plan_activo
        else:
            # Si hay más de un plan activo retorno el primero de la lista
            return plan_activo[0]

    def obtener_conceptos_plan_activo(self):
        plan = self.obtener_plan_activo()
        lineas_concepto = self.env['grp.pep.anual.linea.concepto'].search([('plan_anual_id','=',plan.id)])
        concepto_ids = [l.concepto_id.id for l in lineas_concepto]
        return self.env['grp.pep.concepto'].browse(concepto_ids)

    def obtener_llaves_concepto(self,concepto_id):
        llaves = []
        concepto = self.env['grp.pep.concepto'].browse([concepto_id])
        for linea in concepto.lineas_gasto:
            llaves.append(linea.display_name)
        return llaves

    def saldo_disponible(self,concepto_id,llave,importe):
        saldo = 0
        plan = self.obtener_plan_activo()
        concepto = self.env['grp.pep.concepto'].browse([concepto_id])
        linea_gasto = next((linea for linea in concepto.lineas_gasto if llave == linea.display_name),None)

        # Si existe la llave
        if linea_gasto:
            # A priori tomo el importe inicial del Concepto mismo y aplico el % de la llave
            importe_inicial = concepto.importe * linea_gasto.porcentaje_del_gasto / 100

            # Si hay línea de ejecución
            linea_ejecucion = next((linea for linea in plan.lineas_ejecucion if concepto_id == linea.concepto_id.id),None)
            if linea_ejecucion:
                # El importe inicial se toma de la ejecución y sus ajustes
                importe_inicial = linea_ejecucion.importe_anual_llave(linea_gasto.display_name)

            # Aplico los movimientos con su signo (las cancelaciones son negativas)
            condicion = []
            condicion.append(('plan_anual_id','=',plan.id))
            condicion.append(('concepto_id','=',concepto_id))
            condicion.append(('llave_str','=',llave))
            movimientos = self.env['grp.pep.movimiento.ejecucion'].search(condicion)
            total_movimientos = sum(linea.importe for linea in movimientos)
            saldo = importe_inicial - total_movimientos

        # Qué acción seguir
        if saldo >= importe:
            return plan.CONCEPTO_LLAVE_CON_SALDO
        else:
            if plan.tipo_control_conceptos == plan.ALERTA_NO_BLOQUEANTE:
                return plan.CONCEPTO_LLAVE_SIN_SALDO_ADVERTENCIA

            elif plan.tipo_control_conceptos == plan.ALERTA_BLOQUEANTE:
                return plan.CONCEPTO_LLAVE_SIN_SALDO_BLOQUEO

            elif plan.tipo_control_conceptos == plan.DEFINIDO_EN_CONCEPTO:

                if concepto.tipo_control == concepto.ALERTA_NO_BLOQUEANTE:
                    return plan.CONCEPTO_LLAVE_SIN_SALDO_ADVERTENCIA

                elif concepto.tipo_control == concepto.ALERTA_BLOQUEANTE:
                    return plan.CONCEPTO_LLAVE_SIN_SALDO_BLOQUEO

    def ejecutar_fondo_presupuestal(self,concepto_id,llave,importe,documento,proceso_origen):
        plan = self.obtener_plan_activo()
        if plan.state == 'en_ejecucion':
            values = {
                'plan_anual_id': plan.id,
                'periodo': plan.periodo_activo,
                'concepto_id': concepto_id,
                'llave_str': llave,
                'importe': importe,
                'codigo_documento_asociado': documento,
                'proceso_origen': proceso_origen,
            }
            try:
                self.env['grp.pep.movimiento.ejecucion'].create(values)
            except Exception as e:
                resultado = self.EJECUCION_ERROR
                diagnostico = u'No sepudo crear la ejecución: %s.' % (str(e))
            else:
                resultado = self.EJECUCION_OK
                diagnostico = ''
        else:
                resultado = self.EJECUCION_ERROR
                diagnostico = u'El Plan no está en Ejecución.'

        return (resultado, diagnostico)

    def cancelar_ejecucion_fondo(self,concepto_id,llave,importe,documento,proceso_origen):
        """
        La cancelación de una ejecución se registra como una ejecución con importe negativo.
        Los parámetros de la cancelación deben ser los mismos que los de la ejecución.
        """
        return self.ejecutar_fondo_presupuestal(concepto_id,llave,-importe,documento,proceso_origen)

    @api.multi
    def check_precio_productos_concepto(self):
        self.ensure_one()
        concepto_ids = [l.concepto_id.id for l in self.lineas_concepto]
        conceptos = self.env['grp.pep.concepto'].browse(concepto_ids)
        productos_sin_precio = conceptos.productos_sin_precio()
        if productos_sin_precio:
            raise ValidationError("Error: Los siguientes conceptos tienen productos sin precio, %s" % (productos_sin_precio))

    @api.multi
    def check_llaves_concepto(self):
        self.ensure_one()
        concepto_ids = [l.concepto_id.id for l in self.lineas_concepto]
        conceptos = self.env['grp.pep.concepto'].browse(concepto_ids)
        llaves_sin_porcentaje = conceptos.llaves_sin_porcentaje()
        if llaves_sin_porcentaje:
            raise ValidationError("Error: Los siguientes conceptos tienen llaves con 0%%, %s" % (llaves_sin_porcentaje))
        llaves_no_suman_100 = conceptos.llaves_no_suman_100()
        if llaves_no_suman_100:
            raise ValidationError("Error: Los siguientes conceptos tienen llaves que no suman 100%%, %s" % (llaves_no_suman_100))

    @api.multi
    def check_porcentajes_concepto(self):
        self.ensure_one()
        linea_concepto_ids = [l.id for l in self.lineas_concepto]
        lineas_concepto = self.env['grp.pep.anual.linea.concepto'].browse(linea_concepto_ids)
        conceptos_porc_no_100 = lineas_concepto.porcentajes_no_100()
        if conceptos_porc_no_100:
            raise ValidationError(u"Error: Los siguientes conceptos no totalizan 100%% en la suma de sus periodos, %s" % (conceptos_porc_no_100))

    @api.multi
    def check_necesidad_productos_receta(self):
        self.ensure_one()
        receta_ids = [l.id for l in self.lineas_receta]
        recetas = self.env['grp.pep.receta'].browse(receta_ids)
        recetas_sin_necesidad = recetas.productos_sin_necesidad()
        if recetas_sin_necesidad:
            raise ValidationError("Error: Las siguientes recetas tienen productos sin necesidad, %s" % (recetas_sin_necesidad))

    @api.multi
    def check_productos_actualizados(self):
        self.ensure_one()
        productos_sin_actualizar = self.env['grp.pep.anual.linea.actualizacion'].search([('procesado','=',False),('plan_anual_id','=',self.id)])
        if productos_sin_actualizar:
            raise ValidationError("Error: Todavía quedan productos sin actualizar.")

    @api.multi
    def check_analisis_existencias_ejecutado(self):
        self.ensure_one()
        if self.tiene_productos and not self.lineas_existencia:
            raise ValidationError(u"No se encontraron lineas de analisis de existencias y el plan tiene productos. "
                                  u"Debe haberse ejecutado un Analisis de Existencias previo a "
                                  u"crear un Plan de Adquisiciones.")

    @api.multi
    def actualiza_importes_periodo(self, periodo):
        for linea in self.lineas_ejecucion:
            linea.cierra_importes_periodo(periodo)

    @api.multi
    def registra_historia_llaves(self, periodo):
        for linea in self.lineas_ejecucion:
            linea.registra_historia_llaves_periodo(periodo)

    @api.multi
    def btn_pep_borrador_confeccion(self):
        for record in self:
            record.state = 'confeccion'

    @api.multi
    def btn_pep_confeccion_borrador(self):
        for record in self:
            record.state = 'borrador'

    @api.multi
    def btn_pep_confeccion_analisis(self):
        for record in self:
            record.check_llaves_concepto()
            record.check_precio_productos_concepto()
            record.check_porcentajes_concepto()
            record.check_necesidad_productos_receta()
            record.state = 'analisis'

    @api.multi
    def btn_pep_analisis_confeccion(self):
        for record in self:
            record.state = 'confeccion'

    @api.multi
    def btn_pep_analisis_actualizacion(self):
        for record in self:
            record.state = 'actualizacion'

    @api.multi
    def btn_pep_actualizacion_analisis(self):
        for record in self:
            record.state = 'analisis'

    @api.multi
    def btn_pep_actualizacion_verificacion(self):
        for record in self:
            record.check_productos_actualizados()
            record.check_analisis_existencias_ejecutado()
            record.state = 'verificacion'

    @api.multi
    def btn_pep_verificacion_actualizacion(self):
        for record in self:
            record.state = 'actualizacion'

    @api.multi
    def btn_pep_verificacion_aprobado(self):
        self.ensure_one()
        xml_id_obj = self.env['ir.model.data']
        form_id = xml_id_obj.get_object_reference('grp_plan_ejecucion_presupuestal',
                                                  'view_grp_pep_anual_aprobacion_form')[1]
        return {
            'name': "Aprobación del Plan Anual",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.anual',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(form_id, 'form')],
            'target': 'new'
        }

    @api.multi
    def btn_pep_aprobado_en_ejecucion(self):
        for record in self:
            record.state = 'en_ejecucion'
            record.periodo_activo = 1
            record.cargar_lineas_ejecucion()

    @api.multi
    def btn_pep_cerrar_periodo(self):
        for record in self:
            record.actualiza_importes_periodo(record.periodo_activo)
            record.registra_historia_llaves(record.periodo_activo)
            record.periodo_activo = record.periodo_activo + 1
            if record.periodo_activo > int(record.periodicidad):
                self.btn_pep_en_ejecucion_cierre()

    @api.multi
    def btn_pep_en_ejecucion_cierre(self):
        for record in self:
            record.state = 'cierre'

    @api.multi
    def btn_pep_cierre_finalizado(self):
        for record in self:
            record.state = 'finalizado'
            record.plan_activo = False

    @api.multi
    @api.onchange('anio_fiscal')
    def onchange_anio_fiscal(self):
        if self.anio_fiscal and self.plan_base_id:
            concepto_ids = [l.concepto_id.id for l in self.lineas_concepto]
            conceptos = self.env['grp.pep.concepto'].browse(concepto_ids)
            llaves_invalidas = conceptos.llaves_ausentes(self.anio_fiscal)
            if llaves_invalidas:
                self.anio_fiscal = self._origin.anio_fiscal
                return {
                    'warning': {
                        'title': u'Conceptos con llave inválida',
                        'message': u'Los sguientes conceptos contienen llaves inválidas: %s' % (llaves_invalidas)
                    },
                }

    @api.multi
    @api.onchange('periodicidad')
    def onchange_periodicidad(self):
        self.ajusta_porcentajes()
        if self.periodicidad and self.plan_base_id:
            if self.plan_base_id.periodicidad != self.periodicidad:
                return {
                    'warning': {
                        'title':'Periodicidad',
                        'message':'Cuidado: la periodicidad ha cambiado, es imperativo revisar las grillas presupuestales.',
                    },
                }

    @api.multi
    @api.onchange('estructura_de_servicios_id')
    def onchange_estructura(self):
        if self.estructura_de_servicios_id:
            for receta in self.lineas_receta:
                receta.actualizo_compatibilidad()

    @api.multi
    def _compute_presupuesto_anual(self):
        for rec in self:
            rec.presupuesto_anual = sum(linea.importe_anual for linea in rec.lineas_concepto)

    @api.multi
    def _compute_presupuesto_anual_adqui(self):
        for rec in self:
            rec.presupuesto_anual_adqui = rec.lineas_adquisicion.obtener_presupuesto()

    def _gen_lineas_concepto_para_plan_adquisiciones(self, concepto=None, set_conceptos=None):
        """
            Para un concepto o set de conceptos busca las combinaciones existentes de fuentes
            de financiamiento y ODG que serán utilizadas para generar lineas del plan de adquisiciones.
        """
        assert concepto or set_conceptos, u"Se debe proveer un concepto o set de conceptos para poder generar lineas " \
                                          u"para el plan de Adquisiciones"
        lista = []
        select = """SELECT DISTINCT odg_id, aux_id, ff_id
                    FROM grp_pep_concepto_linea_gasto """

        if concepto:
            where = """ WHERE grp_pep_concepto_id=%s;""" % (concepto.id,)
        else:
            tupla = "(" + ",".join(map(str, set_conceptos)) + ")"
            where = """ WHERE grp_pep_concepto_id in %s;""" % (tupla,)

        self.env.cr.execute(select+where)
        res = self.env.cr.fetchall()

        for row in res:
            lista.append({'odg_id': row[0],
                          'aux_id': row[1],
                          'ff_id': row[2]})
        return lista

    @api.multi
    def ajusta_porcentajes(self):
        for linea in self.lineas_concepto:
            linea.carga_porcentajes_por_defecto()

    @api.multi
    def generar_plan_adquisiciones(self):
        self.ensure_one()

        # Solo se permite generar el plan de aquisiciones en Aprobado y En Ejecución
        if self.state not in (self.APROBADO, self.EN_EJECUCION):
            raise ValidationError(u"El plan debe estar en estado 'Aprobado' para poder generar el plan de adquisiciones")

        # Borro las adquisiciones actuales
        self.lineas_adquisicion.unlink()

        # Obtengo productos y conceptos para crear las nuevas adquisiciones
        dict_producto_y_sus_conceptos, concepto_ids = self._productos_y_conceptos_plan_adquisiciones()

        # A partir de los productos, conceptos y los datos de existencias cargo las lineas de adquisiciones
        # Cargo lineas de Productos
        lista = []
        for producto, set_conceptos in dict_producto_y_sus_conceptos.iteritems():
            lineas_gen = self._gen_lineas_concepto_para_plan_adquisiciones(set_conceptos=set_conceptos)
            for linea in lineas_gen:
                lista.append((0, 0, {'plan_anual_id': self.id,
                                     'concepto_id': None,
                                     'product_id': producto,
                                     'odg_id': linea['odg_id'],
                                     'aux_id': linea['aux_id'],
                                     'ff_id': linea['ff_id']}))
        # Cargo lineas de Conceptos
        for concepto in concepto_ids:
            lineas_gen = self._gen_lineas_concepto_para_plan_adquisiciones(concepto=concepto)
            for linea in lineas_gen:
                lista.append((0, 0, {'plan_anual_id': self.id,
                                     'concepto_id': concepto.id,
                                     'product_id': None,
                                     'odg_id': linea['odg_id'],
                                     'aux_id': linea['aux_id'],
                                     'ff_id': linea['ff_id']}))

        self.lineas_adquisicion = lista
        lineas = self.env['grp.pep.anual.linea.adquisicion'].search([('plan_anual_id', '=', self.id)])
        lineas.set_procedimiento_contratacion_y_cantidad_estimada(dict_producto_y_sus_conceptos)
        pass

    @api.multi
    def exportar_excel_adquisiciones(self):
        self.ensure_one()

        # Creo el libro Excel
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('Sheet 1', cell_overwrite_ok=True)

        ws.protect = False
        ws.password = "/Dd3R$eg(&(=:.$"

        # Creo los 'estilos'
        header_left_bloqueado = easyxf('font: name Calibri, bold True; alignment: horizontal left;'
                                       ' pattern: pattern solid, fore_colour 0x16;')
        texto_bloqueado = easyxf('font: name Calibri; alignment: horizontal left;'
                                 ' pattern: pattern solid, fore_colour 0x16;')
        texto_editable = easyxf('font: name Calibri; alignment: horizontal left;'
                                ' protection: cell_locked false;')
        integer_editable = easyxf('font: name Calibri; alignment: horizontal right;'
                                  ' protection: cell_locked false;')

        fila_0 = 0
        fila_cabezal = fila_0 + 1
        fila = fila_cabezal + 1

        # Escribo el titulo
        ws.write(fila_0, 0, u"Plan de Adquisiciones:", header_left_bloqueado)
        ws.write(fila_0, 2, self.name, texto_bloqueado)

        # Escribo cabezales de filas
        ws.write(fila_cabezal, 0, u"Id. de Planificación", header_left_bloqueado)
        ws.write(fila_cabezal, 1, u"Tipo de Objeto", header_left_bloqueado)
        ws.write(fila_cabezal, 2, u"Descripción Gral. del objeto", header_left_bloqueado)
        ws.write(fila_cabezal, 3, u"Identificación del Objeto", header_left_bloqueado)
        ws.write(fila_cabezal, 4, u"Fuente de Financiamiento", header_left_bloqueado)
        ws.write(fila_cabezal, 5, u"Unidad de Medida", header_left_bloqueado)
        ws.write(fila_cabezal, 6, u"Procedimiento de Contratación", header_left_bloqueado)
        ws.write(fila_cabezal, 7, u"Fecha Estimada de Convocatoria", header_left_bloqueado)
        ws.write(fila_cabezal, 8, u"Fecha Estimada de Recepción de Mercadería", header_left_bloqueado)
        ws.write(fila_cabezal, 9, u"Cantidad Estimada", header_left_bloqueado)
        ws.write(fila_cabezal, 10, u"Importe Estimado", header_left_bloqueado)
        ws.write(fila_cabezal, 11, u"Estimación de Opción de Renovación", header_left_bloqueado)
        ws.write(fila_cabezal, 12, u"Código ODG.Auxiliar", header_left_bloqueado)
        ws.write(fila_cabezal, 13, u"Descripción ODG", header_left_bloqueado)
        ws.write(fila_cabezal, 14, u"Destino de la Adquisición", header_left_bloqueado)
        ws.write(fila_cabezal, 15, u"Sujeto a Autorización Externa de Fondos", header_left_bloqueado)
        ws.write(fila_cabezal, 16, u"Compras Innovadoras", header_left_bloqueado)
        ws.write(fila_cabezal, 17, u"Descripción de Compras Innovadoras", header_left_bloqueado)
        ws.write(fila_cabezal, 18, u"Observaciones", header_left_bloqueado)

        # Escribo filas del plan
        for linea in self.lineas_adquisicion.sorted(key=lambda x: x.identificacion_objeto):
            ws.write(fila, 0, linea.id_planificacion or u"", texto_editable)
            ws.write(fila, 1, linea.tipo_de_objeto or u"", texto_editable)
            ws.write(fila, 2, linea.descripcion_objeto or u"", texto_editable)
            ws.write(fila, 3, linea.identificacion_objeto or u"", texto_editable)
            ws.write(fila, 4, linea.ff_id.ff or u"", texto_editable)
            ws.write(fila, 5, linea.product_uom or u"", texto_editable)
            ws.write(fila, 6, linea.procedimiento_contratacion.display_name or u"", texto_editable)
            ws.write(fila, 7, linea.fecha_estimada_convocatoria or u"", texto_editable)
            ws.write(fila, 8, linea.fecha_estimada_recepcion or u"", texto_editable)
            ws.write(fila, 9, linea.cantidad_estimada or u"", texto_editable)
            ws.write(fila, 10, linea.importe_estimado or u"", texto_editable)
            ws.write(fila, 11, linea.estimacion_renovacion or u"", texto_editable)
            ws.write(fila, 12, linea.codigo_odg or u"", texto_editable)
            ws.write(fila, 13, linea.descripcion_odg or u"", texto_editable)
            ws.write(fila, 14, linea.destino_adquisicion or u"", texto_editable)
            ws.write(fila, 15, linea.sujeto_autorizacion_externa or u"", texto_editable)
            ws.write(fila, 16, u"Si" if linea.compras_innovadoras else u"No", texto_editable)
            ws.write(fila, 17, linea.compras_innovadoras_desc or u"", texto_editable)
            ws.write(fila, 18, linea.observaciones or u"", texto_editable)

            fila += 1

        # Salvo hacia un string IO
        fp = StringIO()
        wb.save(fp)

        # Guardo la planilla en un string
        fp.seek(0)
        data = fp.read()

        # Codifico a base 64
        data_to_save = base64.encodestring(data)

        # Creo el Wizard de Descarga con el archivo
        fp.close()
        file_name = 'Export_Adquisiciones_' + str(self.name) + '.xls'
        wiz_id = self.env['grp.pep.export.adquisiciones'].create({'archivo_nombre': file_name,
                                                                  'archivo_contenido': data_to_save})
        return {
            'name': "Exportar Plan de Adquisiciones",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.export.adquisiciones',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    @api.multi
    def publicar_plan_adquisiciones(self):
        raise ValidationError(u"FUNCIONALIDAD NO IMPLEMENTADA!")

    @api.one
    def copy(self, default=None):
        # Clonar con los datos pertinenetes a la copia
        default = default or {}
        default.update({
            'name': '',
            'plan_activo': False,
            'plan_base_id': self.id,
            'periodo_activo': 0,
            'aprobacion_resultado': '',
            'aprobacion_observaciones': '',
        })
        new_plan = super(grp_pep_anual, self).copy(default)

        # Para cada linea de concepto, creo la correspondiente clonando
        # el concepto referenciado
        for linea in self.lineas_concepto:
            values = {
                'plan_anual_id': new_plan.id,
                'concepto_id': linea.concepto_id.copy({'plan_id':new_plan.id}).id,
                'periodo1_porc': linea.periodo1_porc,
                'periodo2_porc': linea.periodo2_porc,
                'periodo3_porc': linea.periodo3_porc,
                'periodo4_porc': linea.periodo4_porc,
                'periodo5_porc': linea.periodo5_porc,
                'periodo6_porc': linea.periodo6_porc,
                'periodo7_porc': linea.periodo7_porc,
                'periodo8_porc': linea.periodo8_porc,
                'periodo9_porc': linea.periodo9_porc,
                'periodo10_porc': linea.periodo10_porc,
                'periodo11_porc': linea.periodo11_porc,
                'periodo12_porc': linea.periodo12_porc,
            }
            self.env['grp.pep.anual.linea.concepto'].create(values)

        return new_plan

    @api.multi
    def cargar_existencias(self):
        """
            Crea las lineas del Analisis de Existencias, borrando las lineas
            que existan al momento de ejecutar
        """
        self.ensure_one()

        # Solo se permite generar el plan de aquisiciones en Analisis
        if self.state not in (self.ANALISIS,):
            raise ValidationError(u"El plan debe estar en estado 'Análisis' "
                                  u"para poder cargar el Análisis de Existencias")

        # Borro las existencias actuales
        self.lineas_existencia.unlink()

        # Obtengo el resumen de necesidades por producto
        resumen = self._resumen_producto_necesidad()

        # A partir del resumen cargo las existencias
        lista = []
        for prod, cant in resumen.iteritems():
            lista.append((0, 0, {'plan_anual_id': self.id,
                                 'product_id': prod,
                                 'cantidad_planificada': cant}))

        self.lineas_existencia = lista

    @api.multi
    def cargar_existencias_para_actualizar(self):

        self.ensure_one()

        # Borrar las lineas de actualización exitentes
        self.env['grp.pep.anual.linea.actualizacion'].search([('plan_anual_id','=',self.id)]).unlink()

        # Para cada producto resultado del análisis creo un a línea de actualización
        productos = self.env['grp.pep.anual.linea.existencia'].search([('plan_anual_id','=',self.id),('por_procesar','=',True)])
        for un_producto in productos:
            values = {}
            values['plan_anual_id'] = self.id
            values['product_id'] = un_producto.product_id.id
            values['existencia'] = un_producto.existencias
            linea_actualizacion = self.env['grp.pep.anual.linea.actualizacion'].create(values)

            # Tomo los datos de cada concepto incluido en el plan que tenga este producto
            for linea_concepto in self.lineas_concepto:
                if linea_concepto.concepto_id.tiene_el_producto(un_producto.product_id.id):
                    values = linea_concepto.concepto_id.get_linea_producto(un_producto.product_id.id)
                    values['linea_actualizacion_id'] = linea_actualizacion.id
                    self.env['grp.pep.anual.actualizacion.concepto'].create(values)

    def _resumen_producto_necesidad(self):
        """
            Retorna un diccionario producto_id: necesidad agregado para
            todas las lineas de los conceptos que tienen productos.
        """
        ids = [x.concepto_id.id for x in self.lineas_concepto]
        conceptos = self.env['grp.pep.concepto'].browse(ids)
        resumen = conceptos.get_producto_necesidad()

        return resumen

    def _productos_y_conceptos_plan_adquisiciones(self):
        """
            Retorna los productos de conceptos del plan de adquisiciones
            y para los conceptos que tienen en_plan_adquisiciones=True y no tienen productos
            retorno el concepto mismo.
        """
        # Busco los conceptos de las lineas del plan
        ids = [x.concepto_id.id for x in self.lineas_concepto]
        conceptos = self.env['grp.pep.concepto'].browse(ids)

        # Los filtro por aquellos que pertenecen al Plan de Adquisiciones
        conceptos_en_plan_adq = conceptos.filtered(lambda x: x.en_plan_adquisiciones)

        # Obtengo los productos de esos conceptos asociados con los conceptos a los que pertenecen
        dict_productos_y_sus_conceptos = conceptos_en_plan_adq.get_productos_y_sus_conceptos()

        # Obtengo los conceptos sin productos que estan en el plan
        conceptos_sin_prod_adq = conceptos_en_plan_adq.filtrar_sin_productos()

        return dict_productos_y_sus_conceptos, conceptos_sin_prod_adq

    @api.multi
    def abrir_analisis_existencias(self):
        """ Botón para navegar hacia el análisis de existencias"""
        self.ensure_one()
        xml_id_obj = self.env['ir.model.data']
        form_id = xml_id_obj.get_object_reference('grp_plan_ejecucion_presupuestal',
                                                  'view_grp_pep_anual_existencias_form')[1]
        return {
            'name': "Analizar Existencias",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.anual',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(form_id, 'form')],
            'target': 'current',
        }

    @api.multi
    def abrir_plan_adquisiciones(self):
        """ Botón para navegar hacia el plan de adquisiciones"""
        self.ensure_one()
        xml_id_obj = self.env['ir.model.data']
        form_id = xml_id_obj.get_object_reference('grp_plan_ejecucion_presupuestal',
                                                  'view_grp_pep_anual_adquisiciones_form')[1]
        return {
            'name': "Plan de Adquisiciones",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.anual',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(form_id, 'form')],
            'target': 'current',
        }

    @api.multi
    def abrir_informacion_general(self):
        """ Boton para navegar hacia información general del plan """
        self.ensure_one()
        xml_id_obj = self.env['ir.model.data']
        form_id = xml_id_obj.get_object_reference('grp_plan_ejecucion_presupuestal',
                                                  'view_grp_pep_anual_form')[1]
        return {
            'name': "Plan Anual",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.anual',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(form_id, 'form')],
            'target': 'current',
        }

    @api.multi
    def abrir_conceptos_y_distribucion(self):
        """ Boton para despligar la vista correcta de conceptos y distribución del gasto"""
        self.ensure_one()
        xml_id_obj = self.env['ir.model.data']
        vista = 'view_grp_pep_anual_'+self.periodicidad+'_form'
        form_id = xml_id_obj.get_object_reference('grp_plan_ejecucion_presupuestal', vista)[1]
        return {
            'name': "Plan Anual",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.anual',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(form_id, 'form')],
            'target': 'current',
        }

    @api.multi
    def abrir_comparar_credito_siif(self):
        """ Botón para desplegar la vista de comparación con crédito SIIF"""
        self.ensure_one()
        self.cargar_comparar_credito_siif()
        xml_id_obj = self.env['ir.model.data']
        form_id = xml_id_obj.get_object_reference('grp_plan_ejecucion_presupuestal',
                                                  'view_grp_pep_anual_comparar_form')[1]
        return {
            'name': "Comparación con Crédito SIIF",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.anual',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(form_id, 'form')],
            'target': 'current',
        }

    def cargar_lineas_ejecucion(self):
        self.ensure_one()
        self.lineas_ejecucion.unlink()
        for linea in self.lineas_gasto:
            values = {'linea_gasto_id': linea.id,
                      'plan_id': self.id,
                      'importe_anual': linea.concepto_id.importe,
                      'periodo1_importe': linea.periodo1_importe,
                      'periodo2_importe': linea.periodo2_importe,
                      'periodo3_importe': linea.periodo3_importe,
                      'periodo4_importe': linea.periodo4_importe,
                      'periodo5_importe': linea.periodo5_importe,
                      'periodo6_importe': linea.periodo6_importe,
                      'periodo7_importe': linea.periodo7_importe,
                      'periodo8_importe': linea.periodo8_importe,
                      'periodo9_importe': linea.periodo9_importe,
                      'periodo10_importe': linea.periodo10_importe,
                      'periodo11_importe': linea.periodo11_importe,
                      'periodo12_importe': linea.periodo12_importe,
                      }
            ejec_id = self.env['grp.pep.anual.linea.ejecucion'].create(values)
            periodicidad = int(self.periodicidad)
            for item in linea.concepto_id.lineas_gasto:
                for i in range(1, periodicidad+1):
                    importe_concepto = getattr(linea, 'periodo' + str(i) + '_importe')
                    importe_llave = float(importe_concepto * item.porcentaje_del_gasto / 100)
                    llave = {'linea_ejecucion_id': ejec_id.id,
                             'llave_str': item.display_name,
                             'periodo': i,
                             'importe': importe_llave}
                    self.env['grp.pep.ejecucion.llave'].create(llave)

    @api.multi
    def cargar_comparar_credito_siif(self):
        self.ensure_one()
        # borro las líneas actuales
        self.lineas_comparar_credito.unlink()
        dic_llaves = {}
        for linea_concepto in self.lineas_concepto:
            concepto = linea_concepto.concepto_id
            for llave in concepto.lineas_gasto:
                if llave.display_name in dic_llaves:
                    dic_llaves[llave.display_name]['monto_anual'] += concepto.importe * llave.porcentaje_del_gasto / 100
                    dic_llaves[llave.display_name]['concepto_ids'].append(concepto.id)
                else:
                    monto_siif = 0
                    linea_siif = self.env['presupuesto.linea'].search(
                        [('budget_fiscal_year', '=', self.anio_fiscal.name),
                         ('budget_inciso', '=', llave.inciso_id.inciso),
                         ('ue', '=', llave.ue_id.ue),
                         ('programa', '=', llave.programa_id.programa),
                         ('proyecto', '=', llave.proyecto_id.proyecto),
                         ('moneda', '=', llave.moneda_id.moneda),
                         ('tipo_credito', '=', llave.tc_id.tc),
                         ('financiamiento', '=', llave.ff_id.ff),
                         ('objeto_gasto', '=', llave.odg_id.odg),
                         ('auxiliar', '=', llave.aux_id.aux)])
                    if linea_siif:
                        monto_siif = linea_siif.total

                    dic_llaves[llave.display_name] = {'plan_id': self.id,
                                                      'llave_id': llave.id,
                                                      'llave_nombre': llave.display_name,
                                                      'monto_anual': concepto.importe * llave.porcentaje_del_gasto / 100,
                                                      'credito_disponible': monto_siif,
                                                      'concepto_ids': [concepto.id],
                                                     }
        for key, value in dic_llaves.iteritems():
            comparar_id = self.env['grp.pep.comparar.credito.siif'].create({'plan_id': value['plan_id'],
                                                                            'llave_id': value['llave_id'],
                                                                            'llave_nombre': value['llave_nombre'],
                                                                            'monto_anual': value['monto_anual'],
                                                                            'credito_disponible': value['credito_disponible'],
                                                                           })
            for concepto in value['concepto_ids']:
                self.env['grp.pep.comparar.credito.siif.linea'].create({'comparar_id': comparar_id.id,
                                                                        'concepto_id': concepto})

    @api.multi
    def abrir_ajustar_plan(self):
        xml_id_obj = self.env['ir.model.data']
        vista = 'view_grp_pep_ejecucion_'+self.periodicidad+'_form'
        form_id = xml_id_obj.get_object_reference('grp_plan_ejecucion_presupuestal', vista)[1]

        return {
            'name': "Plan Anual",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.anual',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(form_id, 'form')],
            'target': 'current',
        }

    @api.multi
    def btn_copiar_importes_ajuste(self):
        self.ensure_one()
        for linea in self.lineas_ejecucion:
            linea.importe_anual = linea.importe_ajustado

    @api.multi
    def guardar_aprobacion(self):
        self.ensure_one()
        if self.env.context.get('desde_panel_aprobacion', False):
            self.lineas_aprobacion.create({'plan_anual_id': self.id,
                                           'aprobacion_resultado': self.aprobacion_resultado,
                                           'aprobacion_observaciones': self.aprobacion_observaciones})
            # Si ademas el resultado es aprobado, cambio el estado a aprobado
            if self.aprobacion_resultado==self.RA_APROBADO:
                self.state = self.APROBADO
            else:
                self.write({'state': self.CONFECCION,
                            'aprobacion_resultado': None,
                            'aprobacion_observaciones': None})
            # Si no se llamó desde el panel de aprobación, no permito que se guarden
            # los valores de aprobacion en el cabezal
        else:
            self.write({'aprobacion_resultado': None,
                        'aprobacion_observaciones': None})
        return

grp_pep_anual()


# LINEA APROBACION
class grp_pep_anual_linea_adquisicion(models.Model):
    _name = 'grp.pep.anual.linea.aprobacion'

    plan_anual_id = fields.Many2one(comodel_name='grp.pep.anual')
    aprobacion_resultado = fields.Selection(selection=grp_pep_anual.resultados_aprobacion, string=u"Resultado Aprobacion")
    aprobacion_observaciones = fields.Text(string=u"Observaciones")

grp_pep_anual_linea_adquisicion()
