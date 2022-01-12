#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 24 13:14:03 2021

@author: gabinfay
"""
import requests, lxml, re, json, datetime, urllib.request
from bs4 import BeautifulSoup
import psycopg2
from sqlalchemy import create_engine

user = 'projet'
dbname = 'projet'
password = 'projet'
conn = psycopg2.connect(database=dbname, user=user, host="localhost", password=password)
cursor = conn.cursor()
engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format("projet", "projet", "127.0.0.1", 5432, "projet"))

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


def get_google_images_data(soup, query_name, html, headers, pathtofolder):

    # print('\nGoogle Images Metadata:')
    # for google_image in soup.select('.isv-r.PNCib.MSM1fd.BUooTd'):
    #     title = google_image.select_one('.VFACy.kGQAp.sMi44c.lNHeqe.WGvvNb')['title']
    #     source = google_image.select_one('.fxgdke').text
    #     link = google_image.select_one('.VFACy.kGQAp.sMi44c.lNHeqe.WGvvNb')['href']
    #     print(f'{title}\n{source}\n{link}\n')

    # this steps could be refactored to a more compact
    all_script_tags = soup.select('script')

    # # https://regex101.com/r/48UZhY/4
    matched_images_data = ''.join(re.findall(r"AF_initDataCallback\(([^<]+)\);", str(all_script_tags)))

    # https://kodlogs.com/34776/json-decoder-jsondecodeerror-expecting-property-name-enclosed-in-double-quotes
    # if you try to json.loads() without json.dumps() it will throw an error:
    # "Expecting property name enclosed in double quotes"
    matched_images_data_fix = json.dumps(matched_images_data)
    matched_images_data_json = json.loads(matched_images_data_fix)

    # https://regex101.com/r/pdZOnW/3
    matched_google_image_data = re.findall(r'\[\"GRID_STATE0\",null,\[\[1,\[0,\".*?\",(.*),\"All\",', matched_images_data_json)

    # https://regex101.com/r/NnRg27/1
    matched_google_images_thumbnails = ', '.join(
        re.findall(r'\[\"(https\:\/\/encrypted-tbn0\.gstatic\.com\/images\?.*?)\",\d+,\d+\]',
                   str(matched_google_image_data))).split(', ')

    # print('Google Image Thumbnails:')  # in order
    for fixed_google_image_thumbnail in matched_google_images_thumbnails:
        # https://stackoverflow.com/a/4004439/15164646 comment by Frédéric Hamidi
        google_image_thumbnail_not_fixed = bytes(fixed_google_image_thumbnail, 'ascii').decode('unicode-escape')

        # after first decoding, Unicode characters are still present. After the second iteration, they were decoded.
        google_image_thumbnail = bytes(google_image_thumbnail_not_fixed, 'ascii').decode('unicode-escape')
        # print(google_image_thumbnail)

    # removing previously matched thumbnails for easier full resolution image matches.
    removed_matched_google_images_thumbnails = re.sub(
        r'\[\"(https\:\/\/encrypted-tbn0\.gstatic\.com\/images\?.*?)\",\d+,\d+\]', '', str(matched_google_image_data))

    # https://regex101.com/r/fXjfb1/4
    # https://stackoverflow.com/a/19821774/15164646
    matched_google_full_resolution_images = re.findall(r"(?:'|,),\[\"(https:|http.*?)\",\d+,\d+\]",
                                                       removed_matched_google_images_thumbnails)

    # print('\nFull Resolution Images:')  # in order
    # for index, fixed_full_res_image in enumerate(matched_google_full_resolution_images):
    fixed_full_res_image = matched_google_full_resolution_images[0]
    # https://stackoverflow.com/a/4004439/15164646 comment by Frédéric Hamidi
    original_size_img_not_fixed = bytes(fixed_full_res_image, 'ascii').decode('unicode-escape')
    original_size_img = bytes(original_size_img_not_fixed, 'ascii').decode('unicode-escape')
    # print(original_size_img)

    # ------------------------------------------------
    # Download original images

    # print(f'Downloading {index} image...')
    opener=urllib.request.build_opener()
    opener.addheaders=[('User-Agent','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582')]
    urllib.request.install_opener(opener)
    try:
        urllib.request.urlretrieve(original_size_img, pathtofolder+'/'+query_name+'.jpg')
    except:
        pass

def get_suggested_search_data():
    for suggested_search in soup.select('.PKhmud.sc-it.tzVsfd'):
        suggested_search_name = suggested_search.select_one('.hIOe2').text
        suggested_search_link = f"https://www.google.com{suggested_search.a['href']}"

        # https://regex101.com/r/y51ZoC/1
        suggested_search_chips = ''.join(re.findall(r'=isch&chips=(.*?)&hl=en-US', suggested_search_link))
        print(f"{suggested_search_name}\n{suggested_search_link}\n{suggested_search_chips}\n")

    # this steps could be refactored to a more compact
    all_script_tags = soup.select('script')

    # https://regex101.com/r/48UZhY/6
    matched_images_data = ''.join(re.findall(r"AF_initDataCallback\(({key: 'ds:1'.*?)\);</script>", str(all_script_tags)))

    # https://kodlogs.com/34776/json-decoder-jsondecodeerror-expecting-property-name-enclosed-in-double-quotes
    # if you try to json.loads() without json.dumps() it will throw an error:
    # "Expecting property name enclosed in double quotes"
    matched_images_data_fix = json.dumps(matched_images_data)
    matched_images_data_json = json.loads(matched_images_data_fix)

    # search for only suggested search thumbnails related
    # https://regex101.com/r/ITluak/2
    suggested_search_thumbnails_data = ','.join(re.findall(r'{key(.*?)\[null,\"Size\"', matched_images_data_json))

    # https://regex101.com/r/MyNLUk/1
    suggested_search_thumbnail_links_not_fixed = re.findall(r'\"(https:\/\/encrypted.*?)\"', suggested_search_thumbnails_data)

    # print('Suggested Search Thumbnails:')  # in order
    for suggested_search_fixed_thumbnail in suggested_search_thumbnail_links_not_fixed:
        # https://stackoverflow.com/a/4004439/15164646 comment by Frédéric Hamidi
        suggested_search_thumbnail = bytes(suggested_search_fixed_thumbnail, 'ascii').decode('unicode-escape')
        print(suggested_search_thumbnail)

headers = {
    "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
}

pathtofolder='/home/gabinfay/SQL/Scrape/'

cursor.execute("""select route_type, route_name from routes
group by route_type, route_name
ORDER BY route_type
""")

conn.commit()
rows = cursor.fetchall()
for ii,i in enumerate(rows):
    print(f"""{ii}"""+'/'+f'{len(rows)}')
    query = str_route_type(int(i[0]))+' '+str(i[1])+' Paris'
    params = {
    "q": query,
    "tbm": "isch",
    "ijn": "0",
    }
    print('')
    html = requests.get("https://www.google.com/search", params=params, headers=headers)
    print('')
    soup = BeautifulSoup(html.text, 'lxml')
    get_google_images_data(soup, query, html, headers, pathtofolder)
    



