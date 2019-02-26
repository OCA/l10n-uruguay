# -*- encoding: utf-8 -*-
# -------------------------------------------------#
# PARAMETROS NECESARIOS PARA EJECICION DEL PEP     #
# -------------------------------------------------#
from openerp import models, fields, api, tools
from openerp.tools.safe_eval import safe_eval
from openerp.exceptions import ValidationError, Warning


class base_config_settings(models.Model):
    """
        Se agregan parametros para las URL desde donde consumir
        los WS que se usan para importar una ES. Los WS deben ser REST y
        se puede utilizar un servidor CAS para autenticar el consumo. También
        se permite configurar un proxy para el caso en que el odoo esté corriendo en
        una red que los utilice.
    """
    _inherit = 'base.config.settings'

    grp_pep_url_import_ws_es_1 = fields.Char(string=u"Url para WS de info.")
    grp_pep_url_import_ws_es_2 = fields.Char(string=u"Url para WS de datos.")
    grp_pep_url_import_ws_es_auth_service = fields.Char(string=u"Servicio de Autenticación CAS",
                                                        help=u"URL del Servicio de Autenticación CAS")
    grp_pep_url_import_ws_es_auth_user = fields.Char(string=u"Usuario CAS",
                                                     help=u"Usuario para autenticarse contra el WS")
    grp_pep_url_import_ws_es_auth_pass = fields.Char(string=u"Password CAS",
                                                     help=u"Password para autenticarse contra el WS")
    grp_pep_url_import_ws_es_proxy_http = fields.Char(string=u"IP del Proxy para http",
                                                      help=u"Los pedidos a los WS por http se realizarán através de el"
                                                           u" servidor proxy configurado aquí.")
    grp_pep_url_import_ws_es_proxy_https = fields.Char(string=u"IP del Proxy para https",
                                                       help=u"Los pedidos a los WS por https se realizarán através de"
                                                            u" el servidor proxy configurado aquí.")

    @api.multi
    def get_default_grp_pep_url_import_ws_values(self):
        icp = self.env['ir.config_parameter']
        return {
            'grp_pep_url_import_ws_es_1': icp.get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_1'),
            'grp_pep_url_import_ws_es_2': icp.get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_2'),
            'grp_pep_url_import_ws_es_auth_service': icp.get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_auth_service'),
            'grp_pep_url_import_ws_es_auth_user': icp.get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_auth_user'),
            'grp_pep_url_import_ws_es_auth_pass': icp.get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_auth_pass'),
            'grp_pep_url_import_ws_es_proxy_http': icp.get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_proxy_http'),
            'grp_pep_url_import_ws_es_proxy_https': icp.get_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_proxy_https'),
        }

    @api.multi
    def set_grp_pep_url_import_ws_values(self):
        self.ensure_one()
        icp = self.env['ir.config_parameter']
        icp.set_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_1', self.grp_pep_url_import_ws_es_1 or u"")
        icp.set_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_2', self.grp_pep_url_import_ws_es_2 or u"")
        icp.set_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_auth_service', self.grp_pep_url_import_ws_es_auth_service or u"")
        icp.set_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_auth_user', self.grp_pep_url_import_ws_es_auth_user or u"")
        icp.set_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_auth_pass', self.grp_pep_url_import_ws_es_auth_pass or u"")
        icp.set_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_proxy_http', self.grp_pep_url_import_ws_es_auth_pass or u"")
        icp.set_param('grp_plan_ejecucion_presupuestal.grp_pep_url_import_ws_es_proxy_https', self.grp_pep_url_import_ws_es_auth_pass or u"")

    def grp_pep_check_params(self, cr, uid, ids, context=None):
        raise ValidationError(u"FUNCION NO IMPLEMENTADA")