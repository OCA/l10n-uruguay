# -*- encoding: utf-8 -*-

from openerp import models
import base64
from cStringIO import StringIO
from xlwt import Workbook, easyxf
import time


class grp_pep_reporte_planificado_afectado_concepto(models.AbstractModel):
    _name = 'grp.pep.reporte.planificado.afectado.concepto'

    def generar_excel(self, wizard):
        plan = self.env['grp.pep.anual'].browse(wizard.plan_anual_id.id)
        version = wizard.version
        tope = int(plan.periodicidad) + 1
        datos = self._get_lineas_aprobado(wizard.plan_anual_id.id)
        if version > 0:
            # actualizo los importes de los períodos con lo adjudicado
            concepto_ids = [x.concepto_id.id for x in plan.lineas_concepto]
            conceptos = self.env['grp.pep.concepto'].browse(concepto_ids)
            for concepto in conceptos:
                historia_llaves = concepto.historia_llaves
                for llave in historia_llaves:
                    if llave.plan_periodo <= version:
                        clave = str(concepto.id) + llave.llave_str
                        if datos.get(clave):
                            datos[clave].update({'periodo_afectado_' + str(llave.plan_periodo): llave.importe})
            # actualizo los importes anuales
            for key, value in datos.iteritems():
                datos[key]['importe_anual_afectado'] = sum(v for k, v in datos[key].items() if k.startswith('periodo_afectado_'))
        # ordeno la lista por posición en el plan
        lista = []
        for key, value in datos.iteritems():
            lista.append(value)
        lineas = sorted(lista, key=lambda item: (item['posicion'], item['concepto']))

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
        ws.write_merge(fila, 0, fila, 17, u"COMPARACIÓN IMPORTE PLANIFICADO VERSUS IMPORTE AFECTADO POR CONCEPTO DE EJECUCIÓN PRESUPUESTAL", title_left_bloqueado)
        fila = fila + 1
        ws.write(fila, 16, u"Fecha del reporte", texto_resaltado)
        ws.write(fila, 17, time.strftime('%d/%m/%Y'), texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Nombre", texto_resaltado)
        ws.write(fila, 1, plan.name, texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Versión", texto_resaltado)
        ws.write(fila, 1, version, texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Periodicidad", texto_resaltado)
        ws.write(fila, 1, next((p[1] for p in plan.periodos if p[0] == plan.periodicidad), ''), texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Presupuesto anual", texto_resaltado)
        ws.write(fila, 1, plan.presupuesto_anual, integer_editable)
        fila = fila + 1
        ws.write(fila, 0, u"Año fiscal", texto_resaltado)
        ws.write(fila, 1, plan.anio_fiscal.name, texto_bloqueado)

        # Cabezal
        fila = fila + 2
        ws.write(fila, 0, u"Posición", header_left_bloqueado)
        ws.write(fila, 1, u"Concepto", header_left_bloqueado)
        ws.write(fila, 2, u"Inciso", header_left_bloqueado)
        ws.write(fila, 3, u"UE", header_left_bloqueado)
        ws.write(fila, 4, u"Programa", header_left_bloqueado)
        ws.write(fila, 5, u"Proyecto", header_left_bloqueado)
        ws.write(fila, 6, u"Moneda", header_left_bloqueado)
        ws.write(fila, 7, u"TC", header_left_bloqueado)
        ws.write(fila, 8, u"FF", header_left_bloqueado)
        ws.write(fila, 9, u"ODG", header_left_bloqueado)
        ws.write(fila, 10, u"Aux", header_left_bloqueado)
        ws.write(fila, 11, u"Importe anual planificado", header_left_bloqueado)
        ws.write(fila, 12, u"Importe anual afectado", header_left_bloqueado)
        for i in range(0, tope-1):
            ws.write(fila, 13 + i*2, u'Período ' + str(i+1) + u' planificado', header_left_bloqueado)
            ws.write(fila, 13 + (i*2)+1, u'Período ' + str(i+1) + u' afectado', header_left_bloqueado)
        fila = fila + 1
        # Líneas
        for linea in lineas:
            ws.write(fila, 0, linea['posicion'], texto_editable)
            ws.write(fila, 1, linea['concepto'], texto_editable)
            ws.write(fila, 2, linea['llave_inciso'], texto_editable)
            ws.write(fila, 3, linea['llave_ue'], texto_editable)
            ws.write(fila, 4, linea['llave_prog'], texto_editable)
            ws.write(fila, 5, linea['llave_proy'], texto_editable)
            ws.write(fila, 6, linea['llave_mon'], texto_editable)
            ws.write(fila, 7, linea['llave_tc'], texto_editable)
            ws.write(fila, 8, linea['llave_ff'], texto_editable)
            ws.write(fila, 9, linea['llave_odg'], texto_editable)
            ws.write(fila, 10, linea['llave_aux'], texto_editable)
            ws.write(fila, 11, linea['importe_anual_planificado'], integer_editable)
            ws.write(fila, 12, linea['importe_anual_afectado'], integer_editable)
            for i in range(0, tope - 1):
                ws.write(fila, 13 + i*2, linea['periodo_planificado_' + str(i+1)], integer_editable)
                ws.write(fila, 13 + (i*2)+1, linea['periodo_afectado_'+str(i+1)], integer_editable)
            fila = fila + 1

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
        file_name = 'Export_planificado_vs_afectado_concepto_' + plan.name + '.xls'
        wizard.write({'archivo_nombre': file_name,
                      'archivo_contenido': data_to_save})

    def _get_lineas_aprobado(self, plan_id):
        lineas = {}
        plan = self.env['grp.pep.anual'].browse(plan_id)
        periodicidad = int(plan.periodicidad)
        for linea_gasto in plan.lineas_gasto:
            concepto = linea_gasto.concepto_id
            for gasto in concepto.lineas_gasto:
                clave = str(concepto.id) + gasto.display_name
                lineas[clave] = ({'posicion': concepto.posicion_en_plan,
                                  'concepto': concepto.display_name,
                                  'importe_anual_planificado': 0,
                                  'importe_anual_afectado': 0,
                                  'llave_inciso': gasto.inciso_id.inciso,
                                  'llave_ue': gasto.ue_id.ue,
                                  'llave_prog': gasto.programa_id.programa,
                                  'llave_proy': gasto.proyecto_id.proyecto,
                                  'llave_mon': gasto.moneda_id.moneda,
                                  'llave_tc': gasto.tc_id.tc,
                                  'llave_ff': gasto.ff_id.ff,
                                  'llave_odg': gasto.odg_id.odg,
                                  'llave_aux': gasto.aux_id.aux
                                 })
                linea_concepto = linea_gasto.linea_concepto_id
                for i in range(1, periodicidad+1):
                    porcentaje_periodo = float(getattr(linea_concepto, 'periodo' + str(i) + '_porc')) / 100
                    importe_periodo = (concepto.importe * gasto.porcentaje_del_gasto / 100) * porcentaje_periodo
                    lineas[clave].update({'periodo_planificado_' + str(i): importe_periodo})
                    lineas[clave].update({'periodo_afectado_' + str(i): 0})
                    lineas[clave]['importe_anual_planificado'] += importe_periodo
        return lineas

grp_pep_reporte_planificado_afectado_concepto()
