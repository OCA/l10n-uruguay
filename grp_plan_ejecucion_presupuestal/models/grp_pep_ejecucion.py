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

from openerp import models, fields, api, tools
from openerp.exceptions import Warning, ValidationError
import logging

_logger = logging.getLogger(__name__)


class grp_pep_anual_linea_ejecucion(models.Model):
    _name = 'grp.pep.anual.linea.ejecucion'

    linea_gasto_id = fields.Many2one(comodel_name='grp.pep.anual.linea.gasto', ondelete='cascade')
    plan_id = fields.Many2one(string=u'Plan Anual', comodel_name='grp.pep.anual', ondelete='cascade')
    periodo_activo = fields.Integer(related='plan_id.periodo_activo', string=u'Período activo', readonly=True)
    concepto_id = fields.Many2one(related='linea_gasto_id.concepto_id', string=u'Concepto')
    importe_anual = fields.Float(string=u'Importe anual')
    importe_ajustado = fields.Float(string=u'Importe ajustado', compute='_compute_importe_ajustado')
    periodo1_importe = fields.Float(string=u'Período 1')
    periodo2_importe = fields.Float(string=u'Período 2')
    periodo3_importe = fields.Float(string=u'Período 3')
    periodo4_importe = fields.Float(string=u'Período 4')
    periodo5_importe = fields.Float(string=u'Período 5')
    periodo6_importe = fields.Float(string=u'Período 6')
    periodo7_importe = fields.Float(string=u'Período 7')
    periodo8_importe = fields.Float(string=u'Período 8')
    periodo9_importe = fields.Float(string=u'Período 9')
    periodo10_importe = fields.Float(string=u'Período 10')
    periodo11_importe = fields.Float(string=u'Período 11')
    periodo12_importe = fields.Float(string=u'Período 12')
    llaves = fields.One2many(string='Llaves', comodel_name='grp.pep.ejecucion.llave', inverse_name='linea_ejecucion_id')
    actualizar = fields.Boolean(string='Actualizar importe ajustado', compute='_compute_actualizar')

    @api.one
    def _compute_actualizar(self):
        self.actualizar = False
        for linea in self.llaves:
            self.actualizar = self.actualizar or linea.modificado
        pass

    @api.one
    def _compute_importe_ajustado(self):
        self.importe_ajustado = sum(getattr(self, 'periodo' + str(i) + '_importe') for i in range(1, 13))

    @api.onchange('periodo1_importe', 'periodo2_importe', 'periodo3_importe', 'periodo4_importe', 'periodo5_importe', 'periodo6_importe',
                  'periodo7_importe', 'periodo8_importe', 'periodo9_importe', 'periodo10_importe', 'periodo11_importe', 'periodo12_importe')
    def onchange_periodo(self):
        self.ensure_one()
        self._compute_importe_ajustado()

    def nueva_llave(self, llave_str):
        periodicidad = int(self.plan_id.periodicidad)
        for i in range(self.periodo_activo, periodicidad + 1):
            llave = {'linea_ejecucion_id': self.id,
                     'llave_str': llave_str,
                     'periodo': i,
                     'importe': 0}
            self.env['grp.pep.ejecucion.llave'].create(llave)

    def llaves_exceden_ejecutado(self):
        res = ""
        for llave in self.llaves:
            total_ejecutado = self.concepto_id.total_mov_periodo_llave(llave.periodo, llave.llave_str)
            if total_ejecutado > llave.importe:
                res += "%s %s, " % (llave.llave_str, total_ejecutado)
        return res

    @api.multi
    def button_guardar_llaves(self):
        llaves_mal = self.llaves_exceden_ejecutado()
        if llaves_mal:
            raise ValidationError("Error: Las siguientes llaves tienen importes inferiores a lo ya afectado, %s" % (llaves_mal))
        else:
            self.set_llaves_actualizadas()
            for i in range(1, 13):
                setattr(self, 'periodo' + str(i) + '_importe', 0)
            for llave in self.llaves:
                importe_actual = getattr(self, 'periodo' + str(llave.periodo) + '_importe')
                setattr(self, 'periodo' + str(llave.periodo) + '_importe', importe_actual + llave.importe)

    def set_llaves_actualizadas(self):
        for linea in self.llaves:
            linea.modificado = False

    def cierra_importes_periodo(self, periodo):
        concepto = self.concepto_id
        total_periodo = 0
        # actualizo importes de las llaves del período
        for llave in self.llaves:
            if llave.periodo == periodo:
                monto_ejecutado = concepto.total_mov_periodo_llave(periodo, llave.llave_str)
                llave.importe = monto_ejecutado
                total_periodo = total_periodo + monto_ejecutado
        setattr(self, 'periodo' + str(periodo) + '_importe', total_periodo)
        # actualizo importes totales
        total = 0
        for i in range(1, 13):
            total = total + getattr(self, 'periodo' + str(i) + '_importe')
        self.importe_anual = total
        self.importe_ajustado = self.importe_anual

    def registra_historia_llaves_periodo(self, periodo):
        concepto = self.concepto_id
        concepto.historia_llave_periodo(periodo)

    @api.multi
    def importe_anual_llave(self, llave_str):
        sql = "SELECT COALESCE(SUM(importe), 0) FROM public.grp_pep_ejecucion_llave WHERE llave_str = '%s' AND linea_ejecucion_id = %s;" % (llave_str, self.id)
        self.env.cr.execute(sql)
        total = self.env.cr.fetchone()[0]
        return total

grp_pep_anual_linea_ejecucion()


class grp_pep_movimiento_ejecucion(models.Model):
    _name='grp.pep.movimiento.ejecucion'
    _recname='codigo_documento_asociado'

    proceso_origen = [
        ('adquisiciones', u'Adquisiciones'),
        ('cuentas_a_pagar', u'Cuentas a pagar'),
        ('viaticos', u'Viáticos'),
        ('vales_y_reintegros', u'Vales y reintegros'),
        ('contratos', u'Contratos'),
        ('transferencias', u'Transferencias'),
        ('3en1', u'3 en 1'),
        ('afectacion', u'Afectación'),
        ('apg', u'APG'),
        ('3en1_modificacion', u'3 en 1 Modificación'),
        ('afectacion_modificacion', u'Afectacion Modificación'),
        ('apg_modificacion', u'APG Modificación'),
    ]

    plan_anual_id = fields.Many2one(string=u'Plan Anual', comodel_name='grp.pep.anual')
    periodo = fields.Integer(string=u'Período')
    concepto_id = fields.Many2one(string=u'Concepto', comodel_name='grp.pep.concepto')
    llave_str = fields.Char(string='Llave')
    importe = fields.Float(string='Importe')
    codigo_documento_asociado = fields.Char(string='Documento')
    proceso_origen = fields.Selection(string='Proceso origen', selection=proceso_origen)


    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'periodo' in fields:
            fields.remove('periodo')
        return super(grp_pep_movimiento_ejecucion, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

grp_pep_movimiento_ejecucion()


class grp_pep_ejecucion_llave(models.Model):
    _name = 'grp.pep.ejecucion.llave'
    _order = 'periodo, llave_str'

    linea_ejecucion_id = fields.Many2one(string=u'Línea ejecución', comodel_name='grp.pep.anual.linea.ejecucion')
    periodo_activo = fields.Integer(related='linea_ejecucion_id.periodo_activo', string=u'Período activo')
    plan_state = fields.Selection(related='linea_ejecucion_id.plan_id.state', string=u'Estado')
    periodo = fields.Integer(string=u'Período')
    llave_str = fields.Char(string='Llave')
    importe = fields.Float(string='Importe')
    es_periodo_cerrado = fields.Boolean(string='es cerrado', compute='_compute_es_periodo_cerrado')
    modificado = fields.Boolean(string='Modificado', default=False)

    @api.one
    def _compute_es_periodo_cerrado(self):
        self.es_periodo_cerrado = (self.periodo < self.periodo_activo)

    @api.onchange('importe')
    def onchange_importe(self):
        self.modificado = True
        if self.importe < 0:
            self.importe = 0
            raise ValidationError("Error: El importe no puede tener un valor negativo")

grp_pep_ejecucion_llave()
