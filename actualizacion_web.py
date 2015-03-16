#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, sys

import MySQLdb
import datetime
import urllib



class DB(object):
  def getData(self, medidor, ultimo_dato):
    self.db  = MySQLdb.connect(host="localhost",user="user",passwd="password",db="database")
    self.cur = self.db.cursor()
    #Sql Espcial para agronomia porque esta en delta
    if medidor=='Agronomia':
        sql = "SELECT Fecha_hora, Vab, Vbc, Vca, Ia, Ib, Ic, P, FP, WhTot, Pos_Watts_3ph_Av FROM %s where Fecha_hora > '%s'" %(medidor,ultimo_dato)
        self.cur.execute(sql)
        tuplas=self.cur.fetchall()
        array_data=[]
        for variable in tuplas:
            array_diccionario={}
            array_diccionario['fecha_hora']=variable[0].strftime("%Y-%m-%d %H:%M:%S")
            array_diccionario['va']=variable[1]
            array_diccionario['vb']=variable[2]
            array_diccionario['vc']=variable[3]
            array_diccionario['ia']=variable[4]
            array_diccionario['ib']=variable[5]
            array_diccionario['ic']=variable[6]
            array_diccionario['potencia']=variable[7]
            array_diccionario['Ineutro']=0
            array_diccionario['FP']=variable[8]
            array_diccionario['energia']=variable[9]
            array_diccionario['demanda']=variable[10]
            array_diccionario['nombre']=medidor
            array_data.append(array_diccionario)
        return array_data
    else:       
        sql = "SELECT Fecha_hora, Va, Vb, Vc, Ia, Ib, Ic, P, Ineutro, FP, WhTot, Pos_Watts_3ph_Av FROM %s where Fecha_hora > '%s'" %(medidor, ultimo_dato)
        self.cur.execute(sql)
        tuplas=self.cur.fetchall()
        array_data=[]
        for variable in tuplas:
            array_diccionario={}
            array_diccionario['fecha_hora']=variable[0].strftime("%Y-%m-%d %H:%M:%S")
            array_diccionario['va']=variable[1]
            array_diccionario['vb']=variable[2]
            array_diccionario['vc']=variable[3]
            array_diccionario['ia']=variable[4]
            array_diccionario['ib']=variable[5]
            array_diccionario['ic']=variable[6]
            array_diccionario['potencia']=variable[7]
            array_diccionario['Ineutro']=variable[8]
            array_diccionario['FP']=variable[9]
            array_diccionario['energia']=variable[10]
            array_diccionario['demanda']=variable[11]
            array_diccionario['nombre']=medidor
            array_data.append(array_diccionario)
        return array_data

diccionario={0:'Agronomia',
                    1:'AgronomiaDecanato',
                    2:'AgronomiaGalera',
                    3:'AgronomiaQuimica',
                    4:'Artes',
                    5:'AuditoriumMarmol',
                    6:'Cafetines',
                    7:'ComedorUES',
                    8:'Derecho',
                    9:'Economia1',
                    10:'Economia2',
                    11:'Economia3',
                    12:'Economia4',
                    13:'Economia5',
                    14:'Economia6',
                    15:'Humanidades1',
                    16:'Humanidades2',
                    17:'Humanidades3',
                    18:'Humanidades4',
                    19:'MecanicaComplejo',
                    20:'Medicina',
                    21:'Odontologia1',
                    22:'Odontologia2',
                    23:'Odontologia3',
                    24:'OdontologiaImprenta',
                    25:'Periodismo',
                    26:'PrimarioFIA',
                    27:'Psicologia',
                    28:'Quimica',
                    29:'QuimicaImprenta',
                    30:'Rectoria'}

for medidor in diccionario:
    nombre=diccionario[medidor]
    params=urllib.urlencode({'nombre':nombre})
    #POST method of urlib
    f=urllib.urlopen("http://ues-energydashboard.appspot.com/consulta",params)
    ultimo_dato=f.read()
    print 'Ultimo dato en %s, %s' % (nombre, ultimo_dato)
    #cantidad de caracteres que contiene una fecha correcta: 19
    if len(ultimo_dato)==19:
        contenedor=DB()
        array_data=contenedor.getData(nombre,ultimo_dato)
        for datos in array_data:
            print datos
            paquete=urllib.urlencode(datos)
            envio=urllib.urlopen("http://ues-energydashboard.appspot.com/registro",paquete)
            if envio.read()!= 'Done':                
                print "La fila con fecha %s no se subió al servidor" %(datos['fecha_hora'])
                sys.exit()
    else:
        print "La aplicacion no respondio o puede ser que la base de datos este vacia"






