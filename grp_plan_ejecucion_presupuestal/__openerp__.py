# -*- coding: utf-8 -*-
{
    'name':     u'GRP - Plan de Ejecución Presupuestal',
    'author':   'ATOS',
    'website':  'https://atos.net/es-uy/uruguay',
    'category': '',
    'license':  'AGPL-3',
    'version':  '0.15.1',
    'description': u"""
Extensión del GRP Estado Uruguayo
=================================
Habilita la confección de planes anuales de ejecución presupuestal.
""",
    'depends': [
        'base',
        'stock',
        'grp_compras_estatales',
        'grp_tesoreria',
        'grp_factura_siif'
    ],
    'data': [
        'data/sequence.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/grp_pep_estructura_servicios.xml',
        'views/grp_pep_concepto.xml',
        'views/grp_pep_formula.xml',
        'views/grp_pep_receta.xml',
        'views/grp_pep_adquisiciones.xml',
        'views/grp_pep_presupuestal.xml',
        'views/grp_pep_ejecucion.xml',
        'views/grp_pep_analisis_existencias.xml',
        'views/grp_pep_actualizacion_necesidades.xml',
        'views/grp_pep_anual.xml',
        'views/grp_pep_comparar_credito_siif.xml',
        'views/res_config_view.xml',
        'wizard/grp_pep_reporte_wizard.xml',
        'wizard/grp_pep_presupuestal_llaves.xml',
        'wizard/grp_pep_receta_us.xml',
        'views/menu_view.xml',
    ],

    'demo': [],

    'test': [],
    'auto_install': False,
    'installable': True,
    'application': True
}
# -*- encoding: utf-8 -*-
