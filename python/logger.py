import numpy as np #type:ignore
import pandas as pd #type:ignore
import serial #type:ignore
import csv, io, sys, threading, time, traceback, warnings
from flask import Flask, Response, request, render_template_string
from matplotlib.backends.backend_svg import FigureCanvasSVG #type:ignore
from matplotlib.figure import Figure #type:ignore
from waitress import serve #type:ignore
import lib

RAW_DATA_FILENAME = 'data_raw.csv'
HOURLY_DATA_FILENAME = 'data_hourly.csv'

app = Flask(__name__)

def plot_multi_raw_data(load_data:pd.DataFrame, fig:Figure) -> None:
    loads = list(set(load_data['load']))
    loads.sort()
    ax = fig.add_subplot(4,1,1)
    ax.set_title('raw observed power (1k points)')
    ax.set_ylabel('watts')
    load_frames = {}
    for load in loads:
        load_frames[load] = load_data[load_data['load']==load][['measure']]
    for load in loads:
        (load_frames[load]
            .tail(125)
            .plot(ax=ax, y='measure', style='o', legend=False)
        )
    ax.legend(loads, loc='upper left')

def plot_multi_rollups(hourly:pd.DataFrame, fig:Figure) -> None:
    right = min(pd.Timestamp.now(),hourly.index.max())
    loads = list(set(hourly['load']))
    loads.sort()
    ax = fig.add_subplot(4,1,2)
    ax.set_title('kWh by hour (168 hours)')
    ax.set_ylabel('kilowatt-hours')
    left = (right - pd.DateOffset(hours=168)).ceil('H')
    load_frames = {}
    for load in loads:
        load_frames[load] = hourly[hourly['load']==load][['measure']]
    for load in loads:
        (load_frames[load]
            .loc[load_frames[load].index > left]
            .resample(rule='H').sum()
            .plot(ax=ax, style='o', legend=False)
        )
    ax.legend(loads, loc='upper left')

    ax = fig.add_subplot(4,1,3)
    ax.set_title('kWh by day (31 days)')
    ax.set_ylabel('kilowatt-hours')
    left = (right - pd.DateOffset(days=31)).ceil('D')
    for load in loads:
        (load_frames[load]
             .loc[load_frames[load].index > left]
             .resample(rule='D').sum()
             .plot(ax=ax, style='o', legend=False)
        )
    ax.legend(loads, loc='upper left')

    ax = fig.add_subplot(4,1,4)
    ax.set_title('kWh by month (12 months)')
    ax.set_ylabel('kilowatt-hours')
    # month needs special treatment since it's variable freq
    left = (right - pd.DateOffset(months=12)).to_datetime64().astype('<M8[M]')
    for load in loads:
        (load_frames[load]
            .loc[load_frames[load].index > left]
            .resample(rule='MS').sum()
            .plot(ax=ax, style='o', legend=False)
        )
    ax.legend(loads, loc='upper left')

# continuously read serial inputs and write data to the raw data file 
def data_reader() -> None:
    serials:serial.Serial = []
    # trim every 30 sec
    freq = 30
    # retain 15k rows (1 obs/sec, 3600 sec/h, 4h)
    size = 100000
    while True:
        try:
            # write <freq> lines
            with open(RAW_DATA_FILENAME, 'a') as sink:
                for lines in range(freq):
                    serials = lib.transcribe_all(serials, sink)
            # trim the file
            lib.trim(RAW_DATA_FILENAME, size) 
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
            raw_data = lib.read_raw_no_header(RAW_DATA_FILENAME)
            load_data = lib.resolve_name(raw_data)
            # all the hourly data available
            hourly = lib.make_multi_hourly(load_data)
            # this is the previously written history
            hourly_file = lib.read_hourly_no_header(HOURLY_DATA_FILENAME)
            # the first hour in this set is surely partial; ignore it
            # unless the history is also empty
            if len(hourly) > 0 and len(hourly_file) > 0:
                hourly = hourly.drop(hourly.index[0])
            # remove rows corresponding to the new summary
            hourly_file = hourly_file[~hourly_file.index.isin(hourly.index)]
            # append the new summary
            hourly_file = hourly_file.append(hourly)
            hourly_file.sort_index(inplace=True)
            # write the result to 6 sig fig
                               #date_format='%Y-%m-%dT%H:%M:%S',
            hourly_file.to_csv(HOURLY_DATA_FILENAME,
                               sep=' ',
                               date_format='%Y-%m-%dT%H',
                               quoting=csv.QUOTE_NONE,
                               float_format='%.6g')

        except:
            traceback.print_exc(file=sys.stderr)
            print("top level exception",
                  sys.exc_info()[0], file=sys.stderr)

@app.route("/")
def index() -> str:
    fig = Figure(figsize=(10,15))
    fig.set_tight_layout(True) # Make sure the titles don't overlap

    # (time, id, ct, measure)
    raw_data = lib.read_raw_no_header(RAW_DATA_FILENAME)
    load_data = lib.resolve_name(raw_data)
    plot_multi_raw_data(load_data, fig)

    hourly = lib.read_hourly_no_header(HOURLY_DATA_FILENAME)
    plot_multi_rollups(hourly, fig)

    # Give the SVG to the browser
    output = io.BytesIO()
    FigureCanvasSVG(fig).print_svg(output)
    monthly_total = (hourly[hourly['load']=='total'][['measure']]
                     .resample(rule='MS').sum())
    return render_template_string(f"""
        {output.getvalue().decode("utf-8")}
        <p>kWh/mo</p>
        {monthly_total.to_html(header=False)}
    """)

def main() -> None:
    warnings.filterwarnings('ignore')
    threading.Thread(target=data_reader).start()
    threading.Thread(target=summarizer).start()
    serve(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
