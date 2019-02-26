# -*- encoding: utf-8 -*-

from openerp import models
import base64
from cStringIO import StringIO
from xlwt import Workbook, easyxf
import time


class grp_pep_reporte_plan_adquisiciones(models.AbstractModel):
    _name = 'grp.pep.reporte.plan.adquisiciones'

    def generar_excel(self, wizard):
        plan = self.env['grp.pep.anual'].browse(wizard.plan_anual_id.id)

        # Creo el libro Excel
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('Sheet 1', cell_overwrite_ok=True)

        ws.protect = False
        ws.password = "/Dd3R$eg(&(=:.$"

        # Creo los 'estilos'
        title_left_bloqueado = easyxf('font: name Calibri, bold True; alignment: horizontal center;')
        header_left_bloqueado = easyxf('font: name Calibri, bold True; alignment: horizontal left;'
                                       ' pattern: pattern solid, fore_colour 0x16;')
        texto_resaltado = easyxf('font: name Calibri, bold True; alignment: horizontal left;')
        texto_bloqueado = easyxf('font: name Calibri; alignment: horizontal left;')
        texto_editable = easyxf('font: name Calibri; alignment: horizontal left;'
                                ' protection: cell_locked false;')
        integer_editable = easyxf('font: name Calibri; alignment: horizontal right;'
                                  ' protection: cell_locked false;')
        integer_editable.num_format_str = '#,##0.00'
        fila = 0

        # Escribo el titulo
        ws.write_merge(fila, 0, fila, 17, u"PLAN ANUAL DE ADQUISICIONES", title_left_bloqueado)
        fila = fila + 1
        ws.write(fila, 15, u"Fecha del reporte", texto_resaltado)
        ws.write(fila, 16, time.strftime('%d/%m/%Y'), texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Nombre", texto_resaltado)
        ws.write(fila, 1, plan.name, texto_bloqueado)
        ws.write(fila, 7, u"Responsable de Adquisiciones", texto_resaltado)
        fila = fila + 1
        ws.write(fila, 0, u"Año fiscal", texto_resaltado)
        ws.write(fila, 1, plan.anio_fiscal.name, texto_bloqueado)
        ws.write(fila, 7, u"Nombre Apellido", texto_resaltado)
        ws.write(fila, 8, plan.responsable_adqui_id.name or "", texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Presupuesto anual", texto_resaltado)
        ws.write(fila, 1, plan.presupuesto_anual, integer_editable)
        ws.write(fila, 7, u"Teléfono", texto_resaltado)
        ws.write(fila, 8, plan.telefono_responsable_adqui or "", texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Fecha de actualización", texto_resaltado)
        if plan.fecha_actualizacion_adqui:
            fecha_actualizacion = "%02s/%02s/%4s %02s:%02s" % (plan.fecha_actualizacion_adqui[8:10], plan.fecha_actualizacion_adqui[5:7], plan.fecha_actualizacion_adqui[0:4], plan.fecha_actualizacion_adqui[11:13], plan.fecha_actualizacion_adqui[14:16])
            ws.write(fila, 1, fecha_actualizacion or "", integer_editable)
        ws.write(fila, 7, u"Correo electrónico", texto_resaltado)
        ws.write(fila, 8, plan.correo_responsable_adqui or "", texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Unidad de compra", texto_resaltado)
        ws.write(fila, 1, plan.unidad_de_compra or "", integer_editable)
        fila = fila + 3

        # Escribo cabezales de filas
        ws.write(fila, 0, u"Id. de Planificación", header_left_bloqueado)
        ws.write(fila, 1, u"Tipo de Objeto", header_left_bloqueado)
        ws.write(fila, 2, u"Descripción Gral.", header_left_bloqueado)
        ws.write(fila, 3, u"Identificación del Objeto", header_left_bloqueado)
        ws.write(fila, 4, u"Fuente de Financiamiento", header_left_bloqueado)
        ws.write(fila, 5, u"Unidad de Medida", header_left_bloqueado)
        ws.write(fila, 6, u"Procedimiento de Contratación", header_left_bloqueado)
        ws.write(fila, 7, u"Fecha Estimada de Convocatoria", header_left_bloqueado)
        ws.write(fila, 8, u"Fecha Estimada de Recepción de Mercadería", header_left_bloqueado)
        ws.write(fila, 9, u"Cantidad Estimada", header_left_bloqueado)
        ws.write(fila, 10, u"Importe Estimado", header_left_bloqueado)
        ws.write(fila, 11, u"Estimación de Opción de Renovación", header_left_bloqueado)
        ws.write(fila, 12, u"Código ODG.Auxiliar", header_left_bloqueado)
        ws.write(fila, 13, u"Descripción ODG", header_left_bloqueado)
        ws.write(fila, 14, u"Destino de la Adquisición", header_left_bloqueado)
        ws.write(fila, 15, u"Sujeto a Autorización Externa de Fondos", header_left_bloqueado)
        ws.write(fila, 16, u"Compras Innovadoras", header_left_bloqueado)
        ws.write(fila, 17, u"Descripción de Compras Innovadoras", header_left_bloqueado)
        ws.write(fila, 18, u"Observaciones", header_left_bloqueado)
        fila = fila + 1

        # Escribo filas del plan
        for linea in plan.lineas_adquisicion.sorted(key=lambda x: x.identificacion_objeto):
            ws.write(fila, 0, linea.id_planificacion or u"", texto_editable)
            ws.write(fila, 1, linea.tipo_de_objeto or u"", texto_editable)
            ws.write(fila, 2, linea.descripcion_objeto or u"", texto_editable)
            ws.write(fila, 3, linea.identificacion_objeto or u"", texto_editable)
            ws.write(fila, 4, linea.ff_id.ff or u"", texto_editable)
            ws.write(fila, 5, linea.product_uom or u"", texto_editable)
            ws.write(fila, 6, linea.procedimiento_contratacion.display_name or u"", texto_editable)
            if linea.fecha_estimada_convocatoria:
                ws.write(fila, 7, "%02s/%02s/%4s" % (linea.fecha_estimada_convocatoria[8:10], linea.fecha_estimada_convocatoria[5:7], linea.fecha_estimada_convocatoria[0:4]), texto_editable)
            if linea.fecha_estimada_recepcion:
                ws.write(fila, 7, "%02s/%02s/%4s" % (linea.fecha_estimada_recepcion[8:10], linea.fecha_estimada_recepcion[5:7], linea.fecha_estimada_recepcion[0:4]), texto_editable)
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
        file_name = 'Export_plan_adquisiciones_' + plan.name + '.xls'
        wizard.write({'archivo_nombre': file_name,
                      'archivo_contenido': data_to_save})


grp_pep_reporte_plan_adquisiciones()
