"""(1) scenario switching  (2) multi-variable, multi-site bias audit
   (3) does the bias correction fix variance and extremes?"""
import json, urllib.parse, urllib.request, urllib.error, statistics as st

C = "https://climate-api.open-meteo.com/v1/climate"
A = "https://archive-api.open-meteo.com/v1/archive"
MODEL = "MRI_AGCM3_2_S"
START, END = "2011-01-01", "2020-12-31"

VARS = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum",
        "cloud_cover_mean", "relative_humidity_2m_mean", "wind_speed_10m_mean",
        "shortwave_radiation_sum", "pressure_msl_mean", "dew_point_2m_mean"]

SITES = {
    "Pontarlier FR (montagne)": (46.90, 6.35),
    "Brest FR (oceanique)":     (48.39, -4.49),
    "Marseille FR (mediter.)":  (43.30, 5.37),
    "Paris FR (plaine)":        (48.85, 2.35),
    "Reykjavik IS (subpolaire)":(64.15, -21.94),
    "Bamako ML (sahel)":        (12.65, -8.00),
    "Singapour SG (tropical)":  (1.35, 103.82),
    "Phoenix US (aride)":       (33.45, -112.07),
}

def get(url, p):
    qs = urllib.parse.urlencode(p, doseq=True)
    try:
        with urllib.request.urlopen(f"{url}?{qs}", timeout=180) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)

# ---------------------------------------------------------------- (1)
print("=" * 78)
print("(1) SCENARIO — can anything other than RCP8.5 be requested?")
base = {"latitude": 46.90, "longitude": 6.35, "start_date": "2045-06-01",
        "end_date": "2045-06-05", "models": [MODEL],
        "daily": ["temperature_2m_max"], "timezone": "Europe/Paris"}
s, ref = get(C, base)
print(f"   no scenario param : HTTP {s} {ref.get('daily', {}).get('temperature_2m_max')}")
for k, v in [("scenario", "ssp245"), ("scenario", "ssp126"), ("ssp", "245"),
             ("experiment", "ssp245"), ("scenario", "rcp45")]:
    s, js = get(C, {**base, k: v})
    got = js.get("daily", {}).get("temperature_2m_max") if s == 200 else js.get("reason")
    same = " (identique au defaut)" if got == ref.get("daily", {}).get("temperature_2m_max") else " <-- DIFFERENT"
    print(f"   {k}={v:<8}: HTTP {s} {got}{same if s == 200 else ''}")

# ---------------------------------------------------------------- (2)(3)
def series(url, lat, lon, extra):
    s, js = get(url, {"latitude": lat, "longitude": lon, "start_date": START,
                      "end_date": END, "daily": VARS,
                      "timezone": "GMT", **extra})
    return js.get("daily", {})

def stats(v):
    v = [x for x in v if x is not None]
    if len(v) < 100:
        return None
    v_sorted = sorted(v)
    return (st.mean(v), st.pstdev(v), v_sorted[int(0.99 * len(v_sorted))])

print("\n" + "=" * 78)
print(f"(2)(3) BIAS AUDIT — {MODEL} hindcast vs ERA5, {START}..{END}")
print("     dMean = model-obs ;  sdRatio = sd_model/sd_obs ;  dP99 = p99 difference")

for site, (lat, lon) in SITES.items():
    obs = series(A, lat, lon, {})
    mod = series(C, lat, lon, {"models": [MODEL]})
    print(f"\n  {site}")
    print(f"    {'variable':<28}{'dMean':>9}{'sdRatio':>9}{'dP99':>9}")
    for v in VARS:
        o, m = stats(obs.get(v, [])), stats(mod.get(v, []))
        if o is None or m is None:
            print(f"    {v:<28}{'  (indisponible)':>27}")
            continue
        print(f"    {v:<28}{m[0]-o[0]:>+9.2f}{(m[1]/o[1] if o[1] else float('nan')):>9.2f}{m[2]-o[2]:>+9.2f}")
