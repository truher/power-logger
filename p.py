import io
import random
import webbrowser
from flask import Flask, Response, request
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
from waitress import serve

# experimenting with plotting

app = Flask(__name__)

def addplot(axis, d):
    x_points = range(200)
    axis.plot(x_points, [random.randint(1, 30) for x in x_points])
    axis.set_title('Title ' + str(d), fontsize=12)
    axis.set_xlabel('x axis', fontsize=10)
    axis.set_ylabel('y axis', fontsize=10)

@app.route("/")
def index():
    fig = Figure(figsize=(12,6))
    addplot(fig.add_subplot(2,2,1), 1)
    addplot(fig.add_subplot(2,2,2), 2)
    addplot(fig.add_subplot(2,2,3), 3)
    addplot(fig.add_subplot(2,2,4), 4)
    fig.set_tight_layout(True)
    output = io.BytesIO()
    FigureCanvasSVG(fig).print_svg(output)
    return Response(output.getvalue(), mimetype="image/svg+xml")

if __name__ == "__main__":
    webbrowser.open("http://127.0.0.1:5000/")
    # app.run(debug=False, use_reloader=True)  # flask dev server
    serve(app, host="0.0.0.0", port=5000)

