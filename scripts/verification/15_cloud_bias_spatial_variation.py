"""How fast does the cloud-cover bias vary in space?
Decides the calibration grid size: if the bias is smooth, a coarse offline
grid suffices; if it jumps between valley and slope, precomputing lies."""
import json, urllib.parse, urllib.request, urllib.error, statistics as st, time, math

A = "https://archive-api.open-meteo.com/v1/archive"
C = "https://climate-api.open-meteo.com/v1/climate"
MODEL = "MRI_AGCM3_2_S"
START, END = "2015-01-01", "2019-12-31"

KM_PER_DEG_LAT = 111.0

def dlat(km):
    return km / KM_PER_DEG_LAT

def dlon(km, lat):
    return km / (KM_PER_DEG_LAT * math.cos(math.radians(lat)))

# transects: anchor + points at 10, 25, 50 km
CLUSTERS = {
    "Jura (relief marque)": [
        ("Pontarlier",  46.90, 6.35),
        ("+10 km N",    46.90 + dlat(10), 6.35),
        ("+25 km N",    46.90 + dlat(25), 6.35),
        ("+50 km N",    46.90 + dlat(50), 6.35),
    ],
    "Plaine toulousaine": [
        ("Toulouse",   43.60, 1.44),
        ("+10 km N",   43.60 + dlat(10), 1.44),
        ("+25 km N",   43.60 + dlat(25), 1.44),
        ("+50 km N",   43.60 + dlat(50), 1.44),
    ],
    "Cote bretonne (vers l'interieur)": [
        ("Brest",      48.39, -4.49),
        ("+10 km E",   48.39, -4.49 + dlon(10, 48.39)),
        ("+25 km E",   48.39, -4.49 + dlon(25, 48.39)),
        ("+50 km E",   48.39, -4.49 + dlon(50, 48.39)),
    ],
    "Vallee alpine (5 km, fort denivele)": [
        ("Chamonix fond", 45.92, 6.87),
        ("~5 km SE",      45.88, 6.92),
        ("~10 km S",      45.83, 6.87),
    ],
}

def get(url, p, tries=4):
    qs = urllib.parse.urlencode(p, doseq=True)
    for i in range(tries):
        try:
            with urllib.request.urlopen(f"{url}?{qs}", timeout=240) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(25 * (i + 1)); continue
            print(f"      ! HTTP {e.code}"); return {}
    return {}

def bias(lat, lon):
    p = {"latitude": lat, "longitude": lon, "start_date": START, "end_date": END,
         "daily": ["cloud_cover_mean"], "timezone": "GMT"}
    o = get(A, {**p, "models": ["era5"]}); time.sleep(9)
    m = get(C, {**p, "models": [MODEL]}); time.sleep(9)
    od = o.get("daily", {}).get("cloud_cover_mean")
    md = m.get("daily", {}).get("cloud_cover_mean")
    if not od or not md:
        return None, None, None
    pairs = [(a, b) for a, b in zip(od, md) if a is not None and b is not None]
    mo = st.mean([a for a, _ in pairs]); mm = st.mean([b for _, b in pairs])
    return mm - mo, o.get("elevation"), len(pairs)

print(f"Biais de nebulosite (modele - ERA5), {START}..{END}\n")
for cluster, pts in CLUSTERS.items():
    print(f"  {cluster}")
    print(f"    {'point':<16}{'alt':>7}{'biais':>9}{'ecart/ancre':>13}")
    ref = None
    for name, lat, lon in pts:
        b, elev, n = bias(lat, lon)
        if b is None:
            print(f"    {name:<16}  donnees manquantes"); continue
        if ref is None:
            ref = b
            print(f"    {name:<16}{elev:>7.0f}{b:>+9.2f}{'(ancre)':>13}")
        else:
            print(f"    {name:<16}{elev:>7.0f}{b:>+9.2f}{b - ref:>+13.2f}")
    print()
