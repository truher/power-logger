import numpy as np
import pandas as pd
import serial #type:ignore
import binascii, itertools, operator, os, sys

from datetime import datetime
from glob import glob
from scipy import integrate #type:ignore
from typing import Any, Callable, Dict, IO, List, Optional, Tuple, Union
from collections import namedtuple

# frame so we can use "merge" to join for the load names
loadsdf = pd.DataFrame(data={
          'id':["5737333034370D0E14", "5737333034370D0E14", #type:ignore
                "5737333034370D0E14", "5737333034370D0E14",
                "5737333034370A220D", "5737333034370A220D",
                "5737333034370A220D", "5737333034370A220D"],
          'ct':['ct1', 'ct2', 'ct3', 'ct4', #type:ignore
                'ct1', 'ct2', 'ct3', 'ct4'],
          'load':['load1', 'load2', 'load3', 'load4', #type:ignore
                  'load5', 'load6', 'load7', 'load8']})

# see arduino.ino
# TODO: use a common format somehow?
# TODO: use tab or space not both
# input, tab/space delimited
# time err uid ct v_first v_bytes a_first a_bytes
# return (time, id, ct, measure)
def read_raw_no_header(filename:str) -> pd.DataFrame:
    if os.path.isfile(filename):
        return pd.read_csv(filename, delim_whitespace=True, comment='#', #type:ignore
                       index_col=0, parse_dates=True, header=0,
                       names=['time','id','ct','measure'])
    else:
        x = pd.DataFrame(columns=['time','id','ct','measure'])
        x.set_index(keys='time', inplace=True) #type:ignore
        return x

# return (time, measure, load)
def read_hourly_no_header(filename:str) -> pd.DataFrame:
    if os.path.isfile(filename):
        return pd.read_csv(filename, delim_whitespace=True, comment='#', #type:ignore
                       index_col=0, parse_dates=True, header=0,
                       names=['time','load','measure'])
    else:
        x = pd.DataFrame(columns=['time','load','measure'])
        x.set_index(keys='time', inplace=True) #type:ignore
        return x

# append a column for load name based on id and ct
def resolve_name(raw_data:pd.DataFrame) -> pd.DataFrame:
    x = raw_data.reset_index().merge(loadsdf, on=['id','ct']) #type:ignore
    x.set_index(keys='time', inplace=True)
    x.sort_index(inplace=True)
    return x #type:ignore

# treat each load separately, then merge at the end
# input (time, measure, load)
# return (time, measure, load)
def make_multi_hourly(load_data:pd.DataFrame) -> pd.DataFrame:
    hourly = pd.DataFrame(columns=['measure'])
    for load in list(set(load_data['load'])):
        hourly = hourly.append(
            make_hourly(load_data[load_data['load']==load][['measure']])
            .assign(load=load)) #type:ignore
    group = hourly.groupby(level=0).sum() #type:ignore
    hourly = hourly.append(group.assign(load='total'))
    hourly = hourly.reindex(columns=['measure','load']) #type:ignore
    return hourly

# accept (time, measure)
# return (time (hour), measure (total))
def make_hourly(raw_data:pd.DataFrame) -> pd.DataFrame:
    # provide a zero just before the first point, so integration sees
    # the first point but nothing before it
    raw_data = pd.concat(
        [pd.DataFrame(
            index=[raw_data.index.min() - pd.DateOffset(seconds=1)], #type:ignore
            data=[0], columns=['measure']), raw_data])
    raw_data.set_index(raw_data.index.rename('time'), inplace=True) #type:ignore

    # Bucket boundaries we want, with some left padding to be sure we
    # can set the first to zero
    buckets = pd.DataFrame(
        pd.date_range( #type:ignore
            start=raw_data.index.min().floor('H') - pd.DateOffset(hours=1), #type:ignore
            end=raw_data.index.max().ceil('H'), freq='H') #type:ignore
        ).set_index(0) #type:ignore

    # Insert bucket boundaries into the raw dataset (they'll have NaN
    # measures)
    raw_data_with_buckets = raw_data.append(buckets).sort_index() #type:ignore

    # Set the left edge to zero
    raw_data_with_buckets.at[raw_data_with_buckets.index.min()]=0 #type:ignore

    # Fill interpolated values at the bucket boundaries
    interpolated = raw_data_with_buckets.interpolate(method='time', #type:ignore
        limit_area='inside').dropna()

    # Integrate the data series to get cumulative energy (kWh)
    cum_kwh = pd.DataFrame(
        index=interpolated.index, columns=['measure'],
        data=integrate.cumtrapz(
            interpolated['measure'],
            x=interpolated.index, initial=0)
        / (1000 * np.timedelta64(1, 'h'))) #type:ignore

    # Downsample to the buckets, diff to get energy per bucket, trim
    # the leading zero
    hourly = cum_kwh.resample(rule='H',closed='right',label='right', #type:ignore
        loffset='-1H').max().diff().dropna().iloc[1:]
    return hourly #type:ignore

# in order to pass null
VA = namedtuple('VA', ['volts','amps'])   

# read a line from source (unparsed), prepend timestamp, write it to sink
# close the source if something goes wrong
# so now the raw data is not worth keeping
# so 
def transcribe(sink:IO[bytes], interpolator:Callable[[List[int]],List[int]],
               va_updater:Callable[[VA], None]) -> Callable[[IO[bytes]],None]:
    def f(source:serial.Serial)->None:
        try:
            #line = source.readline().rstrip().decode('ascii')
            line = source.readline().rstrip()
            if line:
                #print(type(line))
                #print("line")
                #print(line)
                #now = datetime.now().isoformat(timespec='microseconds')
                now = datetime.now().isoformat(timespec='microseconds').encode('ascii')
                #old_format_line = f'{now} {line}'
                old_format_line = now + b' ' + line
                #print("old_format_line")
                sink.write(old_format_line)
                sink.write(b'\n')
                sink.flush()
                #print(old_format_line, file=sink, flush=True)
                #print(type(old_format_line))
                #print(old_format_line)
                # also interpret the line
                # TODO fix the format
                va = decode_and_interpolate(interpolator, old_format_line)
                if va:
                    # TODO per-load update
                    va_updater(va)
        except serial.serialutil.SerialException:
            print("fail", source.port, file=sys.stderr)
            source.close()
    return f

# trim file <filename> to latest <count> lines
def trim(filename:str, count:int) -> None:
    lines = []
    with open(filename, 'rb') as source:
        lines = source.readlines()
    lines = lines[-count:]
    with open(filename, 'wb') as sink:
        sink.writelines(lines)

# return (time, id, ct, measure) from string
# TODO: actually use this?
def parse(line:str) -> Optional[Dict[str, Any]]:
    try:
        result:Dict[str,Union[datetime, float, str]] = {}
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
        return None

# create new serial stream
def new_serial(port:str) -> serial.Serial:
    print(f'new {port}', file=sys.stderr, flush=True)
    return serial.Serial(port, 9600, 8, 'N', 1, timeout=1)

def is_open(ser:serial.Serial) -> bool:
    if ser.is_open:
        return True
    print(f'closed {ser.port}', file=sys.stderr, flush=True)
    return False

def has_tty(ttys:List[str]) -> Callable[[serial.Serial], bool]:
    def f(ser:serial.Serial) -> bool:
        if ser.port in ttys:
            return True
        print(f'no tty {ser.port}', file=sys.stderr, flush=True)
        return False
    return f

# this is to make mypy happy
def get_port(s:serial.Serial) -> str:
    port:str = s.port
    return port
    
def no_serial(serials:List[serial.Serial]) -> Callable[[str], bool]:
    current_ports:List[str] = [*map(get_port , serials)]
    def f(tty:str) -> bool:
        if tty in current_ports:
            return False
        print(f'no serial {tty}', file=sys.stderr, flush=True)
        return True
    return f

# maintain connections and transcribe them all
# TODO: stop constructing the transcriber every time, pass it in.
# TODO: test this
def transcribe_all(serials:List[serial.Serial],
        transcriber: Callable[[IO[bytes]],None])-> List[serial.Serial]:
    ttys:List[str] = glob("/dev/ttyACM*")
    serials = [*filter(lambda x: is_open(x) and has_tty(ttys)(x), serials)]
    serials.extend([*map(new_serial, filter(no_serial(serials), ttys))])
    [*map(transcriber, serials)]
    return serials

# read the whole file into a list of lines
def readfile(filename:str) -> List[bytes]:
    with open(filename, 'rb') as datafile: # type: IO[bytes]
        return datafile.readlines()

def read_new_raw(filename:str) -> Any:
    return ['foo']

# avoid creating the bases for every row, create it once
def interpolator(samples:int) -> Callable[[List[int]], List[int]]:
    #print("interpolator0")
    # x vals for observations
    interp_xp = np.linspace(0, samples - 1, samples)
    #print("interpolator1")
    # x vals for interpolations, adds in-between vals
    interp_x = np.linspace(0, samples - 1, 2 * samples - 1)
    #print("interpolator2")
    def f(cumulative:List[int]) -> List[int]:
        #print("interpolator3")
        return np.interp(interp_x, interp_xp, cumulative) #type:ignore
    return f

# interpret one row
def bytes_to_array(interpolator:Callable[[List[int]],List[int]],
                   all_fields:List[bytes], data_col:int, first_col:int,
                   trim_first:bool ) -> Any:
    ########print("type(all_fields)")
    #######print(type(all_fields))
    #######print(all_fields)
    try:
        #######print("b0")
        field = all_fields[data_col]
        #######print("b1")
        decoded = binascii.unhexlify(field)
        #######print("b2")
        first = int(all_fields[first_col])
        #######print("b3")
        offsetted = (y-128 for y in decoded)
        #######print("b4")
        cumulative = list(itertools.accumulate(offsetted, func=operator.add, initial=first))
        # TODO: stop encoding the first delta as zero
        #######print("b5")
        cumulative.pop(0)
        interpolated = interpolator(cumulative)
        if trim_first:
            interpolated = interpolated[1:]
        else:
            interpolated = interpolated[:-1]
        return interpolated
    except (IndexError, TypeError, ValueError) as error:
        print(error)
        print(f'ignore broken line: {all_fields}', file=sys.stderr)
        return None

# input: fields from arduino, WITHOUT the time stamp
def goodrow(x:List[bytes]) -> bool:
    #######print("goodrow")
    if x is None:
        print(f'skip empty row')
        return False
    if len(x) != 8:
        print(f'skip row len {len(x)}')
        return False
    #######print(type(x[1]))
    if x[1] != b'0':
        print(f'skip row err {x[1]!r}')
        return False
    return True


# input: one raw row from arduino, WITHOUT the time stamp
# TODO actually fix it to not use timestamp
# output: (volts[], amps[]) to suit VI plots, or None, for invalid row
def decode_and_interpolate(interpolator:Callable[[List[int]],List[int]],
                           line:bytes) -> Optional[VA]:
    #######print("interp")
    #######print(type(line))
    #######print(line)
    fields = line.split()

    if not goodrow(fields):
        return None # skip obviously bad rows

    #######print("interp2")

    # volts is the first observation, so trim the first value
    volts:List[int] = bytes_to_array(interpolator,fields,5,4,True)
    if volts is None:
        return None
        # skip uninterpretable rows

    # amps is the second observation, so trim the last value
    amps:List[int] = bytes_to_array(interpolator,fields,7,6,False)
    if amps is None:
        return None # skip uninterpretable rows

    return VA(volts, amps)

# input: observations (volts, amps)
# output: average power in watts
def average_power_watts(volts: List[int], amps: List[int]) -> int:
    return np.average(np.multiply(volts, amps)) #type:ignore
