import io, webbrowser
import numpy as np
import pandas as pd
import scipy.integrate as it

from flask import Flask, Response, request
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
from waitress import serve

app = Flask(__name__)

def random_data():
    num_rows = 1000000

    time_ideal = pd.date_range(end=pd.Timestamp.now(), periods=num_rows, freq='10S')
    time_deltas  = pd.to_timedelta(np.random.uniform(-1, 1, num_rows),unit='S')
    time_actual = time_ideal + time_deltas

    #data  = np.random.uniform(0, 1, num_rows)
    # lognormal(0,1) has mean exp(0.5) or about 1.65
    data  = np.random.lognormal(0, 1, num_rows)

    df = pd.DataFrame(data={'time': time_actual, 'measure': data})
    df = df.set_index(['time'])
    return df

def make_hourly(raw_data):
    # Bucket boundaries we want, with some left padding
    buckets = pd.DataFrame(pd.date_range(start=raw_data.index.min().floor('10T') - 2 * pd.offsets.Minute(10),
                  end=raw_data.index.max().ceil('10T'), freq='10T')).set_index(0)
    #print("got buckets")
    #print(buckets.tail())

    # Insert bucket boundaries into the raw dataset (they'll have NaN measures)
    raw_data_with_buckets = raw_data.append(buckets).sort_index()

    # Set the left edge to zero
    raw_data_with_buckets.at[raw_data_with_buckets.index.min()]=0
    #print("got raw with buckets")


    # Fill interpolated values at the bucket boundaries
    interpolated = raw_data_with_buckets.interpolate(method='time').dropna()
    #print("got interpolated")
    #print(interpolated)

    # Integrate the data series to get cumulative energy (kWh)
    cum_kwh = pd.DataFrame(index=interpolated.index, columns=['measure'],
                  data=it.cumtrapz(interpolated['measure'],
                                   x=interpolated.index, initial=0) / (1000 * np.timedelta64(1, 'h')))
    #print("got cumtrapz")
    #print(cum_kwh)

    # Downsample to the buckets
    #downsampled = interpolated.resample(rule='10T',closed='right',label='right',loffset='-10T').max()
    cum_kwh_10T = cum_kwh.resample(rule='10T',closed='right',label='right',loffset='-10T').max()
    #print("got cum_kwh_10T")
    #print(cum_kwh_10T)

    hourly = cum_kwh_10T.resample(rule='H').max().diff()
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
        .loc[hourly.index > pd.Timestamp.now() - pd.DateOffset(hours=168)]
        .resample(rule='H').sum()
        .plot(ax=ax, style='o', legend=False)
    )

    ax = fig.add_subplot(4,1,3)
    ax.set_title('kWh by day (31 days)')
    ax.set_ylabel('kilowatt-hours')
    (hourly
         .loc[hourly.index > pd.Timestamp.now() - pd.DateOffset(days=31)]
         .resample(rule='D').sum()
         .plot(ax=ax, style='o', legend=False)
    )

    ax = fig.add_subplot(4,1,4)
    ax.set_title('kWh by month (12 months)')
    ax.set_ylabel('kilowatt-hours')
    (hourly
        .loc[hourly.index > pd.Timestamp.now() - pd.DateOffset(months=12)]
        .resample(rule='MS').sum()
        .plot(ax=ax, style='o', legend=False)
    )

@app.route("/")
def index():

    fig = Figure(figsize=(8,8))
    fig.set_tight_layout(True) # Make sure the titles don't overlap

    raw_data = random_data()
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
