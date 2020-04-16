import pandas as pd
import matplotlib.pyplot as plt

# experimenting with group-by

ids = {"5737333034370D0E14":
          {'ct1':'load1',
           'ct2':'load2',
           'ct3':'load3',
           'ct4':'load4'},
       "5737333034370A220D":
          {'ct1':'load5',
           'ct2':'load6',
           'ct3':'load7',
           'ct4':'load8'}
        }
def load_name(row):
    return ids[row['id']][row['dim']]

df = pd.read_csv("data.csv", delim_whitespace=True, header=0,
                 index_col=0, names=['time','id','dim','measure'],
                 parse_dates=True)
print("raw data")
print(df)

df['load'] = df.apply(load_name, axis=1)
print("with load")
print(df)

b = df.pivot(columns='load', values='measure')
print("b")
print(b)
b.plot(style='o')

c = b.interpolate(method='time')
print("c")
print(c)
c.plot()

plt.show()
