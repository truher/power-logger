from waitress import serve #type:ignore
from flask import Flask, Response, render_template
from typing import Any, Generator
import time
import numpy as np #type:ignore
import orjson

app = Flask(__name__)
rng = np.random.default_rng()

#def get_message() -> str:
#    '''this could be any function that blocks until data is ready'''
#    time.sleep(1.0)
#    s = time.ctime(time.time())
#    print(f"get message {s}")
#    return s

@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

@app.route("/")
def index() -> Any:
    msg = "foo"
    print("index")
    return render_template('pull.html', message=msg)

@app.route('/data')
def data() -> Any:
    print(f"get data")
############################################################3
    # FOR NOW, SMALL LISTS
    #x = rng.integers(1023,size=1000)     
    #y = rng.integers(1023,size=1000)     
############################################################3
    #x = rng.integers(1023,size=10)
    #y = rng.integers(1023,size=10)
    # this could be a partial list
    loads = ['load1','load2','load3','load4',
             'load5','load6','load7','load8']
    #oneload = {'label': 'a', 'x': x, 'y': y}
    loadlist = [{'label':x,
                 'x':rng.integers(1023,size=1000),
                 'y':rng.integers(1023,size=1000)} for x in loads]   
    json_payload = orjson.dumps(loadlist,
                                option=orjson.OPT_SERIALIZE_NUMPY)
    return Response(json_payload, mimetype="application/json")

#@app.route('/stream')
#def stream() -> Response:
#    print("stream")
#    def eventStream() -> Generator[str, None, None]:
#        while True:
#            print("eventstream")
#            # wait for source data to be available, then push it
#            yield 'data: {}\n\n'.format(get_message())
#    return Response(eventStream(), mimetype="text/event-stream")

def main() -> None:
    serve(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()

