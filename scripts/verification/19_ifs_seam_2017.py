"""Could ECMWF IFS carry [2017 -> present], leaving ERA5/ERA5-Land [1950 -> 2017]?

That would close the five-day hole the forced reanalyses leave at the present
day, at the cost of a second seam inside the past. It is worth it only if IFS
and ERA5/ERA5-Land are close enough that the 2017 changeover is invisible.

What has to hold:
  (1) IFS really covers 2017 -> today, every variable, not just temperature
  (2) the IFS/ERA5 offset is small, and constant enough to be corrected
  (3) moving the recent past to IFS does not widen the seam that matters more:
      the one at the present day, against the climate model — which was itself
      bias-corrected against ERA5-Land
"""
import json, math, statistics as st, time, urllib.error, urllib.parse, urllib.request

A = "https://archive-api.open-meteo.com/v1/archive"
C = "https://climate-api.open-meteo.com/v1/climate"
MODEL = "MRI_AGCM3_2_S"
START, END = "2018-01-01", "2024-12-31"

SITES = {"Brest (cotier)":     (48.39, -4.49),
         "Toulouse (plaine)":  (43.60, 1.44),
         "Pontarlier (moy.m)": (46.90, 6.35),
         "Chamonix (haute m)": (45.92, 6.87)}

TEMP = ["temperature_2m_max", "temperature_2m_min"]
SURF = ["precipitation_sum", "rain_sum", "snowfall_sum", "cloud_cover_mean",
        "wind_speed_10m_max", "wind_speed_10m_mean"]

def get(url, p, tries=4):
    qs = urllib.parse.urlencode(p, doseq=True)
    for i in range(tries):
        try:
            with urllib.request.urlopen(f"{url}?{qs}", timeout=240) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(25 * (i + 1)); continue
            try:
                return {"_error": json.load(e).get("reason", e.reason)}
            except Exception:
                return {"_error": f"HTTP {e.code}"}
    return {"_error": "unreachable"}

def daily(url, lat, lon, start, end, model, vars_):
    js = get(url, {"latitude": lat, "longitude": lon, "start_date": start,
                   "end_date": end, "daily": vars_, "models": [model],
                   "timezone": "GMT"})
    if "_error" in js:
        return None, js["_error"]
    d = js.get("daily", {})
    out = {}
    for v in vars_:
        key = v if v in d else next((k for k in d if k.startswith(v + "_")), None)
        out[v] = dict(zip(d["time"], d[key])) if key else {}
    return out, js.get("elevation")

def stats(a, b):
    """b taken as the reference: bias, RMSE, sd ratio, correlation."""
    days = sorted(set(a) & set(b))
    pairs = [(a[d], b[d]) for d in days if a[d] is not None and b[d] is not None]
    if len(pairs) < 30:
        return None
    x = [p for p, _ in pairs]; y = [q for _, q in pairs]
    diff = [p - q for p, q in pairs]
    sy = st.pstdev(y)
    return {"n": len(pairs), "bias": st.mean(diff),
            "rmse": math.sqrt(st.mean([d * d for d in diff])),
            "sd_ratio": (st.pstdev(x) / sy) if sy else float("nan"),
            "r": (st.correlation(x, y) if len(set(x)) > 1 and len(set(y)) > 1 else float("nan"))}

def season(a, b, months):
    sa = {d: v for d, v in a.items() if int(d[5:7]) in months}
    sb = {d: v for d, v in b.items() if int(d[5:7]) in months}
    s = stats(sa, sb)
    return s["bias"] if s else float("nan")

# ------------------------------------------------------------------ (1)
print("(1) Couverture de ecmwf_ifs\n")
for label, start, end in [("2016 (avant la bascule)", "2016-06-01", "2016-06-10"),
                          ("2017 (debut annonce)", "2017-01-01", "2017-01-10"),
                          ("2020", "2020-06-01", "2020-06-10")]:
    d, info = daily(A, 46.90, 6.35, start, end, "ecmwf_ifs", TEMP)
    if d is None:
        print(f"    {label:<26} indisponible : {info}")
    else:
        served = [k for k, v in d["temperature_2m_max"].items() if v is not None]
        print(f"    {label:<26} {len(served)}/10 jours servis"
              f"{'  premier ' + served[0] if served else ''}")
    time.sleep(5)

from datetime import date, timedelta  # noqa: E402
today = date.today()
recent_start = (today - timedelta(days=12)).isoformat()
print(f"\n    Jusqu'ou va chaque source ? (demande jusqu'au {today})")
for model, vars_ in [("era5_land", TEMP), ("era5", SURF[:1]), ("ecmwf_ifs", TEMP)]:
    d, _ = daily(A, 46.90, 6.35, recent_start, today.isoformat(), model, vars_)
    if d:
        v = vars_[0]
        served = [k for k, x in d[v].items() if x is not None]
        gap = (today - date.fromisoformat(served[-1])).days if served else None
        print(f"    {model:<12} dernier jour servi {served[-1] if served else '-'}"
              f"   soit J-{gap}")
    time.sleep(5)

# ------------------------------------------------------------------ (2)
print("\n(2) ecmwf_ifs sert-il toutes les variables ? (Pontarlier, 2020)\n")
d, _ = daily(A, 46.90, 6.35, "2020-01-01", "2020-12-31", "ecmwf_ifs", TEMP + SURF)
for v in TEMP + SURF:
    vals = list(d[v].values()) if d else []
    nn = [x for x in vals if x is not None]
    verdict = "NULL" if not nn else f"{100 * len(nn) / len(vals):.0f}% non-null"
    print(f"    {v:<26}{verdict:>18}")
time.sleep(5)

# ------------------------------------------------------------------ (3)
print(f"\n(3) IFS contre la reanalyse de reference, {START}..{END}")
print("    temperatures contre era5_land, le reste contre era5\n")
print(f"    {'site':<20}{'variable':<22}{'biais':>9}{'RMSE':>8}{'sd IFS/ref':>12}{'r':>7}")
print("    " + "-" * 78)

keep = {}
for site, (lat, lon) in SITES.items():
    ifs, _ = daily(A, lat, lon, START, END, "ecmwf_ifs", TEMP + SURF); time.sleep(6)
    land, _ = daily(A, lat, lon, START, END, "era5_land", TEMP); time.sleep(6)
    era5, _ = daily(A, lat, lon, START, END, "era5", SURF); time.sleep(6)
    if not (ifs and land and era5):
        print(f"    {site:<20} donnees manquantes"); continue
    keep[site] = (ifs, land)
    for v in TEMP + SURF:
        ref = land[v] if v in TEMP else era5[v]
        s = stats(ifs[v], ref)
        if not s:
            print(f"    {site:<20}{v:<22}{'insuffisant':>9}"); continue
        print(f"    {site:<20}{v:<22}{s['bias']:>+9.2f}{s['rmse']:>8.2f}"
              f"{s['sd_ratio']:>12.2f}{s['r']:>7.3f}")
    print()

# ------------------------------------------------------------------ (4)
print("(4) Le biais de temperature est-il constant ? (IFS moins era5_land)\n")
print(f"    {'site':<20}{'Tmax hiver':>12}{'Tmax ete':>11}{'Tmin hiver':>13}{'Tmin ete':>11}")
print("    " + "-" * 68)
for site, (ifs, land) in keep.items():
    print(f"    {site:<20}"
          f"{season(ifs['temperature_2m_max'], land['temperature_2m_max'], (12, 1, 2)):>+12.2f}"
          f"{season(ifs['temperature_2m_max'], land['temperature_2m_max'], (6, 7, 8)):>+11.2f}"
          f"{season(ifs['temperature_2m_min'], land['temperature_2m_min'], (12, 1, 2)):>+13.2f}"
          f"{season(ifs['temperature_2m_min'], land['temperature_2m_min'], (6, 7, 8)):>+11.2f}")

# ------------------------------------------------------------------ (5)
print(f"\n(5) Consequence sur la couture qui compte : {MODEL} contre chaque reference")
print("    (le modele a ete corrige de son biais contre era5_land)\n")
print(f"    {'site':<20}{'mod-era5_land':>16}{'mod-IFS':>10}{'aggravation':>14}")
print("    " + "-" * 62)
for site, (lat, lon) in SITES.items():
    if site not in keep:
        continue
    ifs, land = keep[site]
    mod, _ = daily(C, lat, lon, START, END, MODEL, TEMP); time.sleep(6)
    if not mod:
        print(f"    {site:<20} modele indisponible"); continue
    for v in ["temperature_2m_max"]:
        a = stats(mod[v], land[v]); b = stats(mod[v], ifs[v])
        if not (a and b):
            continue
        print(f"    {site:<20}{a['bias']:>+16.2f}{b['bias']:>+10.2f}"
              f"{abs(b['bias']) - abs(a['bias']):>+14.2f}")

print("\nLecture :")
print("  (3) un biais faible ET une sd proche de 1 -> couture 2017 corrigeable")
print("  (4) un biais qui change de signe ou double selon la saison -> non corrigeable")
print("      par un decalage unique ; il faudrait une correction mensuelle")
print("  (5) une aggravation positive signifie que passer le passe recent a IFS")
print("      creuse la marche du jour present, celle que l'utilisateur voit")
