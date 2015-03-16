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
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Agronomia WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' KWh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Agronomia(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class AgronomiaDecanato(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM AgronomiaDecanato WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' KWh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return AgronomiaDecanato(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class AgronomiaGalera(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM AgronomiaGalera WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return AgronomiaGalera(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class AgronomiaQuimica(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM AgronomiaQuimica WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return AgronomiaQuimica(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Artes(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Artes WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 200s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Artes(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class AuditoriumMarmol(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM AuditoriumMarmol WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return AuditoriumMarmol(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Cafetines(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Cafetines WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Cafetines(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class ComedorUES(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM ComedorUES WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return ComedorUES(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Derecho(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Derecho WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 200s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Derecho(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Economia1(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Economia1 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Economia1(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Economia2(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Economia2 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Economia2(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Economia3(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Economia3 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Economia3(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Economia4(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Economia4 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Economia4(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Economia5(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Economia5 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 200s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Economia5(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Economia6(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Economia6 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Economia6(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Humanidades1(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Humanidades1 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Humanidades1(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Humanidades2(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Humanidades2 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Humanidades2(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Humanidades3(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Humanidades3 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Humanidades3(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Humanidades4(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Humanidades4 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 200s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Humanidades4(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class MecanicaComplejo(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM MecanicaComplejo WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return MecanicaComplejo(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Medicina(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Medicina WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 200s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Medicina(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Odontologia1(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Odontologia1 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 200s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Odontologia1(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Odontologia2(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Odontologia2 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 200s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Odontologia2(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Odontologia3(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Odontologia3 WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 200s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Odontologia3(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class OdontologiaImprenta(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM OdontologiaImprenta WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return OdontologiaImprenta(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Periodismo(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Periodismo WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Periodismo(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class PrimarioFIA(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM PrimarioFIA WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 200s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return PrimarioFIA(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Psicologia(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Psicologia WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s v4')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Psicologia(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Quimica(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Quimica WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 200s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Quimica(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class QuimicaImprenta(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM QuimicaImprenta WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 100s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return QuimicaImprenta(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Rectoria(db.Model):
    fecha_hora=db.DateTimeProperty()    
    va=db.FloatProperty()
    vb=db.FloatProperty()
    vc=db.FloatProperty()
    ia=db.FloatProperty()
    ib=db.FloatProperty()
    ic=db.FloatProperty()
    FP=db.FloatProperty()
    Ineutro=db.FloatProperty()
    potencia=db.FloatProperty()
    energia=db.FloatProperty()
    demanda=db.FloatProperty()

    @classmethod
    def filtro(cls,fecha_inicial,fecha_final):
        dt=db.GqlQuery('SELECT * FROM Rectoria WHERE fecha_hora > :1 AND fecha_hora < :2',fecha_inicial,fecha_final)

        diccionario={ 0:'va', 1:'vb', 2:'vc', 3:'ia', 4:'ib', 5:'ic', 6:'FP', 7:'Ineutro', 8:'potencia'}
        array_data=[]
        for variable in diccionario:
            array_variable=[(fila.fecha_hora,getattr(fila,diccionario[variable])) for fila in dt]

        
            #gviz_api an open-sourced Python library that creates DataTable objects 
            #for consumption by visualizations(Google Chart Tools). 
            #This library can be used to create a DataTable in Python, 
            #and output it in any of three formats: JSON string, JSON response or JavaScript string
            
            description=[("Fecha","datetime"),(diccionario[variable],"number")]
            data_table=gviz_api.DataTable(description)
            data_table.LoadData(array_variable)
            #I experiemented that it is faster to short the columns here than in the database
            json=data_table.ToJSon(columns_order=("Fecha",diccionario[variable]),order_by="Fecha")
            tupla=(diccionario[variable],json)
            array_data.append(tupla)
        array_energia=[ fila.energia for fila in dt]
        #print len(array_energia)
        if len(array_energia)==0:
            energia_consumida=0
        else:            
            energia_consumida=(array_energia[-1] - array_energia[0])

        array_demanda=[ fila.demanda for fila in dt]
        if len(array_demanda)==0:
            demanda_maxima=0
        else:            
            demanda_maxima=max(array_demanda)/1000

        tupla_energia=('energia','Total energia consumida: '+str(energia_consumida)+' Kwh')
        tupla_demanda=('demanda','Demanda maxima: '+str(demanda_maxima)+' KWatts')
        info_medidor=('medidor','Medidor: Shark 200s')
        info_subestacion=('substacion','Subestacion: ')
        array_data.extend([tupla_energia,tupla_demanda,info_medidor,info_subestacion])
        #dict(array_data) convierte array_data en un diccionario con las variables y sus objetos
        #DataTable correspondientes para usarlo facilmente en jinja2
        return dict(array_data)

    @classmethod
    def registro(self, fecha_hora, va, vb, vc, ia, ib, ic, FP, Ineutro, potencia, energia, demanda):
        return Rectoria(fecha_hora=fecha_hora,
                            va=va,
                            vb=va,
                            vc=vc,
                            ia=ia,
                            ib=ib,
                            ic=ic,
                            FP=FP,
                            Ineutro=Ineutro,
                            potencia=potencia,
                            energia=energia,
                            demanda=demanda)

class Consulta(BlogHandler):

    def post(self):        
        nombre=self.request.get('nombre')
        diccionario={'Agronomia':Agronomia,'AgronomiaDecanato':AgronomiaDecanato,
                    'AgronomiaGalera':AgronomiaGalera,
                    'AgronomiaQuimica':AgronomiaQuimica,
                    'Artes':Artes,
                    'AuditoriumMarmol':AuditoriumMarmol,
                    'Cafetines':Cafetines,
                    'ComedorUES':ComedorUES,
                    'Derecho':Derecho,
                    'Economia1':Economia1,
                    'Economia2':Economia2,
                    'Economia3':Economia3,
                    'Economia4':Economia4,
                    'Economia5':Economia5,
                    'Economia6':Economia6,
                    'Humanidades1':Humanidades1,
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
                    'QuimicaImprenta':QuimicaImprenta,
                    'Rectoria':Rectoria}
        #crea un objeto dependiendo del tipo seleccionado en la pagina
        if nombre in diccionario:
            self.Db_entity=diccionario[nombre]()
        self.Db_entity
        fecha = self.Db_entity.all().order('-fecha_hora').get()        
        self.render('registro.html',
            fecha=fecha.fecha_hora)

class Hecho(BlogHandler):
    def get(self):
        self.render('done.html')        

class Registro(BlogHandler):

    def post(self):
        nombre=self.request.get('nombre')
        fecha_hora=datetime.datetime.strptime(
            self.request.get('fecha_hora'),"%Y-%m-%d %H:%M:%S")       
        va=float(self.request.get('va'))
        vb=float(self.request.get('vb'))
        vc=float(self.request.get('vc'))        
        ia=float(self.request.get('ia'))
        ib=float(self.request.get('ib'))
        ic=float(self.request.get('ic'))        
        FP=float(self.request.get('FP'))
        Ineutro=float(self.request.get('Ineutro'))
        potencia=float(self.request.get('potencia'))
        energia=float(self.request.get('energia'))
        demanda=float(self.request.get('demanda'))

        diccionario={'Agronomia':Agronomia,
                    'AgronomiaDecanato':AgronomiaDecanato,
                    'AgronomiaGalera':AgronomiaGalera,
                    'AgronomiaQuimica':AgronomiaQuimica,
                    'Artes':Artes,
                    'AuditoriumMarmol':AuditoriumMarmol,
                    'Cafetines':Cafetines,
                    'ComedorUES':ComedorUES,
                    'Derecho':Derecho,
                    'Economia1':Economia1,
                    'Economia2':Economia2,
                    'Economia3':Economia3,
                    'Economia4':Economia4,
                    'Economia5':Economia5,
                    'Economia6':Economia6,
                    'Humanidades1':Humanidades1,
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
                    'QuimicaImprenta':QuimicaImprenta,
                    'Rectoria':Rectoria}

        #crea un objeto dependiendo del tipo seleccionado en la pagina
        if nombre in diccionario:
            self.Db_entity=diccionario[nombre]()
            #Con el objeto creado se procede a hacer uso de sus atributos
            medidor = self.Db_entity.registro(fecha_hora,va,vb,vc,ia,ib,ic,FP,Ineutro,potencia,energia,demanda)
            medidor.put()
            self.redirect('/hecho')
        else:
            self.error(404)
            return
        

class Home(BlogHandler):
    Medidor=namedtuple('Medidor',['valor','etiqueta'])

    html_select = [Medidor('Agronomia', 'Agronomia'),
            Medidor('AgronomiaDecanato','Agronomia Decanato'),
            Medidor('AgronomiaGalera','Agronomia Galera'),
            Medidor('AgronomiaQuimica','Agronomia Quimica'),
            Medidor('Artes','Artes'),
            Medidor('AuditoriumMarmol','Auditorium Marmol'),
            Medidor('Cafetines','Cafetines'),
            Medidor('ComedorUES','Comedor UES'),
            Medidor('Derecho','Derecho'),
            Medidor('Economia1','Economia 1'),
            Medidor('Economia2','Economia 2'),
            Medidor('Economia3','Economia 3'),
            Medidor('Economia4','Economia 4'),
            Medidor('Economia5','Economia 5'),
            Medidor('Economia6','Economia 6'),
            Medidor('Humanidades1','Humanidades 1'),
            Medidor('Humanidades2','Humanidades 2'),
            Medidor('Humanidades3','Humanidades 3'),
            Medidor('Humanidades4','Humanidades 4'),
            Medidor('MecanicaComplejo','Mecanica Complejo'),
            Medidor('Medicina','Medicina'),
            Medidor('Odontologia1','Odontologia 1'),
            Medidor('Odontologia2','Odontologia 2'),
            Medidor('Odontologia3','Odontologia 3'),
            Medidor('Odontologiaimprenta','Odontologia Imprenta'),
            Medidor('Periodismo','Periodismo'),
            Medidor('PrimarioFIA','Primario FIA'),
            Medidor('Psicologia','Psicologia'),
            Medidor('Quimica','Quimica'),
            Medidor('QuimicaImprenta','Quimica Imprenta'),
            Medidor('Rectoria','Rectoria')]

    Item=namedtuple('Item',['valor','etiqueta'])
    html_variable = [Item('va','Voltaje Fase A'),
                    Item('vb','Voltaje Fase B'),
                    Item('vc','Voltaje Fase C'),
                    Item('ia','Corriente A'),
                    Item('ib','Corriente B'),
                    Item('ic','Corriente C'),
                    Item('P','Potencia Trifasico'),
                    Item('FP','Factor de Potencia Trifasico'),
                    Item('Ineutro','Corriente de Neutro')]

    def funcion_filtro(self,nombre,fecha_inicial,fecha_final):
        self.diccionario={'Agronomia':Agronomia,'AgronomiaDecanato':AgronomiaDecanato,
                    'AgronomiaGalera':AgronomiaGalera,
                    'AgronomiaQuimica':AgronomiaQuimica,
                    'Artes':Artes,
                    'AuditoriumMarmol':AuditoriumMarmol,
                    'Cafetines':Cafetines,
                    'ComedorUES':ComedorUES,
                    'Derecho':Derecho,
                    'Economia1':Economia1,
                    'Economia2':Economia2,
                    'Economia3':Economia3,
                    'Economia4':Economia4,
                    'Economia5':Economia5,
                    'Economia6':Economia6,
                    'Humanidades1':Humanidades1,
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
                    'QuimicaImprenta':QuimicaImprenta,
                    'Rectoria':Rectoria}
        
        #crea un objeto dependiendo del tipo seleccionado en la pagina
        if nombre in self.diccionario:
            self.Db_entity=self.diccionario[nombre]()            
        
        #Con el objeto creado se procede a hacer uso de sus atributos
        return self.Db_entity.filtro(fecha_inicial,fecha_final)

    def tab_position(self,variable):
        diccionario={'va':0, 'vb':1, 'vc':2, 'ia':3, 'ib':4, 'ic':5, 'P':6, 'FP':7, 'Ineutro':8}
        return diccionario[variable]

    def get(self):        
        fecha_inicial_default=datetime.datetime.now()-datetime.timedelta(days=8)
        fecha_hoy=datetime.datetime.now().strftime("%Y-%m-%d")


        self.render('home.html',
            select1=self.html_select,
            select2=self.html_variable,
            tab=self.tab_position('va'),
            fecha_inicial=fecha_inicial_default.strftime("%Y-%m-%d"),
            fecha_final=fecha_hoy)

    def post(self):        
        self.width=self.request.get('width')
        self.height=self.request.get('height')        
        self.nombre=self.request.get('nombre')
        self.variable=self.request.get('variable')
        self.fecha_inicial=datetime.datetime.strptime(
            self.request.get('fecha_inicial'),"%Y-%m-%d")
        self.fecha_final=datetime.datetime.strptime(
            self.request.get('fecha_final'),"%Y-%m-%d")
        #agrega un dia al rango maximo porque sino habria un faltante en las horas de ese dia, pero internamente, no en el frontpage.
        self.fecha_final_interno=self.fecha_final
        self.fecha_final_interno+=datetime.timedelta(days=1)
        
        periodo="Periodo graficado desde el "+self.fecha_inicial.strftime("%d %b %Y")+" al "+self.fecha_final.strftime("%d %b %Y")
        #print("%s" % periodo)
        #print("%s" % self.variable)
        if self.fecha_inicial < self.fecha_final:                    
            json=self.funcion_filtro(self.nombre,self.fecha_inicial,self.fecha_final_interno)
            json['error']=''
        else:
            json={}
            json['error']='Error en el rango solicitado'

        self.render('home.html',
            grafico_width=self.width,
            select1=self.html_select,
            select2=self.html_variable, 
            seleccion1=self.nombre, 
            seleccion2=self.variable,
            tab=self.tab_position(self.variable),
            periodo=periodo,
            fecha_inicial=self.fecha_inicial.strftime("%Y-%m-%d"),
            fecha_final=self.fecha_final.strftime("%Y-%m-%d"),
            **json)

class Index(BlogHandler):
    def get(self):
        self.render('index.html')

        

app = webapp2.WSGIApplication([('/', Index),
                               ('/home', Home),
                               ('/consulta', Consulta),
                               ('/registro', Registro),
                               ('/hecho', Hecho)
                               ],
                              debug=True)
