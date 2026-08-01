"""Does era5_land actually serve every variable we need?
If precipitation or cloud cover come back null, forcing a single source fails."""
import json, urllib.parse, urllib.request, urllib.error, statistics as st, time

A = "https://archive-api.open-meteo.com/v1/archive"
LAT, LON = 46.90, 6.35
NEED = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum",
        "rain_sum", "snowfall_sum", "cloud_cover_mean",
        "wind_speed_10m_max", "wind_speed_10m_mean"]

def get(model, start, end, daily):
    p = {"latitude": LAT, "longitude": LON, "start_date": start, "end_date": end,
         "daily": daily, "timezone": "GMT"}
    if model:
        p["models"] = [model]
    qs = urllib.parse.urlencode(p, doseq=True)
    try:
        with urllib.request.urlopen(f"{A}?{qs}", timeout=180) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)

print("(1) Per-variable availability, one request per variable, 2015 full year\n")
print(f"{'variable':<26}{'era5':>22}{'era5_land':>22}")
print("-" * 70)
store = {}
for v in NEED:
    row = []
    for m in ["era5", "era5_land"]:
        s, js = get(m, "2015-01-01", "2015-12-31", [v])
        d = js.get("daily", {})
        key = next((k for k in d if k != "time"), None)
        if s != 200 or key is None:
            row.append(f"HTTP {s}")
            store[(m, v)] = None
        else:
            vals = d[key]
            nn = [x for x in vals if x is not None]
            store[(m, v)] = vals
            row.append(f"{100*len(nn)/len(vals):.0f}% non-null" if nn else "NULL")
        time.sleep(4)
    print(f"{v:<26}{row[0]:>22}{row[1]:>22}")

print("\n(2) Where both exist: are era5_land values identical to era5?")
print(f"{'variable':<26}{'identique':>12}{'moy era5':>11}{'moy land':>11}")
print("-" * 60)
for v in NEED:
    a, b = store.get(("era5", v)), store.get(("era5_land", v))
    if not a or not b:
        continue
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if not pairs:
        print(f"{v:<26}{'-':>12}")
        continue
    same = sum(1 for x, y in pairs if abs(x - y) < 1e-6) / len(pairs)
    print(f"{v:<26}{100*same:>11.1f}%"
          f"{st.mean([x for x, _ in pairs]):>11.2f}"
          f"{st.mean([y for _, y in pairs]):>11.2f}")

print("\n(3) Same test in a recent year (2023), where the default is IFS")
for v in ["precipitation_sum", "cloud_cover_mean"]:
    line = f"  {v:<24}"
    for m in ["era5", "era5_land", None]:
        s, js = get(m, "2023-01-01", "2023-12-31", [v])
        d = js.get("daily", {})
        key = next((k for k in d if k != "time"), None)
        vals = d.get(key) if key else None
        nn = [x for x in vals if x is not None] if vals else []
        lbl = m or "defaut"
        line += f"  {lbl}={'NULL' if not nn else f'{st.mean(nn):.2f}'}"
        time.sleep(4)
    print(line)
