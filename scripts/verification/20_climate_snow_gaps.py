"""Does the Climate API serve snow every day? No — and the gap is systematic.

Sky class rule 1 rests on snowfall: a day is a snow day at 1 cm or more. If the
variable is missing, the rule cannot be evaluated, and docs/regles.md forbids filling
a gap silently.

The gap is neither seasonal nor uniform, and that is the finding. At Marseille
and Brest it takes the same 61 days every year, 3 July to 1 September, which
invites reading it as a summer artefact. Christchurch settles that reading: half
the year missing, scattered, austral winter included. Ushuaia, where snow is
real, has none at all.

So it cannot be explained away as "no snow in summer" — a rule that would be
exactly backwards south of the equator, and the grid is meant to go worldwide.
Its size depends on the model as much as on the place.

Only precipitation and temperature are complete everywhere, which is why the
snow criterion is derived from those two instead, on both regimes alike.
"""
import json, time, urllib.error, urllib.parse, urllib.request
from itertools import groupby

C = "https://climate-api.open-meteo.com/v1/climate"
MODELS = ["MRI_AGCM3_2_S", "FGOALS_f3_H", "HiRAM_SIT_HR", "MPI_ESM1_2_XR", "NICAM16_8S"]
VARS = ["precipitation_sum", "rain_sum", "snowfall_sum", "cloud_cover_mean",
        "temperature_2m_max"]
SITES = {"Marseille": (43.30, 5.37), "Brest": (48.39, -4.49),
         "Pontarlier": (46.90, 6.35), "Chamonix": (45.92, 6.87),
         # southern hemisphere: 3 July to 1 September is mid-winter there
         "Christchurch": (-43.53, 172.63), "Ushuaia": (-54.80, -68.30)}

def get(lat, lon, start, end, model, tries=4):
    p = {"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
         "daily": VARS, "models": [model], "timezone": "auto"}
    qs = urllib.parse.urlencode(p, doseq=True)
    for i in range(tries):
        try:
            with urllib.request.urlopen(f"{C}?{qs}", timeout=300) as r:
                return json.load(r).get("daily", {})
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(25 * (i + 1)); continue
            print(f"    ! HTTP {e.code}"); return {}
    return {}

def nulls(daily, var):
    vals = daily.get(var) or []
    return [t for t, v in zip(daily.get("time", []), vals) if v is None]

# ---------------------------------------------------------------- (1)
print("(1) Jours nuls par modele, Marseille 2046\n")
print(f"    {'modele':<18}" + "".join(f"{v.split('_')[0]:>13}" for v in VARS))
print("    " + "-" * 83)
for m in MODELS:
    d = get(43.30, 5.37, "2046-01-01", "2046-12-31", m)
    print(f"    {m:<18}" + "".join(f"{len(nulls(d, v)):>13}" for v in VARS))
    time.sleep(10)
print("\n    365 = la variable n'est jamais servie ; 0 = complete.")

# ---------------------------------------------------------------- (2)
print("\n(2) La fenetre manquante est-elle la meme partout ? (MRI_AGCM3_2_S)\n")
print(f"    {'site':<12}{'jours nuls':>12}{'premier':>13}{'dernier':>13}{'plages':>9}")
print("    " + "-" * 61)
for site, (lat, lon) in SITES.items():
    d = get(lat, lon, "2044-01-01", "2048-12-31", "MRI_AGCM3_2_S")
    miss = nulls(d, "snowfall_sum")
    if not miss:
        print(f"    {site:<12}{0:>12}{'—':>13}{'—':>13}{0:>9}")
        time.sleep(10); continue
    idx = [i for i, v in enumerate(d["snowfall_sum"]) if v is None]
    runs = [list(g) for _, g in groupby(enumerate(idx), lambda p: p[1] - p[0])]
    print(f"    {site:<12}{len(miss):>12}{miss[0]:>13}{miss[-1]:>13}{len(runs):>9}")
    print(f"    {'':<12}longueurs des plages : {sorted({len(r) for r in runs})}")
    time.sleep(10)

# ---------------------------------------------------------------- (3)
print("\n(3) Le trou coincide-t-il avec les jours secs ? (Marseille 2046)\n")
d = get(43.30, 5.37, "2046-01-01", "2046-12-31", "MRI_AGCM3_2_S")
rows = list(zip(d["time"], d["precipitation_sum"], d["snowfall_sum"]))
dry = [r for r in rows if r[1] == 0]
gap = [r for r in rows if r[2] is None]
wet_gap = [r for r in gap if r[1] and r[1] > 0]
print(f"    jours secs (0 mm)                 : {len(dry)}")
print(f"    jours sans neige servie           : {len(gap)}")
print(f"    dont jours avec pluie mesuree     : {len(wet_gap)}")
print("\n    Un trou qui recouvre des jours de pluie ne peut pas se lire comme")
print("    « pas de neige ce jour-la ». Et la partie (2) montre qu'il ne peut")
print("    pas non plus se lire comme un artefact d'ete : au sud, il couvre")
print("    l'hiver. D'ou le critere derive des precipitations et de la")
print("    temperature moyenne, applique des deux cotes de la couture.")
