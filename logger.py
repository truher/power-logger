#!/usr/bin/python3
import datetime, glob, serial, sys

def readit(ser, f):
    try:
        r = ser.readline().rstrip().decode('ascii')
        if r:
            now = datetime.datetime.now().isoformat(timespec='microseconds')
            print(f'{now} {r}', file=f)
            f.flush()
    except serial.serialutil.SerialException:
        print("fail", ser.port, file=sys.stderr)
        ser.close()
        # mark it dead
        ser.port = ""

serials = []

with open('data.csv', 'a') as f:
    while True:
        try:
            # remove the dead serials (marked with empty ports)
            serials = [*filter(lambda x: len(x.port)>0, serials)]
    
            # remove serials without matching ttys
            current_ttys = glob.glob("/dev/ttyACM*")
            serials = [*filter(lambda x: x.port in current_ttys, serials)]
    
            # add new serials
            current_ports = [*map(lambda x: x.port, serials)]
            ttys_without_ports = [*set(current_ttys).difference(current_ports)]
            if len(ttys_without_ports) > 0:
                print("connecting", ttys_without_ports, file=sys.stderr)
            serials.extend(
                [*map(lambda f: serial.Serial(f, 9600, 8, 'N', 1, timeout=1),
                      ttys_without_ports)])
    
            # read from all the serials
            [*map(lambda x: readit(x,f), serials)]
    
        except KeyboardInterrupt:
            raise
        except:
            print("top level exception",sys.exc_info()[0], file=sys.stderr)
