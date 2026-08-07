"""(1) Verify the two-call split (era5_land for temperature, era5 for the rest).
   (2) Re-measure the cloud-cover bias against FORCED era5, replacing the
       earlier figures taken from the default endpoint (which silently mixes
       sources per variable and switches to IFS in 2017)."""
import json, urllib.parse, urllib.request, urllib.error, statistics as st, time

A = "https://archive-api.open-meteo.com/v1/archive"
C = "https://climate-api.open-meteo.com/v1/climate"
MODEL = "MRI_AGCM3_2_S"
START, END = "2015-01-01", "2019-12-31"

SITES = {"Pontarlier": (46.90, 6.35), "Brest": (48.39, -4.49),
         "Marseille": (43.30, 5.37), "Reykjavik": (64.15, -21.94),
         "Bamako": (12.65, -8.00), "Singapour": (1.35, 103.82)}

# figures currently written into docs/science.md, taken from the default endpoint
OLD = {"Pontarlier": -4.55, "Brest": -8.28, "Marseille": -8.59,
       "Reykjavik": -5.67, "Bamako": -19.69, "Singapour": -28.19}

def get(url, p, tries=4):
    qs = urllib.parse.urlencode(p, doseq=True)
    for i in range(tries):
        try:
            with urllib.request.urlopen(f"{url}?{qs}", timeout=240) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(25 * (i + 1)); continue
            print(f"    ! HTTP {e.code}"); return {}
    return {}

# ---------------------------------------------------------------- (1)
print("(1) Two-call split at Pontarlier, 2015-01-01..2015-01-05\n")
base = {"latitude": 46.90, "longitude": 6.35, "start_date": "2015-01-01",
        "end_date": "2015-01-05", "timezone": "GMT"}
t = get(A, {**base, "models": ["era5_land"],
            "daily": ["temperature_2m_max", "temperature_2m_min"]})
o = get(A, {**base, "models": ["era5"],
            "daily": ["precipitation_sum", "snowfall_sum", "cloud_cover_mean",
                      "wind_speed_10m_max"]})
td, od = t.get("daily", {}), o.get("daily", {})
print(f"    dates identiques : {td.get('time') == od.get('time')}")
print(f"    altitude era5_land={t.get('elevation')}  era5={o.get('elevation')}")
print(f"    {'date':<12}{'Tmax':>7}{'Tmin':>7}{'precip':>8}{'neige':>7}{'nebul':>7}{'vent':>7}")
for i, d in enumerate(td.get("time", [])):
    print(f"    {d:<12}{td['temperature_2m_max'][i]:>7}{td['temperature_2m_min'][i]:>7}"
          f"{od['precipitation_sum'][i]:>8}{od['snowfall_sum'][i]:>7}"
          f"{od['cloud_cover_mean'][i]:>7}{od['wind_speed_10m_max'][i]:>7}")
time.sleep(10)

# ---------------------------------------------------------------- (2)
print(f"\n(2) Cloud-cover bias, {MODEL} hindcast minus observation, {START}..{END}\n")
print(f"    {'site':<12}{'ERA5 force':>12}{'modele':>9}{'ecart':>9}"
      f"{'ancien (defaut)':>18}{'revision':>11}")
print("    " + "-" * 71)
for s, (lat, lon) in SITES.items():
    p = {"latitude": lat, "longitude": lon, "start_date": START, "end_date": END,
         "daily": ["cloud_cover_mean"], "timezone": "GMT"}
    obs = get(A, {**p, "models": ["era5"]}).get("daily", {}).get("cloud_cover_mean")
    time.sleep(10)
    mod = get(C, {**p, "models": [MODEL]}).get("daily", {}).get("cloud_cover_mean")
    time.sleep(10)
    if not obs or not mod:
        print(f"    {s:<12} donnees manquantes"); continue
    pairs = [(a, b) for a, b in zip(obs, mod) if a is not None and b is not None]
    mo = st.mean([a for a, _ in pairs]); mm = st.mean([b for _, b in pairs])
    new = mm - mo
    print(f"    {s:<12}{mo:>12.2f}{mm:>9.2f}{new:>+9.2f}"
          f"{OLD[s]:>+18.2f}{new - OLD[s]:>+11.2f}")
