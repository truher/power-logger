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
    # watts
    d = {'time':[
    '2020-04-04 14:32:30',
    '2020-04-04 14:42:30',
    '2020-04-04 14:52:30'
    ],
         'measure':[
    0,
    1,
    0
    ]}
    
    df = pd.DataFrame(d)
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index(['time'])
    print(df)
    dr = pd.date_range(start=df.index.min().floor('10T') - 2 * pd.offsets.Minute(10), end=df.index.max().ceil('10T'), freq='10T')
    print(dr)
    drf = pd.DataFrame(dr)
    print(drf)
    drf = drf.set_index(0)
    print(drf)
    drr = df.append(drf)
    drr = drr.sort_index()
    drr.at[drr.index.min()]=0
    print("drr")
    print(drr)
    drri = drr.interpolate(method='time')
    drri = drri.dropna()
    print("drri")
    print(drri)
    #print(len(drri['measure']))
    #print(len(drri.index))
    #x = it.cumtrapz(drri['measure'], x=drri.index, initial=0)
    # kWh
    drri['cum'] = it.cumtrapz(drri['measure'], x=drri.index, initial=0) / (1000 * np.timedelta64(1, 'h'))
    #print(drri.dtypes)
    print("drri")
    print(drri)
    #print(x)
    #print(len(x))
    #drri.plot()
    u = drri.resample(rule='10T',closed='right',label='right',loffset='-10T').max()
    print("u")
    print(u)
    #u.plot()
    u['cumdiff'] = u['cum'].diff()*60000/10
    u = u.dropna()
    print(u)

    fig = Figure(figsize=(10,10))

    ax = fig.add_subplot(4,1,1)
    ax.set_title('observed power (raw)')
    ax.set_xlabel('time')
    ax.set_ylabel('watts')
    df.plot(ax=ax, y='measure', style='o', legend=False)

    ax = fig.add_subplot(4,1,2)
    ax.set_title('interpolated power (1 min periods)')
    ax.set_xlabel('time')
    ax.set_ylabel('watts')
    drri.plot(ax=ax, y='measure', style='o', legend=False)

    ax = fig.add_subplot(4,1,3)
    ax.set_title('cumulative energy (10 min periods)')
    ax.set_xlabel('time')
    ax.set_ylabel('kilowatt-hours')
    u.plot(ax=ax, y='cum', style='o', legend=False)

    ax = fig.add_subplot(4,1,4)
    ax.set_title('mean power (10 min periods)')
    ax.set_xlabel('time')
    ax.set_ylabel('watts')
    u.plot(ax=ax, y='cumdiff', style='o', legend=False)

    fig.set_tight_layout(True)

    output = io.BytesIO()
    FigureCanvasSVG(fig).print_svg(output)
    return Response(output.getvalue(), mimetype="image/svg+xml")

    #u.plot()
    #plt.show()
    #dfi = u.interpolate(method='linear')
    #print(dfi)
    #f=interp1d(df['time'],df['measure'])
    #
    #plt.plot(df['time'],df['measure'],'o')
    #
    #X1 = pd.date_range(np.amin(df['time']), np.amax(df['time']), periods=100).to_pydatetime()
    #Y1 = interp1d(df['time'],df['measure'],kind='nearest')
    #plt.plot(X1, Y1(X1))
    #
    #plt.show()
    
def main():
    serve(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
