from __future__ import division
import os
import re
import random
import hashlib
import hmac
from string import letters
import datetime
import gviz_api
from collections import namedtuple

import webapp2
import jinja2

from google.appengine.ext import db
from google.appengine.ext.db import polymodel

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)




class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

####### Tesis Stuff ##########

class Agronomia(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 15 de abril 2014
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        #se llama para cada lectura de energia, valor es la lectura de energia.
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
            
            #pliego[costo por comercializacion, punta, resto, valle, costo por distribucion]            
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_valle=0
            dinero_resto=0
            
            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        #Prepara la informacion enviada al navegador y parte del calculo de la factura
        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,0,k) 8 digitos, 0 decimales, unidades en KiloWatts-hora
                # por eso ninguna modificacion a la resta
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                #Se evita el problema cuanto la cuenta del medidor vuelve a comenzar
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 15 de abril 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13

            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        #Consulta a la base de datos
        dt=db.GqlQuery('SELECT * FROM Agronomia WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Agronomia WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #Este calculo se determina el factor de potencia
        #para el periodo solicitado
        #corrige problema de retorno de las cuentas de energia para 
        #el calculo de FP.
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        #factor de potencia
        fp=Wh/VAh

        #sirve para reducir la cantidad de muestras enviadas a la grafica
        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        #ciclo principal donde se recorre todo el vector retornado por la base de datos.
        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            #corrige cuando se va sumando el aculumado de energia y la cuenta se reinicia
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia))
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)

            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            #se reduce la cantidad de muestras enviadas a las graficas del navegador
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        #Prepara los datos para ser enviados a Google Chart Tools
        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    #se suben los datos a la bae de datos
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Agronomia(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class AgronomiaDecanato(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,0,k) 8 digitos, 0 decimales, unidades en KiloWatts-hora
                # por eso ninguna modificacion a la resta
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM AgronomiaDecanato WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM AgronomiaDecanato WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia))
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)           
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return AgronomiaDecanato(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class AgronomiaGalera(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,0,k) 8 digitos, 0 decimales, unidades en KiloWatts-hora
                # por eso ninguna modificacion a la resta
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13                      
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM AgronomiaGalera WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM AgronomiaGalera WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia))
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)           
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return AgronomiaGalera(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class AgronomiaQuimica(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM AgronomiaQuimica WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM AgronomiaQuimica WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return AgronomiaQuimica(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class AuditoriumMarmol(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,0,k) 8 digitos, 0 decimales, unidades en KiloWatts-hora
                # por eso ninguna modificacion a la resta
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM AuditoriumMarmol WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM AuditoriumMarmol WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia))
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)           
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return AuditoriumMarmol(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Cafetines(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Cafetines WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Cafetines WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Cafetines(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class ComedorUES(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM ComedorUES WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM ComedorUES WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return ComedorUES(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Derecho(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Derecho WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Derecho WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Derecho(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Economia1(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,0,k) 8 digitos, 0 decimales, unidades en KiloWatts-hora
                # por eso ninguna modificacion a la resta
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Economia1 WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Economia1 WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia))
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)           
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Economia1(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Economia2(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Economia2 WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Economia2 WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Economia2(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Economia3(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Economia3 WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Economia3 WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Economia3(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Economia4(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Economia4 WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Economia4 WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Economia4(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Economia6(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,0,k) 8 digitos, 0 decimales, unidades en KiloWatts-hora
                # por eso ninguna modificacion a la resta
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Economia6 WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Economia6 WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia))
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)           
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Economia6(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Humanidades2(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Humanidades2 WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()

        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Humanidades2 WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Humanidades2(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Humanidades3(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,0,k) 8 digitos, 0 decimales, unidades en KiloWatts-hora
                # por eso ninguna modificacion a la resta
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Humanidades3 WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Humanidades3 WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia))
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)           
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Humanidades3(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Humanidades4(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,2,k) 8 digitos, 2 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 100
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/100
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/100

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Humanidades4 WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Humanidades4 WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/100) #entre 100 por el formato (8,2,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/100               
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Humanidades4(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class MecanicaComplejo(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,0,k) 8 digitos, 0 decimales, unidades en KiloWatts-hora
                # por eso ninguna modificacion a la resta
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM MecanicaComplejo WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM MecanicaComplejo WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia))
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)           
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return MecanicaComplejo(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Medicina(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Medicina WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Medicina WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Medicina(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Odontologia1(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Odontologia1 WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Odontologia1 WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Odontologia1(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Odontologia2(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Odontologia2 WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Odontologia2 WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Odontologia2(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Odontologia3(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Odontologia3 WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Odontologia3 WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Odontologia3(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class OdontologiaImprenta(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,0,k) 8 digitos, 0 decimales, unidades en KiloWatts-hora
                # por eso ninguna modificacion a la resta
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM OdontologiaImprenta WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM OdontologiaImprenta WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia))
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)           
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return OdontologiaImprenta(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Periodismo(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,0,k) 8 digitos, 0 decimales, unidades en KiloWatts-hora
                # por eso ninguna modificacion a la resta
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Periodismo WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Periodismo WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia))
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)           
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Periodismo(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class PrimarioFIA(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['k','M','G']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['k','M','G']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,2,M) 8 digitos, 2 decimales, unidades en MegaWatts-hora
                # por eso desplazamos los dos digitos decimeles, dividiendo entre 100
                # Luego multiplicamos por 1000 para llegar a los KiloWatts-hora
                # Que es igual a multiplicar por 10
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)*10
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)*10

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM PrimarioFIA WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM PrimarioFIA WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)*10) #por 10 por el formato (8,2,M) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)*10               
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:           
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return PrimarioFIA(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Psicologia(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Psicologia WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Psicologia WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Psicologia(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class Quimica(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,3,k) 8 digitos, 3 decimales, unidades en KiloWatts-hora
                # por eso desplazamos los tres digitos decimeles, dividiendo entre 1000
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)/1000
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)/1000

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM Quimica WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM Quimica WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia)/1000) #entre mil por el formato (8,3,k) del medidor
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)/1000                
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return Quimica(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

class QuimicaImprenta(db.Model):
    fecha_hora=db.DateTimeProperty()
    energia_activa=db.IntegerProperty(indexed=False)
    energia_aparente=db.IntegerProperty(indexed=False)
    demanda=db.FloatProperty(indexed=False)

    @classmethod
    def filtro(cls,desde,hasta): 
        def human_readable(num):
        #devuelve el valor en notacion de ingenieria
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return num
                num /= 1000.0
            return num        
        def human_readable_unit(num):
        #devuelve el simbolo de las unidades
            for unit in ['','K','M']:            
                if abs(num) < 1000.0:
                    return unit
                num /= 1000.0
            return unit

        def pliego_tarifario(fecha):
            #pliego tarifario a partir del 1 de enero 2015
            #CAESS GRANDES DEMANDAS ( >50 kW )
            #MEDIA TENSION CON MEDIDOR HORARIO
            this_date=datetime.date(fecha.year, fecha.month, fecha.day)
            pliego=[(datetime.date(2014,4,15), (12.974283, 0.176540, 0.178807, 0.168412, 6.263900)),
                    (datetime.date(2014,7,15), (12.974283, 0.179156, 0.182802, 0.171365, 6.263900)),
                    (datetime.date(2014,10,15),(12.974283, 0.178932, 0.183518, 0.170740, 6.263900)),
                    (datetime.date(2015,1,1),  (13.195557, 0.178932, 0.183518, 0.170740, 6.329066)),
                    (datetime.date(2015,1,15), (13.195557, 0.159446, 0.160570, 0.153326, 6.329066))]
            
            for trimestre, tarifa in pliego:
                if this_date >= trimestre:
                    valor=tarifa
            return valor
        
        def facturacion(fecha,valor,pliego,fp):
            hora=datetime.time(fecha.hour, fecha.minute)
            #Punta: de las 18:00 a 22:59 horas
            inicio_horario_punta = datetime.time(18, 0)
            final_horario_punta = datetime.time(22, 59)
            #Resto: de las 05:00 a 17:59 horas
            inicio_horario_resto = datetime.time(5,0)
            final_horario_resto = datetime.time(17,59)
            #Valle: de las 23:00 a 04:59 horas
                        
            punta=pliego[1]
            resto=pliego[2]
            valle=pliego[3]

            energia_punta=0
            energia_valle=0
            energia_resto=0
            dinero_punta=0
            dinero_resto=0
            dinero_valle=0

            #Si el FP es igual o mayor que 0.75 y menor que 0.90, el cargo por energia sera aumentado en
            #1% por cada centesima que el FP sea inferior a 0.90;

            #Si el FP es igual o mayor que 0.60 y menor que 0.75, el cargo por energia sera aumentado en
            #15% mas el 2% por cada centesima que el FP sea inferior a 0.75;
            if 0.75 <= fp <=0.9:
                porcentaje= 0.9-fp
            elif 0.6 <= fp <=0.75:
                porcentaje=(0.9-fp)*1.5+(0.75-fp)*2
            else:
                porcentaje=0

            #factor de perdidas de transformacion 1.5%
            if inicio_horario_punta <= hora <= final_horario_punta:
                energia_punta=valor
                dinero=valor*punta*1.015
                dinero_punta=dinero
                recargo_fp=dinero*porcentaje         
            elif inicio_horario_resto <= hora <= final_horario_resto:
                energia_resto=valor
                dinero=valor*resto*1.015
                dinero_resto=dinero
                recargo_fp=dinero*porcentaje
            else:
                energia_valle=valor
                dinero=valor*valle*1.015
                dinero_valle=dinero
                recargo_fp=dinero*porcentaje
            return dinero, energia_punta, energia_resto, energia_valle, dinero_punta, dinero_resto, dinero_valle, recargo_fp

        def informacion(array_energia, array_demanda, dinero, energia_punta, energia_resto, energia_valle,
                            dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp):
            if len(array_energia)==0:
                energia_consumida=0
                desde_energia=0
                hasta_energia=0
            else:            
                # Medidor (8,0,k) 8 digitos, 0 decimales, unidades en KiloWatts-hora
                # por eso ninguna modificacion a la resta
                desde_energia=array_energia[0]
                hasta_energia=array_energia[-1]
                if hasta_energia<desde_energia:
                    energia_consumida=((99999999-desde_energia)+hasta_energia)
                else:                    
                    energia_consumida=(hasta_energia - desde_energia)

            if len(array_demanda)==0:
                demanda_maxima=0
            else:            
                demanda_maxima=max(array_demanda)/1000 #las unidades vienen en Watts por eso entre 1000 para tener kW.
                #pliego tarifario a partir del 1 de enero 2015
                #GRANDES DEMANDAS ( >50 kW )
                #MEDIA TENSION CON MEDIDOR HORARIO
                tarifa_distribucion=pliego[4]
                dinero_demanda=demanda_maxima*1.015*tarifa_distribucion
                comercializacion=pliego[0]
                subtotal_dinero=dinero+dinero_demanda+recargo_fp+comercializacion
                iva=subtotal_dinero*0.13
                total_dinero=subtotal_dinero*1.13          
            info_demanda=('demanda_dato',str(demanda_maxima)+' kWatts')
            info_rango_desde=('info_rango_desde',
                          str(human_readable(desde_energia))+
                          ''+str(human_readable_unit(desde_energia))+
                          'W-hora')
            info_rango_hasta=('info_rango_hasta', str(human_readable(hasta_energia))+
                          ''+str(human_readable_unit(hasta_energia))+'W-hora')
            info_tarifa_comercializacion=('tarifa_comercializacion', comercializacion)
            info_tarifa_punta=('tarifa_punta',pliego[1])
            info_tarifa_resto=('tarifa_resto',pliego[2])
            info_tarifa_valle=('tarifa_valle',pliego[3])
            info_tarifa_distribucion=('tarifa_distribucion', tarifa_distribucion)
            info_energia=('energia_dato',str(energia_consumida)+' kW-h')
            info_energia_punta=('info_energia_punta', str(energia_punta)+' kW-h')
            info_energia_resto=('info_energia_resto', str(energia_resto)+' kW-h')
            info_energia_valle=('info_energia_valle', str(energia_valle)+' kW-h')
            info_perd_trafo=('perd_trafo', '1.50%')
            info_dinero_energia=('dinero_energia','$ '+str(dinero))
            info_dinero_demanda=('dinero_demanda','$ '+str(dinero_demanda))
            info_dinero_punta=('dinero_punta', '$ '+str(dinero_punta))
            info_dinero_resto=('dinero_resto','$ '+str(dinero_resto))
            info_dinero_valle=('dinero_valle','$ '+str(dinero_valle))
            info_fp=('fp',fp)
            info_recargo_fp=('recargo_fp', '$ '+str(recargo_fp))
            info_dinero_comercializacion=('dinero_comercializacion','$'+str(comercializacion))
            info_subtotal_dinero=('sub_total','$ '+str(subtotal_dinero))
            info_iva=('iva','$ '+str(iva))
            info_total_dinero=('total_dinero','$ '+str(total_dinero))
            return [info_tarifa_comercializacion,
                    info_tarifa_punta,
                    info_tarifa_resto,
                    info_tarifa_valle,
                    info_tarifa_distribucion,
                    info_energia, 
                    info_demanda, 
                    info_rango_desde, 
                    info_rango_hasta,
                    info_energia_punta,
                    info_energia_resto,
                    info_energia_valle,
                    info_perd_trafo,
                    info_dinero_energia, 
                    info_dinero_demanda,
                    info_dinero_punta,
                    info_dinero_resto,
                    info_dinero_valle,
                    info_fp,
                    info_recargo_fp,
                    info_dinero_comercializacion,
                    info_iva, 
                    info_subtotal_dinero,
                    info_total_dinero]

        dt=db.GqlQuery('SELECT * FROM QuimicaImprenta WHERE fecha_hora > :1 AND fecha_hora < :2',desde,hasta)
        
        # get() method obtains the first single matching entity found in the Datastore
        inicio_rango=dt.get()
        #En el caso que el rango solicitado no tenga los datos.
        if inicio_rango is None:
            return None
        anterior_energia=inicio_rango.energia_activa
        energia_graph=0
        dinero=0
        energia_punta=0
        energia_resto=0
        energia_valle=0
        dinero_punta=0
        dinero_resto=0
        dinero_valle=0
        recargo_fp=0
        array_data=[]
        array_grafico=[]
        array_energia_activa=[]
        array_energia_aparente=[]
        array_demanda=[]
        array_factura=[]
        array_fp=[]

        #extrae el ultimo elemento de la consulta
        final_rango=db.GqlQuery('SELECT * FROM QuimicaImprenta WHERE fecha_hora < :1 ORDER BY fecha_hora DESC LIMIT 1',hasta).get()

        pliego=pliego_tarifario(final_rango.fecha_hora)

        #ahorita tratando de remendar el problema rel retorno de las cuentas de energia        
        if final_rango.energia_activa < inicio_rango.energia_activa:
            Wh=(99999999-inicio_rango.energia_activa)+final_rango.energia_activa

        else:
            Wh=final_rango.energia_activa-inicio_rango.energia_activa 

        if final_rango.energia_aparente < inicio_rango.energia_aparente:
            VAh=(99999999-inicio_rango.energia_aparente)+final_rango.energia_aparente
        else:
            VAh=final_rango.energia_aparente-inicio_rango.energia_aparente

        fp=Wh/VAh

        rango_dias=hasta-desde        
        semanas=(rango_dias.days)//7

        for index, fila in enumerate(dt):
            array_energia_activa.append(fila.energia_activa)
            array_energia_aparente.append(fila.energia_aparente)
            array_demanda.append(fila.demanda)
            if fila.energia_activa>=anterior_energia:
                diferencia_energia=((fila.energia_activa - anterior_energia))
            else:
                diferencia_energia=((99999999-anterior_energia)+fila.energia_activa)           
            anterior_energia=fila.energia_activa
            energia_graph+=diferencia_energia            
            array_factura=facturacion(fila.fecha_hora, diferencia_energia, pliego, fp)
            dinero+=array_factura[0]
            energia_punta+=array_factura[1]
            energia_resto+=array_factura[2]
            energia_valle+=array_factura[3]
            dinero_punta+=array_factura[4]
            dinero_resto+=array_factura[5]
            dinero_valle+=array_factura[6]
            recargo_fp+=array_factura[7]
            if semanas >= 1:
                if index % semanas == 0:              
                    array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))
            else:
                array_grafico.append((fila.fecha_hora, energia_graph, fila.demanda/1000, dinero))

        description=[("Fecha","datetime"),("energia","number"), ("demanda","number"), ("dinero","number")]
        data_table=gviz_api.DataTable(description)
        data_table.LoadData(array_grafico)
        #I experiemented that it is faster to short the columns here than in the database
        json=data_table.ToJSon(columns_order=("Fecha", "energia", "demanda", "dinero"),order_by="Fecha")
        tupla=('datos',json)
        #agrega la tupla a la lista
        array_data.append(tupla)
        #anade las tuplas de la informacion a la lista   
        array_data.extend(informacion(array_energia_activa, array_demanda, dinero, energia_punta, energia_resto,
                                        energia_valle, dinero_punta, dinero_resto, dinero_valle, pliego, fp, recargo_fp))
        #dict(array_data) convierte la lista array_data en un diccionario
        #para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, energia_activa, energia_aparente, demanda):
        return QuimicaImprenta(fecha_hora=fecha_hora,                                                        
                            energia_activa=energia_activa,
                            energia_aparente=energia_aparente,
                            demanda=demanda)                            

#Sirve para sincronizar la base de datos local con la base Datastore
#responde con la fecha y hora de la ultima fila que tiene en la base de datos
class Consulta(BlogHandler):

    def post(self):        
        nombre=self.request.get('nombre')
        diccionario={'Agronomia':Agronomia,
                    'AgronomiaDecanato':AgronomiaDecanato,
                    'AgronomiaGalera':AgronomiaGalera,
                    'AgronomiaQuimica':AgronomiaQuimica,
                    'AuditoriumMarmol':AuditoriumMarmol,
                    'Cafetines':Cafetines,
                    'ComedorUES':ComedorUES,
                    'Derecho':Derecho,
                    'Economia1':Economia1,
                    'Economia2':Economia2,
                    'Economia3':Economia3,
                    'Economia4':Economia4,
                    'Economia6':Economia6,
                    'Humanidades2':Humanidades2,
                    'Humanidades3':Humanidades3,
                    'Humanidades4':Humanidades4,
                    'MecanicaComplejo':MecanicaComplejo,
                    'Medicina':Medicina,
                    'Odontologia1':Odontologia1,
                    'Odontologia2':Odontologia2,
                    'Odontologia3':Odontologia3,
                    'OdontologiaImprenta':OdontologiaImprenta,
                    'Periodismo':Periodismo,
                    'PrimarioFIA':PrimarioFIA,
                    'Psicologia':Psicologia,
                    'Quimica':Quimica,
                    'QuimicaImprenta':QuimicaImprenta}
        #crea un objeto dependiendo del tipo seleccionado en la pagina
        if nombre in diccionario:
            self.Db_entity=diccionario[nombre]()
        self.Db_entity
        fecha = self.Db_entity.all().order('-fecha_hora').get()        
        self.render('registro.html',
            fecha=fecha.fecha_hora)

#Confirma que la fila enviada a la web ha sido subida exitosamente
class Hecho(BlogHandler):
    def get(self):
        self.render('done.html')        

#se escriben los nuevos campos en la base de datos Datastore
class Registro(BlogHandler):

    def post(self):
        nombre=self.request.get('nombre')
        fecha_hora=datetime.datetime.strptime(self.request.get('fecha_hora'),"%Y-%m-%d %H:%M:%S")       
        energia_activa=int(self.request.get('energia_activa'))
        energia_aparente=int(self.request.get('energia_aparente'))
        demanda=float(self.request.get('demanda'))

        diccionario={'Agronomia':Agronomia,
                    'AgronomiaDecanato':AgronomiaDecanato,
                    'AgronomiaGalera':AgronomiaGalera,
                    'AgronomiaQuimica':AgronomiaQuimica,
                    'AuditoriumMarmol':AuditoriumMarmol,
                    'Cafetines':Cafetines,
                    'ComedorUES':ComedorUES,
                    'Derecho':Derecho,
                    'Economia1':Economia1,
                    'Economia2':Economia2,
                    'Economia3':Economia3,
                    'Economia4':Economia4,
                    'Economia6':Economia6,
                    'Humanidades2':Humanidades2,
                    'Humanidades3':Humanidades3,
                    'Humanidades4':Humanidades4,
                    'MecanicaComplejo':MecanicaComplejo,
                    'Medicina':Medicina,
                    'Odontologia1':Odontologia1,
                    'Odontologia2':Odontologia2,
                    'Odontologia3':Odontologia3,
                    'OdontologiaImprenta':OdontologiaImprenta,
                    'Periodismo':Periodismo,
                    'PrimarioFIA':PrimarioFIA,
                    'Psicologia':Psicologia,
                    'Quimica':Quimica,
                    'QuimicaImprenta':QuimicaImprenta}

        #crea un objeto dependiendo del tipo seleccionado en la pagina
        if nombre in diccionario:
            self.Db_entity=diccionario[nombre]()
            #Con el objeto creado se procede a hacer uso de sus atributos
            medidor = self.Db_entity.registro(fecha_hora,energia_activa,energia_aparente,demanda)
            medidor.put()
            self.redirect('/hecho')
        else:
            #aun falta crear la pagina web para esto
            self.error(404)
            return
        

class Home(BlogHandler):
    #decidi generar los dropdowns desde python, como para ejemplo del uso de jinja
    Medidor=namedtuple('Medidor',['valor','etiqueta'])    
    dropdown_medidores = [Medidor('Agronomia', 'Agronomia'),
            Medidor('AgronomiaDecanato','Agronomia Decanato'),
            Medidor('AgronomiaGalera','Agronomia Galera'),
            Medidor('AgronomiaQuimica','Agronomia Quimica'),
            Medidor('AuditoriumMarmol','Auditorium Marmol'),
            Medidor('Cafetines','Cafetines'),
            Medidor('ComedorUES','Comedor UES'),
            Medidor('Derecho','Derecho'),
            Medidor('Economia1','Economia 1'),
            Medidor('Economia2','Economia 2'),
            Medidor('Economia3','Economia 3'),
            Medidor('Economia4','Economia 4'),
            Medidor('Economia6','Economia 6'),
            Medidor('Humanidades2','Humanidades 2'),
            Medidor('Humanidades3','Humanidades 3'),
            Medidor('Humanidades4','Humanidades 4'),
            Medidor('MecanicaComplejo','Mecanica Complejo'),
            Medidor('Medicina','Medicina'),
            Medidor('Odontologia1','Odontologia 1'),
            Medidor('Odontologia2','Odontologia 2'),
            Medidor('Odontologia3','Odontologia 3'),
            Medidor('OdontologiaImprenta','Odontologia Imprenta'),
            Medidor('Periodismo','Periodismo'),
            Medidor('PrimarioFIA','Primario FIA'),
            Medidor('Psicologia','Psicologia'),
            Medidor('Quimica','Quimica'),
            Medidor('QuimicaImprenta','Quimica Imprenta')]

    def funcion_filtro(self,nombre,desde,hasta):
        self.diccionario={'Agronomia':Agronomia,'AgronomiaDecanato':AgronomiaDecanato,
                    'AgronomiaGalera':AgronomiaGalera,
                    'AgronomiaQuimica':AgronomiaQuimica,
                    'AuditoriumMarmol':AuditoriumMarmol,
                    'Cafetines':Cafetines,
                    'ComedorUES':ComedorUES,
                    'Derecho':Derecho,
                    'Economia1':Economia1,
                    'Economia2':Economia2,
                    'Economia3':Economia3,
                    'Economia4':Economia4,
                    'Economia6':Economia6,
                    'Humanidades2':Humanidades2,
                    'Humanidades3':Humanidades3,
                    'Humanidades4':Humanidades4,
                    'MecanicaComplejo':MecanicaComplejo,
                    'Medicina':Medicina,
                    'Odontologia1':Odontologia1,
                    'Odontologia2':Odontologia2,
                    'Odontologia3':Odontologia3,
                    'OdontologiaImprenta':OdontologiaImprenta,
                    'Periodismo':Periodismo,
                    'PrimarioFIA':PrimarioFIA,
                    'Psicologia':Psicologia,
                    'Quimica':Quimica,
                    'QuimicaImprenta':QuimicaImprenta}
        
        #crea un objeto dependiendo del tipo seleccionado en la pagina
        if nombre in self.diccionario:
            self.Db_entity=self.diccionario[nombre]()            
        
        #Con el objeto creado se procede a hacer uso de sus atributos
        return self.Db_entity.filtro(desde,hasta)

    def get(self):        
        desde_default=(datetime.datetime.now()-datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        #se restan 6 horas a la fecha actual debido a que se tomara la hora local del servidor de
        #appengine, que esta 6 horas adelantado.
        fecha_hoy=(datetime.datetime.now()-datetime.timedelta(hours=6)).strftime("%Y-%m-%d")

        self.render('home.html',
            dropdown_medidores=self.dropdown_medidores,
            desde=desde_default,
            hasta=fecha_hoy,
            )

    def post(self):
        #se envia el tamanio del navegador para mostrar la grafica ajustadamente.       
        self.width=self.request.get('width')
        self.height=self.request.get('height')        
        self.nombre=self.request.get('nombre')
        self.desde=datetime.datetime.strptime(self.request.get('desde'),"%Y-%m-%d")       
        self.hasta=datetime.datetime.strptime(self.request.get('hasta'),"%Y-%m-%d")
        #agrega un dia al rango maximo porque sino habria un faltante en las horas de ese dia, pero internamente, no en el frontpage.
        self.hasta_interno=self.hasta+datetime.timedelta(days=1)
        
        periodo="Periodo graficado desde el "+self.desde.strftime("%d %b %Y")+" al "+self.hasta.strftime("%d %b %Y")

        #realiza la peticion del rango solicitado
        if self.desde > self.hasta:
            json={}
            json['error']=' Error en el intervalo solicitado, revise las fechas'                
        elif (self.hasta-self.desde).days > 31:
            json={}
            json['error']=' Intervalo mayor a 31 dias no esta permitido'
        else:
            json=self.funcion_filtro(self.nombre,self.desde,self.hasta_interno)
            if json is None:
                json={}
                json['error']=' Este Intervalo no tiene datos, por favor solicite otro rango de dias'
            else:                
                json['error']='' #sin errores



        self.render('home.html',
            grafico_width=self.width,
            grafico_height=self.height,
            dropdown_medidores=self.dropdown_medidores,
            seleccion1=self.nombre,
            periodo=periodo,
            desde=self.desde.strftime("%Y-%m-%d"),
            hasta=self.hasta.strftime("%Y-%m-%d"),
            **json)


app = webapp2.WSGIApplication([('/', Home),
                               ('/consulta', Consulta),
                               ('/registro', Registro),
                               ('/hecho', Hecho)
                               ],
                              debug=True)
