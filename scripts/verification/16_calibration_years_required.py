"""How many calibration years are enough?
Reference = quantile mapping built on the full 45-year overlap.
Test = same mapping built on N randomly drawn years, repeated R times.
Error is reported in cloud-cover points, as seen at the output of the
correction - i.e. what the user would actually be shown."""
import json, urllib.parse, urllib.request, urllib.error, random, statistics as st, time

A = "https://archive-api.open-meteo.com/v1/archive"
C = "https://climate-api.open-meteo.com/v1/climate"
MODEL = "MRI_AGCM3_2_S"
START, END = "1980-01-01", "2024-12-31"
SITES = {"Pontarlier": (46.90, 6.35), "Toulouse": (43.60, 1.44),
         "Brest": (48.39, -4.49)}
DRAWS = 25
SIZES = [5, 10, 20]
random.seed(0)

def get(url, p, tries=4):
    qs = urllib.parse.urlencode(p, doseq=True)
    for i in range(tries):
        try:
            with urllib.request.urlopen(f"{url}?{qs}", timeout=300) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(30 * (i + 1)); continue
            print(f"   ! HTTP {e.code}"); return {}
    return {}

def quantile(sorted_v, q):
    if not sorted_v:
        return None
    i = q * (len(sorted_v) - 1)
    lo, hi = int(i), min(int(i) + 1, len(sorted_v) - 1)
    return sorted_v[lo] + (sorted_v[hi] - sorted_v[lo]) * (i - lo)

def build(obs_by_month, mod_by_month):
    """empirical quantile mapping per month -> sorted arrays"""
    return {m: (sorted(obs_by_month.get(m, [])), sorted(mod_by_month.get(m, [])))
            for m in range(1, 13)}

def apply_map(mapping, month, value):
    obs_s, mod_s = mapping[month]
    if not obs_s or not mod_s:
        return value
    # percentile of `value` within the model distribution
    lo, hi = 0, len(mod_s)
    while lo < hi:
        mid = (lo + hi) // 2
        if mod_s[mid] < value: lo = mid + 1
        else: hi = mid
    q = lo / max(len(mod_s) - 1, 1)
    return quantile(obs_s, min(max(q, 0.0), 1.0))

def split(times, vals, years=None):
    out = {}
    for t, v in zip(times, vals):
        if v is None: continue
        y, m = int(t[:4]), int(t[5:7])
        if years is not None and y not in years: continue
        out.setdefault(m, []).append(v)
    return out

print(f"Nombre d'annees de calibration necessaire — {MODEL}, {START[:4]}-{END[:4]}")
print(f"{DRAWS} tirages aleatoires par taille ; erreur en points de nebulosite\n")

for site, (lat, lon) in SITES.items():
    p = {"latitude": lat, "longitude": lon, "start_date": START, "end_date": END,
         "daily": ["cloud_cover_mean"], "timezone": "GMT"}
    o = get(A, {**p, "models": ["era5"]}); time.sleep(10)
    m = get(C, {**p, "models": [MODEL]}); time.sleep(10)
    ot, ov = o.get("daily", {}).get("time"), o.get("daily", {}).get("cloud_cover_mean")
    mt, mv = m.get("daily", {}).get("time"), m.get("daily", {}).get("cloud_cover_mean")
    if not ov or not mv:
        print(f"  {site}: donnees manquantes\n"); continue

    all_years = sorted({int(t[:4]) for t in ot})
    ref = build(split(ot, ov), split(mt, mv))

    # test points: model deciles per month, i.e. where real values live
    tests = []
    mod_all = split(mt, mv)
    for mo in range(1, 13):
        s = sorted(mod_all.get(mo, []))
        for q in [0.1, 0.25, 0.5, 0.75, 0.9]:
            v = quantile(s, q)
            if v is not None:
                tests.append((mo, v))

    print(f"  {site}  ({len(all_years)} annees disponibles)")
    print(f"    {'annees':<9}{'erreur moy':>12}{'erreur p90':>12}{'erreur max':>12}")
    for n in SIZES:
        errs = []
        for _ in range(DRAWS):
            yrs = set(random.sample(all_years, n))
            sub = build(split(ot, ov, yrs), split(mt, mv, yrs))
            d = [abs(apply_map(sub, mo, v) - apply_map(ref, mo, v))
                 for mo, v in tests]
            errs.append(st.mean(d))
        errs.sort()
        print(f"    {n:<9}{st.mean(errs):>12.2f}"
              f"{errs[int(0.9 * (len(errs) - 1))]:>12.2f}{errs[-1]:>12.2f}")
    print()
