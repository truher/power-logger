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
from datetime import datetime
from typing import Any
from serial.threaded import ReaderThread #type:ignore
from flask import Flask, Response
from waitress import serve #type:ignore
import numpy as np
import lib

RAW_DATA_FILENAME = 'data_raw.csv'
HOURLY_DATA_FILENAME = 'data_hourly.csv'

app = Flask(__name__)
rng = np.random.default_rng() #type:ignore

raw_queue: queue.SimpleQueue[bytes] = queue.SimpleQueue()

# arduino takes batches of 1000 points
OBSERVATION_COUNT = 1000
interpolator = lib.interpolator(OBSERVATION_COUNT)

randxy = {'x': rng.integers(1023, size=100),
          'y': rng.integers(1023, size=100)}

latest_va = {'load1': randxy,
             'load2': randxy,
             'load3': randxy,
             'load4': randxy,
             'load5': randxy,
             'load6': randxy,
             'load7': randxy,
             'load8': randxy}

def va_updater(volts_amps: lib.VA) -> None:
    """Callback for updating VA"""
    loadname = volts_amps.load.decode('ascii')
    if volts_amps.load not in latest_va:
        latest_va[loadname] = {'x': [], 'y': []}
    latest_va[loadname]['x'] = volts_amps.volts
    latest_va[loadname]['y'] = volts_amps.amps


TRIM_FREQ = 100 # trim every 30 rows
TRIM_SIZE = 5000 # size of raw file to retain

def data_writer() -> None:
    """Updates the raw file.

    Reads some rows from the queue, writes them to the raw data file
    and periodically trims it.
    """
    while True:
        try:
            with open(RAW_DATA_FILENAME, 'ab') as sink:
                for _ in range(TRIM_FREQ):

                    line = raw_queue.get()
                    now_s = datetime.now().isoformat(timespec='microseconds')
                    now_b = now_s.encode('ascii')

                    old_format_line = now_b + b' ' + line

                    volts_amps = lib.decode_and_interpolate(interpolator,
                                                            old_format_line)
                    if volts_amps:
                        va_updater(volts_amps)
                        pwr = lib.average_power_watts(volts_amps.volts,
                                                      volts_amps.amps)
                        load_str = volts_amps.load.decode('ascii')
                        real_old_format_line = f'{now_s}\t{load_str}\t{pwr}'
                        sink.write(real_old_format_line.encode('ascii'))
                        sink.write(b'\n')
                        sink.flush()

            lib.trim(RAW_DATA_FILENAME, TRIM_SIZE)
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

@app.route('/timeseriesdata')
def timeseriesdata() -> Any:
    """timeseriesdata"""
    print('timeseriesdata')
    loadlist = [{'label': load,
                 'x': samples['x'].tolist(),
                 'y': samples['y'].tolist()}
                for load, samples in latest_va.items()]
    json_payload = json.dumps(loadlist)
    return Response(json_payload, mimetype='application/json')

@app.route('/data')
def data() -> Any:
    """data"""
    print('data')
    loadlist = [{'label': load,
                 'x': samples['x'].tolist(),
                 'y': samples['y'].tolist()}
                for load, samples in latest_va.items()]
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
