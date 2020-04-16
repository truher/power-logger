import io, webbrowser
import numpy as np
import pandas as pd
import scipy.integrate as it

from flask import Flask, Response, request
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
from waitress import serve

import lib

app = Flask(__name__)

def make_hourly(raw_data):
    # provide a zero just before the first point, so integration sees the first
    # point but nothing before it
    raw_data = pd.concat(
        [pd.DataFrame(index=[raw_data.index.min() - pd.DateOffset(seconds=1)],
                      data=[0], columns=['measure']), raw_data])

    # Bucket boundaries we want, with some left padding to be sure we can set the first to zero
    buckets = pd.DataFrame(pd.date_range(start=raw_data.index.min().floor('H') - pd.DateOffset(hours=1),
                  end=raw_data.index.max().ceil('H'), freq='H')).set_index(0)

    # Insert bucket boundaries into the raw dataset (they'll have NaN measures)
    raw_data_with_buckets = raw_data.append(buckets).sort_index()

    # Set the left edge to zero
    raw_data_with_buckets.at[raw_data_with_buckets.index.min()]=0

    # Fill interpolated values at the bucket boundaries
    interpolated = raw_data_with_buckets.interpolate(method='time', limit_area='inside').dropna()

    # Integrate the data series to get cumulative energy (kWh)
    cum_kwh = pd.DataFrame(index=interpolated.index, columns=['measure'],
                  data=it.cumtrapz(interpolated['measure'],
                                   x=interpolated.index, initial=0) / (1000 * np.timedelta64(1, 'h')))

    # Downsample to the buckets
    hourly = cum_kwh.resample(rule='H',closed='right',label='right',loffset='-1H').max().diff().dropna()
    return hourly

def plot_raw_data(raw_data, fig):
    ax = fig.add_subplot(4,1,1)
    ax.set_title('raw observed power (1k points)')
    ax.set_ylabel('watts')
    (raw_data
        .tail(1000)
        .plot(ax=ax, y='measure', style='o', legend=False)
    )

def plot_rollups(hourly, fig):
    ax = fig.add_subplot(4,1,2)
    ax.set_title('kWh by hour (168 hours)')
    ax.set_ylabel('kilowatt-hours')
    (hourly
        .loc[hourly.index > (pd.Timestamp.now() - pd.DateOffset(hours=168)).ceil('H')]
        .resample(rule='H').sum()
        .plot(ax=ax, style='o', legend=False)
    )

    ax = fig.add_subplot(4,1,3)
    ax.set_title('kWh by day (31 days)')
    ax.set_ylabel('kilowatt-hours')
    (hourly
         .loc[hourly.index > (pd.Timestamp.now() - pd.DateOffset(days=31)).ceil('D')]
         .resample(rule='D').sum()
         .plot(ax=ax, style='o', legend=False)
    )

    ax = fig.add_subplot(4,1,4)
    ax.set_title('kWh by month (12 months)')
    ax.set_ylabel('kilowatt-hours')
    # month needs special treatment since it's variable freq
    (hourly
        .loc[hourly.index > (pd.Timestamp.now() - pd.DateOffset(months=12)).to_datetime64().astype('<M8[M]')]
        .resample(rule='MS').sum()
        .plot(ax=ax, style='o', legend=False)
    )

@app.route("/")
def index():

    fig = Figure(figsize=(8,8))
    fig.set_tight_layout(True) # Make sure the titles don't overlap

    raw_data = lib.random_data()
    plot_raw_data(raw_data, fig)
    hourly = make_hourly(raw_data)
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
