import csv
import tkinter, os, subprocess
import math
from datetime import date

from tkcalendar import Calendar

import matplotlib

from textwrap import wrap
from plotly.utils import numpy
from matplotlib.widgets import RectangleSelector
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk import word_tokenize
from nltk.corpus import stopwords
from time import sleep
import tkinter as tk

matplotlib.use("TkAgg")

import matplotlib.pyplot as plt
from pathlib import Path
from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from tkinter.messagebox import showinfo
from dateutil import parser
from pymongo import MongoClient


class showGUI(tkinter.Tk):
    def __init__(self, mainDB, appName):
        tkinter.Tk.__init__(self)

        # --- MONGO ---
        client = MongoClient()
        self.mainDB = client[mainDB]
        self.tweet = None

        # --- INTERFAZ ---
        self.title(appName)  # nombre que aparece en la ventana
        self.resizable(width=False, height=False)

        stepOne = tk.LabelFrame(self, text=" 1. Importar colección ")
        stepOne.grid(row=0, column=6, sticky='W', padx=5, pady=5, ipadx=5, ipady=5)

        stepTwo = tk.LabelFrame(self, text=" 2. Generar gráfica ")
        stepTwo.grid(row=1, column=6, sticky='W', padx=5, pady=5, ipadx=5, ipady=5)

        stepThree = tk.LabelFrame(self, text=" Borrar colección ")
        stepThree.grid(row=2, column=6, sticky='W', padx=5, pady=5, ipadx=5, ipady=5)

        # ETIQUETAS DE TEXTO
        Label(stepOne, text="Nombre de la colección").grid(row=1, column=0, sticky=E, padx=(35, 20))
        Label(stepOne, text="Nombre del campo de Tweet").grid(row=2, column=0, sticky=E, padx=(35, 20))
        Label(stepOne, text="Nombre del campo de Fecha").grid(row=3, column=0, sticky=E, padx=(35, 20))
        Label(stepTwo, text="Colección").grid(row=13, column=0, sticky=E)
        Label(stepTwo, text="Idioma").grid(row=13, column=1, sticky=W, padx=(215, 0))
        Label(stepTwo, text="Inicio del evento (dd/mm/aaaa - hh:mm:ss)").grid(row=9, column=0, sticky=E, padx=(35, 20))
        Label(stepTwo, text="Fin del evento (dd/mm/aaaa - hh:mm:ss)").grid(row=10, column=0, sticky=E, padx=(35, 20))
        Label(stepTwo, text="Número de puntos").grid(row=11, column=0, sticky=E, padx=(40, 20))
        Label(stepTwo, text="Número de picos").grid(row=12, column=0, sticky=E, padx=(40, 20), pady=(0, 30))
        Label(stepThree, text="Colección").grid(row=14, column=0, padx=(255, 0))
        self.barLabel = Label(stepOne, text='')
        self.barLabel.grid(row=5, column=0, columnspan=3, pady=(15, 15), padx=(590, 0))

        # ENTRADAS DE TEXTO
        self.collName = Entry(stepOne, width = 15)
        self.collName.grid(row=1, column=1, sticky=W)

        self.tweetText = Entry(stepOne, width = 15)
        self.tweetText.grid(row=2, column=1, sticky=W)

        self.dateField = Entry(stepOne, width = 15)
        self.dateField.grid(row=3, column=1, sticky=W)

        self.pathField = Entry(stepOne, width = 65)
        self.pathField.grid(row=4, column=1, sticky=W)

        self.initDate = Entry(stepTwo, width = 10, state=DISABLED, disabledforeground='black')
        self.initDate.grid(row=9, column=1, sticky=W)

        self.initTime = Entry(stepTwo, width = 10)
        self.initTime.grid(row=9, column=1, sticky=W, padx=(170, 0))

        self.endDate = Entry(stepTwo, width = 10, state=DISABLED, disabledforeground='black')
        self.endDate.grid(row=10, column=1, sticky=W)

        self.endTime = Entry(stepTwo, width = 10)
        self.endTime.grid(row=10, column=1, sticky=W, padx=(170, 0))

        self.points = Entry(stepTwo, width = 3)
        self.points.grid(row=11, column=1, sticky=W)

        self.peaks = Entry(stepTwo, width=3)
        self.peaks.grid(row=12, column=1, sticky=W, pady=(0, 30))

        # BOTONES
        self.selectButton = tkinter.Button(stepOne, text='Seleccionar archivo', command=lambda: self.selectFile(), state=NORMAL)
        self.selectButton.grid(row=4, column=0, sticky=E, padx=(0,20))
        self.loadButton = tkinter.Button(stepOne, text='Cargar', command=lambda: self.loadFile(), state=NORMAL)
        self.loadButton.grid(row=4, column=2, sticky=W, padx=(23,0))
        self.cancelButton = tkinter.Button(stepOne, text='Cancelar', command=lambda: self.stopImport(), state=DISABLED)
        self.cancelButton.grid(row=6, columnspan=3, padx=(100, 200))
        self.cancelPressed = False
        tkinter.Button(stepThree, text='Borrar', command=lambda: self.removeColl(), state=NORMAL).grid(row=14, column=1, padx=(473, 0))
        tkinter.Button(stepTwo, text='Generar', command=lambda: self.loadFrecuencies(), state=NORMAL).grid(row=13, column=2, sticky=W, padx=(200, 0))
        tkinter.Button(stepTwo, text='+', command=lambda: self.openCal('inicio'), state=NORMAL).grid(row=9, column=1, padx=(0, 25))
        tkinter.Button(stepTwo, text='+', command=lambda: self.openCal('fin'), state=NORMAL).grid(row=10, column=1, padx=(0, 25))


        # BARRA DE PROGRESO
        self.traceBar = IntVar(stepOne)
        self.progressBar = ttk.Progressbar(stepOne, orient="horizontal", length=500, mode="determinate", variable=self.traceBar, maximum=100)
        self.progressBar.grid(row=5, column=0, columnspan=3, pady=(15, 15), padx=(100, 200))

        # HISTORIAL
        c = self.mainDB.collection_names()
        if 'history' not in c:
            self.mainDB.create_collection('history')
            self.mainDB['history'].insert({'_id':'backup', 'coll':'', 'tweet':'', 'date':'', 'path':'', 'points':'30', 'peaks':'10'})

        for row in self.mainDB['history'].aggregate([{'$project': {'_id': 0, 'coll': 1, 'tweet': 1, 'date': 1, 'path': 1, 'points': 1, 'peaks': 1}}]):
            self.collName.insert(0, row['coll'])
            self.tweetText.insert(0, row['tweet'])
            self.dateField.insert(0, row['date'])
            self.pathField.insert(0, row['path'])
            self.points.insert(0, int(row['points']))
            self.peaks.insert(0, int(row['peaks']))

        # DROP-DOWN
        self.traceCols = StringVar(self)
        self.traceFrecs = StringVar(self)
        self.traceLangs = StringVar(self)

        # creo un drop-down con los nombres de las colecciones originales
        cols = self.getColls("original", self.mainDB.collection_names())
        self.colsDrop = OptionMenu(stepThree, self.traceCols, *cols)
        self.colsDrop.grid(row=14, column=1, sticky=W)
        self.colsDrop.configure(width=15)
        aux = cols

        if cols[0] != '-':
            self.coll = self.mainDB[cols[0]]
            cols = self.getColls("frec", self.mainDB.collection_names())
            str = self.traceFrecs.get()
            self.collFrec = self.mainDB[str]
            self.collInfo = self.mainDB[str.replace('frec_', 'info_')]

            aux = list(self.collInfo.aggregate([{'$project': {'_id': 0, 'idioma': 1}}, {'$limit': 3}]))

        self.frecsDrop = OptionMenu(stepTwo, self.traceFrecs, *cols)
        self.traceFrecs.trace('w', self.dropChanges)
        self.frecsDrop.grid(row=13, column=1, sticky=W)
        self.frecsDrop.configure(width=20)

        self.langsDrop = OptionMenu(stepTwo, self.traceLangs, *aux)
        self.langsDrop.grid(row=13, column=2, sticky=W)
        self.langsDrop.configure(width=15)

        if self.getColls('original', self.mainDB.collection_names())[0] != '-':
            self.updWidgets(False)

        self.mainloop()

    def openCal(self, tipo):
        def setDate():
            strDate = str(cal.selection_get())[8:10] + "/" + str(cal.selection_get())[5:7] + "/" + str(cal.selection_get())[0:4]

            if tipo is 'inicio':
                self.initDate.configure(state=NORMAL)
                self.initDate.delete(0, 'end')
                self.initDate.insert(0, strDate)
                self.initDate.configure(state=DISABLED)
            else:
                self.endDate.configure(state=NORMAL)
                self.endDate.delete(0, 'end')
                self.endDate.insert(0, strDate)
                self.endDate.configure(state=DISABLED)
            top.destroy()

        top = tk.Toplevel(self)
        top.resizable(width=False, height=False)

        if tipo is 'inicio':
            top.title("Fecha inicial")
        else:
            top.title("Fecha final")

        cal = Calendar(top,
                       font="Arial 14", selectmode='day',
                       cursor="arrow", day=date.today().day, month=date.today().month, year=date.today().year)
        cal.pack(fill="both", expand=True)
        ttk.Button(top, text="OK", command=setDate).pack()

    # selecciona la coleccion del explorador de archivos (al pulsar Seleccionar)
    def selectFile(self):
        path = filedialog.askopenfilename(initialdir="/", title="Selecciona un archivo CSV/JSON", filetypes=(("CSV files", "*.csv"), ("JSON files", "*.json"), ("all files", "*.*")))

        self.pathField.delete(0, 'end')
        self.pathField.insert(0, path)


    # carga el archivo seleccionado a la base de datos (al pulsar Cargar)
    # guarda los parametros en el historial
    # inicia la barra de porgreso, prepara las fechas de los tweets, las frecuencias y los epochs
    # actualiza los widgets con los datos de la coleccion importada
    def loadFile(self):
        # muestra errores
        if len(self.collName.get()) == 0 or len(self.tweetText.get()) == 0 or len(self.dateField.get()) == 0:
            showinfo('No se pudo importar el archivo', '¡Debes completar todos los campos!')
        elif os.path.isfile(self.pathField.get()) == False or len(self.pathField.get()) == 0:
            showinfo('No se pudo importar el archivo', '¡Debes indicar una ruta valida!')
        elif (self.collName.get() in self.mainDB.collection_names()) == True:
            showinfo('Error al importar', "Ya existe una base de datos '" + self.collName.get() + "'")
        else:
            self.loadButton.configure(state=DISABLED)
            self.selectButton.configure(state=DISABLED)
            self.cancelButton.configure(state=NORMAL)
            self.cancelPressed = False

            # actualizo el historial
            self.mainDB['history'].update({'_id': 'backup'}, {'$set': {'coll': self.collName.get(), 'date': self.dateField.get(), 'tweet': self.tweetText.get(), 'path': self.pathField.get(), 'points': self.points.get(), 'peaks': self.peaks.get()}})

            # DESCOMENTAR ESTHER
            # os.chdir('C:/Program Files/MongoDB/Server/3.4/bin'); # NO BORRAR
            self.barLabel.configure(text='Preparando importación...', fg='blue')
            self.update()

            if Path(self.pathField.get()).suffix == '.csv':
                self.importPtrocess = subprocess.Popen(['mongoimport', '-d', 'tfg', '-c', self.collName.get(), '--type', 'csv', '--file', self.pathField.get(), '--headerline'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                file = open(self.pathField.get())
                rows = sum(1 for row in csv.reader(file, delimiter=','))
            elif Path(self.pathField.get()).suffix == '.json':
                self.importPtrocess = subprocess.Popen(['mongoimport', '-d', 'tfg', '-c', self.collName.get(), '--file', self.pathField.get()], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                rows = sum(1 for row in open(self.pathField.get()))

            self.coll = self.mainDB[self.collName.get()]

            # BARRA DE PROGRESO
            self.traceBar.set(0)
            self.progressBar.config(maximum=rows*3)

            var = self.coll.count()
            total = var
            self.barLabel.configure(text='Paso 1/3: importando', fg='blue')
            while self.coll.count() < rows and self.cancelPressed is False:
                self.progressBar.step(var)
                var = self.coll.count()-total
                total += var
                self.update()

            if self.cancelPressed is False:
                self.prepareDates()

            if self.cancelPressed is False:
                self.createFrecuencies()
                self.updWidgets(True)

                self.collFrec = self.mainDB['frec_' + self.collName.get()]
                self.epochI = self.collInfo.find_one({'initEpoch':{'$exists':1}})['initEpoch']
                self.epochF = self.collInfo.find_one({'endEpoch': {'$exists':1}})['endEpoch']

                self.getPoints()

                self.loadButton.configure(state=NORMAL)
                self.selectButton.configure(state=NORMAL)
                self.cancelButton.configure(state=DISABLED)

    # convierte fecha de String a ISO y añade epochs
    def prepareDates(self):
        var = self.coll.find_one()[self.dateField.get()]

        # comprueba el tipo de 'var', si es str lo convierte a ISO
        if type(var) is str:
            self.barLabel.config(text='Paso 2/3: convirtiendo a ISO', fg ='blue')
            i = 0
            for row in self.coll.find():
                if self.cancelPressed is True:
                    break
                isoDate = parser.parse(row[self.dateField.get()])
                self.coll.update_one({'_id': row['_id']}, {'$set': {self.dateField.get(): isoDate}})
                self.coll.update_one({'_id': row['_id']}, {'$set': {'epoch': self.toEpoch(isoDate.year, isoDate.month, isoDate.day, isoDate.hour, isoDate.minute, isoDate.second)}})
                if i%500 == 0:
                    self.progressBar.step(i)
                    self.update()
                    i = 0
                i += 1

        self.barLabel.config(text='Paso 3/3: añadiendo epoch', fg='blue')
        i = 0
        for row in self.coll.find():
            if self.cancelPressed is True:
                break
            isoDate = row[self.dateField.get()]
            self.coll.update_one({'_id': row['_id']}, {'$set': {
                'epoch': self.toEpoch(isoDate.year, isoDate.month, isoDate.day, isoDate.hour, isoDate.minute,
                                          isoDate.second)}})
            if i%500 == 0:
                self.progressBar.step(i)
                self.update()
                i = 0
            i += 1

        if self.cancelPressed is False:
            self.barLabel.config(text='Completado', fg="green")
            self.traceBar.set(self.progressBar.cget('maximum'))
            self.cancelButton.configure(state=DISABLED)

        self.update()

    # crea la colección de frecuencias
    def createFrecuencies(self):
        # creo la colección de frecuencias "frec_nombreColeccionOriginal"
        self.coll.aggregate([{'$group': {
            '_id': {'dia': {'$dayOfMonth': '$'+ self.dateField.get()},
                    'mes': {'$month': '$'+ self.dateField.get()},
                    'año': {'$year': '$'+ self.dateField.get()},
                    'hora': {'$hour': '$'+ self.dateField.get()},
                    'minuto': {'$minute': '$'+ self.dateField.get()},
                    'segundo': {'$second': '$' + self.dateField.get()}},
                    'total': {'$sum': 1}}},
                             {'$sort':{'_id.dia':1, '_id.mes':1, '_id.año':1, '_id.hora':1, '_id.minuto':1, '_id.segundo':1 }},
                             {'$out': 'frec_' + self.collName.get()}], allowDiskUse=True)
        sleep(1)
        self.collFrec = self.mainDB['frec_' + self.collName.get()]

        # añado los 3 idiomas mas usados y los guardo en info_coleccion
        self.coll.aggregate([{'$group':{'_id':'$lang', 'total':{'$sum':1}}}, {'$sort':{'total':-1}}, {'$limit':3}, {'$out': 'info_' + self.collName.get()}], allowDiskUse=True)
        sleep(1)

        self.collInfo = self.mainDB['info_' + self.collName.get()]
        for row in self.collInfo.find().limit(3):
            c = self.mainDB['idiomas'].find_one({'_id':row['_id']})
            self.collInfo.update({'_id':row['_id']},{'$set':{'idioma':c['idioma'], 'language': c['language']}})

        # convierte la fecha a segundos epoch (desde el 2000)
        for row in self.collFrec.find():
            epoch = self.toEpoch(int(row['_id']['año']), int(row['_id']['mes']), int(row['_id']['dia']), int(row['_id']['hora']), int(row['_id']['minuto']), int(row['_id']['segundo']))
            self.collFrec.update_one({'_id': row['_id']}, {'$set': {'epoch': epoch}})

        # acumulamos el total de tweets hasta cada epoch
        total = 0
        for row in self.collFrec.find():
            total += int(row['total'])
            self.collFrec.update_one({'_id': row['_id']}, {'$set': {'acumulado': total}})

        # añado dos documentos con las fechas de inicio y de fin del evento (en formato string y en epoch)
        c = self.collFrec.find_one()
        initDate, initTime, initEpoch = self.toStr(c, str(c['_id']['dia']), str(c['_id']['mes']), str(c['_id']['hora']), str(c['_id']['minuto']), str(c['_id']['segundo']))

        c = self.collFrec.find().sort('epoch', -1)
        endDate, endTime, endEpoch = self.toStr(c[0], str(c[0]['_id']['dia']), str(c[0]['_id']['mes']), str(c[0]['_id']['hora']), str(c[0]['_id']['minuto']), str(c[0]['_id']['segundo']))

        self.collInfo.insert([{"_id": "inits", "initDate": initDate, "initTime": initTime, "initEpoch": initEpoch}, {"_id": "ends","endDate": endDate, "endTime":endTime, "endEpoch": endEpoch}])


    def stopImport(self):
        self.cancelPressed = True
        self.importPtrocess.kill()

        self.mainDB[self.collName.get()].drop()
        self.mainDB['frec_' + self.collName.get()].drop()
        self.mainDB['info_' + self.collName.get()].drop()

        self.barLabel.configure(text='Cancelado', fg='red')
        self.traceBar.set(0)
        self.update()

        self.selectButton.configure(state=NORMAL)
        self.loadButton.configure(state=NORMAL)
        self.cancelButton.configure(state=DISABLED)

    # convert from iso to epoch since 2000th
    def toEpoch(self, y, m, d, h, min, s):
        return y - 2000 + (365 * 24 * 60 * 60) + (m * 30 * 24 * 60 * 60) + (d * 24 * 60 * 60) + (h * 60 * 60) + (min * 60) + s

    # convert iso format to string legible format
    def toStr(self, c, dia, mes, hora, minuto, segundo):
        if c['_id']['dia'] < 10:
            dia = '0' + str(c['_id']['dia'])
        if c['_id']['mes'] < 10:
            mes = '0' + str(c['_id']['mes'])
        if c['_id']['hora'] < 10:
            hora = '0' + str(c['_id']['hora'])
        if c['_id']['minuto'] < 10:
            minuto = '0' + str(c['_id']['minuto'])
        if c['_id']['segundo'] < 10:
            segundo = '0' + str(c['_id']['segundo'])

        date = dia + "/" + mes + "/" + str(c['_id']['año'])
        time = hora + ":" + minuto + ":" + segundo
        epoch = c['epoch']

        return date, time, epoch

    def loadFrecuencies(self):

        if int(self.peaks.get()) > int(self.points.get()):
            showinfo("Número de picos erróneo", "Por favor, selecciona un número de picos menor que el número de puntos")
        else:
            # actualizo el historial
            self.mainDB['history'].update({'_id':'backup'}, {'$set': {'points': self.points.get(), 'peaks': self.peaks.get()}})

            # preparo intervalos para la grafica
            initDate = self.initDate.get()
            initTime = self.initTime.get()
            endDate = self.endDate.get()
            endTime = self.endTime.get()

            self.epochI = self.toEpoch(int(initDate[6:10]), int(initDate[3:5]), int(initDate[0:2]), int(initTime[0:2]),
                              int(initTime[3:5]), int(initTime[6:8]))
            self.epochF = self.toEpoch(int(endDate[6:10]), int(endDate[3:5]), int(endDate[0:2]), int(endTime[0:2]),
                              int(endTime[3:5]), int(endTime[6:8]))

            self.getPoints()

    def getPoints(self):
        show = True

        intervals = int((self.epochF - self.epochI) / int(self.points.get()))

        if intervals > 0:
            x = []
            y = []
            for i in range(int(self.points.get())):
                hour = int(((self.epochI + (i * intervals)) + (self.epochI + ((i + 1) * intervals))) / 2)

                for row in self.collFrec.find({'epoch': hour}):
                    x.append(row['epoch'])

                # calculamos la media de tweets en cada intervalo
                fin = self.epochI + (intervals * (i + 1))
                init = self.epochI + (intervals * i)

                for row in self.collFrec.find({'epoch': fin}, {'_id': 0, 'acumulado': 1}):
                    acumFin = row['acumulado']

                for row in self.collFrec.find({'epoch': init}, {'_id': 0, 'acumulado': 1}):
                    acumInit = row['acumulado']

                # comprueba que acumFin está definida
                if ('acumFin' in locals() or 'acumInit' in locals()):
                    y.append(int((acumFin - acumInit) / intervals))
                else:
                    show = False

        if show and intervals > 0:
            self.showGraph(x, y)
        else:
            showinfo("Intervalo no válido", "Por favor, selecciona un intervalo de tiempo mayor")


    # elimina una collecion de la base de datos y sus frecuencias
    def removeColl(self):
        self.mainDB[self.traceCols.get()].drop()
        self.mainDB['frec_' + self.traceCols.get()].drop()
        self.mainDB['info_' + self.traceCols.get()].drop()

        self.updWidgets(False)


    # actualiza widgets (campos de texto, drop-downs...)
    def updWidgets(self, firstImport):

        self.colsDrop['menu'].delete(0, 'end')
        self.frecsDrop['menu'].delete(0, 'end')

        c = self.getColls('original', self.mainDB.collection_names())
        for row in c:
            self.colsDrop['menu'].add_command(label=row, command=tkinter._setit(self.traceCols, row))
        self.traceCols.set(c[0])

        c = self.getColls('frec', self.mainDB.collection_names())
        if firstImport:
            self.traceFrecs.set('frec_' + self.collName.get())
            for row in c:
                if row != 'frec_' + self.collName.get():
                    self.frecsDrop['menu'].add_command(label=row, command=tkinter._setit(self.traceFrecs, row))
        else:
            for row in c:
                self.frecsDrop['menu'].add_command(label=row, command=tkinter._setit(self.traceFrecs, row))
            self.traceFrecs.set(c[0])

        if c[0] == '-':
            self.initDate.configure(state=NORMAL)
            self.endDate.configure(state=NORMAL)
            self.initDate.delete(0, 'end')
            self.initTime.delete(0, 'end')
            self.endDate.delete(0, 'end')
            self.endTime.delete(0, 'end')
            self.initDate.configure(state=DISABLED)
            self.endDate.configure(state=DISABLED)
            self.langsDrop['menu'].delete(0, 'end')
            self.traceLangs.set('-')

    # detecta cambios en un drop-down
    def dropChanges(self, *args):

        if self.getColls('original', self.mainDB.collection_names())[0] != '-':
            str = self.traceFrecs.get()
            self.coll = self.mainDB[str.replace("frec_", "" )]
            self.collFrec = self.mainDB[str]
            self.collInfo = self.mainDB[str.replace("frec_", "info_")]
            self.makeChanges()


    # cambia los campos de fecha, hora e idiomas según la col. de frecuencias seleccionada
    def makeChanges(self):
        self.initDate.configure(state=NORMAL)
        self.endDate.configure(state=NORMAL)

        self.initDate.delete(0, 'end')
        c = self.collInfo.find_one({'initDate': {'$exists': 1}})
        self.initDate.insert(0, c['initDate'])

        self.initTime.delete(0, 'end')
        c = self.collInfo.find_one({'initTime': {'$exists': 1}})
        self.initTime.insert(0, c['initTime'])

        self.endDate.delete(0, 'end')
        c = self.collInfo.find_one({'endDate': {'$exists': 1}})
        self.endDate.insert(0, c['endDate'])

        self.initDate.configure(state=DISABLED)
        self.endDate.configure(state=DISABLED)

        self.endTime.delete(0, 'end')
        c = self.collInfo.find_one({'endTime': {'$exists': 1}})
        self.endTime.insert(0, c['endTime'])

        self.langsDrop['menu'].delete(0, 'end')
        l = list(self.collInfo.aggregate([{'$project': {'_id': 0, 'idioma': 1}}, {'$limit': 3}]))

        for elem in l:
            self.langsDrop['menu'].add_command(label=elem['idioma'], command=tkinter._setit(self.traceLangs, elem['idioma']))
        self.langsDrop['menu'].add_command(label="Todos", command=tkinter._setit(self.traceLangs, "Todos"))

        self.traceLangs.set(l[0]['idioma'])


    # de una lista de collecciones 'list'
    # devuelve las collecciones originales (si isFrec == False)
    # o las colecciones de frecuencias (si isFrec == True)
    # si no existen colecciones devuelve una lista con "-"
    def getColls(self, col, list):

        # colecciones originales
        if col is 'original':
            c = []
            for i in range(len(list)):
                if list[i].startswith('frec_') is False and list[i].startswith('info_') is False and list[i] != 'idiomas' and list[i] != 'history':
                    c.append(list[i])
        # colecciones de frecuencias
        elif col is 'frec':
            c = []
            for i in range(len(list)):
                if list[i].startswith('frec_') is True:
                    c.append(list[i])

        # valor por defecto
        if not c:
            c.append('-')
        elif col is 'original':
            self.traceCols.set(c[0])
        elif col is 'frec':
            self.traceFrecs.set(c[0])

        return c

    # muestra el grafico de puntos
    def showGraph(self, time, tweets):

        prettyDates = []

        for i in range(len(time)):
            for row in (self.collFrec.find({'epoch': time[i]}, {'_id': 1})):
                # añade un 0 si la hora, minuto, segundo es menor que 10
                # si no, minuto 02 lo trata como 20
                h = row['_id']['hora']
                if h < 10:
                    h = '0' + str(row['_id']['hora'])

                m = row['_id']['minuto']
                if m < 10:
                    m = '0' + str(row['_id']['minuto'])

                s = row['_id']['segundo']
                if s < 10:
                    s = '0' + str(row['_id']['segundo'])

                prettyDates.append(str(row['_id']['dia']) + '/' + str(row['_id']['mes']) + '/' + str(row['_id']['año']) +
                     ' ' + str(h) + ':' + str(m) + ':' + str(s))

        plt.rcParams['toolbar'] = 'None'
        fig = plt.figure()
        fig.canvas.mpl_connect("button_press_event", self.OnClick)
        fig.canvas.mpl_connect("button_release_event", self.OnRelease)
        fig.canvas.set_window_title('Temporary Event Frequencies Generator')
        plt.title('Colección: "' + self.coll.name + '"')
        plt.xlabel('Tiempo') # Etiqueta eje x
        plt.ylabel('Tweets/s') # Etiqueta eje y
        plt.xticks(time, prettyDates, rotation = 85)
        plt.grid(True)
        plt.subplots_adjust(left=0.25, bottom=0.27, right=0.98, top=0.9)

        # OBTENEMOS PICOS
        list = []
        self.timePeaks = []  # guarda los epoch de los picos

        for i in range(1, len(tweets)-1):
            if (tweets[i] > tweets[i-1] and tweets[i] > tweets[i+1]) or (tweets[i] > tweets[i-1] and tweets[i] == tweets[i+1]):
                list.append([time[i], tweets[i]])
        # ordena por el campo tweet y sólo guarda los picos indicados por el usuario
        list.sort(key=lambda list: list[1], reverse=True)
        list = list[:int(self.peaks.get())]

        # dibuja las lineas, recorre la lista de picos y bibuja picos
        plt.plot(time, tweets, linewidth=1, color=(0, 0.6, 1))
        for i in range(len(list)):
            plt.plot(list[i][0], list[i][1], marker='^', markersize=7, color=(0, 0, 0.8))
            self.timePeaks.append(list[i][0])

        self.timePeaks.sort()

        # dibuja el resto de puntos
        for i in range(len(time)):
            if any(time[i] in sublist for sublist in list) == False:
                plt.plot(time[i], tweets[i], marker='o', markersize=5, color=(0, 0.5, 1))

        self.timeline = Tk()
        self.timeline.title('Timeline')
        self.timeline.geometry('600x300')

        figManager = plt.get_current_fig_manager()
        figManager.window.state('iconic')

        # LEYENDAS
        ax = plt.subplot(111)

        # leyenda de idiomas
        props = dict(boxstyle='round', facecolor=(0, 0.5, 1), alpha=0.7)
        ax.text(-0.32, 1, "IDIOMAS MÁS TWEETEADOS: \n\n" + self.countLanguages(), fontsize=9,
                verticalalignment='top', bbox=props, transform=ax.transAxes)

        # leyenda de numero de tweets
        num = self.collFrec.find({"epoch":{'$gte':self.epochI, '$lte':self.epochF}},{'_id':0, 'acumulado':1}).sort('acumulado', -1)[0]['acumulado']
        props = dict(boxstyle='round', facecolor=(0, 0.5, 1), alpha=0.7)
        ax.text(-0.32, 0.7, "TOTAL DE TWEETS: \n\n" + str(num), fontsize=9, verticalalignment='top',
                bbox=props, transform=ax.transAxes)

        # leyenda de usuario con más followers
        user = self.coll.aggregate([{'$match': {'epoch': {'$gte': self.epochI, '$lte': self.epochF}}}, {'$group': {'_id': '$user.screen_name', 'followers': {'$max': '$user.followers_count'}}}, {'$sort': {'followers': -1}}, {'$limit': 1}])
        for row in user:
            text = str(row['_id']) + ' - ' + str(row['followers'])

        props = dict(boxstyle='round', facecolor=(0, 0.5, 1), alpha=0.7)
        ax.text(-0.32, 0.5, "USUARIO CON MÁS FOLLOWERS: \n\n" + text, fontsize=9, verticalalignment='top',
                bbox=props, transform=ax.transAxes)

        # leyenda de usuario con más tweets publicados
        user = self.coll.aggregate([{'$match': {'epoch': {'$gte': self.epochI, '$lte': self.epochF}}}, {'$group': {'_id': '$user.screen_name', 'count': {'$sum': 1}}}, {'$sort': {'count': -1}}, {'$limit': 1}])
        for row in user:
            text = str(row['_id']) + ' - ' + str(row['count'])
        props = dict(boxstyle='round', facecolor=(0, 0.5, 1), alpha=0.7)
        ax.text(-0.32, 0.3, "USUARIO CON MÁS TWEETS: \n\n" + text, fontsize=9, verticalalignment='top',
                  bbox=props, transform=ax.transAxes )

        plt.show(block=False)

        self.tfIdf(False)

        # leyenda de tweet representativo
        if self.tweet != None:
            props = dict(boxstyle='round', facecolor=(0.9, 0.8, 0), alpha=0.7)
            self.text = plt.text(-0.32, 0.1, "TWEET REPRESENTATIVO: \n\n" + '\n'.join(wrap(self.generalTweet, 30)), verticalalignment='top', fontsize=10, bbox=props, transform=ax.transAxes)
        plt.show(block=False)

        def onselect(eclick, erelease):
            print('startposition :', eclick.xdata, eclick.ydata)
            print('endposition: ', erelease.xdata, erelease.ydata)
            print('used button: ', eclick.button)

        def toggle_selector(event):
            print('Key pressed.')
            if event.key in ['Q', 'q'] and toggle_selector.RS.active:
                print('RectangleSelector deactivated')
                toggle_selector.RS.set_active(False)
            if event.key in ['A', 'a'] and not toggle_selector.RS.active:
                print('RectangleSelector activated')
                toggle_selector.RS.set_active(True)

        toggle_selector.RS = RectangleSelector(ax, onselect, drawtype='box', useblit=False)


    # segun el epochI y el epochF
    # calcula los 3 idiomas mas hablados entre esos epochs
    def countLanguages(self):
        self.coll.aggregate([{'$project':{"epoch":1, "lang":1}}, {'$match':{"epoch":{'$gte':self.epochI, '$lte':self.epochF}}}, {'$group':{'_id':"$lang", 'total':{'$sum':1}}}, {'$sort': {'total':-1}}, {'$limit':3}, {'$out': 'temp'}])

        for row in self.mainDB['temp'].find():
            var = self.mainDB['idiomas'].find_one({'_id': row['_id']})
            self.mainDB['temp'].update({'_id': row['_id']}, {'$set': {'idioma': var['idioma'], 'language': var['language']}})

        text = ""
        total = self.coll.find({"epoch":{'$gte':self.epochI, '$lte':self.epochF}}).count()
        others = total
        for row in self.mainDB['temp'].find():
            text += row['idioma'] + ': ' + str(round(row['total'] / total * 100, 2)) + ' %\n'
            others -= row['total']

        text += 'Otros: ' + str(round(others / total * 100, 2)) + ' %'
        self.mainDB['temp'].drop()

        return text


    def OnClick(self, event):
        self.epochI = int(event.xdata)

    def OnRelease(self, event):
        self.epochF = int(event.xdata)
        # intercambio epochI <-> epochF si el zoom se hace de izq a dcha
        if self.epochI > self.epochF:
            aux = self.epochI
            self.epochI = self.epochF
            self.epochF = aux

        # ZOOM
        if self.epochI != self.epochF:
            self.timeline.destroy()     # cerramos el timeline al hacer zoom
            self.getPoints()
        # CLICK
        else:
            self.tfIdf(True)

    def tfIdf(self, click):

        if self.traceLangs.get() == 'Todos':
            lan = self.mainDB['idiomas'].find_one({'idioma': self.traceLangs.get()})
            allLangs = True
        else:
            lan = self.collInfo.find_one({'idioma': self.traceLangs.get()})
            allLangs = False


        tweets = []
        if click is False:
            # todos los idiomas
            if self.traceLangs.get() == 'Todos':

                for row in self.coll.aggregate([{'$project': {'_id': 0, 'epoch': 1, self.tweetText.get(): 1, 'lang': 1}}, {'$match': {'epoch': {'$gte': self.epochI, '$lte': self.epochF}}}, {'$sample': {'size': 500}}]):
                    tweets.append(row[self.tweetText.get()])
            # idioma seleccionado
            else:

                for row in self.coll.aggregate([{'$project': {'_id': 0, 'epoch': 1, self.tweetText.get(): 1, 'lang': 1}}, {'$match': {'epoch': {'$gte': self.epochI, '$lte': self.epochF}, "lang": lan["_id"]}}, {'$sample': {'size': 500}}]):
                    tweets.append(row[self.tweetText.get()])

            self.compute(tweets, lan)

            # variable auxiliar que guarda el tweet representativo de todo el intervalo
            self.generalTweet = self.tweet

            # TFIDF de los Picos
            list = []
            for i in range(len(self.timePeaks)):
                self.epochI = self.timePeaks[i]
                self.epochF = self.timePeaks[i]
                self.computePoint(lan, allLangs)
                print('TWEET DEL PICO ', i+1, ': ',  self.tweet, '\n')
                list.append([self.coll.find_one({self.tweetText.get(): self.tweet})['epoch'], self.tweet])
            list.sort(key=lambda list: list[0])

            for i in range(len(list)):
                tweet = list[i][1]
                t = self.convert65536(tweet)
                t = '\n'.join(wrap(t, 100))
                t = re.sub("{\d{6}\w{1}}", "", t)

                h = self.coll.find({self.tweetText.get(): tweet}, {'_id': 0, self.dateField.get(): 1})
                h = str(h[0]).replace("{'created_at': datetime.datetime(", '')
                h = h.replace(')}', '')
                h = h.split(', ')

                if int(h[4]) < 10:
                    h[4] = '0' + h[4]

                if int(h[5]) < 10:
                    h[5] = '0' + h[5]

                if int(h[1]) < 10:
                    h[1] = '0' + h[1]

                h = h[3] + ':' + h[4] + ':' + h[5] + ' - ' + h[2] + '/' + h[1] +'/' + h[0]

                u = self.coll.find({self.tweetText.get(): tweet}, {'_id': 0, 'user.screen_name': 1})
                u= u[0]['user']['screen_name']

                labHour = Label(self.timeline, text=h + ' - ' + u)
                labHour.config(background='light goldenrod', width=30, justify=LEFT, borderwidth=2, relief="solid")
                labHour.grid(padx=(20, 380), pady=(0, 0))

                labTweet = Label(self.timeline, text=t)
                labTweet.config(background='SpringGreen3', width=80, justify=CENTER, borderwidth=2, relief="solid")
                labTweet.grid(pady=(0, 10), padx=10)

        else:
            # TFIDF Del 'click' y actualizo leyenda
            self.computePoint(lan, allLangs)
            self.text.remove()
            ax = plt.subplot(111)
            props = dict(boxstyle='round', facecolor=(0.9, 0.8, 0), alpha=0.7)
            self.text = plt.text(-0.32, 0.1, 'TWEET REPRESENTATIVO: \n\n' + '\n'.join(wrap(self.tweet, 30)), verticalalignment='top', fontsize=10, bbox=props, transform=ax.transAxes)


    # dada una lista de tweets y un idioma, calcula el tweet mas representativo del conjunto de tweets
    def compute(self, tweets, lan):
        def word_tokenizer(text):
            tokens = word_tokenize(text)
            tokens = [t for t in tokens if t not in stopwords.words(lan["language"])]
            return tokens

        tfidf_vectorizer = TfidfVectorizer(tokenizer=word_tokenizer,
                                           stop_words=stopwords.words(lan["language"]),
                                           min_df=0.0001,
                                           norm='l2',
                                           lowercase=True)

        # entrenamiento
        tfidf_vectorizer.fit_transform(tweets)

        # matriz con valores que indica la importancia de una palabra en un tweet y viceversa
        matrix = tfidf_vectorizer.transform(tweets)
        array = matrix.toarray()

        # calcula el producto escalar de los vectores del tf-idf de cada tweet
        dotPr = []
        a = 0
        for i in range(array.shape[0]):
            dotPr.append([])
            for j in range(array.shape[0]):
                dotPr[i].append(math.sqrt(numpy.dot(array[i], array[j])))
                a = a + 1

        # suma los productos escalares de cada fila
        max = 0
        i = 0
        index = 0
        for row in dotPr:
            if sum(row) > max:
                max = sum(row)
                index = i
            i = i + 1

        self.tweet = tweets[index]

    # dado un punto en la grafica, calcula el tfid de los tweets a +-100 posiciones del epoch en el punto
    def computePoint(self, lan, allLangs):
        tweets = []
        self.epochI -= 100
        self.epochF += 100

        if self.epochI < self.coll.find({}, {'_id': 0, 'epoch': 1}).sort('epoch', 1)[0]['epoch']:
            self.epochI = self.coll.find({}, {'_id': 0, 'epoch': 1}).sort('epoch', 1)[0]['epoch']

        if self.epochF > self.coll.find({}, {'_id': 0, 'epoch': 1}).sort('epoch', -1)[0]['epoch']:
            self.epochF = self.coll.find({}, {'_id': 0, 'epoch': 1}).sort('epoch', -1)[0]['epoch']

        if allLangs is True:
            c = self.coll.find({'epoch': {'$gte': self.epochI, '$lte': self.epochF}}).count()
            for row in self.coll.find({'epoch': {'$gte': self.epochI, '$lte': self.epochF}}).skip(
                    int(c / 2) - 100).limit(200):
                tweets.append(row[self.tweetText.get()])
        else:
            c = self.coll.find({'epoch': {'$gte': self.epochI, '$lte': self.epochF}, "lang": lan["_id"]}).count()
            for row in self.coll.find({'epoch': {'$gte': self.epochI, '$lte': self.epochF}}).skip(
                    int(c / 2) - 100).limit(200):
                tweets.append(row[self.tweetText.get()])

        self.compute(tweets, lan)

    def convert65536(self, s):
        # Converts a string with out-of-range characters in it into a string with codes in it.
        l = list(s);
        i = 0;
        while i < len (l):
            o = ord (l[i]);
            if o > 65535:
                l[i] = "{" + str(o) + "ū}";
            i += 1;
        return "".join(l);

app = showGUI('tfg', 'T.E.F.G')