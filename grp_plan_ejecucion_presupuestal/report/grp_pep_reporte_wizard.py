# -*- encoding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import Warning, ValidationError


class grp_pep_reporte_wizard(models.TransientModel):
    """ Wizard para la ejecución de reportes del plan """

    _name = 'grp.pep.reporte.wizard'

    REP_GASTO = 'gastos'
    REP_NECESIDADES = 'necesidades'
    REP_ADQUISICIONES = 'plan_adquisiciones'
    REP_PEP = 'plan_ejecucion_presupuestal'
    REP_PVE_CONCEPTO = 'planificado_vs_afectado_concepto'
    REP_PVE_ODG = 'planificado_vs_afectado_odg'

    LISTADO_REPORTES = [(REP_GASTO, u'Gastos'),
                        (REP_NECESIDADES, u'Necesidades'),
                        (REP_ADQUISICIONES, u'Plan de Adquisiciones'),
                        (REP_PEP, u'Plan de Ejecución Presupuestal'),
                        (REP_PVE_CONCEPTO, u'Planif. vs Ejec. por Concepto'),
                        (REP_PVE_ODG, u'Planif. vs Ejec. por ODG')]

    plan_anual_id = fields.Many2one(comodel_name='grp.pep.anual', string='Plan anual')
    tipo_reporte = fields.Selection(selection=LISTADO_REPORTES, string=u'Tipo de Reporte')
    version = fields.Integer(string=u'Versión')
    archivo_nombre = fields.Char(string='Nombre del archivo')
    archivo_contenido = fields.Binary(string="Archivo")

    @api.one
    def valida_version(self):
        valor_max = self.plan_anual_id.periodo_activo - 1
        if valor_max < 0:
            valor_max = 0
        if self.version < 0 or self.version > valor_max:
            raise ValidationError(u"La versión no es válida.")
        return True

    @api.multi
    def ejecutar(self):
        self.ensure_one()
        if not self.plan_anual_id:
            raise ValidationError(u"Debe elegir un Plan de Ejecución Presupuestal")
        # TODO: buscar el reporte según el tipo y ejecutarlo
        if self.tipo_reporte==self.REP_GASTO:
            self.env['grp.pep.reporte.gasto'].generar_excel(self)
        elif self.tipo_reporte==self.REP_NECESIDADES:
            self.env['grp.pep.reporte.necesidades'].generar_excel(self)
        elif self.tipo_reporte==self.REP_ADQUISICIONES:
            self.env['grp.pep.reporte.plan.adquisiciones'].generar_excel(self)
        elif self.tipo_reporte==self.REP_PEP:
            if self.valida_version():
                self.env['grp.pep.reporte.plan.ejecucion.presupuestal'].generar_excel(self)
        elif self.tipo_reporte==self.REP_PVE_CONCEPTO:
            if self.valida_version():
                self.env['grp.pep.reporte.planificado.afectado.concepto'].generar_excel(self)
        elif self.tipo_reporte==self.REP_PVE_ODG:
            if self.valida_version():
                self.env['grp.pep.reporte.planificado.afectado.odg'].generar_excel(self)
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'grp.pep.reporte.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
