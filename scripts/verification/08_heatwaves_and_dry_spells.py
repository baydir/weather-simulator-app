"""Does the model under-represent HEATWAVES and DRY SPELLS?
Persistence, not just marginal distribution: bias correction acts day by day
and cannot repair temporal structure. Thresholds are taken from OBSERVATIONS
so both series are judged against the same bar."""
import json, urllib.parse, urllib.request, urllib.error, statistics as st, time

C = "https://climate-api.open-meteo.com/v1/climate"
A = "https://archive-api.open-meteo.com/v1/archive"
MODEL = "MRI_AGCM3_2_S"
START, END = "2000-01-01", "2019-12-31"
SITES = {"Pontarlier": (46.90, 6.35), "Marseille": (43.30, 5.37),
         "Brest": (48.39, -4.49), "Toulouse": (43.60, 1.44)}

def get(url, p, tries=4):
    qs = urllib.parse.urlencode(p, doseq=True)
    for i in range(tries):
        try:
            with urllib.request.urlopen(f"{url}?{qs}", timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(25 * (i + 1)); continue
            print(f"   ! HTTP {e.code}"); return {}
    return {}

def spells(flags):
    """lengths of runs of True"""
    out, n = [], 0
    for f in flags:
        if f: n += 1
        elif n: out.append(n); n = 0
    if n: out.append(n)
    return out

def lag1(v):
    m = st.mean(v)
    num = sum((v[i]-m)*(v[i+1]-m) for i in range(len(v)-1))
    den = sum((x-m)**2 for x in v)
    return num/den if den else float("nan")

def summarise(tmax, prcp, t_thr, label):
    hot = spells([t >= t_thr for t in tmax])
    dry = spells([p < 1.0 for p in prcp])
    hot3 = [s for s in hot if s >= 3]
    print(f"    {label:<10}"
          f"{sum(1 for t in tmax if t >= t_thr):>8}"
          f"{(max(hot) if hot else 0):>9}"
          f"{len(hot3):>9}"
          f"{(st.mean(dry) if dry else 0):>9.2f}"
          f"{(max(dry) if dry else 0):>8}"
          f"{lag1(tmax):>9.3f}")

print(f"HEATWAVES & DRY SPELLS — {MODEL} hindcast vs ERA5, {START}..{END}")
print("Threshold = 90th percentile of OBSERVED Tmax at each site.\n")
print(f"    {'source':<10}{'d>=p90':>8}{'maxRun':>9}{'runs>=3':>9}"
      f"{'dryMean':>9}{'dryMax':>8}{'lag1_T':>9}")

for site, (lat, lon) in SITES.items():
    base = {"latitude": lat, "longitude": lon, "start_date": START,
            "end_date": END, "daily": ["temperature_2m_max", "precipitation_sum"],
            "timezone": "GMT"}
    o = get(A, base).get("daily", {}); time.sleep(10)
    m = get(C, {**base, "models": [MODEL]}).get("daily", {}); time.sleep(10)
    if not o or not m:
        print(f"\n  {site}: donnees manquantes"); continue
    ot = [x for x in o["temperature_2m_max"] if x is not None]
    op = [x for x in o["precipitation_sum"] if x is not None]
    mt = [x for x in m["temperature_2m_max"] if x is not None]
    mp = [x for x in m["precipitation_sum"] if x is not None]
    thr = sorted(ot)[int(0.90 * len(ot))]
    print(f"\n  {site}  (seuil p90 observe = {thr:.1f} C)")
    summarise(ot, op, thr, "ERA5")
    summarise(mt, mp, thr, "modele")
