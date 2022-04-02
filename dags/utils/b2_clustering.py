import requests
import logging
import time
import pandas as pd
from shapely.geometry import Point, shape
from shapely.geometry.polygon import Polygon
import json
from geopy.geocoders import Nominatim  # convert an address into latitude and longitude values
from sklearn.cluster import KMeans
# Matplotlib and associated plotting modules
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.pyplot as plt

logger = logging.getLogger("root")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()  # create console handler
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)


def clustering() -> pd.DataFrame:
    with open('newyork_data.json') as json_data:
        newyork_data = json.load(json_data)
    neighborhoods_data = newyork_data['features']
    logger.info("neighborhoods_data[0]\t\n{}".format(neighborhoods_data[0]))

    # define the dataframe columns
    column_names = ['Borough', 'Neighborhood', 'Latitude', 'Longitude']

    # instantiate the dataframe
    neighborhoods = pd.DataFrame(columns=column_names)
    for data in neighborhoods_data:
        borough = neighborhood_name = data['properties']['borough']
        neighborhood_name = data['properties']['name']

        neighborhood_latlon = data['geometry']['coordinates']
        neighborhood_lat = neighborhood_latlon[1]
        neighborhood_lon = neighborhood_latlon[0]

        neighborhoods = neighborhoods.append({'Borough': borough,
                                              'Neighborhood': neighborhood_name,
                                              'Latitude': neighborhood_lat,
                                              'Longitude': neighborhood_lon}, ignore_index=True)
    logger.info("neighborhoods.head()\t\n{}".format(neighborhoods.head()))
    manhattan_data = neighborhoods[neighborhoods['Borough'] == 'Manhattan'].reset_index(drop=True)
    logger.info("manhattan_data.head()\t\n{}".format(manhattan_data.head()))

    address = 'Manhattan, NY'
    geolocator = Nominatim(user_agent="ny_explorer")
    location = geolocator.geocode(address)
    latitude = location.latitude
    longitude = location.longitude
    logger.info('The geograpical coordinate of Manhattan are {}, {}.'.format(latitude, longitude))

    LIMIT = 100  # limit of number of venues returned by Foursquare API
    radius = 500  # define radius

    def getNearbyVenues(names, latitudes, longitudes, radius=500):
        venues_list = []
        for name, lat, lng in zip(names, latitudes, longitudes):
            print(name)

            # create the API request URL
            url = 'https://api.foursquare.com/v2/venues/explore?&client_id={}&client_secret={}&v={}&ll={},{}&radius={}&limit={}'.format(
                CLIENT_ID,
                CLIENT_SECRET,
                VERSION,
                lat,
                lng,
                radius,
                LIMIT)

            # make the GET request
            results = requests.get(url).json()["response"]['groups'][0]['items']

            # return only relevant information for each nearby venue
            venues_list.append([(
                name,
                lat,
                lng,
                v['venue']['name'],
                v['venue']['location']['lat'],
                v['venue']['location']['lng'],
                v['venue']['categories'][0]['name']) for v in results])

        nearby_venues = pd.DataFrame([item for venue_list in venues_list for item in venue_list])
        nearby_venues.columns = ['Neighborhood',
                                 'Neighborhood Latitude',
                                 'Neighborhood Longitude',
                                 'Venue',
                                 'Venue Latitude',
                                 'Venue Longitude',
                                 'Venue Category']

        return (nearby_venues)

    manhattan_venues = getNearbyVenues(names=manhattan_data['Neighborhood'],
                                       latitudes=manhattan_data['Latitude'],
                                       longitudes=manhattan_data['Longitude']
                                       )

    logger.info("manhattan_venues.shape\t\n{}".format(manhattan_venues.shape))
    logger.info("manhattan_venues.head()\t\n{}".format(manhattan_venues.head()))
    logger.info("how many venues were returned for each neighborhood")
    logger.info(manhattan_venues.groupby('Neighborhood').count())
    logger.info('There are {} uniques categories.'.format(len(manhattan_venues['Venue Category'].unique())))

    # analyze each neighborhood
    # one hot encoding
    manhattan_onehot = pd.get_dummies(manhattan_venues[['Venue Category']], prefix="", prefix_sep="")
    # add neighborhood column back to dataframe
    manhattan_onehot['Neighborhood'] = manhattan_venues['Neighborhood']
    # move neighborhood column to the first column
    fixed_columns = [manhattan_onehot.columns[-1]] + list(manhattan_onehot.columns[:-1])
    manhattan_onehot = manhattan_onehot[fixed_columns]
    # manhattan_onehot.head()
    logger.info("manhattan_onehot.shape\t\n{}".format(manhattan_onehot.shape))

    logger.info("group rows by neighborhood and take the mean frequency of occurrence of each category")
    manhattan_grouped = manhattan_onehot.groupby('Neighborhood').mean().reset_index()
    logger.info(manhattan_grouped.shape)
    logger.info(manhattan_grouped)

    # Find out the most common venues in each neighborhood
    def return_most_common_venues(row, num_top_venues):
        row_categories = row.iloc[1:]
        row_categories_sorted = row_categories.sort_values(ascending=False)

        return row_categories_sorted.index.values[0:num_top_venues]

    num_top_venues = 10

    indicators = ['st', 'nd', 'rd']

    # create columns according to number of top venues
    columns = ['Neighborhood']
    for ind in np.arange(num_top_venues):
        try:
            columns.append('{}{} Most Common Venue'.format(ind + 1, indicators[ind]))
        except:
            columns.append('{}th Most Common Venue'.format(ind + 1))

    # create a new dataframe
    neighborhoods_venues_sorted = pd.DataFrame(columns=columns)
    neighborhoods_venues_sorted['Neighborhood'] = manhattan_grouped['Neighborhood']

    for ind in np.arange(manhattan_grouped.shape[0]):
        neighborhoods_venues_sorted.iloc[ind, 1:] = return_most_common_venues(manhattan_grouped.iloc[ind, :],
                                                                              num_top_venues)

    neighborhoods_venues_sorted.head()
    manhattan_k = manhattan_grouped.drop('Neighborhood', axis=1)
    logger.info("manhattan_k.head()\t\n{}".format(manhattan_k.head()))
    Sum_of_squared_distances = []
    K = range(1, 15)
    for k in K:
        km = KMeans(n_clusters=k)
        km = km.fit(manhattan_k)
        Sum_of_squared_distances.append(km.inertia_)
    plt.plot(K, Sum_of_squared_distances, 'bx-')
    plt.xlabel('k')
    plt.ylabel('Sum_of_squared_distances')
    plt.title('Elbow Method For Optimal K')
    plt.show()

    # set number of clusters
    kclusters = 5

    manhattan_grouped_clustering = manhattan_grouped.drop('Neighborhood', 1)

    # run k-means clustering
    kmeans = KMeans(n_clusters=kclusters, random_state=0).fit(manhattan_grouped_clustering)

    # check cluster labels generated for each row in the dataframe
    kmeans.labels_[0:10]

    # add clustering labels
    neighborhoods_venues_sorted.insert(0, 'Cluster Labels', kmeans.labels_)

    manhattan_merged = manhattan_data

    # merge nyc_grouped with nyc_data to add latitude/longitude for each neighborhood
    manhattan_merged = manhattan_merged.join(neighborhoods_venues_sorted.set_index('Neighborhood'), on='Neighborhood')

    # check the last columns!
    logger.info("manhattan_merged.head()\t\n{}".format(manhattan_merged.head()))
    manhattan_merged.dropna(subset=['Cluster Labels'], axis=0, how='any', inplace=True)
