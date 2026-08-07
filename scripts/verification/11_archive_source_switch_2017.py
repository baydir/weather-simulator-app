"""Does the archive DEFAULT silently switch reanalysis over time?
If so, the "past" series is itself inhomogeneous - fatal for docs/donnees.md."""
import json, urllib.parse, urllib.request, urllib.error, statistics as st, time

A = "https://archive-api.open-meteo.com/v1/archive"
LAT, LON = 46.90, 6.35  # Pontarlier

def get(p):
    qs = urllib.parse.urlencode(p, doseq=True)
    try:
        with urllib.request.urlopen(f"{A}?{qs}", timeout=120) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)

def june(year, models=None):
    p = {"latitude": LAT, "longitude": LON,
         "start_date": f"{year}-06-01", "end_date": f"{year}-06-30",
         "daily": ["temperature_2m_max"], "timezone": "GMT"}
    if models:
        p["models"] = models
    s, js = get(p)
    if s != 200:
        return None, js.get("reason")
    v = [x for x in js["daily"]["temperature_2m_max"] if x is not None]
    return (st.mean(v) if v else None), js.get("elevation")

YEARS = [1960, 1980, 1990, 2000, 2010, 2018, 2020, 2021, 2022, 2024, 2025]
SRC = [None, ["era5"], ["era5_land"], ["cerra"]]
NAMES = ["defaut", "era5", "era5_land", "cerra"]

print("Mean June Tmax at Pontarlier, by requested reanalysis")
print(f"{'year':<7}" + "".join(f"{n:>12}" for n in NAMES))
print("-" * (7 + 12 * len(NAMES)))
for y in YEARS:
    row = []
    for m in SRC:
        v, _ = june(y, m)
        row.append(f"{v:.2f}" if isinstance(v, float) else "-")
        time.sleep(3)
    print(f"{y:<7}" + "".join(f"{c:>12}" for c in row))

print("\nWhich explicit source does the DEFAULT match, per year?")
print(f"{'year':<7}{'defaut':>9}   matches")
for y in YEARS:
    d, _ = june(y); time.sleep(3)
    best, bestd = None, 1e9
    for m, n in zip(SRC[1:], NAMES[1:]):
        v, _ = june(y, m); time.sleep(3)
        if isinstance(v, float) and isinstance(d, float) and abs(v - d) < bestd:
            best, bestd = n, abs(v - d)
    print(f"{y:<7}{(f'{d:.2f}' if isinstance(d, float) else '-'):>9}   "
          f"{best} (ecart {bestd:.3f})" if best else f"{y:<7}   ?")
