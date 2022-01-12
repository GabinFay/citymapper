#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 16 11:29:07 2021

@author: gabinfay
"""

import sys
import os
from os.path import expanduser
sys.path.append(expanduser('~')+'/SQL/Data')
dp = expanduser('~')+'/SQL/Data/'

import folium, io, json, sys
import psycopg2
# from folium.plugins import Draw, MousePosition, MeasureControl
from jinja2 import Template
from branca.element import Element
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsView,QGraphicsPixmapItem,QGraphicsScene,QMainWindow,QApplication,QTableWidget, QTableWidgetItem, QComboBox, QPushButton, QLabel, QSplitter, QHBoxLayout, QVBoxLayout, QWidget,QCompleter
from PyQt5.QtGui import QPixmap

import pandas as pd
import networkx as nx
from sshtunnel import SSHTunnelForwarder
from sqlalchemy import create_engine

# home = expanduser('~')+"/SQL/Data/"
user = 'projet'
dbname = 'projet'
password = 'projet'

####UGLY but immediate
number_of_click = 0

def str_route_type(route_type):
    route_type=int(route_type)
    # we could have used pattern matching in python 3.10 to implement it like a switch case
    if route_type == 0:
        route='TRAM'
    elif route_type ==1:
        route='METRO'
    elif route_type == 2:
        route='RER'
    elif route_type == 3:
        route='BUS'
    else:
        route='ERROR'
    return route

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.resize(600, 600)
	
        self.main = QWidget()
        self.setCentralWidget(self.main)
        self.main.setLayout(QVBoxLayout())
        self.main.setFocusPolicy(Qt.StrongFocus)
                
        self.label = QLabel(self)        
        self.pixmap = QPixmap('Scrape/BUS 180 Paris.jpg')
        self.label.setPixmap(self.pixmap)
		
        controls_panel = QHBoxLayout()
        self.main.layout().addLayout(controls_panel)
        self.main.layout().addWidget(self.label)

        # _label.setFixedSize(30,20)
        self.route_box = QComboBox() 
        self.route_box.setEditable(True)
        self.route_box.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.route_box.setInsertPolicy(QComboBox.NoInsert)
        controls_panel.addWidget(self.route_box,stretch=1)

        self.go_button = QPushButton("Go!")
        self.go_button.clicked.connect(self.button_Go)
        controls_panel.addWidget(self.go_button,stretch=1)
           
        self.connect_DB('local')                   
        self.show()
        

    def connect_DB(self, remoteorlocal='remote'):  
        if remoteorlocal=='local':
            user = 'projet'
            dbname = 'projet'
            password = 'projet'
            self.conn = psycopg2.connect(database=dbname, user=user, host="localhost", password=password)
            self.cursor = self.conn.cursor()
            self.engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format("projet", "projet", "127.0.0.1", 5432, "projet"))
            
        elif remoteorlocal =='remote':
            try:
                server = SSHTunnelForwarder(
                          ('95.216.173.19', 22),
                          ssh_username="projet",
                          ssh_password="projet",
                          remote_bind_address=('localhost', 5432))
                         
                server.start()
                print("!!! don't mind the error message !!!")
                print("server connected") 
                params = {
                    'database': 'projet',
                    'user': 'projet',
                    'password': 'projet',
                    'host': 'localhost',
                    'port': server.local_bind_port
                    }
           
                self.conn = psycopg2.connect(**params)
                self.cursor = self.conn.cursor()
                print("database projet connected to hetzner")
                
                local_port = str(server.local_bind_port)
                self.engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format("projet", "projet", "127.0.0.1", local_port, "projet"))

                
            except:
                print("Connection Failed")
        self.cursor.execute("""SELECT distinct route_type,route_name FROM routes ORDER BY route_type DESC""")
        self.conn.commit()
        rows = self.cursor.fetchall()
        for row in rows:
            self.route_box.addItem(str_route_type(row[0]) + ' ' + row[1])
        
    def button_Go(self):
        self.route = str(self.route_box.currentText())
        if os.path.exists('Scrape/'+self.route+' Paris.jpg'):
            self.pixmap = QPixmap('Scrape/'+self.route+' Paris.jpg','1').scaled(self.label.width(), self.label.height(), Qt.KeepAspectRatio)
            self.label.setPixmap(self.pixmap)
        else:
            self.pixmap = QPixmap('Scrape/'+self.route+' Paris.jpg','1').scaled(self.label.width(), self.label.height(), Qt.KeepAspectRatio)
            self.label.setPixmap(self.pixmap)


       
if __name__ == '__main__':
    app = QApplication(sys.argv) 
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
