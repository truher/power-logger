# make random raw data
import numpy as np
import pandas as pd
import csv, sys

ids = [ "5737333034370D0E14", "5737333034370A220D"]
cts = ['ct1', 'ct2', 'ct3', 'ct4']
num_rows = 15000
t = (pd.date_range(end=pd.Timestamp.now(), periods=num_rows, freq='S')
    + pd.to_timedelta(np.random.uniform(-1, 1, num_rows), unit='S'))
ct = [*map(lambda x: cts[x], np.random.randint(0,4, num_rows))]
id = [*map(lambda x: ids[x], np.random.randint(0,2, num_rows))]
m = np.random.lognormal(0, 1, num_rows)
df = pd.DataFrame(data={'id':id, 'ct':ct, 'measure':m}, index=t)
df.set_index(df.index.rename('time'), inplace=True)
df.to_csv(sys.stdout, sep=' ', date_format='%Y-%m-%dT%H:%M:%S.%f',
          quoting=csv.QUOTE_NONE, float_format='%.6g')
