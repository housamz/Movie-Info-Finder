from flask import Flask, render_template, request, json
from find_movie_info import movie_data

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route('/findMovieInfo', methods=['POST'])
def findmovieinfo():
    movielink = request.form['IMDBLink']
    movieJson = movie_data(movielink)
    return json.dumps(movieJson)


if __name__ == "__main__":
    app.run()
