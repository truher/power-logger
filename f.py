import numpy as np
import pandas as pd
import lib

# how to make random data

def main():
    d = lib.random_data()
    print(d.tail())
    d.to_csv('data2.csv', mode='a', sep=' ')

    dd = pd.read_csv('data2.csv', delim_whitespace=True, index_col='time')
    print(dd.tail())

if __name__ == "__main__":
    main()
