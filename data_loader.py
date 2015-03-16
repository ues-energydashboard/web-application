import datetime
from google.appengine.ext import db
from google.appengine.tools import bulkloader
import tesisduque

class DataLoader(bulkloader.Loader):
    def __init__(self):
        bulkloader.Loader.__init__(self, 'Derecho',                                   
                                   [('fecha_hora',
                                     lambda x: datetime.datetime.strptime(x, '%Y-%m-%d %H:%M:%S')),
                                    ('va', float),
                                    ('vb', float),
                                    ('vc', float),
                                    ('ia', float),
                                    ('ib', float),
                                    ('ic', float),                                    
                                    ('FP', float),
                                    ('Ineutro', float),
                                    ('potencia', float),
                                    ('energia', float),
                                    ('demanda', float),
                                   ])

loaders = [DataLoader]
