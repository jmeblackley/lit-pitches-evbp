#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import requests
import pandas as pd
import folium
from folium.plugins import MarkerCluster


# In[ ]:


def parse_tags(row):
    tags = row['tags']
    if isinstance(tags, str):
        tags_dict = eval(tags)
        for key, value in tags_dict.items():
            row[key] = value
    return row

def get_centroid_for_way(way_id):
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    way({way_id});
    out center;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()
    center = data['elements'][0]['center']
    return center['lat'], center['lon']

def is_in_vancouver(lat, lon):
    north = 49.317
    south = 49.198
    west = -123.264
    east = -123.023
    return (south <= lat <= north) and (west <= lon <= east)

def fetch_data_from_osm():
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json][timeout:25];
    (
      node["leisure"="pitch"]["lit"="yes"](48.987427,-123.561859,49.405165,-122.255173);
      way["leisure"="pitch"]["lit"="yes"](48.987427,-123.561859,49.405165,-122.255173);
      relation["leisure"="pitch"]["lit"="yes"](48.987427,-123.561859,49.405165,-122.255173);
    );
    out body;
    >;
    out skel qt;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    return response.json()




# In[ ]:


data = fetch_data_from_osm()

# Convert to DataFrame
elements = data['elements']
df = pd.DataFrame(elements)

# Processing data
df = df.apply(parse_tags, axis=1)
df.drop('tags', axis=1, inplace=True)
df.rename(columns={'id': 'OSM ID', 'type': 'Type', 'lat': 'Latitude', 'lon': 'Longitude'}, inplace=True)

# Handle missing data for 'ways' and add 'In Vancouver' tag
for index, row in df.iterrows():
    if row['Type'] == 'way' and pd.isna(row['Latitude']):
        lat, lon = get_centroid_for_way(row['OSM ID'])
        df.at[index, 'Latitude'] = lat
        df.at[index, 'Longitude'] = lon
    df.at[index, 'In Vancouver'] = 'Yes' if is_in_vancouver(row['Latitude'], row['Longitude']) else 'No'


# In[ ]:


# Changing map_center to Grandview Park coordinates
map_center = [49.27340023847645, -123.07109064858199]
map_vancouver = folium.Map(location=map_center, zoom_start=12)

# Initialize a MarkerCluster
marker_cluster = MarkerCluster().add_to(map_vancouver)

# Adding markers to the MarkerCluster
for index, row in df.iterrows():
    if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
        popup_text = f"Park Name: {row.get('name', 'No Name')}<br>"
        popup_text += f"In Vancouver: {row['In Vancouver']}"
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            popup=popup_text
        ).add_to(marker_cluster)

# Add Esri Satellite Imagery as the tile layer
esri_imagery = folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Satellite',
    overlay=False,
    control=True
).add_to(map_vancouver)

# Optionally, add other tile layers for more basemap options
folium.TileLayer('OpenStreetMap').add_to(map_vancouver)

# Add layer control to switch between basemaps
folium.LayerControl().add_to(map_vancouver)

# Save the map to an HTML file
map_file = 'lit_fields_vancouver_map_satellite.html'
map_vancouver.save(map_file)

print(f"Map with satellite imagery has been saved as {map_file}")

