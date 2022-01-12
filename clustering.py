#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  7 11:36:39 2022

@author: gabinfay
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  7 11:21:15 2022

@author: gabinfay
"""

"""here, we group nodes into clusters when they represent the same geographical place accessible by different means of transportation
Motivations :
when running shortest duration algorithm, since we don't take waiting time into account, it is going to take a lot of different routes linked by walking
It takes a lot of buses, the result is different from google maps, and there is a significant combined waiting time that makes the path non optimal
we thought it might be interesting the remove weight in the graph, and just choose the path with the smallest number of transits
but, it turns out the result is 100% walk
SOLUTION : don't take walk into account
ISSUE : how do transit routes since there is a separate node depending of the route taken (EX : chatelet by bus != chatelet by RER')
2 SOLUTIONS :
    1. only keep walking trips with a small distance who'll link RER to buses etc '
    2. cluster nodes based on proximity and represent each cluster by one of its member
Here is the implementation of the second solution :
    Algo : use DBSCAN to cluster the nodes. It's a density based clustering algorithm who allows for single node clusters
    Then, choose node with shortest name in each cluster as a supernode
    associate to each node its corresponding supernode id
    replace from_stop_i / to_stop_i from table combined by the associated supernode ids
    create a graph from this modified combined without taking walk into account
    compute weightless shortest path, and compare with google maps

INTERESTING BECAUSE: it makes sense to cluster similar nodes, it reduces complexity by merging rows

"""

import psycopg2
from sshtunnel import SSHTunnelForwarder
from sqlalchemy import create_engine
import pandas as pd
import numpy as np
from io import StringIO
from sklearn.cluster import DBSCAN


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

###################################

nodes = pd.read_sql("SELECT * FROM \"{}\";".format("nodes"), engine) 
X = nodes[['lat','lon']].to_numpy()

db = DBSCAN(eps=0.0005, min_samples=2).fit(X)
clust=np.concatenate([nodes.to_numpy(), db.labels_[:,np.newaxis]],axis=1)

try:
    cursor.execute('drop table cluster')
    conn.commit()
except Exception as e:
    print(e)
    conn.rollback()

query="""create table cluster (
    stop_i numeric,
    lat numeric,
    lon numeric,
    name text,
    label numeric
    )"""
    
cursor.execute(query)
conn.commit()

copy_from_stringio(conn, pd.DataFrame(clust), 'cluster')

# ###################
# """ Solely for vizualisation purposes
# since we decided not to select lat and lon in cluster caring for reducancy, the query doens't work anymore and we'd have to join nodes and cluster to get it back working"""


# try:
#     cursor.execute('drop table avgcluster')
#     conn.commit()
# except Exception as e:
#     print(e)
#     conn.rollback()

# query ="""select * into avgcluster
#         from
#         ((select lat, lon, label from cluster where label=-1)
#         UNION
#         (select avg(lat), avg(lon), label from cluster group by label having label != -1)) as  oui"""
# cursor.execute(query)
# conn.commit()

# for _,i in self.nodes.iterrows():
#     self.webView.addPoint(i['lat'],i['lon'],'blue')
# avgcluster = pd.read_sql("SELECT * FROM \"{}\";".format("avgcluster"), self.engine) 
# for _,i in avgcluster.iterrows():
#     self.webView.addPoint(i['lat'],i['lon'],'red')

# import matplotlib.pyplot as plt
# plt.scatter(self.nodes['lat'],self.nodes['lon'])
# plt.scatter(avgcluster['lat'],avgcluster['lon'])
# plt.show()

#####################

try:
    cursor.execute('drop table supernodes')
    conn.commit()
except Exception as e:
    print(e)
    conn.rollback()

query="""SELECT * into supernodes
FROM
((SELECT * FROM cluster WHERE label = -1)
UNION
(SELECT DISTINCT on (label) *
FROM cluster
WHERE label != -1
ORDER BY label, length(name))) as oui
"""
cursor.execute(query)
conn.commit()

try:
    cursor.execute('drop table nodexsuper')
    conn.commit()
except Exception as e:
    print(e)
    conn.rollback()

query = """SELECT * into nodexsuper
FROM
((SELECT cluster.stop_i as stop_i, cluster.stop_i as superstop_i
FROM cluster
WHERE label = -1)
UNION
(SELECT A.stop_i as stop_i, B.stop_i as superstop_i
FROM (SELECT * FROM cluster WHERE cluster.label != -1) as A
INNER JOIN (SELECT supernodes.stop_i, supernodes.label FROM supernodes WHERE supernodes.label != -1) as B
ON A.label = B.label)
) as oui
"""
cursor.execute(query)
conn.commit()


try:
    cursor.execute('drop table supercomb')
    conn.commit()
except Exception as e:
    print(e)
    conn.rollback()

query="""
SELECT A.superstop_i as superfrom, B.superstop_i as superto, combined.duration_avg, combined.route_i into supercomb
FROM combined
INNER JOIN nodexsuper as A on combined.from_stop_i = A.stop_i
INNER JOIN nodexsuper as B on combined.to_stop_i = B.stop_i
"""
cursor.execute(query)
conn.commit()