#To be able to read csv formated files, we will first have to import the
#csv module.
import csv

with open('MecanicaComplejo.csv','rb') as infile:
    reader = csv.reader(infile)
    nombre=['mecanicacomplejo']
    tipo=['shark100s']
    data=[ nombre+tipo+row for row in reader ]

with open('MecanicaComplejo2.csv','wb') as outfile:
    writer = csv.writer(outfile, quotechar='"', quoting=csv.QUOTE_ALL)
    writer.writerows(data)

infile.close()
outfile.close()
        