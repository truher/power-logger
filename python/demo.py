import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

raw_data = pd.read_csv('d.csv', sep=' ', header=0,
                names=['time','id','ct','offset','type','measure'])
raw_data['datetime'] = pd.to_datetime(raw_data['time'])
raw_data['actual_time'] = (raw_data['datetime']
                           + pd.to_timedelta(raw_data['offset'], unit='us'))
raw_data = raw_data.set_index('actual_time')
raw_data = raw_data.drop(labels=['datetime','offset','time'],axis=1)
print("raw_data")
print(raw_data)
#pivot=pd.pivot_table(raw_data,
 #values='measure',index=['actual_time','id','ct'],columns=['type'])





#xx[(xx['ct']=='ct1')][['type','measure']]
#pivot = pd.pivot_table(raw_data[(raw_data['ct']=='ct1')][['type','measure']],
                       #values='measure',index=['actual_time'],columns=['type'])
#print("pivot")
#print(pivot)
#xxxx = pivot.interpolate(method='time',limit_direction='both')
#xxxxx = pd.DataFrame(data = xxxx['i'] * xxxx['v'], columns=['p'])

def doit(x):
    #// selects one ct
    onect = raw_data[raw_data['ct']==x][['ct','type','measure']]
    #print("onect")
    #print(onect)
    onectpivot = (pd.pivot_table(onect,
                     values='measure',index=['actual_time'],columns=['type'])
                   .assign(ct=x))
    #print("onectpivot")
    #print(onectpivot)
    interp = onectpivot.interpolate(method='time',limit_direction='both')
    #print("interp")
    #print(interp)
    interp['p'] = interp['i'] * interp['v']
    #print("interp")
    #print(interp)
    return interp


y = pd.DataFrame()
#y = y.append([*map(lambda x:
#        raw_data[raw_data['ct']==x][['ct','type','measure']],
#        raw_data.ct.unique())])
#y = y.append([*map(doit, raw_data.ct.unique())])
y = y.append([doit(x) for x in list(raw_data.ct.unique())])
print(y)
#print(y.ct.unique())
#[*map(lambda x: print(x), y.ct.unique())]
#fig = Figure(figsize=(10,10))
fig, ax = plt.subplots(len(y.ct.unique()))
fig.set_tight_layout(True)
#[*map(lambda x: y[y.ct==x][['p']].plot(ax=ax,style='o',legend=False), y.ct.unique())]
#[*map(lambda x: y[y.ct==x[1]][['p']].plot(ax=ax[x[0]],style='o',use_index=True,y='p',legend=False), enumerate(y.ct.unique()))]
def doplot(x):
    y[y.ct==x[1]][['v','i']].plot(ax=ax[x[0]],style='-o',x='v',y='i',legend=False)

#[*map(lambda x: doplot(x), enumerate(y.ct.unique()))]
[doplot(x) for x in enumerate(y.ct.unique())]
#[*map(lambda x: doplot(x), enumerate(y.ct.unique()))]
#[*map(lambda x: y[y.ct==x[1]][['v','i']].plot(ax=ax[x[0]],style='-',x='v',y='i',legend=False), enumerate(y.ct.unique()))]
#ax.legend(y.ct.unique())
#y.plot()
plt.show()


