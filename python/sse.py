from waitress import serve #type:ignore
from flask import Flask, Response, render_template
from typing import Any, Generator
import time

app = Flask(__name__)

def get_message() -> str:
    '''this could be any function that blocks until data is ready'''
    time.sleep(1.0)
    s = time.ctime(time.time())
    print(f"get message {s}")
    return s

@app.route("/")
def index() -> Any:
    msg = "foo"
    print("index")
    return render_template('sse.html', message=msg)

@app.route('/stream')
def stream() -> Response:
    print("stream")
    def eventStream() -> Generator[str, None, None]:
        while True:
            print("eventstream")
            # wait for source data to be available, then push it
            yield 'data: {}\n\n'.format(get_message())
    return Response(eventStream(), mimetype="text/event-stream")

def main() -> None:
    serve(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()

