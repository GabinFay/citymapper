sql_schema = """create table nodes (
stop_i numeric,
lat numeric,
lon numeric,
name text,
primary key (stop_i)
);

create table walk (
from_stop_i numeric,
to_stop_i numeric,
d_walk numeric,
route_i text
);

create table combined(
from_stop_i numeric,
to_stop_i numeric,
duration_avg numeric,
route_i numeric
);

create table routes(
route_type NUMERIC,
route_name TEXT,
route_i NUMERIC
);

create table temporal_day(
from_stop_i numeric,
to_stop_i numeric,
dep_time_ut numeric,
arr_time_ut numeric,
route_type numeric ,
trip_i numeric,
seq numeric ,
route_i numeric
);

create table combxwalk(
from_stop_i numeric,
to_stop_i numeric,
duration_avg numeric,
route_i text
)
"""