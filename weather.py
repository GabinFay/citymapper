#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  7 11:21:15 2022

@author: gabinfay
"""

""" #####################
Running time : ~5 minutes
#########################"""

"""here, we prevent you from walking when its raining
algorithm :
we cut Paris into evenly spaced cells (160 of them), as there are too many nodes to query each one and even reducing them to supernodes by clustering them ain't small enough
for each cell, we query the weather using OpenWeatherMap API, from which we get free access as students to 3000 calls per minute.
then, we associate to each node the number of the cell it's in
we reduce walk to a smaller table short_walk with only distance < 300m otherwise the table is too big and it takes too much time to compute the joins
we copy tables in the database, perform SQL joins in postgres to exclude trips going through the rain from the table walk
then, we can replace walk by this modified walk table in thetp5way or thegraphway

INTERESTING BECAUSE:
    educationaly interesting to work with weather data
    forces to think about data size, performance and limitations
    cool idea
DRAWBACKS:
    unusable due to performance issue : it takes a long time (3 minutes) to perform the joins, and a minute to query the weather so it's unusable 
    short_walk is a drastic reduction of walk
    pretty unuseful and prevents you from the optimal trip
    unnecessary to split Paris into cells : cells have approximately the same weather status (due to poor data ? or just because weather doesn't change much on such a small area)
    when it rains, it rains everywhere and walk is totally forbidden, whilst it's necessary to hop from a subway to a rer
SOLUTION:
    don't mind the rain on trips inferior to 200 meters'
"""

""" Advice : code that was used to build tables is commented out as they are already up and running"""

import psycopg2
from sshtunnel import SSHTunnelForwarder
from sqlalchemy import create_engine
import pandas as pd
import numpy as np
from io import StringIO

def copy_from_stringio(conn, df, table):
    """
    Here we are going save the dataframe in memory 
    and use copy_from() to copy it to the table
    """
    # save dataframe to an in memory buffer
    buffer = StringIO()
    df.to_csv(buffer, index_label='id', header=False, index=False,sep=';')
    buffer.seek(0)
    
    cursor = conn.cursor()
    try:
        cursor.execute(f"""select * from {table}""")
        if not cursor.fetchone():
            cursor.copy_from(buffer, table, sep=";")
            conn.commit()
            print("successfully copied the dataframe into the table")
        else:
            print(f"{table}:won't copy since table ain't empty")
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: %s" % error)
        conn.rollback()
        cursor.close()
        return 1
    cursor.close()

######################################

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
   
conn = psycopg2.connect(**params)
cursor = conn.cursor()
print("database projet connected to hetzner")

local_port = str(server.local_bind_port)
engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format("projet", "projet", "127.0.0.1", local_port, "projet"))

################################

# from pyowm import OWM
# from pyowm.utils import config

# nodes = pd.read_sql("SELECT * FROM \"{}\";".format("nodes"), engine)

# X,Y = np.mgrid[2:2.8:0.05, 48.6:49.1:0.05]
# cells0=np.empty([nodes.shape[0],1])
# for iii, i in nodes.iterrows():
#     lat=i['lat']
#     lon=i['lon']
#     if lon <= 2 or lon >= 2.8 or lat <= 48.6 or lat >= 49.1:
#         cells0[iii] = -1
#     else:
#         b = (lat-48.6,lon-2)
#         cells0[iii] = b[0]//0.05 + (b[1]//0.05)*10

# nodecell = pd.DataFrame(nodes['stop_i'])
# nodecell['cell_i'] = pd.DataFrame(cells0)

# query="""create table nodecell (
#     stop_i numeric,
#     cell_i numeric
#     )"""
# cursor.execute(query)
# conn.commit()

# copy_from_stringio(conn, nodecell, 'nodecell')

# Z = np.vstack(([X.T], [Y.T])).T

# config_dict = config.get_default_config_for_subscription_type('developer')
# owm = OWM('d0c4f93f164c746a4407d679bd8c3b95', config_dict)
# mgr = owm.weather_manager()

# k = 0
# l=0
# cells = pd.DataFrame(np.nan, index=range(160), columns=['lat', 'lon','cell_i','weather'])
# for iy, ix, _ in np.ndindex(Z.shape):
#     if k %2 == 0:
#         observation = mgr.weather_at_coords(float(Z[iy,ix,:][0]),float(Z[iy,ix,:][1]))
#         cells.loc[l] = np.array(list(Z[iy,ix,:])+[l,observation.weather.status],dtype=object)
#         l+=1
#     k +=1
    
# cursor.execute('drop table cells')
# conn.commit()
    
# query="""create table cells (
#     lat numeric,
#     lon numeric,
#     cell_i numeric,
#     weather text
#     )"""
# cursor.execute(query)
# conn.commit()

# copy_from_stringio(conn, cells, 'cells')

query = """select nodecell.stop_i, weather into nodeweather
from cells
INNER JOIN nodecell ON cells.cell_i = nodecell.cell_i
WHERE weather != 'Rain' AND weather != 'Thunderstorm'"""
cursor.execute(query)
conn.commit()

# cursor.execute('drop table walk_weather')
# conn.commit()

query = """select from_stop_i, to_stop_i, d_walk into walk_weather
from short_walk
INNER JOIN nodeweather ON nodeweather.stop_i = short_walk.from_stop_i OR nodeweather.stop_i = short_walk.to_stop_i
GROUP BY from_stop_i, to_stop_i,d_walk"""
cursor.execute(query)
conn.commit()

walk_weather = pd.read_sql("SELECT * FROM \"{}\";".format("walk_weather"), engine)
### Now, you can use this DataFrame in thegraphway and thetp5way

cursor.execute("""drop table nodeweather""")
conn.commit()

