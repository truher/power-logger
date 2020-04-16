import numpy as np
import pandas as pd
from scipy import integrate

# more experimenting with resampling

# watts
raw_data = pd.read_csv('dt.0', 
                       delim_whitespace=True,
                       comment='#',
                       index_col=0,
                       parse_dates=True)
#raw_data['time'] = pd.to_datetime(raw_data['time'])
#raw_data = raw_data.set_index(['time'])
print("raw data")
print(raw_data)
#print(raw_data.index)
# watt-minutes
t=integrate.cumtrapz(raw_data, x=raw_data.index, axis=0, initial=0)/np.timedelta64(1, 'm')
print("cumulative integral")
print(t)
# watt-minutes
x = pd.DataFrame(t, index=raw_data.index, columns=['measure'])
print("cumulative integral frame")
print(x)
yd = x.resample(rule='D').max()
print("resampled to D")
print(yd)
yt = x.resample(rule='T').max().interpolate()
print("resampled to T, note incorrect linear interpolation")
print(yt)
yti = x.resample(rule='T').max().interpolate().resample(rule='10T').max()
print("reresampled to 10T, note incorrect bucketing")
print(yti)

yr = raw_data.resample(rule='T').nearest()
print("raw resampled to T")
print(yr)
yri = raw_data.resample(rule='T').nearest().interpolate()
print("raw resampled to T, interpolated")
print(yri)
yrit = yri.resample(rule='10T').nearest()
print("raw resampled to T, again to 10T")
print(yrit)
yriti=integrate.cumtrapz(yrit, x=yrit.index, axis=0, initial=0)/np.timedelta64(1, 'm')
print("raw resampled to T, again to 10T, integrated")
print(yriti)

yrt=integrate.cumtrapz(yri, x=yri.index, axis=0, initial=0)/np.timedelta64(1, 'm')
print("yri cumulative integral")
print(yrt)
# watt-minutes
yrx = pd.DataFrame(yrt, index=yri.index, columns=['measure'])
print("yri cumulative integral frame")
print(yrx)


#print("hi 5")
#z = raw_data.resample(rule='D').max().interpolate().sum()
#print(z)


# Bucket boundaries we want, with some left padding
buckets = pd.DataFrame(pd.date_range(start=raw_data.index.min().floor('10T') - 2 * pd.offsets.Minute(10),
                       end=raw_data.index.max().ceil('10T'), freq='10T'))
buckets = buckets.set_index(0)
print("buckets")
print(buckets)

# Insert bucket boundaries into the raw dataset (they'll have NaN measures)
raw_data_with_buckets = raw_data.append(buckets)
raw_data_with_buckets = raw_data_with_buckets.sort_index()
raw_data_with_buckets.at[raw_data_with_buckets.index.min()]=0
print("raw_data_with_buckets")
print(raw_data_with_buckets)

interpolated = raw_data_with_buckets.interpolate(method='time')
interpolated = interpolated.dropna()
print("interpolated")
print(interpolated)

mn = integrate.cumtrapz(interpolated, interpolated.index, axis=0, initial=0)/np.timedelta64(1, 'm')
print("mn cumtrapz")
print(mn)
mnf = pd.DataFrame(mn, index=interpolated.index, columns=['measure'])
print("mnf cumtrapz frame")
print(mnf)
mnfr = mnf.resample(rule='10T',closed='right',label='right',loffset='-10T').max()
print("mnfr")
print(mnfr)
mnfrd = mnfr.diff()
print("mnfrd resampled to 10T, max().diff()")
print(mnfrd)

mnfrdr = mnfrd.resample(rule='5T').nearest().resample(rule='60T').sum()
print("mnfrdr resampled to 1h, sum()")
print(mnfrdr)

