# -*- encoding: utf-8 -*-
import copy
import json
from collections import defaultdict

from openerp import models, fields, api, tools
from openerp.exceptions import ValidationError, Warning
from cStringIO import StringIO
from xlwt import Workbook, easyxf
import base64
import re
from xlrd import open_workbook
import urllib2
import logging
_logger = logging.getLogger(__name__)

# Constantes
from openerp.tools import OrderedSet

SEPARADOR_PATH = u' | '
COMENTARIO = u'#'
CTX_BORRAR_ROOT = 'borrar_nodo_raiz'
DISABLE_BOTTOM_UP_IN_WRITE = 'disable_bottom_up'
COMUNA_POBLACION_ATENDIDA = u"Población Atendida"
ES_COPIA = 'es_copia'

# Criterios de Asignación
CR_USUARIO = 'usuario'
CR_CANT_FIJA = 'cantidad_fija'
CR_CANT_VARIABLE = 'cantidad_variable'
TIPOS_DE_CRITERIOS = [(CR_USUARIO, 'Usuario'),
                      (CR_CANT_FIJA, 'Cantidad Fija'),
                      (CR_CANT_VARIABLE, 'Cantidad variable')]


def get_encoded_wb(wb):
    """
        Recibe un Workbook y lo devuelve encoded en b64 listo para grabarse en un campo file
    """
    # Salvo hacia un string IO
    fp = StringIO()
    wb.save(fp)

    # Guardo la planilla en un string
    fp.seek(0)
    data = fp.read()

    # Codifico a base 64
    data_to_save = base64.encodestring(data)
    fp.close()
    return data_to_save


def get_urllib2_with_proxy_handler(self):
    """ Retorna la librería urllib2 con proxy handler instalado """

    proxy_settings = {}
    url_proxy_http = self.env['ir.config_parameter'].get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_proxy_http')
    url_proxy_https = self.env['ir.config_parameter'].get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_proxy_https')

    if url_proxy_http:
        proxy_settings.update({'http': url_proxy_http})
    if url_proxy_https:
        proxy_settings.update({'https': url_proxy_https})

    proxy_support = urllib2.ProxyHandler(proxy_settings)
    opener = urllib2.build_opener(proxy_support)
    urllib2.install_opener(opener)

    return urllib2


# ESTRUCTURA
class grp_pep_estructura(models.Model):
    _name = 'grp.pep.estructura'

    # Estados Estructura de Servicios
    BORRADOR = 'borrador'
    ABIERTA = 'abierta'
    UTILIZADA = 'utilizada'
    estados = [(BORRADOR, 'Borrador'),
               (ABIERTA, 'Abierta'),
               (UTILIZADA, 'Utilizada')]

    name = fields.Char(string="Nombre")
    display_name = fields.Char(compute='_compute_display_name', store=True)
    maxima_profundidad = fields.Integer("Maxima Profundidad", compute='_compute_maxima_profundidad')
    codigo = fields.Char("Código")
    active = fields.Boolean(string="Activa", default=True)
    state = fields.Selection(string='Estado',
                             selection=estados,
                             default=BORRADOR,
                             compute='_compute_state',
                             copy=False)

    root_node = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio',
                                string='Nodo raíz',
                                readonly=1,
                                copy=False)
    poblacion_atendida = fields.Integer(related='root_node.poblacion_atendida',
                                        string=COMUNA_POBLACION_ATENDIDA,
                                        readonly=1)
    unidad_ids = fields.One2many(comodel_name='grp.pep.unidad.de.servicio',
                                 inverse_name='estructura_id',
                                 string='Lista de Unidades')
    nivel_ids = fields.One2many(comodel_name='grp.pep.estructura.nivel',
                                inverse_name='estructura_id',
                                string='Niveles')
    atributo_ids = fields.One2many(comodel_name='grp.pep.estructura.atributo',
                                   inverse_name='estructura_id',
                                   string='Atributos')
    importada_por_ws = fields.Boolean(string=u'Importada por WS', default=False)

    @api.multi
    def _compute_maxima_profundidad(self):
        for rec in self:
            rec.maxima_profundidad = len(rec.nivel_ids)

    @api.multi
    def recalcular_estructura(self):
        self.ensure_one()
        self.root_node.recalcular_poblacion_atendida_top_down()

    def crear_path(self, partes):
        """
            Crea un path con formato válido sobre la estructura actual a
            partir de una lista de partes (strings). Se controlan que las
            partes no contengan el caracter separador  ni el caracter comentario.
        """
        # Si no mandan partes retorno el path al root node
        if not partes:
            return self.root_node.name

        # Control de Caracteres inválidos
        for parte in partes:
            if parte.count(SEPARADOR_PATH.strip()) or parte.count(COMENTARIO):
                raise ValidationError(u"Las partes de una ubicación no pueden contener los caracteres %s ni %s" %
                                      (SEPARADOR_PATH, COMENTARIO))

        # Si no tiene el root_node se lo agrego
        root_name = self.root_node.name
        if partes[0] != root_name:
            partes.insert(0, root_name)

        # Quito los espacios a la izquierda y derecha de las partes
        partes_2 = map(lambda x: unicode(x).strip(), partes)

        # Armo el path y devuelvo
        path = SEPARADOR_PATH.join(partes_2)
        return path

    def _completar_path(self, path):
        """
            Busca si el path viene con root-node, si no tiene se lo agrega
        """
        partes = path.split(SEPARADOR_PATH)
        if partes and not re.match(r'^ES\-\d+$', partes[0]):
            partes.insert(0, self.root_node.name)

        path = SEPARADOR_PATH.join(partes)
        return path

    @api.multi
    def _existe_atributo(self, attr_name=None):
        """
            Verifico que haya al menos un atributo con el nombre que me pasan
        """
        self.ensure_one()
        if attr_name:
            return any(map(lambda x: x.name==attr_name, self.atributo_ids))
        else:
            return False

    @api.multi
    def obtener_lista_niveles(self):
        """
            Retorna una lista con los nombres de los niveles de la estructura
        """
        self.ensure_one()
        return map(lambda x: x.name, self.nivel_ids.sorted(lambda x: x.numero))

    @api.multi
    def obtener_lista_atributos(self):
        """
            Retorna una lista con los nombres de los atributos de la estructura
        """
        self.ensure_one()
        return map(lambda x: x.name, self.atributo_ids.sorted(lambda x: x.name))

    @api.multi
    def obtener_info_niveles_por_path(self, path, attr_name=None):
        """
            A partir de un path devuelve una lista con diccionarios
            [
                {'nivel_id': <id nivel>,
                 'nivel_numero': <nro nivel>,
                 'nivel_nombre': <nombre nivel>,
                 'cantidad': <cantidad>}
            ]
            con los niveles que se encuentran por delante de la unidad seleccionada por el path y
            el resultado de consultar a la estructura sobre su población total filtrando o no
            por algun atributo. La consultas a la estructura se hacen sobre el sub-arbol establecido
            por el path.
            En caso de error devuelve False
        """
        self.ensure_one()
        res = []

        # Verifico existencia del atributo, si hay
        if attr_name and not self._existe_atributo(attr_name=attr_name):
            return False
            # raise ValidationError(u"No existe el atributo %s en la estructura actual." % attr_name)

        path = self._completar_path(path)

        # Obtengo la unidad
        unidad_id = self._obtener_unidad_por_path(path)

        if unidad_id:
            # Si la unidad es_root, obtengo el primer nivel desde la estructura
            if unidad_id.is_root:
                nivel_id = self.get_primer_nivel()
            else:
                nivel_id = unidad_id.nivel_id

            # Creo el primer elemento de la lista y lo agrego a res
            elem = {'nivel_id': nivel_id.id,
                    'nivel_numero': nivel_id.numero,
                    'nivel_nombre': nivel_id.name}

            if attr_name:
                elem['cantidad'] = unidad_id.get_valor_atributo(attr_name)
            else:
                elem['cantidad'] = unidad_id.poblacion_atendida

            res.append(elem)

            while nivel_id:
                nivel_id = nivel_id.siguiente_nivel(return_false_on_final=True)
                if nivel_id:
                    res.append({'nivel_id': nivel_id.id,
                                'nivel_numero': nivel_id.numero,
                                'nivel_nombre': nivel_id.name,
                                'cantidad': 0})

            # Calculo las cantidades por nivel
            niveles_cantidad = defaultdict(int)
            unidad_id.cantidades_por_nivel_subarbol(niveles_cantidad)

            # Las agrego a res
            for dic in res[1:]:
                if dic['nivel_id'] in niveles_cantidad:
                    dic['cantidad'] = niveles_cantidad[dic['nivel_id']]

            return res

        # Si no se encuentra el path es un error
        return False

    @api.multi
    def exportar_estructura(self):
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
        ws.write(fila_0, 0, u"Estructura de Servicios:", header_left_bloqueado)
        ws.write(fila_0, 1, self.name, texto_bloqueado)
        ws.write(fila_0, 2, u"Código", header_left_bloqueado)
        ws.write(fila_0, 3, self.codigo, texto_bloqueado)

        # Escribo cabezal, niveles
        col = 0
        for nivel in self.nivel_ids.sorted(key=lambda x: x.numero):
            ws.write(fila_cabezal, col, nivel.name, header_left_bloqueado)
            col += 1

        # Escribo población atendida
        col_poblacion_atendida = col
        ws.write(fila_cabezal, col_poblacion_atendida, COMUNA_POBLACION_ATENDIDA, header_left_bloqueado)
        col += 1

        # Escribo cabezal, atributos
        attr_col_dict = {}
        for atributo in self.atributo_ids.sorted(key=lambda x: x.name):
            # Escribo la celda
            ws.write(fila_cabezal, col, atributo.name, header_left_bloqueado)
            # Guardo la columna asociada a cada atributo
            attr_col_dict[atributo.name] = col
            col += 1

        # Escribo filas
        col = 0
        for unidad in self.unidad_ids.sorted(key=lambda x: x.path):
            if not unidad.is_root:
                # Escribo las partes del path (quito la ES para que no salga en el excel)
                partes = map(unicode.strip, unidad.path.split(SEPARADOR_PATH))

                # Quito el nombre de la ES para que no salga en el excel
                partes.pop(0)

                # Escribo las partes del path
                for parte in partes:
                    ws.write(fila, col, parte, texto_editable)
                    col += 1

                # Escribo Población Atendida
                ws.write(fila, col_poblacion_atendida, unidad.poblacion_atendida, integer_editable)

                # Escribo los valores de los atributos (si hay) en las columnas correspondientes
                vals = unidad.get_valores_atributos(para_export=True)
                for nombre_attr, valor_attr in vals.iteritems():
                    ws.write(fila, attr_col_dict[nombre_attr], str(valor_attr), integer_editable)

                # Incremento la fila y cereo columna
                fila += 1
                col = 0

        # Codifico a base 64
        data_to_save = get_encoded_wb(wb)

        # Creo el Wizard de Descarga con el archivo
        file_name = 'Export_ES_' + str(self.codigo) + '.xls'
        wiz_id = self.env['grp.pep.export.estructura'].create({'archivo_nombre': file_name,
                                                               'archivo_contenido': data_to_save})
        return {
            'name': "Exportar Estructura de Servicios",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.export.estructura',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    @api.multi
    def importar_estructura(self):
        self.ensure_one()

        if self.state == self.UTILIZADA:
            raise ValidationError(u"No se permite modificar una Estructura en estado '%s'" % self.UTILIZADA)

        wiz_id = self.env['grp.pep.import.estructura'].create({'estructura_id': self.id,
                                                               'archivo_nombre': '',
                                                               'archivo_contenido': None,
                                                               'mensajes': ''})
        return {
            'name': "Importar Estructura de Servicios",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.import.estructura',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'views': [(False, 'form')],
            'context': self.env.context,
            'target': 'new',
        }

    @api.multi
    def existe_path(self, path, incluir_inactivos=False):
        """
            Retorna True si existe el path en la estructura. La busqueda se realiza
            sobre las unidades activas a menos que se envíe el parametro incluir_inactivos en True
        """
        # Busco si existe el path en la ES (el path es unique)
        sql = """SELECT count(id) FROM %s WHERE path=\'%s\'""" % ('grp_pep_unidad_de_servicio', path)
        if not incluir_inactivos:
            sql += """ AND active=TRUE"""
        self.env.cr.execute(sql)
        res = self.env.cr.fetchall()
        return bool(res[0][0])

    def _obtener_unidad_por_path(self, path, incluir_inactivos=False):
        """
            Obtiene una unidad a partir del path, retorna Falso si no existe.
        """
        # Busco si existe el path en la ES (el path es unique)
        sql = """SELECT id FROM %s WHERE path=\'%s\'""" % ('grp_pep_unidad_de_servicio', path)
        if not incluir_inactivos:
            sql += """ AND active=TRUE"""
        self.env.cr.execute(sql)
        res = self.env.cr.fetchall()
        try:
            unidad_id = self.env['grp.pep.unidad.de.servicio'].browse(res[0][0])
        except:
            unidad_id = False

        return unidad_id

    def _path_obtener_parte_existente_y_a_crear(self, path):
        """
            Obtiene la parte existente de un path y la que hay que crear.
            Se asume que la unidad raiz existe, si no se encuentra es porque el
            nombre viene mal de la planilla.
        """
        partes_a_crear = map(unicode.strip, path.split(SEPARADOR_PATH))
        partes_existentes = list()

        path_aux = partes_a_crear[0]
        # Pruebo el nodo raiz, si no está es error
        if self._obtener_unidad_por_path(path_aux):
            partes_existentes.append(partes_a_crear.pop(0))

            # Si existe el nodo raíz verifico el resto del path, si hay
            while partes_a_crear:
                path_aux += SEPARADOR_PATH + partes_a_crear[0]
                if self._obtener_unidad_por_path(path_aux):
                    partes_existentes.append(partes_a_crear.pop(0))
                else:
                    break
            return SEPARADOR_PATH.join(partes_existentes), SEPARADOR_PATH.join(partes_a_crear)
        else:
            raise ValidationError(u"El nombre de la unidad raíz es incorrecto")

    def _crear_path(self, parte_existente, parte_a_crear):
        """
            Función recurrente, crea todas las unidades hasta completar el path
            y retorna la ultima unidad creada.
        """
        assert parte_a_crear, "_crear_path debe ser llamado con una parte a crear"

        parte_a_crear_list = map(unicode.strip, parte_a_crear.split(SEPARADOR_PATH))
        unidad_nombre = parte_a_crear_list.pop(0)

        parent_id = self._obtener_unidad_por_path(parte_existente)
        unidad_id = self.env['grp.pep.unidad.de.servicio'].create({'estructura_id': self.id,
                                                                   'name': unidad_nombre,
                                                                   'parent_id': parent_id.id})

        parte_existente += SEPARADOR_PATH + unidad_nombre
        parte_a_crear = SEPARADOR_PATH.join(parte_a_crear_list)

        if parte_a_crear:
            return self._crear_path(parte_existente, parte_a_crear)

        return unidad_id

    @api.multi
    def obtener_crear_unidad(self, path, acumular_repetidos=False):
        """
            Crea una unidad a partir del path, si ya existe lanza error o acumula
            según lo que indique el parametro acumular_repetidos.
        """
        self.ensure_one()

        if path:
            if path != self.root_node.path:
                # Obtengo la parte 'existente' y 'a crear' del path
                parte_existente, parte_a_crear = self._path_obtener_parte_existente_y_a_crear(path=path)

                if parte_existente == path:
                    if not acumular_repetidos:
                        raise ValidationError(u"Se encontró una ubicación repetida en los datos ( %s )" % path)
                    else:
                        # Retorno la unidad existente
                        unidad_id = self._obtener_unidad_por_path(path=path)
                else:
                    # Sinó, mando crear el path y me traigo la unidad resultante
                    unidad_id = self._crear_path(parte_existente, parte_a_crear)

                return unidad_id
            else:
                # Se intenta crear el nodo root
                raise ValidationError(u"No pueden existir filas con ubicación vacía en el excel!")
        else:
            raise ValidationError(u"Se intentó crear una unidad con ubicación vacía!")

    @api.multi
    @api.depends('name', 'codigo')
    def _compute_display_name(self):
        for rec in self:
            if rec.name and rec.codigo:
                rec.display_name = rec.name + ' - ' + rec.codigo

    def _validar_niveles(self):
        """
            Valida que los niveles estén bien definidos respecto a lo que se declara en la ES
            y que no excedan el maximo permitido por la receta.
        """
        max_depth = self.maxima_profundidad

        sample_list = range(1, max_depth + 1)
        current_list = [x.numero for x in self.nivel_ids]
        if not sample_list == current_list:
            raise ValidationError(u"La cantidad de niveles indicada no coincide con la cantidad"
                                  u" de niveles definidos o la ubicación de algún nivel no es correcta")

        max_niveles_receta = self.env['grp.pep.receta'].MAXIMA_PROFUNDIDAD
        if max_depth > max_niveles_receta or len(self.nivel_ids) > max_niveles_receta:
            raise ValidationError(u"Actualmente no se permite definir más de %s niveles en una estructura." % max_niveles_receta)

    @api.multi
    def _compute_state(self):
        """
            - Si no se encuentra en ningun plan, se considera 'borrador'
            - Si se encuentra solo en planes borrador, se considera 'abierta'.
            - Si se encuentra en al menos un plan con estado > borrador, se considera 'utilizada'
        """
        plan_obj = self.env['grp.pep.anual']
        for rec in self:
            plan_ids = plan_obj.search([('estructura_de_servicios_id', '=', rec.id)])
            estados_planes = set([p.state for p in plan_ids])

            if len(plan_ids)==0:
                rec.state = self.BORRADOR
            elif estados_planes == {plan_obj.BORRADOR}:
                rec.state = self.ABIERTA
            else:
                rec.state = self.UTILIZADA

    @api.model
    def create(self, values):
        # Calculo secuencia
        codigo = self.env['ir.sequence'].next_by_code('grp.pep.estructura.code')
        values['codigo'] = codigo

        # Creo Estructura
        estructura = super(grp_pep_estructura, self).create(values)

        # Si no estoy duplicando aplico validaciones sobre niveles
        if not self.env.context.get(ES_COPIA, False):
            if not estructura.nivel_ids:
                raise ValidationError(u"Es obligatorio ingresar los niveles.")

            self._validar_niveles()

        # Creo el root_node para la estructura
        root_node = self.env['grp.pep.unidad.de.servicio'].create({
            'estructura_id': estructura.id,
            'name': 'ES-' + str(codigo),
            'nivel_id': None,
            'parent_id': None,
            'path': 'ES-' + str(codigo),
            'is_root': True
        })

        estructura.write({'root_node': root_node.id})

        return estructura

    @api.one
    def copy(self, default=None):
        # Copio estructura, Agrego el valor ES_COPIA al contexto para evitar algunos controles en el caso de copia
        nueva_estructura = super(grp_pep_estructura, self.with_context({ES_COPIA: True})).copy(default)
        nueva_estructura.write({'name': nueva_estructura.name + u' (Copia)'})

        # Copio los Niveles
        nuevos_niveles = self.nivel_ids.copy({'estructura_id': nueva_estructura.id})

        # Copio los Atributos
        nuevos_atributos = self.atributo_ids.copy({'estructura_id': nueva_estructura.id})

        # Creo mapeo de atributos viejos a nuevos
        attr_viejo_nuevo = {}
        for attr_v in self.atributo_ids:
            for attr_n in nuevos_atributos:
                if attr_n.name == attr_v.name:
                    attr_viejo_nuevo[attr_v.id] = attr_n.id

        # Llamo al copiar_hijos del root_node, eso copia todas las unidades en cascada
        self.root_node.copiar_hijos(defaults={'estructura_id': nueva_estructura.id,
                                    'parent_id': nueva_estructura.root_node.id},
                                    attr_viejo_nuevo=attr_viejo_nuevo)

        return nueva_estructura

    @api.multi
    def write(self, values):
        super(grp_pep_estructura, self).write(values)
        for rec in self:
            # Si no estoy duplicando aplico validaciones sobre niveles
            if not self.env.context.get(ES_COPIA, False):
                rec._validar_niveles()

            rec.root_node.active = rec.active
        return True

    @api.multi
    def get_primer_nivel(self):
        self.ensure_one()

        primer_nivel = self.nivel_ids.filtered(lambda r: r.numero == 1)
        return primer_nivel[0]

    @api.multi
    def unlink(self):
        # Borro el nodo raíz (el resto se borra en cascada)
        recs = self.with_context({CTX_BORRAR_ROOT: True})
        for rec in recs:
            if rec.state != self.BORRADOR:
                raise ValidationError(u"Solo se puede eliminar una estructura en estado borrador.")
            rec.root_node.unlink()
            super(grp_pep_estructura, rec).unlink()

    _sql_constraints = [
        ('field_unique', 'unique(codigo)', u'Ya existe una Estructura con ese Código')
    ]

grp_pep_estructura()


TIPO_INT = 'integer'
TIPO_FLOAT = 'float'
TIPO_BOOLEAN = 'boolean'
TIPO_STRING = 'string'
TIPOS_DE_ATRIBUTOS = [(TIPO_INT, 'Entero'),
                      (TIPO_FLOAT, 'Decimal'),
                      (TIPO_BOOLEAN, 'Booleano'),
                      (TIPO_STRING, 'Texto')]


# EXPORT ESTRUCTURA
class grp_pep_export_estructura(models.TransientModel):
    """ Wizard para descarga de Export de estructura """
    _name = 'grp.pep.export.estructura'
    archivo_nombre = fields.Char(string='Nombre del archivo')
    archivo_contenido = fields.Binary(string="Archivo")

grp_pep_export_estructura()

MSG_INFO = 'info'
MSG_WARN = 'warning'
MSG_ERROR = 'error'
TIPOS_MENSAJE_ERROR = [(MSG_INFO, u'Información'),
                       (MSG_WARN, u'Advertencia'),
                       (MSG_ERROR, u'Error')]


# IMPORT ESTRUCTURA
class grp_pep_import_estructura(models.TransientModel):
    _name = 'grp.pep.import.estructura'

    estructura_id = fields.Many2one(comodel_name='grp.pep.estructura',
                                    string='Estructura')
    archivo_contenido = fields.Binary(string="Archivo")
    archivo_nombre = fields.Char(string="Archivo Nombre")
    hay_errores = fields.Boolean(default=False)
    hay_warnings = fields.Boolean(default=False)
    import_realizado = fields.Boolean(default=False)
    mensajes = fields.One2many(comodel_name='grp.pep.import.estructura.mensajes',
                               string='Mensajes',
                               inverse_name='wiz_id')

    mensajes_list = list()
    error_flag = False
    warning_flag = False

    def _agregar_mensaje(self, msg, fila, fila_nro, es_error=False, es_warning=False):
        fila_m = [x.value for x in fila]
        if es_error:
            self.error_flag = True
            self.mensajes_list.append(
                {'tipo': MSG_ERROR,
                 'mensaje': u"\nERROR: fila %s --> %s. %s" % (fila_nro, fila_m, msg)})
        elif es_warning:
            self.warning_flag = True
            self.mensajes_list.append(
                {'tipo': MSG_WARN,
                 'mensaje': u"\nADVERTENCIA: fila %s --> %s. %s" % (fila_nro, fila_m, msg)})
        else:
            self.mensajes_list.append(
                {'tipo': MSG_INFO,
                 'mensaje': u"\nINFO: fila %s --> %s. %s" % (fila_nro, fila_m, msg)})

    def _validar_codigo(self, sheet):
        """
            Valido que la estructura declarada en el Excel sea la actual (por el codigo)
        """

        codigo = sheet.cell(0, 3).value
        if codigo != self.estructura_id.codigo:
            raise ValidationError(u"La planilla que se desea importar no fué generada para la estructura actual.")

    def _validar_niveles_atributos(self, sheet):
        """
            Valido que los niveles declarados en la planilla coincidan en nombre y orden con los de la estructura
        """
        col = 0
        for nivel in self.estructura_id.nivel_ids.sorted(key=lambda x: x.numero):
            en_excel = sheet.cell(1, col).value
            if nivel.name != en_excel:
                raise ValidationError(u"El nivel %s de la estructura no se encontró en la "
                                      u"columna %s del excel (Contando desde 0)" % (nivel.name, col))
            col += 1

        # Valido nombre Población Atendida
        en_excel = sheet.cell(1, col).value
        if COMUNA_POBLACION_ATENDIDA != en_excel:
            raise ValidationError(u"La columna %s (Contando desde 0) del excel está mal nombrada."
                                  u" Debería llamarse %s." % (col, COMUNA_POBLACION_ATENDIDA))
        col += 1

        # Valido que los atributos declarados en la planilla coincidan con los de la estructura
        for atributo in self.estructura_id.atributo_ids.sorted(key=lambda x: x.name):
            en_excel = sheet.cell(1, col).value
            if atributo.name != en_excel:
                raise ValidationError(u"El atributo %s de la estructura no se encontró en la "
                                      u"columna %s del excel (Contando desde 0)" % (atributo.name, col))
            col += 1

    def _obtener_sheet(self, wb=None):
        """
            Devuelve una WorkBook.Sheet a partir del archivo cargado en el wizard

        """
        wb = open_workbook(file_contents=base64.decodestring(self.archivo_contenido))
        return wb.sheet_by_index(0)

    def _obtener_path_de_fila_excel(self, fila, fila_nro, cant_niveles):
        """
            Calculo el path a partir de la fila del excel, agregandole el nombre del nodo root.
        """
        # Si es un comentario retorno None
        if unicode(fila[0].value).startswith(COMENTARIO):
            return None

        # No es un comentario, trato de obtener el path
        path_parts = [self.estructura_id.root_node.name]

        fin_path, hueco_en_path, col_hueco = False, False, 0
        for col in xrange(0, cant_niveles):
            value = unicode(fila[col].value)

            # Considero fin del path en la primer celda vacía (de izq a der)
            if not value:
                fin_path = True

            # Si no encontré el fin del path, agrego parte al path
            if not fin_path:
                path_parts.append(value)

            # Si encuentro un hueco prendo la flag para emitir el mensaje
            if fin_path and value:
                col_hueco = fila[col]
                hueco_en_path = True

        if hueco_en_path:
            self._agregar_mensaje(msg=u'Se ha encontrado una o mas celdas vacías en la definición de la ubicación, '
                                      u'se ignoró la parte que sigue a la celda vacía.',
                                  fila=fila,
                                  fila_nro=fila_nro,
                                  es_warning=True)

        path = SEPARADOR_PATH.join(path_parts)
        return path

    def _crear_unidad(self, fila, fila_nro, attrs_sorted, cant_niveles, acumular_repetidos=False):
        """
            Crea una unidad a partir del path y los valores de atributos obtenidos desde el excel.
            Se crean todas las unidades intermedias necesarias para que exista el path especificado.
        """
        # Calculo el path a partir de la fila del excel
        path = self._obtener_path_de_fila_excel(fila=fila, fila_nro=fila_nro, cant_niveles=cant_niveles)

        try:
            # Creo o obtengo la unidad a partir del path
            unidad_id = self.estructura_id.obtener_crear_unidad(path, acumular_repetidos=acumular_repetidos)

            # Armo un Diccionario con los nombres de los atributos y sus valores (sacados de la fila excel)
            vals = unidad_id.get_valores_atributos()
            attr_index = 1
            for atributo in attrs_sorted:
                # Calculo la columna del atributo y obtengo el valor de la celda
                col = attr_index + cant_niveles
                cell_value = fila[col].value

                # Si hay valor verifico que sea casteable al tipo del atributo
                if cell_value != u'':
                    value = atributo.cast_value(cell_value)

                    # El valor es correcto, lo agrego al diccionario vals
                    vals[atributo.name] = value

                attr_index += 1

            # Seteo la población atendida
            unidad_id.set_poblacion_atendida(fila[cant_niveles].value, acumular=acumular_repetidos)

            # Seteo los valores de atributos en la unidad
            unidad_id.set_valores_atributos(vals, acumular=acumular_repetidos)

        except ValidationError as e:
            self._agregar_mensaje(msg=e.value, fila=fila, fila_nro=fila_nro, es_error=True)

    def _insertar_filas_en_estructura(self, sheet, acumular_repetidos=False):
        """
            Inserta las filas de Sheet en la tabla de unidades de servicio
        """
        cant_niveles = self.estructura_id.maxima_profundidad
        cant_filas = sheet.nrows
        attrs_sorted = self.estructura_id.atributo_ids.sorted(lambda x: x.name)
        for n_fila in xrange(2, cant_filas):
            fila = sheet.row(n_fila)
            self.with_context({DISABLE_BOTTOM_UP_IN_WRITE: True})._crear_unidad(fila=fila, fila_nro=n_fila,
                                                                                attrs_sorted=attrs_sorted,
                                                                                cant_niveles=cant_niveles,
                                                                                acumular_repetidos=acumular_repetidos)

    def _inicializar_banderas_wizard(self):
        """
            Inicializo estado del wizard y banderas en falso
        """
        self.write({'hay_errores': False,
                    'hay_warnings': False,
                    'import_realizado': False,
                    'mensajes': [(5,)]})
        self.mensajes_list = list()
        self.error_flag = False
        self.warning_flag = False

    @api.multi
    def importar_estructura_excel(self):
        """
            Importa una ES desde un archivo excel desde wizard
        """
        self.ensure_one()

        # Inicializo estado del wizard y banderas en falso
        self._inicializar_banderas_wizard()

        if not self.estructura_id:
            raise ValidationError(u"No se ha encontrado la estructura sobre la cual importar!")

        if self.archivo_contenido:
            # Obtengo la hoja de excel
            sheet = self._obtener_sheet()

            # Valido que la estructura declarada en el Excel sea la actual (por el codigo)
            self._validar_codigo(sheet=sheet)

            # Valido que los niveles declarados en la planilla coincidan en nombre y orden con los de la estructura
            # Lo mismo para los atributos, en orden lexicografico
            self._validar_niveles_atributos(sheet=sheet)

            # Podo el arbol en la raiz
            self.estructura_id.root_node.podar()

            # Inserto las filas del excel en la ES
            self._insertar_filas_en_estructura(sheet)

        # Escribo los mensajes
        self.write({'hay_errores': self.error_flag,
                    'hay_warnings': self.warning_flag,
                    'import_realizado': True,
                    'mensajes': [(0, 0, x) for x in self.mensajes_list]})

        # Si hubo errores borro los nodos que hayan quedado ingresados
        if self.error_flag:
            self.estructura_id.root_node.podar()

        # Disparo un recalculo top-down
        self.estructura_id.root_node.recalcular_poblacion_atendida_top_down()

        self.import_realizado = True
        return {
            'name': "Importar Estructura de Servicios desde Excel",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.import.estructura',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def get_encoded_wb(self, wb):
        # Salvo hacia un string IO
        fp = StringIO()
        wb.save(fp)

        # Guardo la planilla en un string
        fp.seek(0)
        data = fp.read()

        # Codifico a base 64
        data_to_save = base64.encodestring(data)
        return data_to_save

    @api.multi
    def importar_desde_ws(self, name=u"", poblacion_atendida=u"", data=tuple(), niveles=OrderedSet(), atributos=OrderedSet(),
                          niveles_alias=dict(), atributos_alias=dict()):
        """
            Recibe una lista de JSON donde cada uno tiene como claves los strings que
            aparecen en las listas de niveles y atributos. Cada JSON representa una escuela con su ubicación
            y atributos
        """
        self.ensure_one()

        # Inicializo estado del wizard y banderas en falso
        self._inicializar_banderas_wizard()

        # Le creo sus Niveles y Atributos a la ES
        nivel_ids = []
        atributo_ids = []
        for num, niv in enumerate(niveles, start=1):
            nivel_ids.append((0, 0, {'name': niveles_alias[niv],
                                     'numero': num}))
        for attr in atributos:
            atributo_ids.append((0, 0, {'name': atributos_alias[attr]}))

        # Creo una ES sobre la cual importar
        nueva_es = self.env['grp.pep.estructura'].create({'name': name,
                                                          'importada_por_ws': True,
                                                          'nivel_ids': nivel_ids,
                                                          'atributo_ids': atributo_ids
                                                          })

        # La asigno al wizard
        self.estructura_id = nueva_es.id

        # Formo un Workbook excel con el contenido del WS
        wb = self.crear_wb_desde_ws_data(poblacion_atendida=poblacion_atendida, data=data, niveles=niveles,
                                         atributos=atributos)
        # Lo guardo en el campo de archivo
        self.archivo_contenido = get_encoded_wb(wb)

        # Obtengo la hoja de excel
        sheet = self._obtener_sheet(wb=wb)

        # Inserto las filas del excel en la ES
        self._insertar_filas_en_estructura(sheet, acumular_repetidos=True)

        # Escribo los mensajes
        self.write({'hay_errores': self.error_flag,
                    'hay_warnings': self.warning_flag,
                    'import_realizado': True,
                    'mensajes': [(0, 0, x) for x in self.mensajes_list]})

        # Si hubo errores borro los nodos que hayan quedado ingresados
        if self.error_flag:
            self.estructura_id.root_node.podar()

        # Disparo un recalculo top-down
        self.estructura_id.root_node.recalcular_poblacion_atendida_top_down()

        self.import_realizado = True
        return {
            'name': "Importar Estructura de Servicios desde WS",
            'type': 'ir.actions.act_window',
            'res_model': 'grp.pep.import.estructura',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }, nueva_es

    def crear_wb_desde_ws_data(self, poblacion_atendida=u"", data=tuple(), niveles=OrderedSet(), atributos=OrderedSet()):
        """
            Llena un Workbook con los datos recibidos desde el WS que puede ser importado por
            la misma función que importa excel.
        """
        def get_casted_value(valor):
            try:
                val = int(valor)
            except ValueError:
                try:
                    val = float(valor)
                except ValueError:
                    try:
                        val = unicode(valor)
                    except ValueError:
                        raise ValidationError(u"El valor %s no es transformable a un texto." % valor)

            if isinstance(val, float):
                val = int(valor)
            return val

        # Creo el libro Excel
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('Sheet 1', cell_overwrite_ok=True)
        ws.protect = False

        # Escribo filas
        fila = 2
        col = 0

        # Proceso la data del WS, para cada elemento (unidad de servicio del nivel más bajo)
        for elem in data:
            # Inserto niveles
            for nivel_name in niveles:
                val = get_casted_value(elem[nivel_name])

                # Si es un Nivel debe ser un string
                if not isinstance(val, unicode):
                    raise ValidationError(u"La clave seleccionada para cargar el nivel %s tiene asociado un valor que "
                                          u"no es texto en el elemento %s" % (nivel_name, json.dumps(elem)))
                ws.write(fila, col, val)
                col += 1

            # Inserto población atendida, debe ser un entero
            val = get_casted_value(elem[poblacion_atendida])
            if not isinstance(val, int):
                raise ValidationError(u"La clave '%s' seleccionada para cargar la población "
                                      u"atendida desde el WS tiene asociado un valor no numérico "
                                      u"en el elemento %s" % (poblacion_atendida, json.dumps(elem)))
            ws.write(fila, col, val)
            col += 1

            # Inserto atributos, deben ser enteros
            for attr_name in atributos:
                val = get_casted_value(elem[attr_name])
                if not isinstance(val, int):
                    raise ValidationError(u"La clave '%s' seleccionada para cargar el atributo"
                                          u" desde el WS tiene asociado un valor no numérico "
                                          u"en el elemento %s" % (attr_name, json.dumps(elem)))
                ws.write(fila, col, elem[attr_name])
                col += 1

            # Incremento la fila y cereo columna
            fila += 1
            col = 0

        # Salvo hacia un string IO y retorno
        fp = StringIO()
        wb.save(fp)
        return wb

grp_pep_import_estructura()


# MENSAJES DEL IMPORT
class grp_pep_import_estructura_mensaje(models.TransientModel):
    _name = 'grp.pep.import.estructura.mensajes'

    wiz_id = fields.Many2one(comodel_name='grp.pep.import.estructura', ondelete='cascade')
    tipo = fields.Selection(selection=TIPOS_MENSAJE_ERROR, string=u'Tipo')
    mensaje = fields.Char(string=u'Mensaje')

grp_pep_import_estructura_mensaje()


# ATRIBUTOS
class grp_pep_estructura_atributo(models.Model):
    """ Atributos definidos para cada estructura """

    _name = 'grp.pep.estructura.atributo'

    estructura_id = fields.Many2one(comodel_name='grp.pep.estructura',
                                    ondelete='cascade',
                                    copy=False)
    name = fields.Char(string='Nombre')
    tipo = fields.Selection(string='Tipo', selection=TIPOS_DE_ATRIBUTOS, default=TIPO_INT)
    agrega_hijos = fields.Boolean(string='Agrega Hijos',
                                  help="Si un nodo X tiene hijos, el valor de este atributo"
                                       " en X se calcula como la suma de los valores de este "
                                       "atributo en todos los hijos de X.",
                                  default=True)

    is_integer = fields.Boolean(compute='_compute_is_props', store=True)
    is_float = fields.Boolean(compute='_compute_is_props', store=True)
    is_boolean = fields.Boolean(compute='_compute_is_props', store=True)
    is_string = fields.Boolean(compute='_compute_is_props', store=True)

    @api.multi
    @api.depends('tipo')
    def _compute_is_props(self):
        for rec in self:
            rec.is_integer = (rec.tipo == TIPO_INT)
            rec.is_float = (rec.tipo == TIPO_FLOAT)
            rec.is_boolean = (rec.tipo == TIPO_BOOLEAN)
            rec.is_string = (rec.tipo == TIPO_STRING)

    @api.multi
    def valor_vacio(self):
        """
            Retorna el valor vacío del atributo.
        """
        self.ensure_one()

        if self.is_integer:
            return int()
        elif self.is_boolean:
            return False
        elif self.is_float:
            return float()
        elif self.is_string:
            return str()
        else:
            raise ValidationError(u"El atributo no tiene tipo!")

    @api.multi
    def cast_value(self, value):
        """
            Castea el valor del atributo al tipo correcto
        """
        self.ensure_one()
        try:
            if self.is_integer:
                return int(value)
            elif self.is_boolean:
                return bool(value)
            elif self.is_float:
                return float(value)
            else:
                return str(value)
        except:
            raise ValidationError(u"Valor incorrecto (%s) para el tipo %s" % (value, self.tipo))

grp_pep_estructura_atributo()


# NIVELES
class grp_pep_estructura_nivel(models.Model):
    """ Niveles definidos para una estructura """

    _name = 'grp.pep.estructura.nivel'
    _order = 'numero'

    estructura_id = fields.Many2one(comodel_name='grp.pep.estructura',
                                    ondelete='cascade',
                                    copy=False)
    name = fields.Char(string='Nombre')
    numero = fields.Integer(string='Numero')

    @api.multi
    def siguiente_nivel_id(self, return_false_on_final=False):
        self.ensure_one()

        assert self.estructura_id, "El nivel recibido no tiene estructura!"

        max_depth = self.estructura_id.maxima_profundidad
        numero = self.numero
        if numero >= max_depth:
            if return_false_on_final:
                return False
            raise ValidationError(u"Ya se ha alcanzado la maxima profundidad permitida (%s) en la Estructura de Servicios!" % max_depth)
        else:
            # Se asume que se han definido correctamente los niveles, seguro está el siguiente
            sql = """SELECT id FROM %s
             WHERE estructura_id=%s 
             AND numero = %s""" % (self._table, self.estructura_id.id, numero+1)
            self.env.cr.execute(sql)
            res = self.env.cr.fetchall()

        return res[0][0]

    @api.multi
    def siguiente_nivel(self, return_false_on_final=False):
        self.ensure_one()
        n_id = self.siguiente_nivel_id(return_false_on_final=return_false_on_final)

        if n_id:
            return self.browse(n_id)
        else:
            return False

    _sql_constraints = [
        ('estructura_numero_uniq', 'unique(estructura_id, numero)', 'No se puede repetir el número de los niveles'),
    ]

grp_pep_estructura_nivel()


# UNIDADES
class grp_pep_unidad_de_servicio(models.Model):
    """ Unidades de Servicio, son los nodos del arbol de la estructura"""

    _name = 'grp.pep.unidad.de.servicio'
    _order = 'path'

    estructura_id = fields.Many2one(comodel_name='grp.pep.estructura',
                                    string=u'Estructura de Servicios',
                                    ondelete='restrict',
                                    copy=False)
    name = fields.Char(string=u"Nombre", size=20)
    nivel_id = fields.Many2one(comodel_name='grp.pep.estructura.nivel',
                               string=u'Nivel',
                               ondelete='restrict',
                               copy=False)
    nivel_nro = fields.Integer(related="nivel_id.numero", string=u"Nivel Nro", store=True)
    parent_id = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio',
                                string=u'Padre',
                                ondelete='cascade',
                                copy=False)
    child_ids = fields.One2many(comodel_name='grp.pep.unidad.de.servicio', inverse_name='parent_id', string=u'Hijos')
    atributos_valor_ids = fields.One2many(comodel_name='grp.pep.unidad.atributo.valor',
                                          inverse_name='unidad_id')
    atributos_valor_str = fields.Char(string=u'Valores de Atributos', compute='_compute_atributos_valor_str')
    poblacion_atendida = fields.Integer(string=u'Población Atendida')
    path = fields.Char(string=u"Ubicación en la Estructura",
                       copy=False)
    is_root = fields.Boolean(string=u"Es Raíz", default=False)
    in_bottom_level = fields.Boolean(string=u"En último nivel", compute='_compute_in_bottom_level')
    active = fields.Boolean(string=u"Activo", default=True)

    @api.multi
    def set_poblacion_atendida(self, valor, acumular=False):
        """
            Setea la población atendida verificando que el valor obtenido
            sea casteable a integer. Si recibe el flag acumular, el valor
            recibido se suma a lo que ya hay.
        """
        self.ensure_one()
        try:
            v = int(valor)
        except:
            raise ValidationError(u"El valor obtenido de la planilla para la columna %s "
                                  u"es incorrecto." % COMUNA_POBLACION_ATENDIDA)
        if acumular:
            self.poblacion_atendida += v
        else:
            self.poblacion_atendida = v

    @api.multi
    def _compute_atributos_valor_str(self):
        for rec in self:
            valores = rec.get_valores_atributos()
            res = u""
            # Armo string con  los nombres y valores de los atributos
            for nombre, valor in valores.iteritems():
                res += u', ' + unicode(nombre) + u': '+unicode(valor)

            # Si hay valores, quito la coma y espacio inicial
            if res:
                res = res[2:]
            rec.atributos_valor_str = res

    @api.multi
    def _compute_in_bottom_level(self):
        for rec in self:
            rec.in_bottom_level = (rec.nivel_id.numero == rec.estructura_id.maxima_profundidad)

    @api.multi
    def podar(self):
        """
            Borra todos los hijos del nodo actual en cascada
        """
        self.child_ids.unlink()

    @api.multi
    def cantidades_por_nivel_subarbol(self, res):
        """
            Recursiva. Carga res<defaultdict> con nivel_id: cant_nodos de ese nivel
        """
        self.ensure_one()

        res[self.nivel_id.id] += 1
        for hijo in self.child_ids:
            hijo.cantidades_por_nivel_subarbol(res)

    def recalcular_poblacion_atendida_bottom_up(self):
        """
            Re-calcula su poblacion atendida y dispara el re-calculo de la
            población atendida en su nodo padre.
        """
        assert self.env.context.get(DISABLE_BOTTOM_UP_IN_WRITE, False),\
            "Llamar a recalcular población bottom-up sin setear la flag DISABLE_BOTTOM_UP_IN_WRITE no está permitido."

        # Si hay hijos se calcula como la suma de ellos, sinó el valor ya está
        # en el registro y no hay que hacer nada.
        if len(self.child_ids) > 0:
            poblacion_atendida = 0
            valores_atributos = defaultdict(int)
            for hijo in self.child_ids:
                poblacion_atendida += hijo.poblacion_atendida
                valores = hijo.get_valores_atributos()

                # Acumulo valores de atributos
                for k, v in valores.iteritems():
                    valores_atributos[k] += v

            # Escribo poblacion_atendida usando super para no meterme con el write mio que es complejo
            super(grp_pep_unidad_de_servicio, self).write({'poblacion_atendida': poblacion_atendida})
            self.set_valores_atributos(valores_atributos)

        if self.parent_id:
            self.parent_id.recalcular_poblacion_atendida_bottom_up()

    def recalcular_poblacion_atendida_top_down(self):
        """
            Dispara un re-calculo de las poblaciones atendidas en todos por debajo del actual.
        """
        # Si es hoja y no es root, retorno el valor directamente
        if len(self.child_ids) == 0 and not self.is_root:
            return self.poblacion_atendida, self.get_valores_atributos()

        # Tiene hijos
        poblacion_atendida = 0
        valores_atributos = defaultdict(int)
        for hijo in self.child_ids:
            poblacion, valores = hijo.recalcular_poblacion_atendida_top_down()

            # Acumulo poblacion
            poblacion_atendida += poblacion

            # Acumulo valores de atributos
            for k, v in valores.iteritems():
                valores_atributos[k] += v

        # Escribo poblacion_atendida usando super para no meterme con el write mio que es complejo
        super(grp_pep_unidad_de_servicio, self).write({'poblacion_atendida': poblacion_atendida})
        self.set_valores_atributos(valores_atributos)

        return poblacion_atendida, valores_atributos


    @api.multi
    def get_valor_atributo(self, nombre):
        """
            Obtiene el valor de un atributo
        """
        self.ensure_one()

        # Busco en los valores, si existe lo retorno
        for attr_val in self.atributos_valor_ids:
            if attr_val.atributo_id.name == nombre:
                return attr_val.get_valor()

        # Si no existe retorno el valor vacio en la estructura
        for attr in self.estructura_id.atributo_ids:
            if attr.name == nombre:
                return attr.valor_vacio()

        raise ValidationError(u"Nombre de atributo %s no conocido por la estructura %s." % (nombre, self.estructura_id.codigo))

    @api.multi
    def set_valores_atributos(self, vals, acumular=False):
        """
            Setea los valores de vals en los atributos correspondientes borrando
            los valores actuales antes de setear los nuevos.
        """
        self.ensure_one()
        atributo_valor_obj = self.env['grp.pep.unidad.atributo.valor']

        # Obtengo un dict que mapea nombre de atributo con su id
        attr_name_id = {x.name: x.id for x in self.estructura_id.atributo_ids}

        # En caso de no acumular o no haber valores de atributos en la unidad
        if not acumular or not self.atributos_valor_ids:
            # Borrar los valores que hay (puede no haber ninguno)
            self.atributos_valor_ids.unlink()

            # Creo nuevas filas de valores, una por cada nombre de atributo en vals
            for attr_name, attr_val in vals.iteritems():
                nuevo_valor = atributo_valor_obj.create({'atributo_id': attr_name_id[attr_name],
                                                         'unidad_id': self.id})
                nuevo_valor.set_valor(vals[attr_name])
        else:
            # Recorro solo los valores de atributos para los que recibí actualizaciones en vals
            for attr_val in self.atributos_valor_ids.filtered(lambda av: av.atributo_id.name in vals.keys()):
                attr_name = attr_val.atributo_id.name
                attr_val.set_valor(vals[attr_name], acumular=acumular)

    @api.multi
    def get_valores_atributos(self, para_export=False):
        """
            Retorna un diccionario con nombres y valores de los atributos.
            para_export=True devuelve u'' en los valores vacios para poder
            insertar en el excel y que quede la celda vacía en lugar de 0 o 0.00
        """
        self.ensure_one()

        # Creo un diccionario con todos los nombres de los atributos y sus valores vacios
        if para_export:
            res = {attr.name: u'' for attr in self.estructura_id.atributo_ids}
        else:
            res = {attr.name: attr.valor_vacio() for attr in self.estructura_id.atributo_ids}

        # Obtengo los valores no vacíos que haya
        vals = {attr_val.atributo_id.name: attr_val.get_valor() for attr_val in self.atributos_valor_ids}

        # Actualizo res con esos valores
        res.update(vals)

        return res

    @api.onchange('estructura_id')
    def onchange_estructura_id(self):
        res = {}
        self.parent_id = False
        if self.estructura_id:
            ids = self.estructura_id.unidad_ids.ids
            res['domain'] = {'parent_id': [('id', 'in', ids)]}
        return res

    @api.model
    def create(self, values):
        # Si es Root no puede tener padre ni nivel
        if 'is_root' in values and values['is_root']:
            values['parent_id'] = None
            values['nivel_id'] = None

        # Si hay padre (no estoy creando un ROOT)
        if 'parent_id' in values and values['parent_id']:
            padre = self.browse(values['parent_id'])

            # Obtengo el nivel del padre
            if not padre.nivel_id:
                # Padre es ROOT, pregunto a la estructura su primer nivel
                values['nivel_id'] = padre.estructura_id.get_primer_nivel().id
            else:
                # Padre no es ROOT, tiene su nivel, guardo el nivel que le sigue al del nodo padre
                values['nivel_id'] = padre.nivel_id.siguiente_nivel_id()

            # Si pusieron el separador en el nombre lo quito
            values['name'] = values['name'].replace(SEPARADOR_PATH.strip(), '')

            # Armo el path del nodo actual
            values['path'] = padre.path + SEPARADOR_PATH + values['name']

            # Se hereda la condición de activo del padre
            values['active'] = padre.active

        unidad_id = super(grp_pep_unidad_de_servicio, self).create(values)
        
        # Si estoy creando un nodo del ultimo nivel, disparo el calculo bottom-up
        if unidad_id.in_bottom_level and not self.env.context.get(DISABLE_BOTTOM_UP_IN_WRITE, False):
            # Des-habilito el disparo desde el write para evitar loop infinito
            unidad_id.with_context({DISABLE_BOTTOM_UP_IN_WRITE: True}).recalcular_poblacion_atendida_bottom_up()
            
        return unidad_id

    @api.multi
    def write(self, values):
        # Si pusieron el separador en el nombre lo quito, al igual que el comentario
        if 'name' in values:
            values['name'] = values['name'].replace(SEPARADOR_PATH.strip(), '').replace(COMENTARIO, '')

        super(grp_pep_unidad_de_servicio, self).write(values)
        for rec in self:
            # Armo la condicion de busqueda de hijos para actualizaciónen cascada
            # Siempre se buscan los activos y los inactivos
            condicion_hijos_cascada = [('parent_id', '=', rec.id), '|', ('active', '=', rec.active), ('active', '=', not rec.active)]

            # Si es root, No puede tener padre ni nivel
            if rec.is_root:
                super(grp_pep_unidad_de_servicio, rec).write({'parent_id': None,
                                                              'nivel_id': None})
                # Disparo la cascada por si se cambió la condición de activo
                child_ids = self.search(condicion_hijos_cascada)
                child_ids.write({})
            else:
                # Si hay padre (no estoy creando un ROOT)
                if rec.parent_id:
                    padre = rec.parent_id

                    if not padre.nivel_id:
                        # Padre es ROOT, pregunto primer nivel a la estructura
                        nivel_id = padre.estructura_id.get_primer_nivel().id
                    else:
                        # Padre no es ROOT, tiene su nivel, le pregunto el siguiente
                        nivel_id = padre.nivel_id.siguiente_nivel_id()

                    # Los siguientes valores se actualizan en CASCADA para todos los hijos
                    # En el caso del 'active' e utiliza el valor que venga (cuando se activa o desactiva
                    # un nodo intermedio) y si no viene se utiliza la del padre (cuando se desea propagar la cascada)
                    super(grp_pep_unidad_de_servicio, rec).write({'nivel_id': nivel_id,
                                                                  'path': padre.path + SEPARADOR_PATH + rec.name,
                                                                  'active': padre.active if 'active' not in values else values['active']})
                    # Disparo la cascada
                    child_ids = self.search(condicion_hijos_cascada)
                    child_ids.write({})

                    # Si hubo cambios en 'poblacion_atendida', 'atributos_valor_ids' o 'active' debo recalcular
                    if 'poblacion_atendida' in values or 'atributos_valor_ids' in values or 'active' in values:
                        if not self.env.context.get(DISABLE_BOTTOM_UP_IN_WRITE, False):
                            # Des-habilito el disparo desde el write para evitar loop infinito
                            self.with_context({DISABLE_BOTTOM_UP_IN_WRITE: True}).recalcular_poblacion_atendida_bottom_up()
        return True

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.estructura_id.state != rec.estructura_id.BORRADOR:
                raise ValidationError(u"Solo se puede eliminar nodos de una estructura en borrador.")
            if rec.is_root and not self.env.context.get(CTX_BORRAR_ROOT, False):
                raise ValidationError(u"No se puede eliminar directamente el nodo raíz, "
                                      u"este se borra junto con la Estructura de Servicios a la que pertenece.")
            super(grp_pep_unidad_de_servicio, rec).unlink()

    @api.multi
    def copiar_hijos(self, defaults={}, attr_viejo_nuevo={}):
        self.ensure_one()

        for hijo in self.child_ids:
            # Copio hijo con la misma ES y parent_id
            nuevo_hijo = hijo.copy(defaults)

            # Copio los valores de los atributos hacia el nuevo hijo
            for valor in hijo.atributos_valor_ids:
                nuevo_valor = valor.copy({'unidad_id': nuevo_hijo.id,
                                          'atributo_id': attr_viejo_nuevo[valor.atributo_id.id]})

            # Copio el defaults antes de la llamada recursiva para no modificarlo
            # para la siguiente iteración del for
            defaults2 = copy.copy(defaults)
            defaults2.update({'parent_id': nuevo_hijo.id})
            hijo.copiar_hijos(defaults=defaults2, attr_viejo_nuevo=attr_viejo_nuevo)

    _sql_constraints = [
        ('path_uniq', 'unique(path)', 'No se puede repetir la Ubicación en la Estructura'),
    ]

grp_pep_unidad_de_servicio()


# VALOR ATRIBUTO
class grp_pep_unidad_atributo_valor(models.Model):
    _name = 'grp.pep.unidad.atributo.valor'

    unidad_id = fields.Many2one(comodel_name='grp.pep.unidad.de.servicio',
                                string='Unidad de Servicio',
                                ondelete='cascade',
                                copy=False)
    atributo_id = fields.Many2one(comodel_name='grp.pep.estructura.atributo',
                                  string='Atributo',
                                  copy=False)

    valor_integer = fields.Integer(string='Valor')
    valor_float = fields.Float(string='Valor')
    valor_boolean = fields.Boolean(string='Valor')
    valor_string = fields.Char(string='Valor')

    def get_valor(self):
        if self.atributo_id.is_integer:
            return self.valor_integer
        elif self.atributo_id.is_float:
            return self.valor_float
        elif self.atributo_id.is_boolean:
            return self.valor_boolean
        elif self.atributo_id.is_string:
            return self.valor_string
        else:
            raise ValidationError(u"No se reconoce el tipo del atributo %s" % self.atributo_id.name)

    def set_valor(self, valor, acumular=False):
        """
            Escribe el valor segun el tipo del atributo, cereando el resto de los valores de otros tipos.
            Acumula en caso de que acumular sea True para valores int y float.
        """
        values = {
            'valor_integer': 0,
            'valor_float': 0.0,
            'valor_boolean': False,
            'valor_string': ''
        }
        if self.atributo_id.is_integer:
            if not acumular:
                values['valor_integer'] = int(valor)
            else:
                values['valor_integer'] = self.valor_integer + int(valor)
        elif self.atributo_id.is_float:
            if not acumular:
                values['valor_float'] = float(valor)
            else:
                values['valor_float'] = self.valor_float + float(valor)
        elif self.atributo_id.is_boolean:
            values['valor_boolean'] = bool(valor)
        elif self.atributo_id.is_string:
            values['valor_string'] = str(valor)
        else:
            raise ValidationError(u"No se reconoce el tipo del atributo %s" % self.atributo_id.name)

        self.write(values)

    _sql_constraints = [
        ('unidad_atributo_uniq', 'unique(unidad_id, atributo_id)',
         'Solo se puede ingresar un valor por atributo en cada unidad.'),
    ]

grp_pep_unidad_atributo_valor()


# -------------------------------------------#
# WIZARDS PARA IMPORTAR ESTRUCTURA DESDED WS #
# -------------------------------------------#

# WIZARD ESTRUCTURA DESDE WS
class grp_pep_es_desde_ws(models.Model):
    """ Wizard para creación de Estructura dede WS """

    _name = 'grp.pep.es.desde.ws'

    SELECTION_NIVELES = []
    SELECTION_ATRIBUTOS = []

    # Estados Estructura de Servicios
    ES_INICIO = 'inicio'
    ES_DEFINICION = 'definicion'
    ES_IMPORTACION = 'importacion'

    estados = [(ES_INICIO, 'Inicio'),
               (ES_DEFINICION, 'Definición'),
               (ES_IMPORTACION, 'Importación')]

    name = fields.Char(string=u"Nombre")
    state = fields.Selection(string=u'Estado',
                             selection=estados,
                             default=ES_INICIO)
    poblacion_atendida = fields.Selection(selection='get_selection_atributos',
                                          string=u"Población atendida en WS",
                                          help=u"Seleccione cual atributo de los que envía el WS representa"
                                               u" la población atendida")
    es_creada = fields.Many2one(comodel_name='grp.pep.estructura', string=u"Estructura Creada")
    nivel_ids = fields.One2many(comodel_name='grp.pep.es.niveles.desde.ws',
                                inverse_name='wiz_desde_ws_id',
                                string=u'Niveles')
    atributo_ids = fields.One2many(comodel_name='grp.pep.es.atributo.desde.ws',
                                   inverse_name='wiz_desde_ws_id',
                                   string=u'Atributos')

    def load_niveles_y_atributos_desde_ws(self):
        """
            Obtiene los niveles y atributos presentados por el WS, arma los selections y los
            guarda en la instancia de la clase.
        """
        ws_url = self.env['ir.config_parameter'].get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_1')
        res_json = {}
        if ws_url:
            # Consumo el WS
            try:
                urllib2 = get_urllib2_with_proxy_handler(self)
                res = urllib2.urlopen(ws_url)

                if res.code == 200:
                    res_str = res.read()
                    res_json = json.loads(res_str)
            except Exception as e:
                _logger.error('FALLO LA CONEXION AL WS DEL CEIP: '+str(e))

            if res_json:
                # Obtengo Niveles
                if 'niveles' in res_json:
                    self.SELECTION_NIVELES = [(x, x) for x in res_json['niveles']]
                else:
                    ValidationError(u"El WS respondió correctamente pero no se encontró la llave 'niveles' "
                                    u"en la respuesta, esto implica que el JSON retornado por el WS no cumple"
                                    u" con el formato requerido.")
                # Obtengo Atributos
                if 'atributos' in res_json:
                    self.SELECTION_ATRIBUTOS = [(x, x) for x in res_json['atributos']]
                else:
                    ValidationError(u"El WS respondió correctamente pero no se encontró la llave 'atributos' "
                                    u"en la respuesta, esto implica que el JSON retornado por el WS no cumple"
                                    u" con el formato requerido.")

    @api.model
    def get_selection_atributos(self):
        """ Retorna el selection de atributos y lo obtiene si no está """
        if not self.SELECTION_ATRIBUTOS:
            self.load_niveles_y_atributos_desde_ws()
        return self.SELECTION_ATRIBUTOS

    @api.model
    def get_selection_atributos_sin_poblacion_atendida(self):
        """
            Retorna el selection de atributos sin el que representa la población atendida
            y lo obtiene si no está
        """

        if not self.SELECTION_ATRIBUTOS:
            self.load_niveles_y_atributos_desde_ws()

        # Como es un api model tengo que hacer esto para traer la instancia
        # de wizard a partir del id que puse en el contexto desde la vista
        wiz_id = self.env.context.get('default_wiz_desde_ws_id', False)
        if wiz_id:
            wiz = self.browse(wiz_id)
            pob_atend = wiz.poblacion_atendida
            sel_atributos = filter(lambda x: x != (pob_atend, pob_atend), self.SELECTION_ATRIBUTOS)
            return sel_atributos

        return self.SELECTION_ATRIBUTOS

    @api.model
    def get_selection_niveles(self):
        """ Retorna el selection de niveles y lo obtiene si no está """
        if not self.SELECTION_NIVELES:
            self.load_niveles_y_atributos_desde_ws()
        return self.SELECTION_NIVELES

    @api.multi
    def inicio_a_definicion(self):
        self.ensure_one()

        # Borro niveles y atributos relacionados por las dudas
        self.nivel_ids.unlink()
        self.atributo_ids.unlink()

        # Verificao que existan las Configuraciones Generales necesarias
        ws_url_1 = self.env['ir.config_parameter'].get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_1')
        ws_url_2 = self.env['ir.config_parameter'].get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_2')
        if not ws_url_1 or not ws_url_2:
            raise ValidationError(u"Es necesario configurar las URLs de los WS de info y datos en Configuraciones "
                                  u"Generales: Plan de Ejecución presupuestal.")

        self.state = self.ES_DEFINICION

    def get_data_desde_ws(self):
        ws_url = self.env['ir.config_parameter'].get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_2')
        res_json = []
        if ws_url:
            # Consumo el WS
            try:
                urllib2 = get_urllib2_with_proxy_handler(self)
                res = urllib2.urlopen(ws_url)

                if res.code == 200:
                    res_str = res.read()
                    res_json = json.loads(res_str)

                    return res_json
            except Exception as e:
                _logger.error('FALLO LA CONEXION AL WS DE CEIP: '+str(e))
        return res_json

    @api.multi
    def definicion_a_importacion(self):
        self.ensure_one()

        # Obtengo datos de Unidades de servicio desde WS
        data = self.get_data_desde_ws()

        # Obtengo lista de niveles y atributos
        niveles = OrderedSet([x.name for x in self.nivel_ids.sorted(key=lambda r: r.numero)])
        atributos = OrderedSet([x.name for x in self.atributo_ids.sorted(key=lambda r: r.name)])
        niveles_alias = {x.name: x.alias for x in self.nivel_ids}
        atributos_alias = {x.name: x.alias for x in self.atributo_ids}

        # Creo ES desde los datos obtenidos
        wiz_id = self.env['grp.pep.import.estructura'].create({'archivo_nombre': '',
                                                               'mensajes': ''})
        action, nueva_es = wiz_id.importar_desde_ws(name=self.name,
                                                    poblacion_atendida=self.poblacion_atendida,
                                                    data=data,
                                                    niveles=niveles,
                                                    atributos=atributos,
                                                    niveles_alias=niveles_alias,
                                                    atributos_alias=atributos_alias)
        if wiz_id.hay_errores:
            # Si hubo errores borro la estructura creada
            nueva_es.unlink()
            self.write({'state': self.ES_IMPORTACION})
        else:
            self.write({'state': self.ES_IMPORTACION,
                        'es_creada': nueva_es.id})

        # Agrego la marca para ocultar los carteles del import excel del wizard
        if 'context' in action:
            action['context'].update({'desde_ws': True})
        else:
            action['context'] = {'desde_ws': True}

        return action

    def _validar_niveles(self):
        """
            Valida que los niveles estén bien definidos (en orden secuencial)
            y que no excedan el maximo permitido por la receta.
        """
        max_depth = len(self.nivel_ids)

        sample_list = range(1, max_depth + 1)
        current_list = list()
        name_set = set()
        alias_set = set()
        for nivel in self.nivel_ids:
            current_list.append(int(nivel.numero))
            name_set.add(nivel.name)
            alias_set.add(nivel.alias)

        if len(name_set) != max_depth:
            raise ValidationError(u"No pueden haber nombres de niveles repetidos.")

        if len(alias_set) != max_depth:
            raise ValidationError(u"No pueden haber alias de niveles repetidos.")

        if not sample_list == current_list:
            raise ValidationError(u"La ubicación de algún nivel no es correcta")

        max_niveles_receta = self.env['grp.pep.receta'].MAXIMA_PROFUNDIDAD
        if max_depth > max_niveles_receta:
            raise ValidationError(u"Actualmente no se permite definir más de %s niveles en una estructura." % max_niveles_receta)

    def _validar_atributos(self):
        """
            Valida que los atributos nombres y alias de los atributos no se repitan
        """
        cant_attrs = len(self.atributo_ids)

        name_set = set()
        alias_set = set()
        for attr in self.atributo_ids:
            name_set.add(attr.name)
            alias_set.add(attr.alias)

        if len(name_set) != cant_attrs:
            raise ValidationError(u"No pueden haber nombres de atributos repetidos.")

        if len(alias_set) != cant_attrs:
            raise ValidationError(u"No pueden haber alias de atributos repetidos.")

    @api.multi
    def write(self, values):
        super(grp_pep_es_desde_ws, self).write(values)
        for rec in self:
            rec._validar_niveles()
            rec._validar_atributos()
        return True

grp_pep_es_desde_ws()


# WIZARD NIVELES DESDE WS
class grp_pep_es_nivel_desde_ws(models.Model):
    """ Wizard para definir Niveles desde WS """

    _name = 'grp.pep.es.niveles.desde.ws'
    _order = 'numero'

    @api.model
    def _get_selection_niveles(self):
        return self.env['grp.pep.es.desde.ws'].get_selection_niveles()

    @api.model
    def _get_selection_numero(self):
        mp = self.env['grp.pep.receta'].MAXIMA_PROFUNDIDAD
        sel = [(x+1, str(x+1)) for x in range(mp)]
        return sel

    wiz_desde_ws_id = fields.Many2one(comodel_name='grp.pep.es.desde.ws',
                                      ondelete='cascade')
    name = fields.Selection(selection='_get_selection_niveles', string=u'Nombre en WS', help=u"Nombre de nivel enviado por el WS")
    alias = fields.Char(string=u"Alias", help=u"Nombre con el que será creado el nivel en la estructura importada")
    numero = fields.Selection(selection='_get_selection_numero', string=u'Número')

grp_pep_es_nivel_desde_ws()


# WIZARD ATRIBUTOS DESDE WS
class grp_pep_es_atributo_desde_ws(models.Model):
    """ Wizard para definir Atributos desde WS """

    _name = 'grp.pep.es.atributo.desde.ws'

    @api.model
    def _get_selection_atributos(self):
        sel_atributos = self.env['grp.pep.es.desde.ws'].get_selection_atributos_sin_poblacion_atendida()
        return sel_atributos

    wiz_desde_ws_id = fields.Many2one(comodel_name='grp.pep.es.desde.ws',
                                      ondelete='cascade')
    name = fields.Selection(selection='_get_selection_atributos', string=u'Nombre en WS', help=u"Nombre de atributo enviado por el WS")
    alias = fields.Char(string=u"Alias", help=u"Nombre con el que será creado el atributo en la estructura importada.")
    tipo = fields.Selection(string=u'Tipo',
                            selection=TIPOS_DE_ATRIBUTOS,
                            default=TIPO_INT)
    agrega_hijos = fields.Boolean(string=u'Agrega Hijos',
                                  help=u"Si un nodo X tiene hijos, el valor de este atributo"
                                       u" en X se calcula como la suma de los valores de este "
                                       u"atributo en todos los hijos de X.",
                                  default=True)

    is_integer = fields.Boolean(compute='_compute_is_props', store=True)
    is_float = fields.Boolean(compute='_compute_is_props', store=True)
    is_boolean = fields.Boolean(compute='_compute_is_props', store=True)
    is_string = fields.Boolean(compute='_compute_is_props', store=True)

    @api.multi
    def _compute_is_props(self):
        """ Calcula el tipo, devuelve int para todos """
        for rec in self:
            rec.write({'is_integer': True,
                       'is_float': False,
                       'is_boolean': False,
                       'is_string': False})

grp_pep_es_atributo_desde_ws()

