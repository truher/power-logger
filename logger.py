import datetime, serial, string

def readit(idx, ser):
    r = ser.readline()
    if r != "":
        f = r.split()
        id = f[0]
        print(datetime.datetime.now(),id," ".join(f))
    
def main():
    ser0 = serial.Serial('/dev/ttyACM0', 9600, 8, 'N', 1, timeout=20)
    ser1 = serial.Serial('/dev/ttyACM1', 9600, 8, 'N', 1, timeout=20)

    while True:
        readit(0, ser0)
        readit(1, ser1)

if __name__ == "__main__":
    main()
