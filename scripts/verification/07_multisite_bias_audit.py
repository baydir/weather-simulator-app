"""Lighter bias audit with explicit error reporting and throttling."""
import json, urllib.parse, urllib.request, urllib.error, statistics as st, time

C = "https://climate-api.open-meteo.com/v1/climate"
A = "https://archive-api.open-meteo.com/v1/archive"
MODEL = "MRI_AGCM3_2_S"
START, END = "2015-01-01", "2019-12-31"

VARS = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum",
        "cloud_cover_mean", "relative_humidity_2m_mean", "wind_speed_10m_mean",
        "shortwave_radiation_sum", "dew_point_2m_mean"]

SITES = {
    "Pontarlier FR montagne": (46.90, 6.35),
    "Brest FR oceanique":     (48.39, -4.49),
    "Marseille FR mediter.":  (43.30, 5.37),
    "Reykjavik IS subpolaire":(64.15, -21.94),
    "Bamako ML sahel":        (12.65, -8.00),
    "Singapour SG tropical":  (1.35, 103.82),
}

def get(url, p, tries=4):
    qs = urllib.parse.urlencode(p, doseq=True)
    for i in range(tries):
        try:
            with urllib.request.urlopen(f"{url}?{qs}", timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:120]
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(20 * (i + 1))
                continue
            print(f"      ! HTTP {e.code}: {body}")
            return {}
    return {}

def stats(v):
    v = [x for x in v if x is not None]
    if len(v) < 100:
        return None
    s = sorted(v)
    return st.mean(v), st.pstdev(v), s[int(0.99 * len(s))]

print(f"BIAS AUDIT — {MODEL} hindcast vs ERA5, {START}..{END}")
print("dMean = modele-obs ; sdRatio = sd_modele/sd_obs ; dP99 = ecart des p99\n")

for site, (lat, lon) in SITES.items():
    base = {"latitude": lat, "longitude": lon, "start_date": START,
            "end_date": END, "daily": VARS, "timezone": "GMT"}
    obs = get(A, base).get("daily", {})
    time.sleep(8)
    mod = get(C, {**base, "models": [MODEL]}).get("daily", {})
    time.sleep(8)
    if not obs or not mod:
        print(f"  {site}: donnees manquantes\n")
        continue
    print(f"  {site}")
    print(f"    {'variable':<28}{'dMean':>9}{'sdRatio':>9}{'dP99':>9}")
    for v in VARS:
        o, m = stats(obs.get(v, [])), stats(mod.get(v, []))
        if o is None or m is None:
            print(f"    {v:<28}{'(indisponible)':>27}")
            continue
        print(f"    {v:<28}{m[0]-o[0]:>+9.2f}"
              f"{(m[1]/o[1] if o[1] else float('nan')):>9.2f}{m[2]-o[2]:>+9.2f}")
    print()
