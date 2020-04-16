import numpy as np
import pandas as pd

# how to make random data

def random_data():
    num_rows = 1000000

    time_ideal = pd.date_range(end=pd.Timestamp.now(), periods=num_rows, freq='10S')
    time_deltas  = pd.to_timedelta(np.random.uniform(-1, 1, num_rows),unit='S')
    time_actual = time_ideal + time_deltas

    #data  = np.random.uniform(0, 1, num_rows)
    # lognormal(0,1) has mean exp(0.5) or about 1.65
    data  = np.random.lognormal(0, 1, num_rows)

    df = pd.DataFrame(data={'time': time_actual, 'measure': data})
    df = df.set_index(['time'])
    return df

    
def main():
    d = random_data()
    print(d.tail())
    d.to_csv('data.csv', mode='a', sep=' ')

    dd = pd.read_csv('data.csv', delim_whitespace=True, index_col='time')
    print(dd.tail())

if __name__ == "__main__":
    main()
