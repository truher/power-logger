import io
import numpy as np
import pandas as pd
import random
import scipy.integrate as it
import webbrowser

from flask import Flask, Response, request
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
from waitress import serve

app = Flask(__name__)

@app.route("/")
def index():
    # Read the raw file (watts)
    raw_data = pd.read_csv('dt.0', delim_whitespace=True, comment='#')
    raw_data['time'] = pd.to_datetime(raw_data['time'])
    raw_data = raw_data.set_index(['time'])

    # Bucket boundaries we want, with some left padding
    buckets = pd.DataFrame(pd.date_range(start=raw_data.index.min().floor('10T') - 2 * pd.offsets.Minute(10),
                       end=raw_data.index.max().ceil('10T'), freq='10T'))
    buckets = buckets.set_index(0)

    # Insert bucket boundaries into the raw dataset (they'll have NaN measures)
    raw_data_with_buckets = raw_data.append(buckets)
    raw_data_with_buckets = raw_data_with_buckets.sort_index()

    # Set the left edge to zero
    raw_data_with_buckets.at[raw_data_with_buckets.index.min()]=0

    # Fill interpolated values at the bucket boundaries
    interpolated = raw_data_with_buckets.interpolate(method='time')
    interpolated = interpolated.dropna()

    # Integrate the data series to get cumulative energy (kWh)
    interpolated['cum'] = it.cumtrapz(interpolated['measure'],
                                      x=interpolated.index, initial=0) / (1000 * np.timedelta64(1, 'h'))

    # Downsample to the buckets
    downsampled = interpolated.resample(rule='10T',closed='right',label='right',loffset='-10T').max()

    # Differentiate to get mean power by bucket (watts)
    downsampled['cumdiff'] = downsampled['cum'].diff()*60000/10
    downsampled = downsampled.dropna()

    # Plot the results
    fig = Figure(figsize=(10,10))

    ax = fig.add_subplot(4,1,1)
    ax.set_title('observed power (raw)')
    ax.set_xlabel('time')
    ax.set_ylabel('watts')
    raw_data.plot(ax=ax, y='measure', style='o', legend=False)

    ax = fig.add_subplot(4,1,2)
    ax.set_title('interpolated power (10 min periods)')
    ax.set_xlabel('time')
    ax.set_ylabel('watts')
    interpolated.plot(ax=ax, y='measure', style='o', legend=False)

    ax = fig.add_subplot(4,1,3)
    ax.set_title('cumulative energy (10 min periods)')
    ax.set_xlabel('time')
    ax.set_ylabel('kilowatt-hours')
    downsampled.plot(ax=ax, y='cum', style='o', legend=False)

    ax = fig.add_subplot(4,1,4)
    ax.set_title('mean power (10 min periods)')
    ax.set_xlabel('time')
    ax.set_ylabel('watts')
    downsampled.plot(ax=ax, y='cumdiff', style='o', legend=False)

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
