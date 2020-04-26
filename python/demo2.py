import pandas as pd

raw_data = pd.read_csv('l3.csv', delim_whitespace=True, header=0,
               names=['time','id','ct','v_first','dv','a_first','da'])
print(raw_data)
xx=bytes.fromhex(raw_data.iloc[0].dv)
print(xx)
xxx=[x-256 if x > 127 else x for x in list(xx)]
print(xxx)
