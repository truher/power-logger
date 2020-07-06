"""Logger application"""
from __future__ import annotations
import csv
import json
import queue
import sys
import threading
import time
import traceback
import warnings
from config import loadnames
from datetime import datetime
from typing import Any, Optional
from serial.threaded import ReaderThread #type:ignore
from flask import Flask, Response
from waitress import serve #type:ignore
import numpy as np
import lib

SAMPLE_DATA_FILENAME = 'data_sample.csv'
RAW_DATA_FILENAME = 'data_raw.csv'
HOURLY_DATA_FILENAME = 'data_hourly.csv'

app = Flask(__name__)
rng = np.random.default_rng() #type:ignore

raw_queue: queue.SimpleQueue[bytes] = queue.SimpleQueue()

# arduino takes batches of 1000 points
OBSERVATION_COUNT = 1000

randx = rng.integers(1023, size=100)
randy = rng.integers(1023, size=100)

latest_va = {'load1': lib.VA('load1',randx,randy),
             'load2': lib.VA('load2',randx,randy),
             'load3': lib.VA('load3',randx,randy),
             'load4': lib.VA('load4',randx,randy),
             'load5': lib.VA('load5',randx,randy),
             'load6': lib.VA('load6',randx,randy),
             'load7': lib.VA('load7',randx,randy),
             'load8': lib.VA('load8',randx,randy),}

def va_updater(volts_amps: lib.VA) -> None:
    """Callback for updating VA"""
    latest_va[volts_amps.load] = volts_amps

TRIM_FREQ = 200 # trim every N rows
TRIM_SIZE = 10000 # size of raw file to retain

def data_writer() -> None:
    """Updates the raw file.

    Reads some rows from the queue, writes them to the raw data file
    and periodically trims it.
    """
    while True:
        try:
            # TODO: remove sample data, it's just for debugging
            with open(RAW_DATA_FILENAME, 'ab') as sink, open(SAMPLE_DATA_FILENAME, 'ab') as sample_sink:
                for _ in range(TRIM_FREQ):

                    line = raw_queue.get()
                    # print(line) # TODO for debugging, make configurable
                    now_s: str = datetime.now().isoformat(timespec='microseconds')
                    now_b: bytes = now_s.encode('ascii')

                    # TODO: timestamp at enqueue rather than dequeue, avoid linger time?
                    old_format_line: bytes = now_b + b' ' + line

                    samples: Optional[lib.VA] = lib.decode_and_interpolate(
                        loadnames, old_format_line)
                    if not samples:
                        continue

                    sample_v_mean: float = np.mean(samples.volts) #type:ignore
                    sample_v_stdev: float = np.std(samples.volts) #type:ignore
                    sample_a_mean: float = np.mean(samples.amps) #type:ignore
                    sample_a_stdev: float = np.std(samples.amps) #type:ignore
 
                    sample_line: str = f'{now_s}\t{samples.load}\t{sample_v_mean}\t{sample_v_stdev}\t{sample_a_mean}\t{sample_a_stdev}'
                    sample_sink.write(sample_line.encode('ascii'))
                    sample_sink.write(b'\n')
                    sample_sink.flush()

                    zeroed: lib.VA = lib.zero_samples(samples)
                    lib.do_stats(zeroed.load, zeroed.volts, zeroed.amps)
                    volts_amps: lib.VA = lib.scale_samples(zeroed)

                    va_updater(volts_amps)
                    pwr: float = lib.average_power_watts(volts_amps.volts,
                                                  volts_amps.amps)
                    vrms: float = lib.rms(volts_amps.volts)
                    arms: float = lib.rms(volts_amps.amps)
                    load_s: str = volts_amps.load
                    real_old_format_line = f'{now_s}\t{load_s}\t{pwr}\t{vrms}\t{arms}'
                    sink.write(real_old_format_line.encode('ascii'))
                    sink.write(b'\n')
                    sink.flush()

            lib.trim(RAW_DATA_FILENAME, TRIM_SIZE)
            lib.trim(SAMPLE_DATA_FILENAME, TRIM_SIZE)
        except: # pylint: disable=bare-except
            traceback.print_exc(file=sys.stderr)
            print("top level exception",
                  sys.exc_info()[0], file=sys.stderr)

def queue_writer_factory() -> lib.QueueLine:
    """Produce a QueueLine instance."""
    return lib.QueueLine(raw_queue)

def data_reader() -> None:
    """Continuously reads serial inputs, writes to queue."""
    serials: ReaderThread = []
    while True:
        try:
            # TODO: catch lost connections, and use notify to catch new ttys
            serials = lib.refresh_serials(serials, queue_writer_factory)
            time.sleep(10)
        except: # pylint: disable=bare-except
            traceback.print_exc(file=sys.stderr)
            print("top level exception",
                  sys.exc_info()[0], file=sys.stderr)

def summarizer() -> None:
    """Periodically read the raw file and update the hourly file."""
    while True:
        try:
            time.sleep(60)
            # all the raw data available
            load_data = lib.read_raw_no_header(RAW_DATA_FILENAME)
            # all the hourly data available
            hourly = lib.make_multi_hourly(load_data)
            # this is the previously written history
            hourly_file = lib.read_hourly_no_header(HOURLY_DATA_FILENAME)
            # the first hour in this set is surely partial; ignore it
            # unless the history is also empty
            if len(hourly) > 0 and len(hourly_file) > 0:
                hourly = hourly.drop(hourly.index[0]) #type:ignore
            # remove rows corresponding to the new summary
            hourly_file = hourly_file[
                ~hourly_file.index.isin(hourly.index)] #type:ignore
            # append the new summary
            hourly_file = hourly_file.append(hourly)
            hourly_file.sort_index(inplace=True) #type:ignore
            # write the result to 6 sig fig
            hourly_file.to_csv(HOURLY_DATA_FILENAME,
                               sep=' ',
                               header=False, #type:ignore
                               date_format='%Y-%m-%dT%H',
                               quoting=csv.QUOTE_NONE,
                               float_format='%.6g')
        except: # pylint: disable=bare-except
            traceback.print_exc(file=sys.stderr)
            print("top level exception",
                  sys.exc_info()[0], file=sys.stderr)

@app.route('/')
def index() -> Any:
    """index"""
    print('index')
    return app.send_static_file('index.html')

# TODO: serve these using send_from_directory
@app.route('/logger')
def logger() -> Any:
    """logger"""
    print('logger')
    return app.send_static_file('logger.html')

@app.route('/timeseries')
def timeseries() -> Any:
    """timeseries"""
    print('timeseries')
    return app.send_static_file('timeseries.html')

@app.route('/raw')
def raw() -> Any:
    """raw"""
    print('raw')
    return app.send_static_file('raw.html')

@app.route('/summary')
def summary() -> Any:
    """summary"""
    print('summary')
    return app.send_static_file('summary.html')

@app.route('/stats')
def stats() -> Any:
    """stats"""
    print('stats')
    return app.send_static_file('stats.html')

@app.route('/rawdata')
def rawdata() -> Any:
    """rawdata"""
    print('rawdata')
    raw_data = lib.read_raw_no_header(RAW_DATA_FILENAME)
    json_payload = json.dumps(raw_data.to_records().tolist()) #type:ignore
    return Response(json_payload, mimetype='application/json')

@app.route('/summarydata')
def summarydata() -> Any:
    """summarydata"""
    print('summarydata')
    hourly = lib.read_hourly_no_header(HOURLY_DATA_FILENAME)
    json_payload = json.dumps(hourly.to_records().tolist()) #type:ignore
    return Response(json_payload, mimetype='application/json')

@app.route('/data')
def data() -> Any:
    """data"""
    print('data')
    loadlist = [{'load': va.load,
                 'volts': va.volts.tolist(), #type:ignore
                 'amps': va.amps.tolist()} #type:ignore
                for va in latest_va.values()]
    json_payload = json.dumps(loadlist)
    return Response(json_payload, mimetype='application/json')

def main() -> None:
    """main"""
    warnings.filterwarnings('ignore')
    threading.Thread(target=data_reader).start()
    threading.Thread(target=data_writer).start()
    threading.Thread(target=summarizer).start()
    serve(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
