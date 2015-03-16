#!/bin/bash

intentos=10
python /home/duque/tesisduque/actualizacion_web.py
#si no retorna 0, que se vuelva a mandar
for ((n=1; n<$intentos; n++))
  do
  	if [ $? -ne 0 ]
  		then
  			sleep 5m 
    		python /home/duque/tesisduque/actualizacion_web.py
		fi
  done
