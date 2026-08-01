import json, urllib.parse, urllib.request, urllib.error

LAT, LON = 46.90, 6.35
CLIMATE = "https://climate-api.open-meteo.com/v1/climate"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

VARS = ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
        "precipitation_sum", "rain_sum", "snowfall_sum", "precipitation_hours",
        "cloud_cover_mean", "sunshine_duration", "shortwave_radiation_sum",
        "relative_humidity_2m_mean", "relative_humidity_2m_max", "relative_humidity_2m_min",
        "wind_speed_10m_mean", "wind_speed_10m_max", "wind_gusts_10m_max",
        "pressure_msl_mean", "soil_moisture_0_to_10cm_mean",
        "et0_fao_evapotranspiration", "apparent_temperature_max",
        "dew_point_2m_mean", "weather_code"]

def get(url, params):
    qs = urllib.parse.urlencode(params, doseq=True)
    try:
        with urllib.request.urlopen(f"{url}?{qs}", timeout=90) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def probe(url, extra, label, start, end):
    """Request each var one at a time; report whether values are actually non-null."""
    out = {}
    for v in VARS:
        p = {"latitude": LAT, "longitude": LON, "start_date": start,
             "end_date": end, "daily": [v], "timezone": "Europe/Paris"}
        p.update(extra)
        s, js = get(url, p)
        if s != 200:
            out[v] = f"HTTP {s}"
            continue
        d = js.get("daily", {})
        key = next((k for k in d if k != "time"), None)
        if key is None:
            out[v] = "absent"
        else:
            vals = d[key]
            nn = [x for x in vals if x is not None]
            out[v] = f"OK {vals[:2]}" if nn else "NULL"
    return out


print("Probing CLIMATE (MRI_AGCM3_2_S, 2045-06-01..03) vs ARCHIVE (2020-06-01..03)\n")
clim = probe(CLIMATE, {"models": ["MRI_AGCM3_2_S"]}, "climate", "2045-06-01", "2045-06-03")
arch = probe(ARCHIVE, {}, "archive", "2020-06-01", "2020-06-03")

print(f"{'variable':<34} {'ARCHIVE':<24} {'CLIMATE':<24}")
print("-" * 84)
for v in VARS:
    print(f"{v:<34} {arch[v][:23]:<24} {clim[v][:23]:<24}")
