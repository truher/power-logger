import io #, webbrowser
import numpy as np
import pandas as pd
import csv
import threading
import sys
import time
import traceback
#import scipy.integrate as it

from flask import Flask, Response, request, render_template_string
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
from waitress import serve

import lib

app = Flask(__name__)

def plot_raw_data(raw_data, fig):
    ax = fig.add_subplot(4,1,1)
    ax.set_title('raw observed power (1k points)')
    ax.set_ylabel('watts')
    (raw_data
        .tail(1000)
        .plot(ax=ax, y='measure', style='o', legend=False)
    )

def plot_multi_raw_data(load_data, fig):
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

def plot_multi_rollups(hourly, fig):
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

def plot_rollups(hourly, fig):
    right = min(pd.Timestamp.now(),hourly.index.max())
    ax = fig.add_subplot(4,1,2)
    ax.set_title('kWh by hour (168 hours)')
    ax.set_ylabel('kilowatt-hours')
    left = (right - pd.DateOffset(hours=168)).ceil('H')
    (hourly
        .loc[hourly.index > left]
        .resample(rule='H').sum()
        .plot(ax=ax, style='o', legend=False)
    )

    ax = fig.add_subplot(4,1,3)
    ax.set_title('kWh by day (31 days)')
    ax.set_ylabel('kilowatt-hours')
    left = (right - pd.DateOffset(days=31)).ceil('D')
    (hourly
         .loc[hourly.index > left]
         .resample(rule='D').sum()
         .plot(ax=ax, style='o', legend=False)
    )

    ax = fig.add_subplot(4,1,4)
    ax.set_title('kWh by month (12 months)')
    ax.set_ylabel('kilowatt-hours')
    # month needs special treatment since it's variable freq
    left = (right - pd.DateOffset(months=12)).to_datetime64().astype('<M8[M]')
    (hourly
        .loc[hourly.index > left]
        .resample(rule='MS').sum()
        .plot(ax=ax, style='o', legend=False)
    )

@app.route("/")
def index():
    fig = Figure(figsize=(10,15))
    fig.set_tight_layout(True) # Make sure the titles don't overlap

    raw_data = lib.read_raw_no_header('test_data_long.csv')
    #raw_data = lib.multi_random_data()
    #raw_data = lib.random_data()
    #raw_data = lib.read_raw('test_data.csv') # show test data
    load_data = lib.resolve_name(raw_data)
    #plot_raw_data(raw_data, fig)
    plot_multi_raw_data(load_data, fig)
    hourly = lib.make_multi_hourly(load_data)
    #hourly = lib.make_hourly(raw_data)
    #plot_rollups(hourly, fig)
    plot_multi_rollups(hourly, fig)

    # Give the SVG to the browser
    output = io.BytesIO()
    FigureCanvasSVG(fig).print_svg(output)
    #return Response(output.getvalue(), mimetype="image/svg+xml")
    monthly_total = (hourly[hourly['load']=='total'][['measure']]
                     .resample(rule='MS').sum())
    return render_template_string(f"""
        {output.getvalue().decode("utf-8")}
        <p>kWh/mo</p>
        {monthly_total.to_html(header=False)}
    """)

# continuously read serial inputs and write data to the raw data file 
def data_reader():
    serials = []
    # trim every 30 sec
    freq = 30
    # retain 100k rows (8 obs/sec, 3600 sec/h, 3h)
    size = 100000
    filename = 'data_raw.csv'
    while True:
        try:
            # write <freq> lines
            with open(filename, 'a') as sink:
                for lines in range(freq):
                    serials = lib.transcribe_all(serials, sink)
            # trim the file
            lib.trim(filename, size) 
        except:
            traceback.print_exc(file=sys.stderr)
            print("top level exception",
                      sys.exc_info()[0], file=sys.stderr)

# periodically read the raw file and update the hourly file
def summarizer():
    raw_filename = 'data_raw.csv'
    hourly_filename = 'data_hourly.csv'
    while True:
        try:
            time.sleep(60)
            # all the raw data available
            raw_data = lib.read_raw_no_header(raw_filename)
            load_data = lib.resolve_name(raw_data)
            # all the hourly data available
            hourly = lib.make_multi_hourly(load_data)
            # this is the previously written history
            hourly_file = lib.read_hourly_no_header(hourly_filename)
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
            hourly_file.to_csv(hourly_filename, sep=' ',
                               date_format='%Y-%m-%dT%H:%M:%S.%f',
                               quoting=csv.QUOTE_NONE,
                               float_format='%6g')

        except:
            traceback.print_exc(file=sys.stderr)
            print("top level exception",
                  sys.exc_info()[0], file=sys.stderr)
        

def main():
    threading.Thread(target=data_reader).start()
    threading.Thread(target=summarizer).start()
    # Waitress is the recommended flask runner
    serve(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
