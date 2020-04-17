# common libs
import numpy as np
import pandas as pd
from scipy import integrate

def jitter_time(num_rows):
    time_ideal = pd.date_range(end=pd.Timestamp.now(), periods=num_rows,
                               freq='10S')
    time_deltas  = pd.to_timedelta(np.random.uniform(-1, 1, num_rows),
                                   unit='S')
    time_actual = time_ideal + time_deltas
    return time_actual

# return (time, measure)
def random_data():
    num_rows = 1000000
    time_actual = jitter_time(num_rows)

    #data  = np.random.uniform(0.99, 1.01, num_rows)
    # lognormal(0,1) has mean exp(0.5) or about 1.65
    measure = np.random.lognormal(0, 1, num_rows)

    df = pd.DataFrame(data={'measure': measure}, index=time_actual)
    #df = pd.DataFrame(data={'time': time_actual, 'measure': data})
    #df = df.set_index(['time'])
    return df

# return (time, id, ct, measure)
def multi_random_data():
    ids = ['5737333034370A220D', '5737333034370D0E14']
    cts = ['ct1', 'ct2', 'ct3', 'ct4']

    num_rows = 1000000
    time_actual = jitter_time(num_rows)
    ct = [*map(lambda x: cts[x], np.random.randint(0,4, num_rows))]
    id = [*map(lambda x: ids[x], np.random.randint(0,2, num_rows))]
    measure = np.random.lognormal(0, 1, num_rows)

    df = pd.DataFrame(data={'id':id, 'ct':ct, 'measure':measure},
                      index=time_actual)
    return df

def read_raw(filename):
    raw_data = pd.read_csv(filename, delim_whitespace=True, comment='#',
                           index_col=0, parse_dates=True)
    return raw_data

def make_hourly(raw_data):
    # provide a zero just before the first point, so integration sees
    # the first point but nothing before it
    raw_data = pd.concat(
        [pd.DataFrame(
            index=[raw_data.index.min() - pd.DateOffset(seconds=1)],
            data=[0], columns=['measure']), raw_data])

    # Bucket boundaries we want, with some left padding to be sure we
    # can set the first to zero
    buckets = pd.DataFrame(
        pd.date_range(
            start=raw_data.index.min().floor('H') - pd.DateOffset(hours=1),
            end=raw_data.index.max().ceil('H'), freq='H')).set_index(0)

    # Insert bucket boundaries into the raw dataset (they'll have NaN
    # measures)
    raw_data_with_buckets = raw_data.append(buckets).sort_index()

    # Set the left edge to zero
    raw_data_with_buckets.at[raw_data_with_buckets.index.min()]=0

    # Fill interpolated values at the bucket boundaries
    interpolated = raw_data_with_buckets.interpolate(method='time',
        limit_area='inside').dropna()

    # Integrate the data series to get cumulative energy (kWh)
    cum_kwh = pd.DataFrame(
        index=interpolated.index, columns=['measure'],
        data=integrate.cumtrapz(
            interpolated['measure'],
            x=interpolated.index, initial=0)
        / (1000 * np.timedelta64(1, 'h')))

    # Downsample to the buckets, diff to get energy per bucket, trim
    # the leading zero
    hourly = cum_kwh.resample(rule='H',closed='right',label='right',
        loffset='-1H').max().diff().dropna().iloc[1:]
    return hourly
