# make random hourly data
import numpy as np
import pandas as pd
import csv, sys

t = pd.date_range(start='4/1/2020', end='4/14/2020', freq='H')
m = np.random.lognormal(0, 2, len(t))
loads = ['load1', 'load2', 'load3', 'load4', 'load5', 'load6', 'load7',
         'load8', 'total']
load = [*map(lambda x: loads[x], np.random.randint(0,9, len(t)))]
df = pd.DataFrame(data={'load':load, 'measure':m}, index=t)
df.set_index(df.index.rename('time'), inplace=True)
df.to_csv(sys.stdout, sep=' ', date_format='%Y-%m-%dT%H',
          quoting=csv.QUOTE_NONE, float_format='%.6g')
