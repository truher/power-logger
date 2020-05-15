from __future__ import annotations
import numpy as np
import pandas as pd
import serial #type:ignore
from serial.threaded import Packetizer,ReaderThread #type:ignore
import binascii, itertools, operator, os, queue, sys, time, traceback

from datetime import datetime
from glob import glob
from scipy import integrate #type:ignore
from typing import Any, Callable, Dict, IO, List, Optional, Tuple, Union
from collections import namedtuple

class QueueLine(Packetizer): #type:ignore
    TERMINATOR = b'\n'
    SLEEP_TIME = 0.05 # reduce the spinning in a very simple way
    def __init__(self, raw_queue: queue.SimpleQueue[bytes]) -> None:
        super().__init__()
        self.raw_queue = raw_queue
        self.buffers_per_line = 0
    def connection_made(self, transport: ReaderThread) -> None:
        print('port opened')
        super().connection_made(transport)
    def handle_packet(self, packet: bytes) -> None:
        #print(f"{datetime.now()} port {self.transport.serial.port} line {len(packet)} buffers per line  {self.buffers_per_line}")
        self.buffers_per_line = 0
        self.raw_queue.put(packet)
    def connection_lost(self, exc:Exception) -> None:
        print('port closed')
        super().connection_lost(exc)
    def data_received(self, data:bytes) -> None:
        # overrides Packetizer.data_received
        #print(f'{datetime.now()} port {self.transport.serial.port} data buffer {len(self.buffer)} new len {len(data)}')
        self.buffers_per_line += 1
        self.buffer.extend(data) #type:ignore
        while self.TERMINATOR in self.buffer: #type:ignore
            packet, self.buffer = self.buffer.split(self.TERMINATOR, 1) #type:ignore
            self.handle_packet(packet)
        # sleep immediately *after* handling the packet to avoid harming latency
        time.sleep(self.SLEEP_TIME)

# see arduino.ino
# TODO: use a common format somehow?
# TODO: use tab or space not both
# input, tab/space delimited
# time err uid ct v_first v_bytes a_first a_bytes
# return (time, id, ct, measure)
def read_raw_no_header(filename:str) -> pd.DataFrame:
    if os.path.isfile(filename):
        x = pd.read_csv(filename, delim_whitespace=True, comment='#', #type:ignore
        #return pd.read_csv(filename, delim_whitespace=True, comment='#', #type:ignore
                       index_col=0, parse_dates=True, header=None,
                       #names=['time','id','ct','measure'])
                       names=['time','load','measure'])
        #x.set_index(keys='time', inplace=True)
        x.sort_index(inplace=True) #type:ignore
        return x
    else:
        #x = pd.DataFrame(columns=['time','id','ct','measure'])
        x = pd.DataFrame(columns=['time','load','measure'])
        x.set_index(keys='time', inplace=True) #type:ignore
        x.sort_index(inplace=True) #type:ignore
        return x

# return (time, measure, load)
def read_hourly_no_header(filename:str) -> pd.DataFrame:
    if os.path.isfile(filename):
        return pd.read_csv(filename, delim_whitespace=True, comment='#', #type:ignore
                       index_col=0, parse_dates=True, header=None,
                       names=['time','load','measure'])
    else:
        x = pd.DataFrame(columns=['time','load','measure'])
        x.set_index(keys='time', inplace=True) #type:ignore
        return x

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

# TODO: add power here
# in order to pass null
VA = namedtuple('VA', ['load','volts','amps'])   



# trim file <filename> to latest <count> lines
# TODO: use a circular mmap instead
def trim(filename:str, count:int) -> None:
    #print("trim")
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
        print(f'parse ignore broken line: {line}', file=sys.stderr)
        return None

# create new serial stream
def new_serial(port:str, factory: Callable[[],QueueLine]) -> ReaderThread:
    print(f'new {port}', file=sys.stderr, flush=True)
    ser = serial.Serial(port, 115200, 8, 'N', 1, timeout=1)
    t = ReaderThread(ser, factory)
    t.start()
    t.connect()
    return t

def is_open(ser:ReaderThread) -> bool:
    if ser.serial.is_open:
        return True
    print(f'closed {ser.s.port}', file=sys.stderr, flush=True)
    return False

def has_tty(ttys:List[str]) -> Callable[[ReaderThread], bool]:
    def f(ser:ReaderThread) -> bool:
        if ser.serial.port in ttys:
            return True
        print(f'no tty {ser.serial.port}', file=sys.stderr, flush=True)
        return False
    return f

# this is to make mypy happy
def get_port(s:ReaderThread) -> str:
    port:str = s.serial.port
    return port
    
def no_serial(serials:List[ReaderThread]) -> Callable[[str], bool]:
    current_ports:List[str] = [*map(get_port , serials)]
    def f(tty:str) -> bool:
        if tty in current_ports:
            return False
        print(f'no serial {tty}', file=sys.stderr, flush=True)
        return True
    return f

# refresh the serials list with ttys
def refresh_serials(serials:List[ReaderThread],
                    queue_writer_factory: Callable[[],QueueLine]) -> List[ReaderThread]:

    # list of the ttys that exist
    ttys:List[str] = glob("/dev/ttyACM*")

    # keep the list of serial ports that are open and that match a tty
    # TODO: replace is_open with the threaded connection_lost method?
    # TODO: dispose of the broken ones somehow?
    serials = [*filter(lambda x: is_open(x) and has_tty(ttys)(x), serials)]

    # create new serials for ttys without serials
    ttys_needing_serials = filter(no_serial(serials), ttys)

    for tty in ttys_needing_serials:
        serials.append(new_serial(tty, queue_writer_factory))

    return serials

# read the whole file into a list of lines
def readfile(filename:str) -> List[bytes]:
    with open(filename, 'rb') as datafile: # type: IO[bytes]
        return datafile.readlines()

def read_new_raw(filename:str) -> Any:
    return ['foo']

# avoid creating the bases for every row, create it once
def interpolator(samples:int) -> Callable[[List[int]], List[int]]:
    # x vals for observations
    interp_xp = np.linspace(0, samples - 1, samples)
    # x vals for interpolations, adds in-between vals
    interp_x = np.linspace(0, samples - 1, 2 * samples - 1)
    def f(cumulative:List[int]) -> List[int]:
        return np.interp(interp_x, interp_xp, cumulative) #type:ignore
    return f

# interpret one row
def bytes_to_array(interpolator:Callable[[List[int]],List[int]],
                   all_fields:List[bytes], data_col:int, first_col:int,
                   trim_first:bool ) -> Any:
    try:
        field = all_fields[data_col]
        decoded = binascii.unhexlify(field)
        first = int(all_fields[first_col])
        offsetted = (y-128 for y in decoded)
        cumulative = list(itertools.accumulate(offsetted, func=operator.add, initial=first))
        # TODO: stop encoding the first delta as zero
        cumulative.pop(0)
        interpolated = interpolator(cumulative)
        if trim_first:
            interpolated = interpolated[1:]
        else:
            interpolated = interpolated[:-1]
        return interpolated
    except (IndexError, TypeError, ValueError) as error:
        print(error)
        print(f'bytes_to_array ignore broken line: {all_fields}', file=sys.stderr)
        return None

# input: fields from arduino, WITHOUT the time stamp
def goodrow(x:List[bytes]) -> bool:
    if x is None:
        print(f'skip empty row')
        return False
    if len(x) != 8:
        print(f'skip row len {len(x)}')
        print(x)
        return False
    if x[1] != b'0':
        print(f'skip row err {x[1]!r}')
        return False
    return True

loadnames = {b"5737333034370D0E14ct1":b'load1',
             b"5737333034370D0E14ct2":b'load2',
             b"5737333034370D0E14ct3":b'load3',
             b"5737333034370D0E14ct4":b'load4',
             b"5701333034370A220Dct1":b'load5',
             b"5701333034370A220Dct2":b'load6',
             b"5701333034370A220Dct3":b'load7',
             b"5701333034370A220Dct4":b'load8'}

# extract name from a row
# TODO: change to new format
def load(x:List[bytes]) -> bytes:
    return loadnames[x[2]+x[3]]


# input: one raw row from arduino, WITHOUT the time stamp
# TODO actually fix it to not use timestamp
# output: (volts[], amps[]) to suit VI plots, or None, for invalid row
def decode_and_interpolate(interpolator:Callable[[List[int]],List[int]],
                           line:bytes) -> Optional[VA]:
    fields = line.split()

    if not goodrow(fields):
        return None # skip obviously bad rows

    load_name = load(fields)

    # volts is the first observation, so trim the first value
    volts:List[int] = bytes_to_array(interpolator,fields,5,4,True)
    if volts is None:
        return None # skip uninterpretable rows

    # amps is the second observation, so trim the last value
    amps:List[int] = bytes_to_array(interpolator,fields,7,6,False)
    if amps is None:
        return None # skip uninterpretable rows

    return VA(load_name,volts, amps)

# TODO: add the multiply to VA
# input: observations (volts, amps)
# output: average power in watts
def average_power_watts(volts: List[int], amps: List[int]) -> int:
    return np.average(np.multiply(volts, amps)) #type:ignore


