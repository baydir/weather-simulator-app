"""Coverage audit: which models actually return non-null data, for which
variables, across the full 1950-2050 range and at several locations."""
import json, urllib.parse, urllib.request

CLIMATE = "https://climate-api.open-meteo.com/v1/climate"
MODELS = ["CMCC_CM2_VHR4", "FGOALS_f3_H", "HiRAM_SIT_HR", "MRI_AGCM3_2_S",
          "EC_Earth3P_HR", "MPI_ESM1_2_XR", "NICAM16_8S"]
YEARS = ["1955", "1985", "2015", "2030", "2045", "2050"]
SITES = {"Pontarlier": (46.90, 6.35), "Brest": (48.39, -4.49),
         "Marseille": (43.30, 5.37), "Chamonix": (45.92, 6.87)}
CORE = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "cloud_cover_mean"]

def get(params):
    qs = urllib.parse.urlencode(params, doseq=True)
    with urllib.request.urlopen(f"{CLIMATE}?{qs}", timeout=120) as r:
        return json.load(r)

def frac_ok(lat, lon, model, year, var):
    js = get({"latitude": lat, "longitude": lon,
              "start_date": f"{year}-01-01", "end_date": f"{year}-12-31",
              "models": [model], "daily": [var], "timezone": "Europe/Paris"})
    d = js.get("daily", {})
    key = next((k for k in d if k != "time"), None)
    if key is None:
        return 0.0
    vals = d[key]
    if not vals:
        return 0.0
    return sum(1 for v in vals if v is not None) / len(vals)

print("PART 1 — Pontarlier, share of non-null days per model x year "
      "(temperature_2m_max)\n")
print(f"{'model':<16}" + "".join(f"{y:>9}" for y in YEARS))
print("-" * (16 + 9 * len(YEARS)))
for m in MODELS:
    row = [frac_ok(46.90, 6.35, m, y, "temperature_2m_max") for y in YEARS]
    print(f"{m:<16}" + "".join(f"{v*100:>8.0f}%" for v in row))

print("\n\nPART 2 — year 2045, share of non-null days per model x variable "
      "(Pontarlier)\n")
print(f"{'model':<16}" + "".join(f"{v.replace('_2m','').replace('_sum','')[:13]:>15}" for v in CORE))
print("-" * (16 + 15 * len(CORE)))
for m in MODELS:
    row = [frac_ok(46.90, 6.35, m, "2045", v) for v in CORE]
    print(f"{m:<16}" + "".join(f"{v*100:>14.0f}%" for v in row))

print("\n\nPART 3 — year 2045, temperature_2m_max, per model x location\n")
print(f"{'model':<16}" + "".join(f"{s:>13}" for s in SITES))
print("-" * (16 + 13 * len(SITES)))
for m in MODELS:
    row = [frac_ok(lat, lon, m, "2045", "temperature_2m_max")
           for lat, lon in SITES.values()]
    print(f"{m:<16}" + "".join(f"{v*100:>12.0f}%" for v in row))
