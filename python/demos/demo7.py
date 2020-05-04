# updating web chart
from waitress import serve #type:ignore
from flask import Flask, render_template_string, make_response
from matplotlib.backends.backend_svg import FigureCanvasSVG #type:ignore
import io
from matplotlib.figure import Figure #type:ignore
import numpy as np #type:ignore

app = Flask(__name__)

@app.route("/")
def index() -> str:
    x = np.linspace(0,999,1000)
    y = np.random.uniform(0,1,1000)   

    fig = Figure(figsize=(10,5))
    fig.set_tight_layout(True)

    ax = fig.add_subplot(2,2,1)
    ax.set_title("title")
    ax.set_ylabel("y-axis")
    ax.set_xlabel("x-axis")
    ax.plot(x,y)
    ax = fig.add_subplot(2,2,2)
    ax.set_title("title")
    ax.set_ylabel("y-axis")
    ax.set_xlabel("x-axis")
    ax.plot(x,y)
    ax = fig.add_subplot(2,2,3)
    ax.set_title("title")
    ax.set_ylabel("y-axis")
    ax.set_xlabel("x-axis")
    ax.plot(x,y)
    ax = fig.add_subplot(2,2,4)
    ax.set_title("title")
    ax.set_ylabel("y-axis")
    ax.set_xlabel("x-axis")
    ax.plot(x,y)

    # Give the SVG to the browser
    output = io.BytesIO()
    FigureCanvasSVG(fig).print_svg(output)
    html = render_template_string(f"""
        {output.getvalue().decode("utf-8")}
    """)
    response = make_response(html)
    response.headers['refresh']  = '0.25';
    return response

def main() -> None:
    serve(app, host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
