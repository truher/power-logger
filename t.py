import io
import numpy as np
import pandas as pd
import scipy.integrate as it
import webbrowser

from flask import Flask, Response, request
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
from waitress import serve

import lib

app = Flask(__name__)
ids = [ "5737333034370D0E14", "5737333034370A220D" ]

def read_file():
    # Read the raw file (watts)
    raw_data = pd.read_csv('dt.0', delim_whitespace=True, comment='#')
    raw_data['time'] = pd.to_datetime(raw_data['time'])
    raw_data = raw_data.set_index(['time'])
    return raw_data

@app.route("/")
def index():

    #raw_data = read_file()
    raw_data = lib.random_data()
    print("got raw_data")
    print(raw_data.tail())

    # Bucket boundaries we want, with some left padding
    buckets = pd.DataFrame(pd.date_range(start=raw_data.index.min().floor('10T') - 2 * pd.offsets.Minute(10),
                       end=raw_data.index.max().ceil('10T'), freq='10T'))
    buckets = buckets.set_index(0)
    print("got buckets")
    print(buckets.tail())

    # Insert bucket boundaries into the raw dataset (they'll have NaN measures)
    raw_data_with_buckets = raw_data.append(buckets)
    raw_data_with_buckets = raw_data_with_buckets.sort_index()

    # Set the left edge to zero
    raw_data_with_buckets.at[raw_data_with_buckets.index.min()]=0
    print("got raw with buckets")

    # Fill interpolated values at the bucket boundaries
    interpolated = raw_data_with_buckets.interpolate(method='time')
    interpolated = interpolated.dropna()
    print("got interpolated")

    # Integrate the data series to get cumulative energy (kWh)
    interpolated['cum'] = it.cumtrapz(interpolated['measure'],
                                      x=interpolated.index, initial=0) / (1000 * np.timedelta64(1, 'h'))
    print("got cumtrapz")

    # Downsample to the buckets
    downsampled = interpolated.resample(rule='10T',closed='right',label='right',loffset='-10T').max()
    print("got downsampled")
    # roll up the 10 min samples to hours
    hourly = downsampled.resample(rule='H').max()
    print("got hourly")
    print(hourly.tail())
    # roll up the hours to days
    daily = hourly.resample(rule='D').max()
    print("got daily")
    print(daily.tail())
    # roll up the days to months
    monthly = daily.resample(rule='MS').max()
    print("got monthly")
    print(monthly)

    # Differentiate to get mean power by bucket (watts)
    # * 1000 (kw -> w)
    # * 60   (h -> min)
    # / 10   (min -> 10min)
    # => * 6000
    # todo: this does the current period wrong
    downsampled['cumdiff'] = downsampled['cum'].diff()*6000
    downsampled = downsampled.dropna()
    print("got diff")
    print(downsampled.tail())

    # * 1000 (kw -> w)
    # todo: this does the current hour wrong
    hourly['cumdiff'] = hourly['cum'].diff()*1000
    hourly = hourly.dropna()
    print("got hourly")
    print(hourly.tail())

    # * 1000 (kw -> w)
    # / 24   (h -> d)
    # todo: this does the current day wrong
    daily['cumdiff'] = daily['cum'].diff()*1000/24
    daily = daily.dropna()
    print("got daily")
    print(daily.tail())

    # * 1000 (kw -> w)
    # / 24   (h -> d)
    # / days-in-month (d -> m)
    # todo: this does the current month wrong
    monthly['cumdiff'] = monthly['cum'].diff()*1000/(24 * monthly.index.days_in_month)
    monthly = monthly.dropna()
    print("got monthly days")
    print(monthly.index.days_in_month)
    print("got monthly")
    print(monthly.tail())

    # Plot the results
    fig = Figure(figsize=(10,20))

    ax = fig.add_subplot(7,1,1)
    ax.set_title('observed power (raw) should cover 3h')
    ax.set_xlabel('time')
    ax.set_ylabel('watts')
    raw_data.tail(1000).plot(ax=ax, y='measure', style='o', legend=False)
    print("got plot1")

    # todo: make fine-grained view shorter
    ax = fig.add_subplot(7,1,2)
    ax.set_title('observed power with interpolated bucket boundaries (10 min periods) should cover 7d')
    ax.set_xlabel('time')
    ax.set_ylabel('watts')
    interpolated.tail(1000).plot(ax=ax, y='measure', style='o', legend=False)
    print("got plot2")

    ax = fig.add_subplot(7,1,3)
    ax.set_title('cumulative energy (10 min periods) should cover 7d')
    ax.set_xlabel('time')
    ax.set_ylabel('kilowatt-hours')
    downsampled.tail(1000).plot(ax=ax, y='cum', style='o', legend=False)
    print("got plot3")

    ax = fig.add_subplot(7,1,4)
    ax.set_title('mean power (10 min periods) should cover 7d')
    ax.set_xlabel('time')
    ax.set_ylabel('watts')
    downsampled.tail(1000).plot(ax=ax, y='cumdiff', style='o', legend=False)
    print("got plot4")

    ax = fig.add_subplot(7,1,5)
    ax.set_title('mean power (1 h periods) should cover 1m')
    ax.set_xlabel('time')
    ax.set_ylabel('watts')
    hourly.tail(1000).plot(ax=ax, y='cumdiff', style='o', legend=False)
    print("got plot5")

    ax = fig.add_subplot(7,1,6)
    ax.set_title('mean power (1 d periods) should cover 3y')
    ax.set_xlabel('time')
    ax.set_ylabel('watts')
    daily.tail(1000).plot(ax=ax, y='cumdiff', style='o', legend=False)
    print("got plot6")

    ax = fig.add_subplot(7,1,7)
    ax.set_title('mean power (1 m periods) should cover 100y')
    ax.set_xlabel('time')
    ax.set_ylabel('watts')
    monthly.tail(1000).plot(ax=ax, y='cumdiff', style='o', legend=False)
    print("got plot7")


    # Make sure the titles don't overlap
    fig.set_tight_layout(True)

    # Give the SVG to the browser
    output = io.BytesIO()
    FigureCanvasSVG(fig).print_svg(output)
    return Response(output.getvalue(), mimetype="image/svg+xml")
    
def main():
    # Waitress is the recommended flask runner
    serve(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
