"""Is the joint consistency between cloud cover and precipitation preserved
in the bias-corrected CMIP6 output? Compare against ERA5 over a full year."""
import json, urllib.parse, urllib.request, statistics as st

LAT, LON = 46.90, 6.35
CLIMATE = "https://climate-api.open-meteo.com/v1/climate"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
D = ["cloud_cover_mean", "precipitation_sum"]

def get(url, params):
    qs = urllib.parse.urlencode(params, doseq=True)
    with urllib.request.urlopen(f"{url}?{qs}", timeout=120) as r:
        return json.load(r)

def corr(x, y):
    n = len(x); mx, my = st.mean(x), st.mean(y)
    num = sum((a-mx)*(b-my) for a, b in zip(x, y))
    den = (sum((a-mx)**2 for a in x) * sum((b-my)**2 for b in y)) ** 0.5
    return num/den if den else float("nan")

def report(label, js):
    d = js["daily"]
    pairs = [(c, p) for c, p in zip(d["cloud_cover_mean"], d["precipitation_sum"])
             if c is not None and p is not None]
    cc = [c for c, _ in pairs]; pr = [p for _, p in pairs]
    wet = [(c, p) for c, p in pairs if p >= 1.0]
    dry = [(c, p) for c, p in pairs if p < 0.1]
    wet_clear = [1 for c, p in wet if c < 30]
    print(f"\n{label}  (n={len(pairs)})")
    print(f"  corr(cloud_cover, precip)      = {corr(cc, pr):+.3f}")
    print(f"  mean cloud cover, wet days     = {st.mean([c for c,_ in wet]):.1f}%  (n={len(wet)})")
    print(f"  mean cloud cover, dry days     = {st.mean([c for c,_ in dry]):.1f}%  (n={len(dry)})")
    print(f"  wet days (>=1mm) with cc <30%  = {len(wet_clear)}/{len(wet)} "
          f"({100*len(wet_clear)/max(len(wet),1):.1f}%)")

report("ERA5 archive 2015 (observed)", get(ARCHIVE, {
    "latitude": LAT, "longitude": LON, "start_date": "2015-01-01",
    "end_date": "2015-12-31", "daily": D, "timezone": "Europe/Paris"}))

for m in ["MRI_AGCM3_2_S", "EC_Earth3P_HR", "CMCC_CM2_VHR4"]:
    report(f"CMIP6 {m} 2045", get(CLIMATE, {
        "latitude": LAT, "longitude": LON, "start_date": "2045-01-01",
        "end_date": "2045-12-31", "models": [m], "daily": D,
        "timezone": "Europe/Paris"}))

# same models over a HISTORICAL year, to separate model artefact from future drift
for m in ["MRI_AGCM3_2_S"]:
    report(f"CMIP6 {m} 2015 (hindcast, comparable to ERA5 above)", get(CLIMATE, {
        "latitude": LAT, "longitude": LON, "start_date": "2015-01-01",
        "end_date": "2015-12-31", "models": [m], "daily": D,
        "timezone": "Europe/Paris"}))
