from flask import Flask, render_template, request
from meteo_app.geocoding import get_coordinates
from meteo_app.get_meteo import get_meteo

DEFAULT_MODEL = "CMCC_CM2_VHR4"

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/results", methods=["POST"])
def results():
    location = request.form["location"]
    start_date = request.form["start_date"]
    end_date = request.form["end_date"]

    try:
        latitude, longitude = get_coordinates(location)
    except ValueError as e:
        return render_template("error.html", message=str(e))

    df = get_meteo(longitude, latitude, start_date, end_date, DEFAULT_MODEL)
    df = df.reset_index()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    data = df.to_dict(orient="records")

    return render_template("results.html", location=location, data=data)

if __name__ == "__main__":
    app.run(debug=True)

