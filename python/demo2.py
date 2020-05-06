import time
import pandas as pd #type:ignore
import numpy as np #type:ignore
import matplotlib.pyplot as plt #type:ignore
import matplotlib.dates as mdates # type:ignore
import matplotlib.ticker as ticker # type:ignore
from pandas import to_datetime as pd_to_datetime
from numpy import timedelta64 as np_timedelta64
from pandas import to_numeric as pd_to_numeric
from pandas import to_timedelta as pd_to_timedelta
from typing import List,Any,Tuple,IO,Iterable
import binascii
import itertools
import operator
import sys

pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 2000)
pd.set_option('max_colwidth', 50)
pd.set_option('max_seq_item', 10)
pd.set_option('display.min_rows', 20)
pd.set_option('display.max_rows', 40)

# return time series for N observations, counting back
# from T (string) by DT (us) interval.
def timeseries(n:int, t:str, dt:int) -> List[str]:
    t_datetime = pd_to_datetime(t)
    return [t_datetime - np_timedelta64(x, 'us') for x in range(0, n, dt)]

def readfile() -> List[bytes]:
    with open('l3.csv', 'rb') as datafile: # type: IO[bytes]
        return datafile.readlines()

def goodrow(x:List[bytes]) -> bool:
    if len(x) != 8:
        print(f'skip row len {len(x)}')
        return False
    if x[1] != b'0':
        print(f'skip row err {x[1]!r}')
        return False
    return True

def d(x:int) -> int:
    return x-128

# from arduino
OBSERVATION_COUNT = 1000
# x vals for observations
interp_xp = np.linspace(0, OBSERVATION_COUNT - 1, OBSERVATION_COUNT)
# x vals for interpolations, adds in-between vals
interp_x = np.linspace(0, OBSERVATION_COUNT - 1, 2 * OBSERVATION_COUNT - 1)

def bytes_to_array(all_fields:List[bytes], data_col:int, first_col:int, trim_first:bool ) -> Any:
    field = all_fields[data_col]
    decoded = binascii.unhexlify(field)
    first = int(all_fields[first_col])
    offsetted = (y-128 for y in decoded)
    #cumulative = itertools.accumulate(offsetted, func=operator.add, initial=first)
    cumulative = list(itertools.accumulate(offsetted, func=operator.add, initial=first))
    # TODO: stop encoding the first delta as zero
    #cumulative = list(itertools.islice(cumulative, 1, None))
    cumulative.pop(0)
    interpolated = np.interp(interp_x, interp_xp, cumulative)
    if trim_first:
        interpolated = interpolated[1:]
    else:
        interpolated = interpolated[:-1]
    return interpolated

#def cume():
    #return list(itertools.accumulate(decoded_fromhex))

# read file, ~100 us
allrows = readfile() # type: List[bytes]
allrowsfields = [x.split() for x in allrows]

# remove bad rows, ~25 us
allrowsfields = [x for x in allrowsfields if goodrow(x)]

# volts is the first observation, so trim the first value
vbs = [bytes_to_array(x,5,4,True) for x in allrowsfields]

# amps is the second observation, so trim the last value
abs_ = [bytes_to_array(x,7,6,False) for x in allrowsfields]

print(len(vbs[20]))
print(vbs[20])
plt.plot(vbs[20],abs_[20])
plt.show()

sys.exit()










raw_data = pd.read_csv('l3.csv', delim_whitespace=True, header=None,
               names=['time','err','id','ct','v_first','dv','a_first','da']) # type: pd.DataFrame
print(raw_data)
raw_data['err'] = raw_data['err'].apply(pd_to_numeric, errors='coerce')
print(f"errors {len(raw_data[raw_data['err'] != 0])}")
raw_data = raw_data[raw_data['err'] == 0] # ignore error rows
raw_data = raw_data.drop(labels=['err'], axis=1)
raw_data['row'] = raw_data.index
print(raw_data)
#raw_data['dvbs'] = raw_data['dv'].apply(lambda x: [y-256 if y > 127 else y for y in list(bytes.fromhex(x))])
#raw_data['dabs'] = raw_data['da'].apply(lambda x: [y-256 if y > 127 else y for y in list(bytes.fromhex(x))])
raw_data['dvbs'] = raw_data['dv'].apply(lambda x: [y-128 for y in list(bytes.fromhex(x))])
raw_data['dabs'] = raw_data['da'].apply(lambda x: [y-128 for y in list(bytes.fromhex(x))])
raw_data['vbs'] = raw_data['dvbs'].apply(lambda x: list(np.cumsum(x)))
raw_data['abs'] = raw_data['dabs'].apply(lambda x: list(np.cumsum(x)))
raw_data['idx'] = [list(range(0,1000)) for x in range(0, len(raw_data))]
raw_data = raw_data.drop(labels=['dv','da'], axis=1)
print(raw_data)

raw_data = raw_data.apply(pd.Series.explode)
cols = ['dvbs','dabs','vbs','abs','idx']
raw_data[cols] = raw_data[cols].apply(pd.to_numeric, errors='raise')
raw_data['vbs'] = raw_data['vbs'].add(raw_data['v_first'])
raw_data['abs'] += raw_data['a_first']
print(raw_data)
print(raw_data.dtypes)
print(raw_data.describe(include='all'))
print(f"dvbs range {raw_data['dvbs'].max() - raw_data['dvbs'].min()}")
print(f"dabs range {raw_data['dabs'].max() - raw_data['dabs'].min()}")
# is this row volts?
raw_data['is_v'] = [[1,0] for x in range(0,len(raw_data))]
raw_data = raw_data.explode('is_v')
# erase every other sample
raw_data.loc[raw_data['is_v']==1,'abs']=np.nan
raw_data.loc[raw_data['is_v']==0,'vbs']=np.nan
# the last (999) sample is approximately at the timestamp,
# other samples are earlier
# offset in us
raw_data['offset'] = (2 * (raw_data['idx'] - 999) - raw_data['is_v']) * 100
raw_data['datetime'] = pd_to_datetime(raw_data['time'])
raw_data['actual_time'] = (raw_data['datetime']
                           + pd_to_timedelta(raw_data['offset'], unit='us'))
raw_data = raw_data.set_index('actual_time')
raw_data = raw_data.drop(labels=['datetime','offset','time','is_v','idx','v_first','a_first','dvbs','dabs'],axis=1)
print(raw_data)

def doit(x):
    # type: (int) -> Any
    print(f"doit {x}")
    t0 = time.perf_counter()
    onerow = raw_data.loc[raw_data['row']==x][['id','ct','row','vbs','abs']]
    t1 = time.perf_counter()
    #print("onerow")
    #print(onerow)
    interp = onerow.interpolate(method='time',limit_direction='both')
    t2 = time.perf_counter()
    print(f"{t1-t0} {t2-t1}")
    #print("interp")
    #print(interp)
    return interp

print("calculate y...")
y = pd.DataFrame()
t0 = time.perf_counter()
y = y.append([doit(x) for x in list(raw_data.row.unique())])
t1 = time.perf_counter()



print("done!")
print(f"{t1-t0}")
print("y")
print(y)
print(y.dtypes)
print(y.describe(include='all'))
#raw_data.plot(x='vbs',y='abs')
#plt.show()
#fig, ax = plt.subplots(len(raw_data.ct.unique()))
fig, ax = plt.subplots()
fig.set_tight_layout(True)
def doplot(x):
    # type: (Tuple[int, str]) -> None
    y[y['ct']==x[1]][['vbs','abs']].plot(ax=ax,style='-o',y=['vbs','abs'],label=[f'{x[1]}v',f'{x[1]}a'])
    #y[y.ct==x[1]][['vbs','abs']].plot(ax=ax[x[0]],style='-o',x='vbs',y='abs',legend=False)
    #raw_data[(raw_data.index<4) & (raw_data.ct==x[1])][['idx','abs']].plot(ax=ax[x[0]],style='-o',x='idx',y='abs',legend=False)
[doplot(x) for x in enumerate(raw_data['ct'].unique())] #type:ignore
#ax.legend(y.ct.unique())
ax.xaxis.set_major_locator(ticker.MaxNLocator(10))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%dT%H:%M:%S.%f'))
plt.show()
