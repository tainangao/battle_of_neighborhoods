import folium as folium
import numpy as np
# Matplotlib and associated plotting modules
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.pyplot as plt

# create a numpy array of length 6 and has linear spacing from the min to max
threshold_scale = np.linspace(df2['PRICE PER SQUARE FOOT'].min(),
                              df2['PRICE PER SQUARE FOOT'].max(),
                              6, dtype=int)
threshold_scale = threshold_scale.tolist() # change the numpy array to a list
threshold_scale[-1] = threshold_scale[-1] + 1 # make sure that the last value of the list is greater than the max price

# let Folium determine the scale.
manhattan_map = folium.Map(location=[40.7831, -73.9712], zoom_start=12)
manhattan_map.choropleth(
    geo_data=jsdata,
    data=df2,
    columns=['ntaname', 'PRICE PER SQUARE FOOT'],
    key_on='feature.properties.ntaname',
    threshold_scale=threshold_scale,
    fill_color= 'YlOrRd',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name='Apartment sales price in NY',
    reset=True
)
manhattan_map

# create map
map_clusters = folium.Map(location=[latitude, longitude], zoom_start=11)

# set color scheme for the clusters
x = np.arange(kclusters)
ys = [i + x + (i * x) ** 2 for i in range(kclusters)]
colors_array = cm.rainbow(np.linspace(0, 1, len(ys)))
rainbow = [colors.rgb2hex(i) for i in colors_array]

# add markers to the map
markers_colors = []
for lat, lon, poi, cluster in zip(manhattan_merged['Latitude'], manhattan_merged['Longitude'],
                                  manhattan_merged['Neighborhood'], manhattan_merged['Cluster Labels']):
    label = folium.Popup(str(poi) + ' Cluster ' + str(cluster), parse_html=True)
    folium.CircleMarker(
        [lat, lon],
        radius=5,
        popup=label,
        color=rainbow[int(cluster) - 1],
        fill=True,
        fill_color=rainbow[int(cluster) - 1],
        fill_opacity=0.7).add_to(map_clusters)

map_clusters

# add markers to the Choropleth
markers_colors = []
for lat, lon, poi, cluster in zip(manhattan_merged['Latitude'], manhattan_merged['Longitude'],
                                  manhattan_merged['Neighborhood'], manhattan_merged['Cluster Labels']):
    label = folium.Popup(str(poi) + ' Cluster ' + str(cluster), parse_html=True)
    folium.CircleMarker(
        [lat, lon],
        radius=5,
        popup=label,
        color=rainbow[int(cluster) - 1],
        fill=True,
        fill_color=rainbow[int(cluster) - 1],
        fill_opacity=0.7).add_to(manhattan_map)

manhattan_map