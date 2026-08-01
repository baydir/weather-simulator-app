import json, urllib.parse, urllib.request, urllib.error

LAT, LON = 46.90, 6.35
CLIMATE = "https://climate-api.open-meteo.com/v1/climate"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"

def get(url, params):
    qs = urllib.parse.urlencode(params, doseq=True)
    try:
        with urllib.request.urlopen(f"{url}?{qs}", timeout=60) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)

print("A. Climate API asked for weather_code -> what lands in `daily`?")
s, js = get(CLIMATE, {"latitude": LAT, "longitude": LON,
    "start_date": "2045-06-01", "end_date": "2045-06-03",
    "models": ["MRI_AGCM3_2_S"], "daily": ["weather_code"], "timezone": "Europe/Paris"})
print(f"   HTTP {s}")
print(f"   daily block = {json.dumps(js.get('daily'), ensure_ascii=False)}")
print(f"   daily_units = {json.dumps(js.get('daily_units'), ensure_ascii=False)}")

print("\nB. Climate API: real upper bound (walk past 2050)")
for end in ["2050-12-31", "2051-01-01", "2051-12-31"]:
    s, js = get(CLIMATE, {"latitude": LAT, "longitude": LON,
        "start_date": "2050-12-20", "end_date": end,
        "models": ["MRI_AGCM3_2_S"], "daily": ["temperature_2m_max"], "timezone": "Europe/Paris"})
    if s == 200:
        t = js["daily"]["time"]; v = js["daily"]["temperature_2m_max"]
        nn = sum(1 for x in v if x is not None)
        print(f"   end={end}: HTTP 200, last={t[-1]}, {len(t)} days, {nn} non-null")
    else:
        print(f"   end={end}: HTTP {s} -> {js.get('reason')}")

print("\nC. Archive API: how close to today does it reach?")
for end in ["2026-07-30", "2026-07-25", "2026-07-20", "2026-07-15"]:
    s, js = get(ARCHIVE, {"latitude": LAT, "longitude": LON,
        "start_date": end, "end_date": end,
        "daily": ["weather_code", "temperature_2m_max"], "timezone": "Europe/Paris"})
    d = js.get("daily", {})
    print(f"   {end}: HTTP {s} -> wc={d.get('weather_code')} tmax={d.get('temperature_2m_max')}")

print("\nD. Which daily vars does the Climate API silently drop?")
want = ["weather_code", "sunshine_duration", "precipitation_hours",
        "wind_gusts_10m_max", "apparent_temperature_max", "cloud_cover_mean",
        "et0_fao_evapotranspiration", "snowfall_sum", "rain_sum"]
s, js = get(CLIMATE, {"latitude": LAT, "longitude": LON,
    "start_date": "2045-06-01", "end_date": "2045-06-02",
    "models": ["MRI_AGCM3_2_S"], "daily": want, "timezone": "Europe/Paris"})
got = set(js.get("daily", {}).keys()) - {"time"}
print(f"   HTTP {s}")
for w in want:
    print(f"   {'OK  ' if w in got else 'DROP'} {w}")
