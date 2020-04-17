import io #, webbrowser
import numpy as np
import pandas as pd
#import scipy.integrate as it

from flask import Flask, Response, request
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

def plot_rollups(hourly, fig):
    right = min(pd.Timestamp.now(),hourly.index.max())
    ax = fig.add_subplot(4,1,2)
    ax.set_title('kWh by hour (168 hours)')
    ax.set_ylabel('kilowatt-hours')
    (hourly
        .loc[hourly.index > (right - pd.DateOffset(hours=168)).ceil('H')]
        .resample(rule='H').sum()
        .plot(ax=ax, style='o', legend=False)
    )

    ax = fig.add_subplot(4,1,3)
    ax.set_title('kWh by day (31 days)')
    ax.set_ylabel('kilowatt-hours')
    (hourly
         .loc[hourly.index > (right - pd.DateOffset(days=31)).ceil('D')]
         .resample(rule='D').sum()
         .plot(ax=ax, style='o', legend=False)
    )

    ax = fig.add_subplot(4,1,4)
    ax.set_title('kWh by month (12 months)')
    ax.set_ylabel('kilowatt-hours')
    # month needs special treatment since it's variable freq
    (hourly
        .loc[hourly.index > (right - pd.DateOffset(months=12)).to_datetime64().astype('<M8[M]')]
        .resample(rule='MS').sum()
        .plot(ax=ax, style='o', legend=False)
    )

@app.route("/")
def index():

    fig = Figure(figsize=(8,8))
    fig.set_tight_layout(True) # Make sure the titles don't overlap

    raw_data = lib.random_data()
    #raw_data = lib.read_raw('test_data.csv') # show test data
    print(raw_data)
    plot_raw_data(raw_data, fig)
    hourly = lib.make_hourly(raw_data)
    print(hourly)
    plot_rollups(hourly, fig)

    # Give the SVG to the browser
    output = io.BytesIO()
    FigureCanvasSVG(fig).print_svg(output)
    return Response(output.getvalue(), mimetype="image/svg+xml")
    
def main():
    # Waitress is the recommended flask runner
    serve(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
