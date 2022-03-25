import pandas as pd
import numpy as np
import logging
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.pyplot as plt
from scipy.stats import norm

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

df = pd.read_excel('dags/data/2021_manhattan.xlsx', skiprows=7, usecols="B,I,L,M,P,T")
df.columns = ['neighborhood', 'address', 'residential_units', 'commercial_units', 'gross_square_feet', 'sale_price']
record_cnt1 = df.shape[0]
logger.info('Successfully read data into a DataFrame. Current dataframe size: {}'.format(df.shape))
df['commercial_units'].replace(0, np.nan, inplace=True)
df['sale_price'].replace(0, np.nan, inplace=True)
df['gross_square_feet'].replace(0, np.nan, inplace=True)

missing_data = df.isnull()
for column in missing_data.columns.values.tolist():
    logger.info(column)
    logger.info('{}\n'.format(missing_data[column].value_counts()))

# if a property has commercial unit(s), drop it
df = df[df.commercial_units.isnull()]
record_cnt2 = df.shape[0]
logger.info("Excluded not-residential data points. Dropped {0:.2f}% of the data so far.".format(
    (record_cnt1 - record_cnt2) / record_cnt1 * 100))
df.drop(['commercial_units'], axis=1, inplace=True)

df.dropna(subset=["sale_price"], axis=0, inplace=True)
record_cnt3 = df.shape[0]
logger.info('Excluded data points that lack sale price. Dropped {0:.2f}% of the data so far.'.format(
    (record_cnt1 - record_cnt3) / record_cnt1 * 100))

# actually, let's not drop these data, because -
# 1. gross_square_feet & sale_price are very weakly correlated (0.041251)
# 2. I don't want to lose 90% of the data
# df.dropna(subset=["gross_square_feet"], axis=0, inplace=True)
# record_cnt3 = df.shape[0]

df.reset_index(drop=True, inplace=True)

missing_data = df.isnull()
for column in missing_data.columns.values.tolist():
    logger.info(column)
    logger.info('{}\n'.format(missing_data[column].value_counts()))

# print(df['sale_price'].plot(kind='box'))
df['sale_price'].describe(include='all').map(lambda x: '{:,.2f}'.format(x))
mean, std = np.mean(df['sale_price']), np.std(df['sale_price'])
z_score = np.abs((df['sale_price'] - mean) / std)
threshold = 1
good = z_score < threshold
# visual_scatter = np.random.normal(size=df['sale_price'].size)
# plt.scatter(df['sale_price'][good], visual_scatter[good], s=2, label="Good", color="#4CAF50")
# plt.scatter(df['sale_price'][~good], visual_scatter[~good], s=8, label="Bad", color="#F44336")
# plt.legend();
df = df[good]

logger.info("Rejected {} points".format((~good).sum()))
logger.info("z-score of {} corresponds to a prob of {:0.2f}%".format(threshold, 100 * 2 * norm.sf(threshold)))
record_cnt4 = df.shape[0]
logger.info("Excluded sale price outliers. Dropped {0:.2f}% of the data so far.".format(
    (record_cnt1 - record_cnt4) / record_cnt1 * 100))
logger.info("Current dataframe size: {}".format(df.shape))

df['neighborhood'] = df['neighborhood'].apply(lambda x: x.title())
df['full_address'] = df['address'] + ', ' + df['neighborhood'] + ', Manhattan, NY, USA'

df.to_csv('dags/data/sales.csv', index=False, columns=['full_address', 'sale_price'])
