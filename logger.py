#!/usr/bin/python3
import serial, sys, threading, traceback
from datetime import datetime
from glob import glob
from inotify_simple import INotify, flags

def transcribe(sink):
    def f(source):
        try:
            line = source.readline().rstrip().decode('ascii')
            if line:
                now = datetime.now().isoformat(timespec='microseconds')
                print(f'{now} {line}', file=sink, flush=True)
        except serial.serialutil.SerialException:
            print("fail", source.port, file=sys.stderr)
            source.close()
    return f

def new_serial(port):
    print(f'new {port}', file=sys.stderr, flush=True)
    return serial.Serial(port, 9600, 8, 'N', 1, timeout=1)

def is_open(ser):
    if ser.is_open:
        return True
    print(f'closed {ser.port}', file=sys.stderr, flush=True)
    return False

def has_tty(ttys):
    def f(ser):
        if ser.port in ttys:
            return True
        print(f'no tty {ser.port}', file=sys.stderr, flush=True)
        return False
    return f

def no_serial(serials):
    current_ports = [*map(lambda x: x.port, serials)]
    def f(tty):
        if tty in current_ports:
            return False
        print(f'no serial {tty}', file=sys.stderr, flush=True)
        return True
    return f

def transcribe_all(serials, sink):
    ttys = glob("/dev/ttyACM*")
    serials = [*filter(lambda x: is_open(x) and has_tty(ttys)(x), serials)]
    serials.extend([*map(new_serial, filter(no_serial(serials), ttys))])
    [*map(transcribe(sink), serials)]
    return serials

def serial_reader():
    print("serial_reader", file=sys.stderr)
    serials = []
    with open('data.csv', 'a') as sink:
        while True:
            try:
                serials = transcribe_all(serials, sink)
            except KeyboardInterrupt:
                traceback.print_exc(file=sys.stderr)
                raise
            except:
                traceback.print_exc(file=sys.stderr)
                print("top level exception",
                      sys.exc_info()[0], file=sys.stderr)

def file_reader():
    print("file_reader", file=sys.stderr)
    with open('data.csv', 'r') as fin:
        inotify = INotify()
        inotify.add_watch('data.csv', flags.MODIFY)
        while True:
            line = fin.readline().rstrip()
            if line:
                try:
                    fields = line.split()
                    if len(fields) != 4:
                        print(f'wrong field count: {line}', file=sys.stderr)
                        continue
                    time_str = fields[0]
                    parsed_time = datetime.fromisoformat(time_str)
                    id = fields[1]
                    if len(id) != 18:
                        print(f'wrong id length: {line}', file=sys.stderr)
                        continue
                    ct = fields[2]
                    if len(ct) != 3:
                        print(f'wrong ct length: {line}', file=sys.stderr)
                        continue
                    measure = fields[3]
                    parsed_measure = float(measure)
                    print(f'{time_str} {id} {ct} {measure}')
                except ValueError:
                    print(f'ignore broken line: {line}', file=sys.stderr)
            else:
                # wait for modify event
                inotify.read()

def main():
    print("main", file=sys.stderr)
    threading.Thread(target=serial_reader).start()
    threading.Thread(target=file_reader).start()

if __name__ == "__main__":
    main()
