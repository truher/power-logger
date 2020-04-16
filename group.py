import pandas as pd
import matplotlib.pyplot as plt

# experimenting with group-by


df = pd.read_csv("dd.0", delim_whitespace=True)
print(df)
df['time']=pd.to_datetime(df['time'])
print(df)
print(df['measure'])
print(df.columns)
df['hr']=df['time'].dt.floor('10T')
df['k']=df['id'].map(str)+df['dim'].map(str)
print(df)
#plt.figure()
#jdf.groupby(['hr','id','dim'])['measure'].sum().unstack().plot()
a = df.groupby(['hr','k'])['measure'].mean()
print(a)
b = a.unstack()
print(b)
b.plot()
#g = df.groupby(['id','dim','hr'])['measure'].sum()
#g = df.groupby(['hr'])['measure'].sum()
#print(g)

#g.plot(x='hr', y='measure')
plt.show()
