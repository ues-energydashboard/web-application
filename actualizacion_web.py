#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, sys

import MySQLdb
import datetime
import urllib



class DB(object):
  def getData(self, medidor, ultimo_dato):
    self.db  = MySQLdb.connect(host="localhost",user="root",passwd="proyecto12",db="MedidoresV2")
    self.cur = self.db.cursor()       
    sql = "SELECT fecha_hora,WhTot,VAhTot,Pos_Watts_3ph_Av FROM %s where Fecha_hora > '%s'" %(medidor, ultimo_dato)
    self.cur.execute(sql)
    tuplas=self.cur.fetchall()
    array_data=[]
    for variable in tuplas:
        array_diccionario={}
        array_diccionario['nombre']=medidor
        array_diccionario['fecha_hora']=variable[0].strftime("%Y-%m-%d %H:%M:%S")
        array_diccionario['energia_activa']=variable[1]
        array_diccionario['energia_aparente']=variable[2]
        array_diccionario['demanda']=variable[3]
        array_data.append(array_diccionario)
    return array_data

diccionario={0:'Agronomia',
                    1:'AgronomiaDecanato',
                    2:'AgronomiaGalera',
                    3:'AgronomiaQuimica',
                    4:'AuditoriumMarmol',
                    5:'Cafetines',
                    6:'ComedorUES',
                    7:'Derecho',
                    8:'Economia1',
                    9:'Economia2',
                    10:'Economia3',
                    11:'Economia4',
                    12:'Economia6',
                    13:'Humanidades2',
                    14:'Humanidades3',
                    15:'Humanidades4',
                    16:'MecanicaComplejo',
                    17:'Medicina',
                    18:'Odontologia1',
                    19:'Odontologia2',
                    20:'Odontologia3',
                    21:'OdontologiaImprenta',
                    22:'Periodismo',
                    23:'PrimarioFIA',
                    24:'Psicologia',
                    25:'Quimica',
                    26:'QuimicaImprenta'}

def actualizacion():
    for medidor in diccionario:
        nombre=diccionario[medidor]
        params=urllib.urlencode({'nombre':nombre})
        #POST method of urlib
        f=urllib.urlopen("http://ues.miconsumodeenergia.com/consulta",params)
        ultimo_dato=f.read()
        print 'Ultimo dato en %s, %s' % (nombre, ultimo_dato)
        #cantidad de caracteres que contiene una fecha correcta: 19
        if len(ultimo_dato)==19:
            contenedor=DB()
            array_data=contenedor.getData(nombre,ultimo_dato)
            for datos in array_data:
                print datos
                paquete=urllib.urlencode(datos)
                envio=urllib.urlopen("http://ues.miconsumodeenergia.com/registro",paquete)
                if envio.read()!= 'Done':                
                    print "La fila con fecha %s no se subió al servidor" %(datos['fecha_hora'])
                    return
        else:
            print "La aplicacion no respondio o puede ser que la base de datos este vacia"
            return

actualizacion()