import pandas as pd
import matplotlib.pyplot as plt
import lib

# experimenting with group-by

df = pd.read_csv("test_data_multi.csv", comment='#', delim_whitespace=True,
                 header=0, index_col=0, names=['time','id','ct','measure'],
                 parse_dates=True)
print("raw data")
print(df)

df['load'] = df.apply(lib.load_name, axis=1)
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
