import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 2000)
pd.set_option('max_colwidth', 50)
pd.set_option('max_seq_item', 10)
pd.set_option('display.min_rows', 20)
pd.set_option('display.max_rows', 40)


raw_data = pd.read_csv('l3.csv', delim_whitespace=True, header=None,
               names=['time','err','id','ct','v_first','dv','a_first','da'])
print(raw_data)
raw_data['err'] = raw_data['err'].apply(pd.to_numeric, errors='coerce')
print(f"errors {len(raw_data[raw_data.err != 0])}")
raw_data = raw_data[raw_data.err == 0] # ignore error rows
raw_data = raw_data.drop(labels=['err'], axis=1)
raw_data['row'] = raw_data.index
print(raw_data)
#raw_data['dvbs'] = raw_data.dv.apply(lambda x: [y-256 if y > 127 else y for y in list(bytes.fromhex(x))])
#raw_data['dabs'] = raw_data.da.apply(lambda x: [y-256 if y > 127 else y for y in list(bytes.fromhex(x))])
raw_data['dvbs'] = raw_data.dv.apply(lambda x: [y-128 for y in list(bytes.fromhex(x))])
raw_data['dabs'] = raw_data.da.apply(lambda x: [y-128 for y in list(bytes.fromhex(x))])
raw_data['vbs'] = raw_data.dvbs.apply(lambda x: list(np.cumsum(x)))
raw_data['abs'] = raw_data.dabs.apply(lambda x: list(np.cumsum(x)))
raw_data['idx'] = [list(range(0,1000)) for x in range(0, len(raw_data))]
raw_data = raw_data.drop(labels=['dv','da'], axis=1)
print(raw_data)
raw_data = raw_data.apply(pd.Series.explode)
cols = ['dvbs','dabs','vbs','abs','idx']
raw_data[cols] = raw_data[cols].apply(pd.to_numeric, errors='raise')
raw_data['vbs'] += raw_data['v_first']
raw_data['abs'] += raw_data['a_first']
print(raw_data)
print(raw_data.dtypes)
print(raw_data.describe(include='all'))
print(f"dvbs range {raw_data.dvbs.max() - raw_data.dvbs.min()}")
print(f"dabs range {raw_data.dabs.max() - raw_data.dabs.min()}")
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
raw_data['datetime'] = pd.to_datetime(raw_data['time'])
raw_data['actual_time'] = (raw_data['datetime']
                           + pd.to_timedelta(raw_data['offset'], unit='us'))
raw_data = raw_data.set_index('actual_time')
raw_data = raw_data.drop(labels=['datetime','offset','time','is_v','idx','v_first','a_first','dvbs','dabs'],axis=1)
print(raw_data)

def doit(x):
    onerow = raw_data.loc[raw_data['row']==x][['id','ct','row','vbs','abs']]
    #print("onerow")
    #print(onerow)
    interp = onerow.interpolate(method='time',limit_direction='both')
    #print("interp")
    #print(interp)
    return interp

print("calculate y...")
y = pd.DataFrame()
y = y.append([doit(x) for x in list(raw_data.row.unique())])
print("done!")
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
    y[y.ct==x[1]][['vbs','abs']].plot(ax=ax,style='-o',y=['vbs','abs'],label=[f'{x[1]}v',f'{x[1]}a'])
    #y[y.ct==x[1]][['vbs','abs']].plot(ax=ax[x[0]],style='-o',x='vbs',y='abs',legend=False)
    #raw_data[(raw_data.index<4) & (raw_data.ct==x[1])][['idx','abs']].plot(ax=ax[x[0]],style='-o',x='idx',y='abs',legend=False)
[doplot(x) for x in enumerate(raw_data.ct.unique())]
#ax.legend(y.ct.unique())
ax.xaxis.set_major_locator(ticker.MaxNLocator(10))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%dT%H:%M:%S.%f'))
plt.show()
