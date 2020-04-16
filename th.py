import datetime, os, time, threading
import pandas as pd

# experimenting with threads

# flush d to "disk" (i.e. print) and the accumulator
# this is the only accumulator writer
def flusher(batch, accumulator):
    print("FLUSH")
    accumulator['time'].extend(batch['time'])
    accumulator['ct'].extend(batch['ct'])
    accumulator['measure'].extend(batch['measure'])
    for i in range(len(batch['time'])):
        print(f"{batch['time'][i]} {batch['ct'][i]} {batch['measure'][i]}")
        
def reader(accumulator):
    while(1):
        batch = {'time':[], 'ct':[], 'measure':[]}
        for x in range(10):
            print(f"READ {x}")
            r = int.from_bytes(os.urandom(8),
                               byteorder="big") / ((1 << 64) - 1)
            p = {'time': datetime.datetime.now(),
                 'ct': 'somecode',
                 'measure': r }
            for key,value in p.items():
                batch[key].append(value)
            time.sleep(1)
        flusher(batch, accumulator)

# e.g. could do summarization now and then
def worker(accumulator):
    while(1):
        print("WORKER")
        df = pd.DataFrame.from_dict(accumulator)
        df = df.set_index('time')
        print(df)
        time.sleep(12)

# e.g. web server
def server(accumulator):
    while(1):
        print("SERVER")
        df = pd.DataFrame.from_dict(accumulator)
        df = df.set_index('time')
        print(df)
        time.sleep(15)


def main():
    print("main")
    d = {'time':[], 'ct':[], 'measure':[]}
    threading.Thread(target=reader, args=(d,)).start()
    threading.Thread(target=worker, args=(d,)).start()
    threading.Thread(target=server, args=(d,)).start()

if __name__ == "__main__":
    main()
