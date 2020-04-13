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

def parse(line):
    try:
        result = {}
        fields = line.split()
        if len(fields) != 4:
            raise ValueError(f'wrong field count: {line}')

        time_str = fields[0]
        result['time'] = datetime.fromisoformat(time_str)

        id_str = fields[1]
        if len(id_str) != 18:
            raise ValueError(f'wrong id length: {id_str}')
        result['id'] = id_str

        ct_str = fields[2]
        if len(ct_str) != 3:
            raise ValueError(f'wrong ct length: {ct_str}')
        result['ct'] = ct_str

        measure_str = fields[3]
        result['measure'] = float(measure_str)
        return result

    except ValueError:
        traceback.print_exc(file=sys.stderr)
        print(f'ignore broken line: {line}', file=sys.stderr)

def file_reader():
    print("file_reader", file=sys.stderr)
    with open('data.csv', 'r') as fin:
        inotify = INotify()
        inotify.add_watch('data.csv', flags.MODIFY)
        while True:
            line = fin.readline().rstrip()
            if not line:
                # EOF, wait for next modify event
                inotify.read()
                continue
            result = parse(line)
            if result is None:
                continue
            print(result)
            #print(f'{time_str} {id} {ct} {measure}')

def main():
    print("main", file=sys.stderr)
    threading.Thread(target=serial_reader).start()
    threading.Thread(target=file_reader).start()

if __name__ == "__main__":
    main()
