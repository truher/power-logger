import numpy as np
import pandas as pd
import serial
import sys
import os

from datetime import datetime
from glob import glob
from scipy import integrate

# frame so we can use "merge" to join for the load names
loadsdf = pd.DataFrame(data={
          'id':["5737333034370D0E14", "5737333034370D0E14",
                "5737333034370D0E14", "5737333034370D0E14",
                "5737333034370A220D", "5737333034370A220D",
                "5737333034370A220D", "5737333034370A220D"],
          'ct':['ct1', 'ct2', 'ct3', 'ct4',
                'ct1', 'ct2', 'ct3', 'ct4'],
          'load':['load1', 'load2', 'load3', 'load4',
                  'load5', 'load6', 'load7', 'load8']})

# return (time, id, ct, measure)
def read_raw_no_header(filename):
    if os.path.isfile(filename):
        return pd.read_csv(filename, delim_whitespace=True, comment='#',
                       index_col=0, parse_dates=True, header=0,
                       names=['time','id','ct','measure'])
    else:
        x = pd.DataFrame(columns=['time','id','ct','measure'])
        x.set_index(keys='time', inplace=True)
        return x

# return (time, measure, load)
def read_hourly_no_header(filename):
    if os.path.isfile(filename):
        return pd.read_csv(filename, delim_whitespace=True, comment='#',
                       index_col=0, parse_dates=True, header=0,
                       names=['time','load','measure'])
    else:
        x = pd.DataFrame(columns=['time','load','measure'])
        x.set_index(keys='time', inplace=True)
        return x

# append a column for load name based on id and ct
def resolve_name(raw_data):
    x = raw_data.reset_index().merge(loadsdf, on=['id','ct'])
    x.set_index(keys='time', inplace=True)
    x.sort_index(inplace=True)
    return x

# treat each load separately, then merge at the end
# input (time, measure, load)
# return (time, measure, load)
def make_multi_hourly(load_data):
    hourly = pd.DataFrame(columns=['measure'])
    for load in list(set(load_data['load'])):
        hourly = hourly.append(
            make_hourly(load_data[load_data['load']==load][['measure']])
            .assign(load=load))
    group = hourly.groupby(level=0).sum()
    hourly = hourly.append(group.assign(load='total'))
    hourly = hourly.reindex(columns=['measure','load'])
    return hourly

# accept (time, measure)
# return (time (hour), measure (total))
def make_hourly(raw_data):
    # provide a zero just before the first point, so integration sees
    # the first point but nothing before it
    raw_data = pd.concat(
        [pd.DataFrame(
            index=[raw_data.index.min() - pd.DateOffset(seconds=1)],
            data=[0], columns=['measure']), raw_data])
    raw_data.set_index(raw_data.index.rename('time'), inplace=True)

    # Bucket boundaries we want, with some left padding to be sure we
    # can set the first to zero
    buckets = pd.DataFrame(
        pd.date_range(
            start=raw_data.index.min().floor('H') - pd.DateOffset(hours=1),
            end=raw_data.index.max().ceil('H'), freq='H')
        ).set_index(0)

    # Insert bucket boundaries into the raw dataset (they'll have NaN
    # measures)
    raw_data_with_buckets = raw_data.append(buckets).sort_index()

    # Set the left edge to zero
    raw_data_with_buckets.at[raw_data_with_buckets.index.min()]=0

    # Fill interpolated values at the bucket boundaries
    interpolated = raw_data_with_buckets.interpolate(method='time',
        limit_area='inside').dropna()

    # Integrate the data series to get cumulative energy (kWh)
    cum_kwh = pd.DataFrame(
        index=interpolated.index, columns=['measure'],
        data=integrate.cumtrapz(
            interpolated['measure'],
            x=interpolated.index, initial=0)
        / (1000 * np.timedelta64(1, 'h')))

    # Downsample to the buckets, diff to get energy per bucket, trim
    # the leading zero
    hourly = cum_kwh.resample(rule='H',closed='right',label='right',
        loffset='-1H').max().diff().dropna().iloc[1:]
    return hourly

# read a line from source, prepend timestamp, write it to sync
# close the source if something goes wrong
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

# trim file <filename> to latest <count> lines
def trim(filename, count):
    lines = []
    with open(filename, 'r') as source:
        lines = source.readlines()
    lines = lines[-count:]
    with open(filename, 'w') as sink:
        sink.writelines(lines)

# return (time, id, ct, measure) from string
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
        print(f'ignore broken line: {line}', file=sys.stderr)

# create new serial stream
def new_serial(port):
    print(f'new {port}', file=sys.stderr, flush=True)
    return serial.Serial(port, 9600, 8, 'N', 1, timeout=0.001)

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

# maintain connections and transcribe them all
def transcribe_all(serials, sink):
    ttys = glob("/dev/ttyACM*")
    serials = [*filter(lambda x: is_open(x) and has_tty(ttys)(x), serials)]
    serials.extend([*map(new_serial, filter(no_serial(serials), ttys))])
    [*map(transcribe(sink), serials)]
    return serials
