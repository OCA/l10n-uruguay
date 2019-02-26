# -*- encoding: utf-8 -*-

from openerp import models
from openerp.exceptions import Warning


class grp_pep_reporte_gasto(models.AbstractModel):
    _name = 'grp.pep.reporte.gasto'

    def generar_excel(self):
        plan = self.env['grp.pep.anual'].obtener_plan_activo()
        raise Warning(u"Entre al reporte de gasto "+plan.name)

grp_pep_reporte_gasto()
