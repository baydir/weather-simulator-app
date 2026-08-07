"""Which reanalysis should serve past TEMPERATURE?

Two findings, both underpinning docs/donnees.md:
  (A) the archive default is ECMWF IFS from 2017 onward, ERA5-Land before;
  (B) the CMIP6 model sits far closer to ERA5-Land than to ERA5, because
      Open-Meteo bias-corrects its climate data against ERA5-Land.

(B) is what justifies forcing era5_land for temperature even though every
other variable has to come from era5.
"""
import json
import statistics as st
import time
import urllib.error
import urllib.parse
import urllib.request

A = "https://archive-api.open-meteo.com/v1/archive"
C = "https://climate-api.open-meteo.com/v1/climate"
MODEL = "MRI_AGCM3_2_S"
SITES = {"Pontarlier": (46.90, 6.35), "Brest": (48.39, -4.49),
         "Toulouse": (43.60, 1.44)}
VARS = ["temperature_2m_max", "temperature_2m_min"]


def get(url, params, tries=4):
    qs = urllib.parse.urlencode(params, doseq=True)
    for i in range(tries):
        try:
            with urllib.request.urlopen(f"{url}?{qs}", timeout=300) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(30 * (i + 1))
                continue
            print(f"    ! HTTP {e.code}")
            return {}
    return {}


def june_mean(year, model):
    p = {"latitude": 46.90, "longitude": 6.35,
         "start_date": f"{year}-06-01", "end_date": f"{year}-06-30",
         "daily": ["temperature_2m_max"], "timezone": "GMT"}
    if model:
        p["models"] = [model]
    d = get(A, p).get("daily", {}).get("temperature_2m_max")
    v = [x for x in (d or []) if x is not None]
    return st.mean(v) if v else None


print("(A) The archive default switches source in 2017")
print("    Mean June Tmax at Pontarlier\n")
print(f"    {'year':<7}{'default':>10}{'ecmwf_ifs':>12}{'era5_land':>12}")
for year in [2014, 2015, 2016, 2017, 2018, 2020, 2023]:
    d = june_mean(year, None); time.sleep(4)
    i = june_mean(year, "ecmwf_ifs"); time.sleep(4)
    l = june_mean(year, "era5_land"); time.sleep(4)
    f = lambda x: f"{x:.2f}" if isinstance(x, float) else "-"
    print(f"    {year:<7}{f(d):>10}{f(i):>12}{f(l):>12}")
print("\n    Expected: default == era5_land up to 2016, == ecmwf_ifs from 2017.\n")

print("(B) Which reanalysis is the CMIP6 hindcast closer to?")
print("    2000-2016 only, i.e. before the IFS switch contaminates anything\n")
print(f"    {'site':<12}{'variable':<22}{'vs ERA5':>10}{'vs ERA5-Land':>14}")
S, E = "2000-01-01", "2016-12-31"
agg = {"era5": [], "era5_land": []}
for site, (lat, lon) in SITES.items():
    p = {"latitude": lat, "longitude": lon, "start_date": S, "end_date": E,
         "daily": VARS, "timezone": "GMT"}
    e5 = get(A, {**p, "models": ["era5"]}).get("daily", {}); time.sleep(9)
    el = get(A, {**p, "models": ["era5_land"]}).get("daily", {}); time.sleep(9)
    mo = get(C, {**p, "models": [MODEL]}).get("daily", {}); time.sleep(9)
    if not (e5 and el and mo):
        print(f"    {site:<12} donnees manquantes")
        continue
    for v in VARS:
        d5 = st.mean([m - o for m, o in zip(mo[v], e5[v])
                      if m is not None and o is not None])
        dl = st.mean([m - o for m, o in zip(mo[v], el[v])
                      if m is not None and o is not None])
        agg["era5"].append(abs(d5))
        agg["era5_land"].append(abs(dl))
        print(f"    {site:<12}{v:<22}{d5:>+10.3f}{dl:>+14.3f}")

if agg["era5"]:
    print(f"\n    Mean absolute offset — ERA5 {st.mean(agg['era5']):.3f} C, "
          f"ERA5-Land {st.mean(agg['era5_land']):.3f} C")
    print("    ERA5-Land should win by roughly a factor of two, and be far "
          "more consistent in sign.")
