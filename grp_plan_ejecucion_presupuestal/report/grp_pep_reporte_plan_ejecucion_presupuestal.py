# -*- encoding: utf-8 -*-

from openerp import models
import base64
from cStringIO import StringIO
from xlwt import Workbook, easyxf
import time


class grp_pep_reporte_plan_ejecucion_presupuestal(models.AbstractModel):
    _name = 'grp.pep.reporte.plan.ejecucion.presupuestal'

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
                            datos[clave].update({'periodo_' + str(llave.plan_periodo): llave.importe})
            for key, value in datos.iteritems():
                datos[key]['importe_anual'] = sum(v for k, v in datos[key].items() if k.startswith('periodo_'))
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
        ws.write_merge(fila, 0, fila, 6, u"PLAN ANUAL DE EJECUCIÓN PRESUPUESTAL", title_left_bloqueado)
        fila = fila + 1
        ws.write(fila, 10, u"Fecha del reporte", texto_resaltado)
        ws.write(fila, 11, time.strftime('%d/%m/%Y'), texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Nombre", texto_resaltado)
        ws.write(fila, 1, plan.name, texto_bloqueado)
        ws.write(fila, 4, u"Información del Organismo", texto_resaltado)
        ws.write(fila, 8, u"Jerarca que Autoriza", texto_resaltado)
        fila = fila + 1
        ws.write(fila, 0, u"Versión", texto_resaltado)
        ws.write(fila, 1, version, texto_bloqueado)
        ws.write(fila, 4, u"Nro. Inciso", texto_resaltado)
        ws.write(fila, 5, plan.inciso_id.idInciso, texto_bloqueado)
        ws.write(fila, 8, u"Nombre Apellido", texto_resaltado)
        ws.write(fila, 9, plan.jerarca_id.name, texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Plan base", texto_resaltado)
        ws.write(fila, 1, plan.plan_base_id.name, texto_bloqueado)
        ws.write(fila, 4, u"Descripción Inciso", texto_resaltado)
        ws.write(fila, 5, plan.inciso_id.descInciso, texto_bloqueado)
        ws.write(fila, 8, u"Cargo", texto_resaltado)
        ws.write(fila, 9, plan.cargo_jerarca.name, texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Estructura de servicio", texto_resaltado)
        ws.write(fila, 1, plan.estructura_de_servicios_id.name, texto_bloqueado)
        ws.write(fila, 4, u"Nro. Unidad Ejecutora", texto_resaltado)
        ws.write(fila, 5, plan.numero_unidad_ejecutora, texto_bloqueado)
        ws.write(fila, 8, u"Teléfono", texto_resaltado)
        if plan.telefono_jerarca:
            ws.write(fila, 9, plan.telefono_jerarca, texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Fecha de creación", texto_resaltado)
        fecha = plan.create_date
        fecha_de_creacion = "%02s/%02s/%4s %02s:%02s" % (fecha[8:10], fecha[5:7], fecha[0:4], fecha[11:13], fecha[14:16])
        ws.write(fila, 1, fecha_de_creacion, texto_bloqueado)
        ws.write(fila, 4, u"Unidad Ejecutora", texto_resaltado)
        ws.write(fila, 5, plan.unidad_ejecutora_id.descUE, texto_bloqueado)
        ws.write(fila, 8, u"Correo electrónico", texto_resaltado)
        if plan.correo_jerarca:
            ws.write(fila, 9, plan.correo_jerarca, texto_bloqueado)
        fila = fila + 1
        if plan.plan_activo:
            ws.write(fila, 0, 'Activo', texto_resaltado)
        else:
            ws.write(fila, 0, 'No Activo', texto_resaltado)
        ws.write(fila, 8, u"Responsable de Elaboración", texto_resaltado)
        fila = fila + 1
        ws.write(fila, 0, u"Periodicidad", texto_resaltado)
        ws.write(fila, 1, next((p[1] for p in plan.periodos if p[0] == plan.periodicidad), ''), texto_bloqueado)
        ws.write(fila, 8, u"Nombre Apellido", texto_resaltado)
        ws.write(fila, 9, plan.responsable_id.name, texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Presupuesto anual", texto_resaltado)
        ws.write(fila, 1, plan.presupuesto_anual, integer_editable)
        ws.write(fila, 8, u"Teléfono", texto_resaltado)
        if plan.telefono_responsable:
            ws.write(fila, 9, plan.telefono_responsable, texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Año fiscal", texto_resaltado)
        ws.write(fila, 1, plan.anio_fiscal.name, texto_bloqueado)
        ws.write(fila, 8, u"Correo electrónico", texto_resaltado)
        if plan.telefono_responsable:
            ws.write(fila, 9, plan.correo_responsable, texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Tipo de control de los conceptos", texto_resaltado)
        ws.write(fila, 1, plan.tipo_control_conceptos, texto_bloqueado)

        # Cabezal
        fila = fila + 2
        ws.write(fila, 0, u"Posición", header_left_bloqueado)
        ws.write(fila, 1, u"Concepto", header_left_bloqueado)
        ws.write(fila, 2, u"Método de cálculo", header_left_bloqueado)
        ws.write(fila, 3, u"Importe anual", header_left_bloqueado)
        ws.write(fila, 4, u"Inciso", header_left_bloqueado)
        ws.write(fila, 5, u"UE", header_left_bloqueado)
        ws.write(fila, 6, u"Programa", header_left_bloqueado)
        ws.write(fila, 7, u"Proyecto", header_left_bloqueado)
        ws.write(fila, 8, u"Moneda", header_left_bloqueado)
        ws.write(fila, 9, u"TC", header_left_bloqueado)
        ws.write(fila, 10, u"FF", header_left_bloqueado)
        ws.write(fila, 11, u"ODG", header_left_bloqueado)
        ws.write(fila, 12, u"Aux", header_left_bloqueado)
        for i in range(1, tope):
            ws.write(fila, 12+i, u'Período ' + str(i), header_left_bloqueado)
        fila = fila + 1
        # Líneas
        for linea in lineas:
            ws.write(fila, 0, linea['posicion'], texto_editable)
            ws.write(fila, 1, linea['concepto'], texto_editable)
            ws.write(fila, 2, linea['metodo'], texto_editable)
            ws.write(fila, 3, linea['importe_anual'], integer_editable)
            ws.write(fila, 4, linea['llave_inciso'], texto_editable)
            ws.write(fila, 5, linea['llave_ue'], texto_editable)
            ws.write(fila, 6, linea['llave_prog'], texto_editable)
            ws.write(fila, 7, linea['llave_proy'], texto_editable)
            ws.write(fila, 8, linea['llave_mon'], texto_editable)
            ws.write(fila, 9, linea['llave_tc'], texto_editable)
            ws.write(fila, 10, linea['llave_ff'], texto_editable)
            ws.write(fila, 11, linea['llave_odg'], texto_editable)
            ws.write(fila, 12, linea['llave_aux'], texto_editable)
            for i in range(1, tope):
                ws.write(fila, 12+i, linea['periodo_'+str(i)], integer_editable)
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
        file_name = 'Export_PEP_' + plan.name + '.xls'
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
                                  'metodo': concepto.metodo_calculo,
                                  'importe_anual': 0,
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
                    lineas[clave].update({'periodo_' + str(i): importe_periodo})
                    lineas[clave]['importe_anual'] += importe_periodo
        return lineas

grp_pep_reporte_plan_ejecucion_presupuestal()
