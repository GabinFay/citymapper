#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 16 11:29:07 2021

@author: gabinfay
"""

import sys
from os.path import expanduser
sys.path.append(expanduser('~')+'/SQL/Data')
dp = expanduser('~')+'/SQL/Data/'

import folium, io, json, sys, math, random, os
import psycopg2
from folium.plugins import Draw, MousePosition, MeasureControl
from jinja2 import Template
from branca.element import Element
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import numpy as np
import geopandas as gpd

import pandas as pd
import geopandas as gpd
from pandas import DataFrame
import networkx as nx
import re
from sshtunnel import SSHTunnelForwarder


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

def compute_distance(trip, hops):
    """trip is an array, A > type > name > STOP1 > route_type > route_name > STOP2 > route_type ..... > B
    hops hops"""
    """ALGO : for each hop, find all the elementary trips you did (in combined), then add their duration_avg
    return duration_avg"""
    pass

def quickest_tp5():
    """
    run the query, for each hop, compute duration avg. Add, trip + duration_avg in a new array
    """
    pass
    
    


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.resize(600, 600)
	
        main = QWidget()
        self.setCentralWidget(main)
        main.setLayout(QVBoxLayout())
        main.setFocusPolicy(Qt.StrongFocus)

        self.tableWidget = QTableWidget()
        self.tableWidget.doubleClicked.connect(self.table_Click)
        self.rows = []

        self.webView = myWebView()
		
        controls_panel = QHBoxLayout()
        mysplit = QSplitter(Qt.Vertical)
        mysplit.addWidget(self.tableWidget)
        mysplit.addWidget(self.webView)

        main.layout().addLayout(controls_panel)
        main.layout().addWidget(mysplit)

        _label = QLabel('From: ', self)
        _label.setFixedSize(30,20)
        self.from_box = QComboBox() 
        self.from_box.setEditable(True)
        self.from_box.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.from_box.setInsertPolicy(QComboBox.NoInsert)
        controls_panel.addWidget(_label)
        controls_panel.addWidget(self.from_box)

        _label = QLabel('  To: ', self)
        _label.setFixedSize(20,20)
        self.to_box = QComboBox() 
        self.to_box.setEditable(True)
        self.to_box.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.to_box.setInsertPolicy(QComboBox.NoInsert)
        controls_panel.addWidget(_label)
        controls_panel.addWidget(self.to_box)

        _label = QLabel('Hops: ', self)
        _label.setFixedSize(20,20)
        self.hop_box = QComboBox() 
        self.hop_box.addItems( ['1', '2', '3', '4', '5'] )
        self.hop_box.setCurrentIndex( 0 )
        controls_panel.addWidget(_label)
        controls_panel.addWidget(self.hop_box)

        self.go_button = QPushButton("Go!")
        self.go_button.clicked.connect(self.button_Go)
        controls_panel.addWidget(self.go_button)
           
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.button_Clear)
        controls_panel.addWidget(self.clear_button)

        self.maptype_box = QComboBox()
        self.maptype_box.addItems(self.webView.maptypes)
        self.maptype_box.currentIndexChanged.connect(self.webView.setMap)
        controls_panel.addWidget(self.maptype_box)
           
        self.connect_DB()

        self.startingpoint = True
                   
        self.show()
        

    def connect_DB(self):  
        try:
            server = SSHTunnelForwarder(
                     ('95.216.173.19', 22),
                     ssh_username="gabin",
                     ssh_password="projet",
                     remote_bind_address=('localhost', 5432))
                     
            server.start()
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
    
            self.cursor.execute("""SELECT distinct name FROM nodes ORDER BY name""")
            self.conn.commit()
            rows = self.cursor.fetchall()
    
            for row in rows : 
                self.from_box.addItem(str(row[0]))
                self.to_box.addItem(str(row[0]))
            
        except:
            print("Connection Failed")



    def table_Click(self):
        coords = []
        for i, col in enumerate(self.rows[self.tableWidget.currentRow()]):
            if i%2==0:
                self.rows = []
                col = col.replace("'", "''")
                query = f"""SELECT avg(lat),avg(lon)
FROM nodes
WHERE name = '{col}'"""
                self.cursor.execute(query)
                self.conn.commit()
                self.rows += self.cursor.fetchall()
                coords.append(self.rows[0])
                self.webView.addMarker(coords[int(i/2)][0], coords[int(i/2)][1])
                if i >= 2:
                    self.webView.addSegment(coords[int(i/2)-1][0], coords[int(i/2)-1][1], coords[int(i/2)][0], coords[int(i/2)][1])
                
    def button_Go(self):
        self.tableWidget.clearContents()

        _fromstation = str(self.from_box.currentText()).replace("'","''")
        _tostation = str(self.to_box.currentText()).replace("'", "''")
        _hops = int(self.hop_box.currentText())
        self.rows = []
        if _hops >= 1 : 
            query=f"""SELECT distinct A.name, A.route_type, A.route_name, B.name 
FROM stoproutename as A, stoproutename as B
WHERE A.name = $${_fromstation}$$
AND B.name = $${_tostation}$$
AND A.route_name = B.route_name
AND A.route_type = B.route_type"""
            self.cursor.execute(query)
            self.conn.commit()
            self.rows += self.cursor.fetchall()

        if _hops >= 2 : 
            query = f"""SELECT distinct A.name, A.route_type, A.route_name, BB.name, BB.route_type, BB.route_name, B.name
FROM stoproutename as A, stoproutename as B, stoproutename as AA, stoproutename as BB
WHERE A.name = $${_fromstation}$$
AND B.name = $${_tostation}$$
AND A.route_name = AA.route_name
AND A.route_type = AA.route_type
AND B.route_name = BB.route_name
AND B.route_type = BB.route_type
AND A.route_name != BB.route_name
AND A.route_type != BB.route_type
AND AA.name = BB.name
AND A.name != AA.name
AND AA.name != B.name"""
            # query=""f" SELECT distinct A.geo_point_2d, A.nom_long, A.res_com, B.geo_point_2d, B.nom_long, C.res_com, D.geo_point_2d, D.nom_long FROM metros as A, metros as B, metros as C, metros as D WHERE A.nom_long = ${_fromstation}$ AND D.nom_long = $${_tostation}$$ AND A.res_com = B.res_com AND B.nom_long = C.nom_long AND C.res_com = D.res_com AND A.res_com <> C.res_com AND A.nom_long <> B.nom_long AND B.nom_long <> D.nom_long"""
            self.cursor.execute(query)
            self.conn.commit()
            self.rows += self.cursor.fetchall()

        if _hops >= 3 :
            query = f"""
SELECT distinct A.name, AA.route_type, AA.route_name, AA.name, AAA.route_type, AAA.route_name, BB.name, BB.route_type, BB.route_name, B.name
FROM stoproutename as A, stoproutename as B, stoproutename as AA, stoproutename as BB, stoproutename as AA1, stoproutename as AAA
WHERE A.name = $${_fromstation}$$
AND B.name = $${_tostation}$$
AND A.route_name = AA.route_name
AND A.route_type = AA.route_type
AND AA.name = AA1.name
AND AA1.route_name = AAA.route_name
AND AA1.route_type = AAA.route_type
AND AAA.name = BB.name
AND BB.route_name = B.route_name
AND BB.route_type = B.route_type
AND A.name != AA.name
AND A.name != AAA.name
AND AA1.name != AAA.name
AND A.route_name != AAA.route_name
AND A.route_type != AAA.route_type
AND A.route_name != BB.route_name
AND A.route_type != BB.route_type
AND AAA.route_name != BB.route_name
"""

            self.cursor.execute(query)
            self.conn.commit()    
            self.rows += self.cursor.fetchall()

        print('no path was found')

        if len(self.rows) == 0 : 
            self.tableWidget.setRowCount(0)
            self.tableWidget.setColumnCount(0)
            return

        numrows = len(self.rows)
        numcols = len(self.rows[-1])
        self.tableWidget.setRowCount(numrows)
        self.tableWidget.setColumnCount(numcols)
        
        i = 0
        for row in self.rows : 
            j = 0
            for col in row :
                self.tableWidget.setItem(i, j, QTableWidgetItem(str(col)))
                j = j + 1
            for j in range(1,len(row),3):
                self.tableWidget.setItem(i, j, QTableWidgetItem(str_route_type(row[j])))   
            i = i + 1
        print('over')
             

        header = self.tableWidget.horizontalHeader()
        j = 0
        while j < numcols : 
            header.setSectionResizeMode(j, QHeaderView.ResizeToContents)
            j = j+1
        self.update()
        # print('over')


    def button_Clear(self):
        self.webView.clearMap(self.maptype_box.currentIndex())
        self.startingpoint = True
        self.update()
        global number_of_click
        number_of_click=0


    def mouseClick(self, lat, lng):
        global number_of_click
        self.webView.addPoint(lat, lng)
        # run sql query  to find closest station
        # set this station to the From box

        print(f"Clicked on: latitude {lat}, longitude {lng}")
        self.cursor.execute(f"""SELECT A.name, A.stop_i
FROM nodes as A
WHERE ((A.lat - {lat})^2 + (A.lon - {lng})^2) <= ALL (SELECT (lat - {lat})^2 + (lon - {lng})^2 FROM nodes)""")
        self.conn.commit()
        myrows = self.cursor.fetchall()
        # index = random.randint(0,len(myrows))
        if number_of_click == 0:
            self.from_box.setCurrentIndex(self.from_box.findText(myrows[0][0], Qt.MatchFixedString))
        else:
            self.to_box.setCurrentIndex(self.to_box.findText(myrows[0][0], Qt.MatchFixedString))
        number_of_click += 1



class myWebView (QWebEngineView):
    def __init__(self):
        super().__init__()

        self.maptypes = ["Stamen Terrain", "OpenStreetMap","stamentoner", "cartodbpositron"]
        self.setMap(0)


    def add_customjs(self, map_object):
        my_js = f"""{map_object.get_name()}.on("click",
                 function (e) {{
                    var data = `{{"coordinates": ${{JSON.stringify(e.latlng)}}}}`;
                    console.log(data)}}); """
        e = Element(my_js)
        html = map_object.get_root()
        html.script.get_root().render()
        html.script._children[e.get_name()] = e

        return map_object


    def handleClick(self, msg):
        data = json.loads(msg)
        lat = data['coordinates']['lat']
        lng = data['coordinates']['lng']

        window.mouseClick(lat, lng)


    def addSegment(self, lat1, lng1, lat2, lng2):
        js = Template(
        """
        L.polyline(
            [ [{{latitude1}}, {{longitude1}}], [{{latitude2}}, {{longitude2}}] ], {
                "color": "purple",
                "opacity": 1.0,
                "weight": 4,
                "line_cap": "butt"
            }
        ).addTo({{map}});
        """
        ).render(map=self.mymap.get_name(), latitude1=lat1, longitude1=lng1, latitude2=lat2, longitude2=lng2 )

        self.page().runJavaScript(js)


    def addMarker(self, lat, lng):
        js = Template(
        """
        L.marker([{{latitude}}, {{longitude}}] ).addTo({{map}});
        L.circleMarker(
            [{{latitude}}, {{longitude}}], {
                "bubblingMouseEvents": true,
                "color": "#3388ff",
                "popup": "hello",
                "dashArray": null,
                "dashOffset": null,
                "fill": false,
                "fillColor": "#3388ff",
                "fillOpacity": 0.2,
                "fillRule": "evenodd",
                "lineCap": "round",
                "lineJoin": "round",
                "opacity": 1.0,
                "radius": 2,
                "stroke": true,
                "weight": 5
            }
        ).addTo({{map}});
        """
        ).render(map=self.mymap.get_name(), latitude=lat, longitude=lng)
        self.page().runJavaScript(js)


    def addPoint(self, lat, lng):
        js = Template(
        """
        L.circleMarker(
            [{{latitude}}, {{longitude}}], {
                "bubblingMouseEvents": true,
                "color": 'green',
                "popup": "hello",
                "dashArray": null,
                "dashOffset": null,
                "fill": false,
                "fillColor": 'green',
                "fillOpacity": 0.2,
                "fillRule": "evenodd",
                "lineCap": "round",
                "lineJoin": "round",
                "opacity": 1.0,
                "radius": 2,
                "stroke": true,
                "weight": 5
            }
        ).addTo({{map}});
        """
        ).render(map=self.mymap.get_name(), latitude=lat, longitude=lng)
        self.page().runJavaScript(js)


    def setMap (self, i):
        self.mymap = folium.Map(location=[48.8619, 2.3519], tiles=self.maptypes[i], zoom_start=12, prefer_canvas=True)

        self.mymap = self.add_customjs(self.mymap)

        page = WebEnginePage(self)
        self.setPage(page)

        data = io.BytesIO()
        self.mymap.save(data, close_file=False)

        self.setHtml(data.getvalue().decode())

    def clearMap(self, index):
        self.setMap(index)



class WebEnginePage(QWebEnginePage):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def javaScriptConsoleMessage(self, level, msg, line, sourceID):
        #print(msg)
        if 'coordinates' in msg:
            self.parent.handleClick(msg)


       
			
if __name__ == '__main__':
    app = QApplication(sys.argv) 
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
