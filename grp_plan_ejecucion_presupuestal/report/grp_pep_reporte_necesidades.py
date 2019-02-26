# -*- encoding: utf-8 -*-

from openerp import models
import base64
from cStringIO import StringIO
from xlwt import Workbook, easyxf
import time


class grp_pep_reporte_necesidades(models.AbstractModel):
    _name = 'grp.pep.reporte.necesidades'

    def generar_excel(self, wizard):
        plan = self.env['grp.pep.anual'].browse(wizard.plan_anual_id.id)
        ids = [x.concepto_id.id for x in plan.lineas_concepto]
        conceptos = self.env['grp.pep.concepto'].browse(ids)
        datos = conceptos.get_producto_necesidad_actualizada()

        lista_productos = []
        for producto_id, necesidad in datos.iteritems():
            producto = self.env['product.product'].browse(producto_id)
            lista_productos.append({'producto': producto.display_name,
                                    'sice': producto.grp_sice_cod,
                                    'unidad': producto.uom_id.name,
                                    'necesidad': necesidad})
        # Creo el libro Excel
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('Sheet 1', cell_overwrite_ok=True)

        ws.protect = False
        ws.password = "/Dd3R$eg(&(=:.$"

        # Creo los 'estilos'
        title_left_bloqueado = easyxf('font: name Calibri, bold True; alignment: horizontal center;')
        header_left_bloqueado = easyxf('font: name Calibri, bold True; alignment: horizontal left;'
                                       ' pattern: pattern solid, fore_colour 0x16;')
        texto_bloqueado = easyxf('font: name Calibri; alignment: horizontal left;')
        texto_editable = easyxf('font: name Calibri; alignment: horizontal left;'
                                ' protection: cell_locked false;')
        integer_editable = easyxf('font: name Calibri; alignment: horizontal right;'
                                  ' protection: cell_locked false;')
        fila = 0

        # Escribo el titulo
        ws.write_merge(fila, 0, fila, 6, u"REPORTE DE NECESIDADES", title_left_bloqueado)
        fila = fila + 1
        ws.write(fila, 5, u"Fecha del reporte", texto_bloqueado)
        ws.write(fila, 6, time.strftime('%d/%m/%Y'), texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Nombre", texto_bloqueado)
        ws.write(fila, 1, plan.name, texto_bloqueado)
        fila = fila + 1
        ws.write(fila, 0, u"Año fiscal", texto_bloqueado)
        ws.write(fila, 1, plan.anio_fiscal.name, texto_bloqueado)

        # Cabezal
        fila = fila + 2
        ws.write(fila, 0, u"Producto", header_left_bloqueado)
        ws.write(fila, 1, u"Código SICE", header_left_bloqueado)
        ws.write(fila, 2, u"Unidad de medida", header_left_bloqueado)
        ws.write(fila, 3, u"Cantidad", header_left_bloqueado)
        fila = fila + 1
        #Líneas
        for linea in lista_productos:
            ws.write(fila, 0, linea['producto'], texto_editable)
            ws.write(fila, 1, linea['sice'], integer_editable)
            ws.write(fila, 2, linea['unidad'], texto_editable)
            ws.write(fila, 3, linea['necesidad'], integer_editable)
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
        file_name = 'Export_Necesidades_' + plan.name + '.xls'
        wizard.write({'archivo_nombre': file_name,
                      'archivo_contenido': data_to_save})

grp_pep_reporte_necesidades()
