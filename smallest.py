#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 16 11:29:07 2021

@author: gabinfay
"""

"""DOESN'T REALLY WORKS, It outputs a correct non optimal path as the algorithm is very naive
"""

import sys
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
from PyQt5.QtWidgets import QMainWindow,QApplication,QTableWidget, QTableWidgetItem, QComboBox, QPushButton, QLabel, QSplitter, QHBoxLayout, QVBoxLayout, QWidget,QCompleter

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
        self.show()
        

    def connect_DB(self):  
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

            self.cursor.execute("""SELECT distinct name FROM nodes ORDER BY name""")
            self.conn.commit()
            rows = self.cursor.fetchall()
    
            for row in rows : 
                self.from_box.addItem(str(row[0]))
                self.to_box.addItem(str(row[0]))
            
        except:
            print("Connection Failed")

    def path_processing(self, G, path, print_name):
        duration = nx.classes.function.path_weight(G, path, weight="duration_avg")
        # shortest_duration = nx.dijkstra_path_length(G_full, source=self.from_stop_i, target=self.to_stop_i, weight="duration_avg")/60
        print(f"Le temps de {print_name} est {duration//60} minutes")
        pathGraph = nx.path_graph(path)
        edges = []
        for ea in pathGraph.edges():
            edges.append((ea, G.edges[ea[0], ea[1]]))
        routes_taken = []
        for i in edges:
            try:
                # if self.routes.loc[self.routes['route_i']==int(i[1]['route_i'])] == []:
                print('debme')
                routes_taken.append(self.routes.loc[self.routes['route_i']==int(i[1]['route_i'])])
            except Exception as e:
                print(e)
                routes_taken.append(pd.DataFrame([['w','w','w']],columns=['route_type','route_name','route_i']))
        print('dm')
        routes_taken = pd.concat(routes_taken,ignore_index=True)
        shortest_names = pd.concat([self.nodes.loc[self.nodes['stop_i']==i] for i in path]).reset_index()
        print('debme')
        which_routes_taken = routes_taken[['route_type','route_name']].drop_duplicates()
        which_routes_taken = which_routes_taken[which_routes_taken.route_type != 'w']
        ###############################################
        # adding waiting time each time you have to take a new route
        print('dem')
        import datetime
        import time
        
        today = datetime.datetime.utcnow()
        curr_unix_time = time.mktime(today.utctimetuple())
        starting_time = datetime.datetime.utcfromtimestamp(curr_unix_time).strftime('%Y-%m-%d %H:%M:%S')[-8:].split(':')
        starting_time = int(starting_time[0])*3600 + int(starting_time[1])*60 + int(starting_time[2])
        
        current_time = starting_time
        for i,j in enumerate(which_routes_taken.index):
            self.rows = []
            query = f"""
                SELECT dep_time_ut
                FROM temporal_day
                WHERE {edges[j][0][0]} = from_stop_i
                AND {edges[j][0][1]} = to_stop_i
                AND dep_time_ut > {current_time}
                ORDER BY dep_time_ut
                LIMIT 1
                """
            self.cursor.execute(query)
            self.conn.commit()
            self.rows += self.cursor.fetchall()
            
            # no rows can be selected, leading to self.rows being empty if you've missed the last train for the day, so you need to look for tomorrow's one
            if not self.rows:
                query=f"""
                    SELECT dep_time_ut + 24*3600
                    FROM temporal_day
                    WHERE {edges[j][0][0]} = from_stop_i
                    AND {edges[j][0][1]} = to_stop_i
                    ORDER BY dep_time_ut
                    LIMIT 1
                    """
                self.cursor.execute(query)
                self.conn.commit()
                self.rows += self.cursor.fetchall()
            try:
                current_time = float(self.rows[0][0])
                k = j
                if j != which_routes_taken.index[-1]:
                    while k < which_routes_taken.index[i+1]:
                        current_time += float(edges[k][1]['duration_avg'])
                        current_time += 30 # to account for time spent in each station
                        k += 1
                else:
                    while k <= routes_taken.index[-1]:
                        current_time += float(edges[k][1]['duration_avg'])
                        current_time += 30 # to account for time spent in each station
                        k += 1
            except Exception as e:
                print(e)
                # print('deebome')
                pass
            

        total_time = current_time - starting_time
        print(f"Le temps en tenant compte de l'attente est {int(total_time//3600)}h {int(total_time%3600//60)}m {int(total_time%3600%60)}s")
        return shortest_names, which_routes_taken, total_time

    def button_Go(self):
        
        self.tableWidget.clearContents()
        self.rows = []
        
        self.nodes = pd.read_sql("SELECT * FROM \"{}\";".format("nodes"), self.engine)  
        self.routes = pd.read_sql("SELECT * FROM \"{}\";".format("routes"), self.engine)        
        self.supercomb = pd.read_sql("SELECT * FROM \"{}\";".format("supercomb"), self.engine)
        
        G = nx.from_pandas_edgelist(self.supercomb, source="superfrom", target="superto", edge_attr=True)
        self.smallest = nx.bidirectional_shortest_path(G, source=self.superfrom_i, target=self.superto_i)
        self.smallest = [int(i) for i in self.smallest]
        self.smallest_names, self.smallest_routes, self.smallest_time = self.path_processing(G, self.smallest, 'shortest')
        print('dm')

        numrows = 2
        numcols = len(self.smallest_routes)
        self.tableWidget.setRowCount(numrows)
        self.tableWidget.setColumnCount(2*numcols+1)
        self.add_path_to_table(self.smallest_names,self.smallest_routes,0)
        self.tableWidget.resizeColumnsToContents()
        print('dm')
        
##########################

    def add_path_to_table(self, shortest_names, which_routes_taken,row_num):
        numcols=self.tableWidget.columnCount()
        jj=0
        for sss,route in which_routes_taken.iterrows():
            self.tableWidget.setItem(row_num, jj, QTableWidgetItem(shortest_names.iloc[sss-1]['name']))   
            self.tableWidget.setItem(row_num, jj+1, QTableWidgetItem(str_route_type(route['route_type'])+' '+route['route_name']))   
            jj += 2
        self.tableWidget.setItem(row_num, jj, QTableWidgetItem(shortest_names.iloc[-1]['name']))
        total_time = self.smallest_time
        self.tableWidget.setSpan(row_num+1, 1, 1, 2*numcols) 
        newItem = QTableWidgetItem(f"""{int(total_time//3600)}h {int(total_time%3600//60)}m {int(total_time%3600%60)}s""")  
        self.tableWidget.setItem(row_num+1, 1, newItem)
        newItem = QTableWidgetItem('TEMPS TOTAL')  
        self.tableWidget.setItem(row_num+1, 0, newItem)

    def table_Click(self):
        which_routes_taken = self.smallest_routes
        shortest = self.smallest
        HEX = ['#52766c','blue', 'pink','black','purple','#52766c','#52766c','blue', 'pink','black','purple']
        nth_route = 0
        colors = []
        for sss, i in enumerate(shortest):
            if i != 'w':
                if sss <= which_routes_taken.index[-1] and sss == which_routes_taken.index[nth_route+1]:
                    nth_route += 1
                lat=self.nodes.loc[self.nodes['stop_i']==i]['lat'].item()
                lng=self.nodes.loc[self.nodes['stop_i']==i]['lon'].item()
                colors.append(HEX[nth_route])
                self.webView.addPoint(lat,lng,HEX[nth_route])
            else:
                colors.append('w')

    def button_Clear(self):
        self.webView.clearMap(self.maptype_box.currentIndex())
        self.update()
        global number_of_click
        number_of_click=0


    def mouseClick(self, lat, lng):
        global number_of_click
        
        print(f"Clicked on: latitude {lat}, longitude {lng}")
        self.cursor.execute(f"""SELECT A.name, nodexsuper.superstop_i
FROM nodes as A INNER JOIN nodexsuper ON A.stop_i = nodexsuper.stop_i
WHERE ((A.lat - {lat})^2 + (A.lon - {lng})^2) <= ALL (SELECT (lat - {lat})^2 + (lon - {lng})^2 FROM nodes)""")
        self.conn.commit()
        myrows = self.cursor.fetchall()

        # index = random.randint(0,len(myrows))
        if number_of_click == 0:
            self.webView.addPoint(lat, lng, 'green')
            self.from_box.setCurrentIndex(self.from_box.findText(myrows[0][0], Qt.MatchFixedString))
            self.superfrom_i = int(myrows[0][1])

        else:
            self.webView.addPoint(lat, lng, 'red')
            self.to_box.setCurrentIndex(self.to_box.findText(myrows[0][0], Qt.MatchFixedString))
            self.superto_i = int(myrows[0][1])

        number_of_click += 1


class myWebView (QWebEngineView):
    def __init__(self):
        super().__init__()

        # self.maptypes = ["Stamen Terrain", "OpenStreetMap","stamentoner", "cartodbpositron"]
        self.maptypes = ['Esri Satellite']
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


    def addSegment(self, lat1, lng1, lat2, lng2,color):
        js = Template(
        """
        L.polyline(
            [ [{{latitude1}}, {{longitude1}}], [{{latitude2}}, {{longitude2}}] ], {
                "color": '{{color}}',
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


    def addPoint(self, lat, lng, color):
        js = Template(
        """
        L.circleMarker(
            [{{latitude}}, {{longitude}}], {
                "bubblingMouseEvents": true,
                "color": '{{color}}',
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
        ).render(map=self.mymap.get_name(), latitude=lat, longitude=lng,color=color)
        self.page().runJavaScript(js)


    def setMap (self, i):
        # self.mymap = folium.Map(location=[48.8619, 2.3519], tiles=self.maptypes[i], zoom_start=12, prefer_canvas=True)
        self.mymap = folium.Map(location=[48.8619, 2.3519], tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', zoom_start=12, prefer_canvas=True)

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
