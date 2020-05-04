# data for d3fc plots
from waitress import serve #type:ignore
from flask import Flask, Response, render_template
from typing import Any, Generator, Callable
import orjson, random, time
import numpy as np #type:ignore

app = Flask(__name__)
rng = np.random.default_rng()

@app.after_request
def add_header(r:Response) -> Response:
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

@app.route('/')
def index() -> Any:
    print('index')
    return app.send_static_file('index.html')

@app.route('/data')
def data() -> Any:
    print('data')
    loads = ['load1','load2','load3','load4',
             'load5','load6','load7','load8']
    loadlist = [{'label':x,
                 'x':rng.integers(1023,size=100),
                 'y':rng.integers(1023,size=100)}
                 for x in random.sample(loads, len(loads))]   
    # drop some rows to test the js rendering
    loadlist = loadlist[3:]
    json_payload = orjson.dumps(loadlist,
                                option=orjson.OPT_SERIALIZE_NUMPY)
    return Response(json_payload, mimetype='application/json')

def main() -> None:
    serve(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
