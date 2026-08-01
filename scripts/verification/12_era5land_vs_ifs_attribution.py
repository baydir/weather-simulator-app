"""Why is ERA5-Land warmer than ECMWF IFS?
Discriminators:
  - terrain      : an elevation artefact should grow with relief
  - season       : a lapse-rate offset should be roughly season-independent
  - Tmax vs Tmin : a surface-energy-balance artefact hits daytime hardest
"""
import json, urllib.parse, urllib.request, urllib.error, statistics as st, time

A = "https://archive-api.open-meteo.com/v1/archive"
START, END = "2018-01-01", "2024-12-31"
SITES = {"Brest (cotier, plat)":   (48.39, -4.49),
         "Toulouse (plaine)":      (43.60, 1.44),
         "Pontarlier (moyenne m.)":(46.90, 6.35),
         "Chamonix (haute m.)":    (45.92, 6.87)}

def get(lat, lon, model):
    p = {"latitude": lat, "longitude": lon, "start_date": START, "end_date": END,
         "daily": ["temperature_2m_max", "temperature_2m_min"],
         "models": [model], "timezone": "GMT"}
    qs = urllib.parse.urlencode(p, doseq=True)
    with urllib.request.urlopen(f"{A}?{qs}", timeout=180) as r:
        return json.load(r)

def by_month(times, vals, months):
    return [v for t, v in zip(times, vals)
            if v is not None and int(t[5:7]) in months]

print(f"ERA5-Land minus ECMWF IFS, {START}..{END}")
print(f"{'site':<26}{'elev':>7}{'dTmax':>8}{'dTmin':>8}"
      f"{'dTmax hiv':>11}{'dTmax ete':>11}")
print("-" * 71)

for site, (lat, lon) in SITES.items():
    l = get(lat, lon, "era5_land"); time.sleep(8)
    i = get(lat, lon, "ecmwf_ifs"); time.sleep(8)
    lt, it = l["daily"], i["daily"]
    d_max = st.mean([a - b for a, b in zip(lt["temperature_2m_max"],
                                           it["temperature_2m_max"])
                     if a is not None and b is not None])
    d_min = st.mean([a - b for a, b in zip(lt["temperature_2m_min"],
                                           it["temperature_2m_min"])
                     if a is not None and b is not None])
    win = st.mean([a - b for t, a, b in zip(lt["time"], lt["temperature_2m_max"],
                                            it["temperature_2m_max"])
                   if a is not None and b is not None and int(t[5:7]) in (12, 1, 2)])
    sum_ = st.mean([a - b for t, a, b in zip(lt["time"], lt["temperature_2m_max"],
                                             it["temperature_2m_max"])
                    if a is not None and b is not None and int(t[5:7]) in (6, 7, 8)])
    print(f"{site:<26}{l['elevation']:>7.0f}{d_max:>+8.2f}{d_min:>+8.2f}"
          f"{win:>+11.2f}{sum_:>+11.2f}")

print("\nLecture :")
print("  ecart identique Tmax/Tmin + croissant avec le relief -> altitude")
print("  ecart concentre sur Tmax, ou sur une saison           -> bilan d'energie de surface")
