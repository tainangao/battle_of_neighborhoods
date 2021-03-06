import requests
import logging
import time
import pandas as pd
from shapely.geometry import Point, shape
from shapely.geometry.polygon import Polygon
import json
from pandas import json_normalize  # tranform JSON file into a pandas dataframe

logger = logging.getLogger("root")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()  # create console handler
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

# Set your Google API key here.

# Even if using the free 2500 queries a day, its worth getting an API key since the rate limit is 50 / second.
# With API_KEY = None, you will run into a 2 second delay every 10 requests or so.
# With a "Google Maps Geocoding API" key from https://console.developers.google.com/apis/,
# the daily limit will be 2500, but at a much faster rate.
# Example: API_KEY = 'AIzaSyC9azed9tLdjpZNjg2_kVePWvMIBq154eA'
GEOCODING_API_KEY = 'AIzaSyDDxZ_AAK8zH78td088DYo3vAP6_tu1Wkc'
# Backoff time sets how many minutes to wait between google pings when your API limit is hit
GEOCODING_BACKOFF_MINUTE = 30
# Set your output file name here.
output_filename = 'sales_geo.csv'
# Set your input file here
input_filename = 'dags/data/sales.csv'
# Specify the column name in your input data that contains addresses here
address_column_name = "full_address"
# Return Full Google Results? If True, full JSON results from Google are included in output
RETURN_FULL_RESULTS = False

# Make a big list of all of the addresses to be processed.
df_sales = pd.read_csv(input_filename)
addresses = df_sales[address_column_name].tolist()  # TODO


# credit goes to https://github.com/richiemorrisroe/PPR
def get_geocoding_result(address, api_key=None, return_full_response=False):
    """
    Get geocode results from Google Maps Geocoding API.

    Note, that in the case of multiple google geocode reuslts, this function returns details of the FIRST result.

    @param address: String address as accurate as possible. For Example "18 Grafton Street, Dublin, Ireland"
    @param api_key: String API key if present from google.
                    If supplied, requests will use your allowance from the Google API. If not, you
                    will be limited to the free usage of 2500 requests per day.
    @param return_full_response: Boolean to indicate if you'd like to return the full response from google. This
                    is useful if you'd like additional location details for storage or parsing later.
    """
    # Set up your Geocoding url
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json?address={}".format(address)
    if api_key is not None:
        geocode_url = geocode_url + "&key={}".format(api_key)

    # Ping google for the reuslts:
    results = requests.get(geocode_url)
    # Results will be in JSON format - convert to dict using requests functionality
    results = results.json()

    # if there's no results or an error, return empty results.
    if len(results['results']) == 0:
        output = {
            # "formatted_address": None,
            "latitude": None,
            "longitude": None,
            # "accuracy": None,
            # "google_place_id": None,
            # "type": None,
            # "postcode": None
        }
    else:
        answer = results['results'][0]
        output = {
            # "formatted_address": answer.get('formatted_address'),
            "latitude": answer.get('geometry').get('location').get('lat'),
            "longitude": answer.get('geometry').get('location').get('lng'),
            # "accuracy": answer.get('geometry').get('location_type'),
            # "google_place_id": answer.get("place_id"),
            # "type": ",".join(answer.get('types')),
            # "postcode": ",".join([x['long_name'] for x in answer.get('address_components')
            #                       if 'postal_code' in x.get('types')])
        }

    # Append some other details:
    output['input_string'] = address
    output['number_of_results'] = len(results['results'])
    output['status'] = results.get('status')
    if return_full_response is True:
        output['response'] = results

    return output


# credit goes to https://github.com/richiemorrisroe/PPR
def get_geocoding_results(api_key=None, return_full_response=False):
    # Create a list to hold results
    results = []
    # Go through each address in turn
    for address in addresses:
        # While the address geocoding is not finished:
        geocoded = False
        while geocoded is not True:
            # Geocode the address with google
            try:
                geocode_result = get_geocoding_result(address, GEOCODING_API_KEY,
                                                      return_full_response=RETURN_FULL_RESULTS)
            except Exception as e:
                logger.exception(e)
                logger.error("Major error with {}".format(address))
                logger.error("Skipping!")
                geocoded = True

            # If we're over the API limit, backoff for a while and try again later.
            if geocode_result['status'] == 'OVER_QUERY_LIMIT':
                logger.info("Hit Query Limit! Backing off for a bit.")
                time.sleep(GEOCODING_BACKOFF_MINUTE * 60)  # sleep for 30 minutes
                geocoded = False
            else:
                # If we're ok with API use, save the results
                # Note that the results might be empty / non-ok - log this
                if geocode_result['status'] != 'OK':
                    logger.warning("Error geocoding {}: {}".format(address, geocode_result['status']))
                logger.debug("Geocoded: {}: {}".format(address, geocode_result['status']))
                results.append(geocode_result)
                geocoded = True

        # Print status every 100 addresses
        if len(results) % 100 == 0:
            logger.info("Completed {} of {} address".format(len(results), len(addresses)))

        # Every 500 addresses, save progress to file(in case of a failure so you have something!)
        if len(results) % 500 == 0:
            pd.DataFrame(results).to_csv("{}_bak".format(output_filename))

    # All done
    logger.info("Finished geocoding all addresses")
    # Write the full results to csv using the pandas library.
    pd.DataFrame(results).to_csv(output_filename, encoding='utf8')
    # return pd.DataFrame(results)


def merge_dfs(csv1: str, csv2: str) -> pd.DataFrame:
    df1 = pd.read_csv(csv1)
    df2 = pd.read_csv(csv2)
    df = pd.merge([df1, df2], how='inner', left_on='full_address', right_on='input_string')
    # df.to_csv('dags/data/sales_enriched.csv', columns=['full_address', 'sale_price', 'latitude', 'longitude'], index=False)
    return df


# df_geo = get_geocoding_results()
# df = df_sales.merge(df_geo, how='inner', left_on='full_address', right_on='input_string')


def assign_ntaname(csv1: str, csv2: str):
    with open('Neighborhood Tabulation Areas.geojson') as f:
        jsdata = json.load(f)
        # keep Manhattan only data
        mn_geojson = []
        for element in jsdata["features"]:
            if 'Manhattan' in element['properties']['boro_name']:
                mn_geojson.append(element)  # new_features has the one's you want

    df = merge_dfs('sales.csv', 'sales_geo.csv')
    results = []
    i = 0
    length = len(df['full_address'])
    while i < length:
        # construct point based on lat/long returned by geocoder
        point = Point(df['longitude'][i], df['latitude'][i])

        # check each polygon to see if it contains the point
        for feature in mn_geojson['features']:
            polygon = shape(feature['geometry'])
            if polygon.contains(point):
                results.append(feature)

        i += 1
    results = pd.DataFrame(results)
    logger.info(results.head())
    results1 = results['properties'].to_dict()
    results2 = pd.DataFrame(results1)
    logger.info(results2.head())
    results3 = results2.transpose()
    logger.info(results3.head())
    results4 = pd.DataFrame(results3['ntaname'])
    logger.info(results2.head())

    df = pd.concat([df, results4], sort=False, axis=1)
    logger.info("Added 'natname' column.")
    logger.info(df.head())
    df.to_csv('dags/data/sales_enriched.csv')
