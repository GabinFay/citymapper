### Integrer des tables pandas et des fichiers csv dans des bases de données immédiatement ###

import pandas as pd
import psycopg2
from io import StringIO
import geojson
from sshtunnel import SSHTunnelForwarder
from sqlalchemy import create_engine
from schema import sql_schema


import sys
from os.path import expanduser
sys.path.append(expanduser('~')+'/SQL/Data')
dp = expanduser('~')+'/SQL/Data/'

# user = 'projet'
# dbname = 'projet'
# password = 'projet'
# conn = psycopg2.connect(database=dbname, user=user, host="localhost", password=password)
# cursor = conn.cursor()
# engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format("projet", "projet", "127.0.0.1", 5432, "projet"))


### Toggle this to directly manage the server database #############

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
   
    conn = psycopg2.connect(**params)
    cursor = conn.cursor()
    print("database projet connected to the remote server")
    local_port = str(server.local_bind_port)
    print('dm')
    engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format("projet", "projet", "127.0.0.1", local_port, "projet"))

except:
    print("Connection to the remote server failed")

""" copy DataFrame into a table defined in the schema of the db """
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
            print(f"{table} : won't copy since table ain't empty")
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: %s" % error)
        conn.rollback()
        cursor.close()
        return 1
    cursor.close()

def create_nodes():
    nodes = pd.read_csv(dp+'network_'+'nodes.csv', delimiter = ';')
    nodes.columns= nodes.columns.str.lower()
    nodes['name'] = nodes['name'].str.lower()
    copy_from_stringio(conn, nodes, 'nodes')
    
def create_temporal_day():
    import datetime
    
    temporal_day = pd.read_csv(dp+'network_temporal_day.csv', delimiter = ';')
    temporal_day.columns = temporal_day.columns.str.lower()
    def secs(time_ut):
        """return number of seconds since midnight so we can later compare dep_time_ut with our current unix time"""
        relative_time = datetime.datetime.utcfromtimestamp(time_ut).strftime('%Y-%m-%d %H:%M:%S')[-8:].split(':')
        return int(relative_time[0])*3600 + int(relative_time[1])*60 + int(relative_time[2])
    
    dep = temporal_day['dep_time_ut']
    dep = dep.apply(secs)
    arr = temporal_day['arr_time_ut']
    arr = arr.apply(secs)
    temporal_day['dep_time_ut'] = dep
    temporal_day['arr_time_ut'] = arr
    
    copy_from_stringio(conn, temporal_day, 'temporal_day')

##### routes ########

def create_routes():
    with open(dp+'routes.geojson') as f:
        gj = geojson.load(f)['features']
    
    data = [[line['properties']['route_type'],line['properties']['route_name'],line['properties']['route_I']] for line in gj]
    routes = pd.DataFrame(data, columns=['route_type', 'route_name', 'route_I'])
    routes.columns= routes.columns.str.lower()
    copy_from_stringio(conn, routes, 'routes')
    
    cursor.execute("""
    select route_type, route_name, min(route_i) as route_rps_i into route_rps
    from routes
    group by route_type, route_name
    """)
    conn.commit()
    
    cursor.execute("""
    select route_i, route_rps.route_rps_i into routexsuper
    from routes INNER JOIN route_rps
    ON routes.route_type=route_rps.route_type AND routes.route_name = route_rps.route_name
    """)
    conn.commit()

###################### combined ##############

def create_combined():
    comb = pd.read_csv(dp+'network_combined.csv', delimiter=';')
    comb.columns= comb.columns.str.lower()
    comb_split_routes = comb['route_i_counts'].str.split(',|:')
    comb_split_routes = pd.DataFrame(comb_split_routes)
    comb = pd.concat([comb[['from_stop_i','to_stop_i','duration_avg']],comb_split_routes],axis=1)
    comb=comb.explode('route_i_counts')
    comb=comb.iloc[::2]
    
    copy_from_stringio(conn, comb, 'combined')
    
    cursor.execute("""select from_stop_i, to_stop_i, duration_avg, routexsuper.route_rps_i into super_route_comb
    from combined
    INNER JOIN routexsuper ON combined.route_i = routexsuper.route_i""")
    conn.commit()

# #######################################

def create_stoproutename():
    cursor.execute("""
        SELECT * into stopxroute
        FROM
        ((SELECT from_stop_i as stop_i, route_i
        FROM combined)
        UNION
        (SELECT to_stop_i as stop_i, route_i
        FROM combined)) as yes""")
    conn.commit()
    cursor.execute("""select distinct nodes.name, A.stop_I, route_type, route_name into stoproutename
    from stopxroute as A
    INNER JOIN routes ON A.route_i = routes.route_i
    INNER JOIN nodes ON A.stop_i = nodes.stop_i
    order by A.stop_I""")
    conn.commit()

# ############## walk + combxwalk + short_walk ##############

def create_walk():
    walk = pd.read_csv(dp+'network_walk.csv', delimiter=';')
    walk.columns= walk.columns.str.lower()
    walk['d_walk'] /= 2.5         ### we assumed a person walks at 2.5 m.s-1  
    walk = walk[["from_stop_i","to_stop_i","d_walk"]].rename(columns={'d_walk': 'duration_avg'})
    walk['route_i'] = 'w'
    comb = pd.read_sql("SELECT * FROM \"{}\";".format("combined"), engine)  
    combxwalk = pd.concat([walk,comb])
    copy_from_stringio(conn, walk, 'walk')
    copy_from_stringio(conn, combxwalk, 'combxwalk')
    
    query="""select * into short_walk from walk WHERE d_walk < 300"""
    cursor.execute(query)
    conn.commit()
    
############## RUNNING ZONE

cursor.execute('DROP SCHEMA public CASCADE')
conn.commit()
cursor.execute('CREATE SCHEMA public')
conn.commit()
cursor.execute('GRANT ALL ON SCHEMA public TO postgres')
conn.commit()
cursor.execute('GRANT ALL ON SCHEMA public TO public')
conn.commit()


for i in sql_schema.split(';'):
    try:
        cursor.execute(i)
        conn.commit()
    except psycopg2.ProgrammingError as err:
        # print("we caught the exception : don't mind")
        # print(err)
        conn.rollback()

create_nodes()
create_temporal_day()
create_routes()
create_combined()
create_stoproutename()
create_walk()

