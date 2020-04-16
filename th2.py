#!/usr/bin/python3

import datetime, os, time, threading
from inotify_simple import INotify, flags

# experimenting with inotify and threads

def file_writer():
    with open('data.csv', 'a') as f:
        while True:
            #print("file write")
            r = int.from_bytes(os.urandom(8),
                               byteorder="big") / ((1 << 64) - 1)
            now = datetime.datetime.now().isoformat(timespec='microseconds')
            print(f'{now} {r}', file=f)
            f.flush()
            time.sleep(0.5)

def file_reader():
    with open('data.csv', 'r') as fin:
        inotify = INotify()
        inotify.add_watch('data.csv', flags.MODIFY)
        while True:
            line = fin.readline().rstrip()
            if line:
                t = datetime.datetime.fromisoformat(line[:26])
                n = datetime.datetime.now()
                td = n-t
                now = n.isoformat(timespec='microseconds')
                print(f'read {now} {line} {td}')
                #print(f'{line}')
            else:
                #print("wait")
                # wait for events, don't care what events
                inotify.read()
                #time.sleep(2) # TODO: get rid of this

def main():
    print("main")
    threading.Thread(target=file_writer).start()
    threading.Thread(target=file_reader).start()

if __name__ == "__main__":
    main()
