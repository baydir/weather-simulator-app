"""Section 3 prerequisites:
   (A) is wind DIRECTION available on both sides?
   (B) geographic precision: which reanalysis can we force, what elevation
       does each side assume, and does it match reality?"""
import json, urllib.parse, urllib.request, urllib.error, time

A = "https://archive-api.open-meteo.com/v1/archive"
C = "https://climate-api.open-meteo.com/v1/climate"
MODEL = "MRI_AGCM3_2_S"

SITES = {"Pontarlier (837 m)": (46.90, 6.35),
         "Chamonix (1035 m)":  (45.92, 6.87),
         "Brest (35 m)":       (48.39, -4.49)}

def get(url, p):
    qs = urllib.parse.urlencode(p, doseq=True)
    try:
        with urllib.request.urlopen(f"{url}?{qs}", timeout=120) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)

def vals(js, keys):
    d = js.get("daily", {})
    out = {}
    for k in keys:
        v = d.get(k)
        out[k] = "ABSENT" if v is None else ("NULL" if all(x is None for x in v)
                                             else f"OK {v[:2]}")
    return out

WIND = ["wind_speed_10m_max", "wind_speed_10m_mean",
        "wind_direction_10m_dominant", "wind_gusts_10m_max"]

print("=" * 74)
print("(A) WIND DIRECTION availability")
s, js = get(A, {"latitude": 46.90, "longitude": 6.35, "start_date": "2020-06-01",
                "end_date": "2020-06-02", "daily": WIND, "timezone": "GMT"})
print(f"  ARCHIVE  HTTP {s}")
for k, v in vals(js, WIND).items(): print(f"    {k:<32} {v}")
time.sleep(5)
s, js = get(C, {"latitude": 46.90, "longitude": 6.35, "start_date": "2045-06-01",
                "end_date": "2045-06-02", "models": [MODEL], "daily": WIND,
                "timezone": "GMT"})
print(f"  CLIMATE  HTTP {s}")
for k, v in vals(js, WIND).items(): print(f"    {k:<32} {v}")

print("\n" + "=" * 74)
print("(B) GEOGRAPHIC PRECISION — reported elevation per source/model")
print(f"    {'site':<20}{'source':<26}{'elevation':>10}")
for site, (lat, lon) in SITES.items():
    base = {"latitude": lat, "longitude": lon, "start_date": "2020-06-01",
            "end_date": "2020-06-01", "daily": ["temperature_2m_max"],
            "timezone": "GMT"}
    for label, extra in [("archive defaut", {}),
                         ("archive era5", {"models": ["era5"]}),
                         ("archive era5_land", {"models": ["era5_land"]})]:
        s, js = get(A, {**base, **extra})
        e = js.get("elevation", f"HTTP {s}")
        t = js.get("daily", {}).get("temperature_2m_max", [None])[0]
        print(f"    {site:<20}{label:<26}{str(e):>10}   Tmax={t}")
        time.sleep(4)
    s, js = get(C, {**base, "start_date": "2045-06-01", "end_date": "2045-06-01",
                    "models": [MODEL]})
    print(f"    {site:<20}{'climate ' + MODEL:<26}{str(js.get('elevation')):>10}")
    time.sleep(4)

print("\n" + "=" * 74)
print("(C) Does an explicit `elevation` override change the temperature?")
for elev in [None, 837, 1200]:
    p = {"latitude": 46.90, "longitude": 6.35, "start_date": "2020-06-01",
         "end_date": "2020-06-03", "daily": ["temperature_2m_max"],
         "timezone": "GMT"}
    if elev is not None:
        p["elevation"] = elev
    s, js = get(A, p)
    print(f"    archive elevation={str(elev):<6} -> reported={js.get('elevation')}"
          f"  Tmax={js.get('daily', {}).get('temperature_2m_max')}")
    time.sleep(4)
