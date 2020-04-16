import pandas as pd
import math

# experimenting with partial resampling

# 10 second observations
n = 1000000
t = pd.date_range(end=pd.Timestamp.now(), periods=n, freq='10S')
s = [*range(1,n+1)]
df = pd.DataFrame(data={'t':t,'s':s})
df = df.set_index(['t'])
print(df)
min_t = df.index.to_period('M').min().to_timestamp()
print(f'min: {min_t}')
max_t = df.index.to_period('M').max().to_timestamp()
print(f'max: {max_t}')
months = pd.date_range(start=min_t, end=max_t, freq='MS')
print(months)
pre = df[:max_t]
print(pre)
post = df[max_t:]
print(post)
pre = pre.resample(rule='MS').max()
print(pre)
df = pd.concat([pre,post])
print(df.head(10))
print(df.tail(10))
