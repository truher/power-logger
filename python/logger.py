from __future__ import annotations
import numpy as np
import pandas as pd
import serial #type:ignore
import csv, orjson, queue, sys, threading, time, traceback, warnings
from flask import Flask, Response
from waitress import serve #type:ignore
from typing import Any,Optional
import lib

RAW_DATA_FILENAME = 'data_raw.csv'
HOURLY_DATA_FILENAME = 'data_hourly.csv'

app = Flask(__name__)
# TODO: remove this
rng = np.random.default_rng() #type:ignore

raw_queue: queue.SimpleQueue[Optional[bytes]] = queue.SimpleQueue()

# arduino takes batches of 1000 points
OBSERVATION_COUNT = 1000
interpolator = lib.interpolator(OBSERVATION_COUNT)

randxy = {'x':rng.integers(1023,size=100), 'y': rng.integers(1023,size=100)}

latest_va = {'load1': randxy,
             'load2': randxy,
             'load3': randxy,
             'load4': randxy,
             'load5': randxy,
             'load6': randxy,
             'load7': randxy,
             'load8': randxy}

def va_updater(va:lib.VA) -> None:
    loadname = va.load.decode('ascii')
    print(f"update {loadname}")
    if va.load not in latest_va:
        latest_va[loadname] = {'x':[],'y':[]}
    latest_va[loadname]['x'] = va.volts
    latest_va[loadname]['y'] = va.amps

transcriber = lib.transcribe(raw_queue, interpolator, va_updater)

FREQ = 30 # trim every 30 rows
SIZE = 5000 # size of raw file to retain

# read some rows from the queue, write them to the raw data file
# and periodically trim it.
def data_writer() -> None:
    while True:
        try:
            with open(RAW_DATA_FILENAME, 'ab') as sink:
                for lines in range(FREQ): # write <FREQ> lines
                    #time.sleep(2) # this should fall behind
                    payload = raw_queue.get()
                    if payload: # could be None
                        sink.write(payload)
                        sink.write(b'\n')
                        sink.flush()
                        print(f'queue size {raw_queue.qsize()}')
            lib.trim(RAW_DATA_FILENAME, SIZE) # trim the file
        except:
            traceback.print_exc(file=sys.stderr)
            print("top level exception",
                      sys.exc_info()[0], file=sys.stderr)

# continuously read serial inputs and write to the queue
def data_reader() -> None:
    serials:serial.Serial = []
    while True:
        try:
            # refresh after *every* row?  TODO: do this differently
            serials = lib.refresh_serials(serials)
            for serial in serials:
                # read one line from serial, write to queue
                transcriber(serial)
        except:
            traceback.print_exc(file=sys.stderr)
            print("top level exception",
                      sys.exc_info()[0], file=sys.stderr)

# periodically read the raw file and update the hourly file
def summarizer() -> None:
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
            hourly_file = hourly_file[~hourly_file.index.isin(hourly.index)] #type:ignore
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
        except:
            traceback.print_exc(file=sys.stderr)
            print("top level exception",
                  sys.exc_info()[0], file=sys.stderr)

@app.route('/')
def index() -> Any:
    print('index')
    return app.send_static_file('index.html')

@app.route('/logger')
def logger() -> Any:
    print('logger')
    return app.send_static_file('logger.html')

@app.route('/raw')
def raw() -> Any:
    print('raw')
    return app.send_static_file('raw.html')

@app.route('/rawdata')
def rawdata() -> Any:
    print('rawdata')
    raw_data = lib.read_raw_no_header(RAW_DATA_FILENAME)
    json_payload = orjson.dumps(raw_data.to_records().tolist()) #type:ignore
    return Response(json_payload, mimetype='application/json')

@app.route('/summary')
def summary() -> Any:
    print('summary')
    return app.send_static_file('summary.html')


@app.route('/summarydata')
def summarydata() -> Any:
    print('summarydata')
    hourly = lib.read_hourly_no_header(HOURLY_DATA_FILENAME)
    json_payload = orjson.dumps(hourly.to_records().tolist()) #type:ignore
    return Response(json_payload, mimetype='application/json')

@app.route('/data')
def data() -> Any:
    print('data')
    loads = ['load1','load2','load3','load4',
             'load5','load6','load7','load8']
    loadlist = [{'label':load,
                 'x':latest_va[load]['x'],
                 'y':latest_va[load]['y']}
                 for load in latest_va.keys()]   
                 #for load in random.sample(loads, len(loads))]   
    # drop some rows to test the js rendering
    #loadlist = loadlist[3:]
    json_payload = orjson.dumps(loadlist,
                                option=orjson.OPT_SERIALIZE_NUMPY)
    return Response(json_payload, mimetype='application/json')

def main() -> None:
    warnings.filterwarnings('ignore')
    threading.Thread(target=data_reader).start()
    threading.Thread(target=data_writer).start()
    threading.Thread(target=summarizer).start()
    serve(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
