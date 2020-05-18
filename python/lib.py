"""Library for power logging."""
from __future__ import annotations
from collections import namedtuple
from glob import glob
from typing import Any, Callable, IO, List, Optional
import binascii
import itertools
import operator
import os
import queue
import sys
import time
from serial.threaded import Packetizer, ReaderThread #type:ignore
from scipy import integrate #type:ignore
import numpy as np
import pandas as pd

import serial #type:ignore

class QueueLine(Packetizer): #type:ignore
    """Handles input within one reader thread."""
    TERMINATOR = b'\n'
    SLEEP_TIME = 0.05 # reduce the spinning in a very simple way
    def __init__(self, raw_queue: queue.SimpleQueue[bytes]) -> None:
        """Inits QueueLine with the specified queue."""
        super().__init__()
        self.raw_queue = raw_queue
        self.buffers_per_line = 0
    def connection_made(self, transport: ReaderThread) -> None:
        """Prints a message on connect."""
        print('port opened')
        super().connection_made(transport)
    def handle_packet(self, packet: bytes) -> None:
        """Enqueues a line."""
        self.buffers_per_line = 0
        self.raw_queue.put(packet)
    def connection_lost(self, exc: Exception) -> None:
        """Prints a message on disconnect."""
        print('port closed')
        super().connection_lost(exc)
    def data_received(self, data: bytes) -> None:
        """Handle a block (override).

        Buffers the input, calls handle_packet if there's a complete line.
        Sleeps awhile to avoid spinning.
        """
        self.buffers_per_line += 1
        self.buffer.extend(data) #type:ignore
        while self.TERMINATOR in self.buffer: #type:ignore
            packet, self.buffer = self.buffer.split(self.TERMINATOR, 1) #type:ignore
            self.handle_packet(packet)
        # sleep immediately *after* handling the packet to avoid harming latency
        time.sleep(self.SLEEP_TIME)

def read_raw_no_header(filename: str) -> pd.DataFrame:
    """Reads a raw file.

    See arduino.ino

    Args:
        filename: input file, whitespace delimited, with these columns:
            time err uid ct v_first v_bytes a_first a_bytes

    Returns:
        DataFrame with index (time), columns (load, ct, measure)
    """
    if os.path.isfile(filename):
        file_contents = pd.read_csv(filename, delim_whitespace=True,
                                    comment='#', index_col=0,
                                    parse_dates=True, header=None,
                                    names=['time', 'load', 'measure'])
        file_contents.sort_index(inplace=True) #type:ignore
        return file_contents

    new_frame = pd.DataFrame(columns=['time', 'load', 'measure'])
    new_frame.set_index(keys='time', inplace=True) #type:ignore
    new_frame.sort_index(inplace=True) #type:ignore
    return new_frame

# return (time, measure, load)
def read_hourly_no_header(filename: str) -> pd.DataFrame:
    """Reads an hourly file."""
    if os.path.isfile(filename):
        return pd.read_csv(filename, delim_whitespace=True, comment='#',
                           index_col=0, parse_dates=True, header=None,
                           names=['time', 'load', 'measure'])
    new_frame = pd.DataFrame(columns=['time', 'load', 'measure'])
    new_frame.set_index(keys='time', inplace=True) #type:ignore
    return new_frame

def make_multi_hourly(load_data: pd.DataFrame) -> pd.DataFrame:
    """Aggregates VI data by hour, for each load.

        Treats each load separately, then merges at the end.

    Args:
        DataFrame with index (time), columns (time, measure, load)

    Returns:
        Dataframe with index (time), columns (time, measure, load)
    """
    hourly = pd.DataFrame(columns=['measure'])
    for one_load in list(set(load_data['load'])):
        hourly = hourly.append(
            make_hourly(load_data[load_data['load'] == one_load][['measure']])
            .assign(load=one_load)) #type:ignore
    group = hourly.groupby(level=0).sum() #type:ignore
    hourly = hourly.append(group.assign(load='total'))
    hourly = hourly.reindex(columns=['measure', 'load']) #type:ignore
    return hourly

def make_hourly(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate VI data by hour for one load.

    Args:
        DataFrame with index (time), columns (measure).  Time can be anything.

    Returns:
        Dataframe with index (time), columns (measure).  Time has hour grain.
    """
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
    raw_data_with_buckets.at[raw_data_with_buckets.index.min()] = 0 #type:ignore

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
    hourly = cum_kwh.resample(rule='H', closed='right', label='right', #type:ignore
                              loffset='-1H').max().diff().dropna().iloc[1:]
    return hourly #type:ignore

# TODO: add power here
# This NamedTuple exists in order to pass null
VA = namedtuple('VA', ['load', 'volts', 'amps'])



def trim(filename: str, count: int) -> None:
    """Read the file and write out the last <count> lines."""
    lines = []
    with open(filename, 'rb') as source:
        lines = source.readlines()
    lines = lines[-count:]
    with open(filename, 'wb') as sink:
        sink.writelines(lines)

def new_serial(port: str, factory: Callable[[], QueueLine]) -> ReaderThread:
    """Creates a new serial stream, in its own reader thread."""
    print(f'new {port}', file=sys.stderr, flush=True)
    ser = serial.Serial(port, 115200, 8, 'N', 1, timeout=1)
    reader_thread = ReaderThread(ser, factory)
    reader_thread.start()
    reader_thread.connect()
    return reader_thread

def is_open(ser: ReaderThread) -> bool:
    """True if serial is open."""
    if ser.serial.is_open:
        return True
    print(f'closed {ser.s.port}', file=sys.stderr, flush=True)
    return False

def has_tty(ttys: List[str]) -> Callable[[ReaderThread], bool]:
    """Returns a function to check if a port is in the tty list."""
    def f_has_tty(reader_thread: ReaderThread) -> bool:
        """True if the reader thread's serial port is in the tty list."""
        if reader_thread.serial.port in ttys:
            return True
        print(f'no tty {reader_thread.serial.port}', file=sys.stderr, flush=True)
        return False
    return f_has_tty

# this is to make mypy happy
def get_port(reader_thread: ReaderThread) -> str:
    """Returns port from serial within reader_thread."""
    port: str = reader_thread.serial.port
    return port

def no_serial(serials: List[ReaderThread]) -> Callable[[str], bool]:
    """Returns a function to check if a tty is in the port list."""
    current_ports: List[str] = [*map(get_port, serials)]
    def f_no_serial(tty: str) -> bool:
        """True if the tty is not in the port list."""
        if tty in current_ports:
            return False
        print(f'no serial {tty}', file=sys.stderr, flush=True)
        return True
    return f_no_serial

# refresh the serials list with ttys
def refresh_serials(serials: List[ReaderThread],
                    queue_writer_factory: Callable[[], QueueLine]) -> List[ReaderThread]:
    """Checks for new ttys and dead serials, return a good list."""

    # list of the ttys that exist
    ttys: List[str] = glob("/dev/ttyACM*")

    # keep the list of serial ports that are open and that match a tty
    # TODO: replace is_open with the threaded connection_lost method?
    # TODO: dispose of the broken ones somehow?
    serials = [*filter(lambda x: is_open(x) and has_tty(ttys)(x), serials)]

    # create new serials for ttys without serials
    ttys_needing_serials = filter(no_serial(serials), ttys)

    for tty in ttys_needing_serials:
        serials.append(new_serial(tty, queue_writer_factory))

    return serials

# avoid creating the bases for every row, create it once
def interpolator(samples: int) -> Callable[[List[int]], List[int]]:
    """Returns an interpolator function."""
    # x vals for observations
    interp_xp = np.linspace(0, samples - 1, samples)
    # x vals for interpolations, adds in-between vals
    interp_x = np.linspace(0, samples - 1, 2 * samples - 1)
    def f_interp(cumulative: List[int]) -> List[int]:
        """Interpolate the list."""
        # the slice here is for a performance experiment TODO remove it.
        # return np.interp(interp_x, interp_xp[0:len(cumulative)], cumulative) #type:ignore
        return np.interp(interp_x, interp_xp, cumulative) #type:ignore
    return f_interp

# interpret one row
def bytes_to_array(interp: Callable[[List[int]], List[int]],
                   all_fields: List[bytes], data_col: int, first_col: int,
                   trim_first: bool) -> Any:
    """Decode one sample series."""
    try:
        field = all_fields[data_col]
        decoded = binascii.unhexlify(field)
        first = int(all_fields[first_col])
        offsetted = (y-128 for y in decoded)
        cumulative = list(itertools.accumulate(offsetted, func=operator.add, initial=first))
        # TODO: stop encoding the first delta as zero
        cumulative.pop(0)
        interpolated = interp(cumulative)
        if trim_first:
            interpolated = interpolated[1:]
        else:
            interpolated = interpolated[:-1]
        return interpolated
    except (IndexError, TypeError, ValueError) as error:
        print(error)
        print(f'bytes_to_array ignore broken line: {all_fields}', file=sys.stderr)
        return None

def goodrow(fields: List[bytes]) -> bool:
    """Finds obvious kinds of invalidity.

    Args:
        fields: parsed arduino line

    Returns:
        False if invalid, true otherwise
    """
    if fields is None:
        print('skip empty row')
        return False
    if len(fields) != 8:
        print(f'skip row len {len(fields)}')
        print(fields)
        return False
    if fields[1] != b'0':
        print(f'skip row err {fields[1]!r}')
        return False
    return True

loadnames = {b"5737333034370D0E14ct1": b'load1',
             b"5737333034370D0E14ct2": b'load2',
             b"5737333034370D0E14ct3": b'load3',
             b"5737333034370D0E14ct4": b'load4',
             b"5737333034370A220Dct1": b'load5',
             b"5737333034370A220Dct2": b'load6',
             b"5737333034370A220Dct3": b'load7',
             b"5737333034370A220Dct4": b'load8'}

def load(fields: List[bytes]) -> bytes:
    """Maps arduino fields to load names.

    Args:
        fields: parsed arduino line

    Returns:
        Load name
    """
    return loadnames[fields[2]+fields[3]]


def decode_and_interpolate(interp: Callable[[List[int]], List[int]],
                           line: bytes) -> Optional[VA]:
    """Decodes and interpolates sample series.

    Arduino samples voltage and current alternately,
    so the sample series don't line up.  Interpolate
    between the samples and trim the ends.

    Args:
        interp: function that actually does the interpolation
        line: raw (encoded) input from arduino

    Returns:
        A VA named tuple containing interpolated and trimmed sample series,
        or None, for invalid input
    """
    fields = line.split()

    if not goodrow(fields):
        return None # skip obviously bad rows

    load_name = load(fields)

    # volts is the first observation, so trim the first value
    volts: List[int] = bytes_to_array(interp, fields, 5, 4, True)
    if volts is None:
        return None # skip uninterpretable rows

    # amps is the second observation, so trim the last value
    amps: List[int] = bytes_to_array(interp, fields, 7, 6, False)
    if amps is None:
        return None # skip uninterpretable rows

    return VA(load_name, volts, amps)

# TODO: add the multiply to VA
def average_power_watts(volts: List[int], amps: List[int]) -> int:
    """Calculates average power in watts.

    Args:
        volts: series of voltage samples
        amps: series of current samples
    """
    return np.average(np.multiply(volts, amps)) #type:ignore
