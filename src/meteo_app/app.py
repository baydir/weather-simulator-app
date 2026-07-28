from flask import Flask, render_template, request, jsonify
from meteo_app.geocoding import get_coordinates
from meteo_app.get_meteo import get_meteo
from meteo_app.data_processing import combine, transform_data
from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_MODEL = "CMCC_CM2_VHR4"

app = Flask(__name__)

@app.route("/")
def home():
    today = datetime.now(ZoneInfo("Europe/Paris")).date().isoformat()
    return render_template("index.html", today=today)   

@app.route("/api/geocode", methods=["GET"])
def geocode():
    location = request.args.get("location")
    if not location:
        return jsonify({"error": "Missing 'location' parameter."}), 400
    try:
        latitude, longitude = get_coordinates(location)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"latitude": latitude, "longitude": longitude})

@app.route("/results")
def results():
    today = datetime.now(ZoneInfo("Europe/Paris")).date().isoformat()
    return render_template("results.html", today=today)
    return render_template("results.html", location=location, data=data)

@app.route("/api/process", methods=["POST"])
def process():
    payload = request.get_json()
    raw_archive = payload.get("archive")
    raw_climate = payload.get("climate")
    model = payload.get("model", DEFAULT_MODEL)

    try:
        df = combine(raw_archive, raw_climate, model)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    df = transform_data(df)
    df = df.reset_index()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    data = df.to_dict(orient="records")

    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True)

