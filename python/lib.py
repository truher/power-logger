"""Library for power logging."""
from __future__ import annotations
from dataclasses import dataclass
from glob import glob
from typing import Callable, Dict, List, NamedTuple, Optional
import base64
import math
import os
import queue
import sys
import time
from serial.threaded import Packetizer, ReaderThread #type:ignore
from scipy import integrate #type:ignore
from scipy.signal import butter
from scipy.signal import filtfilt
import numpy as np
import pandas as pd
import serial #type:ignore
from config import ACTUAL_RMS_VOLTS
from config import ACTUAL_RMS_AMPS
from config import scale_rms_volts
from config import scale_rms_amps

import cmath

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
        # TODO: prepend timestamp?
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
        file_contents = pd.read_csv(filename, delim_whitespace=True, #type:ignore
                                    comment='#', index_col=0,
                                    parse_dates=True, header=None,
                                    names=['time', 'load', 'measure', 'vrms', 'arms'])
        file_contents = file_contents.fillna(0)
        file_contents.sort_index(inplace=True) #type:ignore
        return file_contents

    new_frame = pd.DataFrame(columns=['time', 'load', 'measure', 'vrms', 'arms'])
    new_frame.set_index(keys='time', inplace=True) #type:ignore
    new_frame.sort_index(inplace=True) #type:ignore
    return new_frame

# return (time, measure, load)
def read_hourly_no_header(filename: str) -> pd.DataFrame:
    """Reads an hourly file."""
    if os.path.isfile(filename):
        file_contents = pd.read_csv(filename, delim_whitespace=True, #type:ignore
                                    comment='#', index_col=0,
                                    parse_dates=True, header=None,
                                    names=['time', 'load', 'measure'])
        file_contents = file_contents.fillna(0)
        return file_contents
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

@dataclass
class Conf:
    """configuration state of the arduino"""
    channel: int = 0
    frequency: int = 0
    length: int = 0

# TODO: add power here
class VA(NamedTuple):
    """one named observation of volts and amps series"""
    load: str
    frequency: int
    length: int
    volts: np.ndarray[np.float64] # pylint: disable=E1136  # pylint/issues/3139
    amps: np.ndarray[np.float64] # pylint: disable=E1136  # pylint/issues/3139

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

# refresh the serials list (in place) with ttys
def refresh_serials(serials: List[ReaderThread],
                    queue_writer_factory: Callable[[], QueueLine]) -> None:
                    #queue_writer_factory: Callable[[], QueueLine]) -> List[ReaderThread]:
    """Checks for new ttys and dead serials, return a good list."""

    # list of the ttys that exist
    ttys: List[str] = glob("/dev/ttyACM*")

    # keep the list of serial ports that are open and that match a tty
    # TODO: replace is_open with the threaded connection_lost method?
    # TODO: dispose of the broken ones somehow?
    serials[:] = [*filter(lambda x: is_open(x) and has_tty(ttys)(x), serials)]

    # create new serials for ttys without serials
    ttys_needing_serials = filter(no_serial(serials), ttys)

    for tty in ttys_needing_serials:
        serials.append(new_serial(tty, queue_writer_factory))

    #return serials

# interpret one row
def bytes_to_array(all_fields: List[bytes],
                   data_col: int) -> Optional[np.ndarray[np.float64]]: # pylint: disable=E1136
    """Decode one sample series.
    Returns:
        An ndarray containing the samples
    """
    try:
        field: bytes = all_fields[data_col]
        decoded: bytes = base64.b85decode(field)
        unpacked: np.ndarray[np.int16] = ( # pylint: disable=E1136  # pylint/issues/3139
            np.frombuffer(decoded, dtype='int16')) #type:ignore
        return unpacked.astype(np.float64)
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
    if len(fields) != 7:
        print(f'skip row len {len(fields)}')
        print(fields)
        return False
    return True

def load(loadnames: Dict[bytes, str], fields: List[bytes]) -> str:
    """Maps arduino fields to load names.

    Args:
        fields: parsed arduino line

    Returns:
        Load name
    """
    return loadnames[fields[1]+fields[2]]

@dataclass
class Sums:
    """sums"""
    count: int = 0
    total: float = 0
    sq_total: float = 0

@dataclass
class Stats:
    """stats"""
    count: int
    mean: float
    rms: float

@dataclass
class LoadSums:
    """load sums"""
    name: str
    vsums: Sums
    asums: Sums

# TODO: derive this from loadnames
allsums = {'load1': LoadSums('load1', Sums(), Sums()),
           'load2': LoadSums('load2', Sums(), Sums()),
           'load3': LoadSums('load3', Sums(), Sums()),
           'load4': LoadSums('load4', Sums(), Sums()),
           'load5': LoadSums('load5', Sums(), Sums()),
           'load6': LoadSums('load6', Sums(), Sums()),
           'load7': LoadSums('load7', Sums(), Sums()),
           'load8': LoadSums('load8', Sums(), Sums()),
           'load9': LoadSums('load9', Sums(), Sums()),
           'load10': LoadSums('load10', Sums(), Sums()),
           'load11': LoadSums('load11', Sums(), Sums()),
           'load12': LoadSums('load12', Sums(), Sums()),
           'load13': LoadSums('load13', Sums(), Sums()),
           'load14': LoadSums('load14', Sums(), Sums()),
           'load15': LoadSums('load15', Sums(), Sums()),
           'load16': LoadSums('load16', Sums(), Sums())}

def update_stats(samples: np.ndarray[np.float64], # pylint: disable=E1136  # pylint/issues/3139
                 sums: Sums) -> None:
    """Keeps running stats
    Args:
        samples: an ndarray
    """
    for sample in samples:
        sums.total += sample
        sums.sq_total += sample * sample
        sums.count += 1

def dump_stats(sums: Sums) -> Stats:
    """Calculate count, mean, vms"""
    if sums.count == 0:
        return Stats(0, 0, 0)
    return Stats(sums.count, sums.total/sums.count,
                 math.sqrt(sums.sq_total/sums.count))

def print_stats(lsums: LoadSums) -> None:
    """print a summary of stats"""
    vstats: Stats = dump_stats(lsums.vsums)
    astats: Stats = dump_stats(lsums.asums)
    print(f'{lsums.name} {vstats.count} {vstats.mean} {vstats.rms}'
          f' {astats.count} {astats.mean} {astats.rms}')

def do_stats(load_name_s: str,
             volt_samples: np.ndarray[np.float64], # pylint: disable=E1136  # pylint/issues/3139
             amp_samples: np.ndarray[np.float64]) -> None: # pylint: disable=E1136  # pylint/issues/3139
    """maintain stats"""
    lsums: LoadSums = allsums[load_name_s]
    update_stats(volt_samples, lsums.vsums)
    update_stats(amp_samples, lsums.asums)
    print_stats(lsums)


def zero_samples(samples: VA) -> VA:
    """Eliminates sample offset.

    Since these are AC coupled measurements, and we look for
    a long time, the zero is just the mean.
    """
    volts: np.ndarray[np.float64] = (# pylint: disable=E1136  # pylint/issues/3139
        samples.volts)
    amps: np.ndarray[np.float64] = ( # pylint: disable=E1136  # pylint/issues/3139
        samples.amps)

    volts = volts - np.mean(volts)
    amps = amps - np.mean(amps)

    # low-pass filtering, seems like i don't need this anymore?
    #cutoff_freq = 300  # 15f
    #cutoff_freq = 900  # 15f
    #cutoff_freq = 300  # 5f, ok with order 3?
    #cutoff_freq = 60  # f duh this reduces amplitude by half, by defintion of butterworth
    #filter_order = 2
    #filter_order = 5
    #b, a = butter(filter_order, 2*cutoff_freq/samples.frequency)
    # padding to avoid edge effects
    # TODO: less padding :-)
    # bah this does not work because mirroring the edge is a crummy extrapolation
    # TODO: cut off the edges?
    #amps = filtfilt(b, a, np.concatenate((np.flip(amps),amps,np.flip(amps))))[amps.size:2*amps.size]
    #volts = filtfilt(b, a, np.concatenate((np.flip(volts),volts,np.flip(volts))))[volts.size:2*volts.size]
    #volts = filtfilt(b, a, volts)
    #amps = filtfilt(b, a, amps)

    # phase correction with FFT (eyeballed the difference)
    amps = np.fft.irfft(np.fft.rfft(amps) * cmath.rect(1., 2 * np.pi / 180))
    volts = np.fft.irfft(np.fft.rfft(volts) * cmath.rect(1., 7 * np.pi / 180))
    
    return VA(samples.load, samples.frequency, samples.length, volts, amps)

def scale_samples(samples: VA) -> VA:
    """Transforms zeroed samples to measures"""
    scale_vrms: float = scale_rms_volts[samples.load]
    scale_arms: float = scale_rms_amps[samples.load]
    volts: np.ndarray[np.float64] = ( # pylint: disable=E1136  # pylint/issues/3139
        samples.volts * ACTUAL_RMS_VOLTS / scale_vrms)
    amps: np.ndarray[np.float64] = ( # pylint: disable=E1136  # pylint/issues/3139
        samples.amps * ACTUAL_RMS_AMPS / scale_arms)
    return VA(samples.load, samples.frequency, samples.length, volts, amps)

# date uid ct len b1 b2
def decode(loadnames: Dict[bytes, str], line: bytes) -> Optional[VA]:
    """Decodes sample series.

    Args:
        line: raw (encoded) input from arduino

    Returns:
        A VA named tuple containing sample series,
        or None, for invalid input
    """
    fields: List[bytes] = line.split()

    if not goodrow(fields):
        return None # skip obviously bad rows

    load_name_s: str = load(loadnames, fields)

    # volts is the first observation, so trim the first value
    volt_samples: Optional[np.ndarray[np.float64]] = ( # pylint: disable=E1136  # pylint/issues/3139
        bytes_to_array(fields, 5))
    if volt_samples is None:
        return None # skip uninterpretable rows

    # amps is the second observation, so trim the last value
    amp_samples: Optional[np.ndarray[np.float64]] = ( # pylint: disable=E1136  # pylint/issues/3139
        bytes_to_array(fields, 6))
    if amp_samples is None:
        return None # skip uninterpretable rows

    frequency = int(fields[3])
    length = int(fields[4])

    return VA(load_name_s, frequency, length, volt_samples, amp_samples)

# TODO: add the multiply to VA
def average_power_watts(volts: np.ndarray[np.float64], # pylint: disable=E1136  # pylint/issues/3139
                        amps: np.ndarray[np.float64]) -> float: # pylint: disable=E1136  # pylint/issues/3139
    """Calculates average power in watts.

    Args:
        volts: series of voltage samples
        amps: series of current samples
    """
    return np.average(np.multiply(volts, amps)) #type:ignore

def rms(samples: np.ndarray[np.float64]) -> float: # pylint: disable=E1136  # pylint/issues/3139
    """RMS of samples"""
    return math.sqrt(np.sum(samples*samples)/len(samples))
