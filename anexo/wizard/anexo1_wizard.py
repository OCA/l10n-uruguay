# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution
# Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
#from openerp.tools.float_utils import float_round as round
import logging

_logger = logging.getLogger(__name__)


class anexo1_wizard(osv.osv):
    _name = 'anexo1.wizard'
    _columns = {
        'ejercicio_fiscal': fields.many2one('account.fiscalyear', 'Ejercicio fiscal', required=True),
        'target_move': fields.selection((('posted', 'Todos los asientos asentados'), ('all', 'Todos los asientos')),
                                        'Movimientos destino', required=True),
    }

    def print_report(self, cr, uid, ids, context=None):
        lista = []
        if context is None:
            context = {}

        data = self.read(cr, uid, ids)[0]

	sum_saldo_inicial_BU=0
	sum_saldo_alta_BU=0
	sum_saldo_baja_BU=0
	sum_saldo_final_BU=0
	sum_saldo_amort_inicial_BU=0
	sum_saldo_amort_amortizacion_BU=0
	sum_saldo_amort_baja_BU=0
	sum_saldo_amort_final_BU=0
	sum_saldo_neto_T_BU=0
	sum_saldo_neto_T_1_BU=0

	sum_saldo_inicial_INT=0
	sum_saldo_alta_INT=0
	sum_saldo_baja_INT=0
	sum_saldo_final_INT=0
	sum_saldo_amort_inicial_INT=0
	sum_saldo_amort_amortizacion_INT=0
	sum_saldo_amort_baja_INT=0
	sum_saldo_amort_final_INT=0
	sum_saldo_neto_T_INT=0
	sum_saldo_neto_T_1_INT=0

        datas = {'ids': context.get('active_ids', [])}
        report_obj = self.pool.get('anexo1.anexo')
        lista_id_anexos = report_obj.search(cr, uid, [])
        for anexo in report_obj.browse(cr, uid, lista_id_anexos):
            if anexo.cuenta_ids:
                for cuenta in anexo.cuenta_ids:
                    fila = self.crearFila(cr, uid, cuenta.codigoCuentas, cuenta.codigoCuentaAmortizacion, data['ejercicio_fiscal'][1], data['target_move'])
                    fila['tipo']=anexo.tipo
                    if(anexo.tipo=='BU'):
			sum_saldo_inicial_BU+=fila['val_saldo_inicial']
			sum_saldo_alta_BU+=fila['val_alta']
			sum_saldo_baja_BU+=fila['val_baja']
			sum_saldo_final_BU+=fila['val_saldo_final']
			sum_saldo_amort_inicial_BU+=fila['amort_saldo_inicial']
			sum_saldo_amort_amortizacion_BU+=fila['amort_amortizacion']
			sum_saldo_amort_baja_BU+=fila['amort_baja']
			sum_saldo_amort_final_BU+=fila['amort_saldo_final']
			sum_saldo_neto_T_BU+=fila['valor_neto_t']
			sum_saldo_neto_T_1_BU+=fila['valor_neto_t_1']
                    elif (anexo.tipo=='INT'):
			sum_saldo_inicial_INT+=fila['val_saldo_inicial']
			sum_saldo_alta_INT+=fila['val_alta']
			sum_saldo_baja_INT+=fila['val_baja']
			sum_saldo_final_INT+=fila['val_saldo_final']
			sum_saldo_amort_inicial_INT+=fila['amort_saldo_inicial']
			sum_saldo_amort_amortizacion_INT+=fila['amort_amortizacion']
			sum_saldo_amort_baja_INT+=fila['amort_baja']
			sum_saldo_amort_final_INT+=fila['amort_saldo_final']
			sum_saldo_neto_T_INT+=fila['valor_neto_t']
			sum_saldo_neto_T_1_INT+=fila['valor_neto_t_1']
                    lista.append(fila)
        datas['data'] = lista
        datas['anio_fiscal'] = data['ejercicio_fiscal'][1]

        res_users_obj = self.pool.get('res.users')
        company_obj = self.pool.get('res.company')
        company = res_users_obj.browse(cr, uid, uid, context=context).company_id
        datas['empresa'] = company.name
        datas['sum_saldo_inicial_BU']=sum_saldo_inicial_BU
        datas['sum_saldo_alta_BU']=sum_saldo_alta_BU
        datas['sum_saldo_baja_BU']=sum_saldo_baja_BU
        datas['sum_saldo_final_BU']=sum_saldo_final_BU
        datas['sum_saldo_amort_inicial_BU']=sum_saldo_amort_inicial_BU
        datas['sum_saldo_amort_amortizacion_BU']=sum_saldo_amort_amortizacion_BU
        datas['sum_saldo_amort_baja_BU']=sum_saldo_amort_baja_BU
        datas['sum_saldo_amort_final_BU']=sum_saldo_amort_final_BU
        datas['sum_saldo_neto_T_BU']=sum_saldo_neto_T_BU
        datas['sum_saldo_neto_T_1_BU']=sum_saldo_neto_T_1_BU

        datas['sum_saldo_inicial_INT']=sum_saldo_inicial_INT
        datas['sum_saldo_alta_INT']=sum_saldo_alta_INT
        datas['sum_saldo_baja_INT']=sum_saldo_baja_INT
        datas['sum_saldo_final_INT']=sum_saldo_final_INT
        datas['sum_saldo_amort_inicial_INT']=sum_saldo_amort_inicial_INT
        datas['sum_saldo_amort_amortizacion_INT']=sum_saldo_amort_amortizacion_INT
        datas['sum_saldo_amort_baja_INT']=sum_saldo_amort_baja_INT
        datas['sum_saldo_amort_final_INT']=sum_saldo_amort_final_INT
        datas['sum_saldo_neto_T_INT']=sum_saldo_neto_T_INT
        datas['sum_saldo_neto_T_1_INT']=sum_saldo_neto_T_1_INT

        anio= int(data['ejercicio_fiscal'][1][2:])
        datas['anio_yy_t']=str(anio)
        datas['anio_yy_t_1']=str(anio-1)
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'anexo.rpt',
            'datas': datas,
        }

    def crearFila(self, cr, uid, cuenta, cuenta_amort, anio, movimiento_destino):
        myres = {}
        myres['nombre'] = cuenta.code + ' - ' + cuenta.name
        myres['val_saldo_inicial'] = 0
        myres['val_alta'] = 0
        myres['val_baja'] = 0
        myres['val_saldo_final'] = 0
        myres['amort_saldo_inicial'] = 0
        myres['amort_baja'] = 0
        myres['amort_amortizacion'] = 0
        myres['amort_saldo_final'] = 0
        myres['valor_neto_t_1'] = 0

        saldo_inicial = 0
        saldo_alta = 0
        saldo_baja = 0
        saldo_final = 0

        saldo_final_amort = 0
        saldo_inicial_amort = 0

        condition_posted = ""
        if (movimiento_destino == 'posted'):
            condition_posted = " and am.state='posted' "

        query = """select COALESCE(sum(aml.credit), 0) credit, COALESCE(sum(aml.debit), 0) debit
                from account_move am, account_move_line aml
                where am.period_id=(select id from account_period where code='00/%s')
                and aml.move_id=am.id and account_id=%s %s
                """ % (anio, cuenta.id, condition_posted)
        cr.execute(query)
        row = cr.fetchone()
        if row[0] > 0:
            myres['val_saldo_inicial'] = round(row[0])
            saldo_inicial = row[0]
        else:
            myres['val_saldo_inicial'] = round(row[1])
            saldo_inicial = row[1]

        cr.execute("""select COALESCE(sum(aml.debit), 0) debit, COALESCE(sum(aml.credit), 0) credit
                from account_move am, account_move_line aml
                where am.period_id in (select id from account_period where code<>'00/%s' and code like '%s')
                and aml.move_id=am.id and account_id=%s %s """ % (anio, '%' + anio, cuenta.id, condition_posted))
        row = cr.fetchone()
        myres['val_alta'] = round(row[0])
        saldo_alta = row[0]
        myres['val_baja'] = round(row[1])
        saldo_baja = row[1]
        myres['val_saldo_final'] = round(saldo_inicial, 0) + round (saldo_alta, 0) - round(saldo_baja, 0)
        saldo_final = round(saldo_inicial, 0) + round(saldo_alta, 0) - round(saldo_baja, 0)

        #INICIO PARTE 2

        saldo_inicial_amort = 0
        saldo_baja_amort = 0
        saldo_amortizacion_amort = 0


        myres['amort_saldo_inicial'] = 0.0
        myres['amort_saldo_inicial'] = 0.0
        myres['amort_baja'] = 0.0
        myres['amort_amortizacion'] = 0.0

        if cuenta_amort and cuenta_amort.id:
            query = """select COALESCE(sum(aml.credit), 0) credit, COALESCE(sum(aml.debit), 0) debit
                        from account_move am, account_move_line aml
                        where am.period_id=(select id from account_period where code='00/%s')
                        and aml.move_id=am.id and account_id=%s %s
                        """ % (anio, cuenta_amort.id, condition_posted)
            _logger.info(query)
            cr.execute(query)
            row = cr.fetchone()
            _logger.info(row[0])
            _logger.info(row[1])
            if row[0] > 0:
                myres['amort_saldo_inicial'] = round(row[0])
                saldo_inicial_amort = row[0]
            else:
                myres['amort_saldo_inicial'] = round(row[1])
                saldo_inicial_amort = row[1]

            cr.execute("""select COALESCE(sum(aml.debit), 0) debit, COALESCE(sum(aml.credit), 0) credit
                    from account_move am, account_move_line aml
                    where am.period_id in (select id from account_period where code<>'00/%s' and code like '%s')
                    and aml.move_id=am.id and account_id=%s %s """ % (anio, '%' + anio, cuenta_amort.id, condition_posted))
            row = cr.fetchone()
            myres['amort_baja'] = round(row[0])
            saldo_baja_amort = row[0]
            myres['amort_amortizacion'] = round(row[1])
            saldo_amortizacion_amort = row[1]


        saldo_final_amort = round(saldo_inicial_amort, 0) - round(saldo_baja_amort, 0) + round(saldo_amortizacion_amort, 0)
        myres['amort_saldo_final'] = round(saldo_inicial_amort, 0) - round(saldo_baja_amort, 0) + round(saldo_amortizacion_amort, 0)

        myres['valor_neto_t'] = round(saldo_final, 0) - round(saldo_final_amort, 0)
        myres['valor_neto_t_1'] = round(saldo_inicial, 0) - round(saldo_inicial_amort, 0)

        _logger.info("Antes del return en crearFila: %s", myres)
        return myres

anexo1_wizard()
