"""Is the DAILY weather_code reproducible by applying Open-Meteo's own rule
to DAILY aggregates? Compare against (a) hourly rule + max aggregation,
recomputed from hourly data, and (b) rule applied to daily means/sums."""
import json, urllib.parse, urllib.request, collections, time

A = "https://archive-api.open-meteo.com/v1/archive"
LAT, LON = 46.90, 6.35
START, END = "2018-01-01", "2019-12-31"

def get(p):
    qs = urllib.parse.urlencode(p, doseq=True)
    with urllib.request.urlopen(f"{A}?{qs}", timeout=180) as r:
        return json.load(r)

def rule(cloud, precip_mm, snow_cm, dt_hours):
    """Open-Meteo WeatherCode.calculate, minus the branches needing CAPE,
    convective precip, visibility and freezing-rain flags (all unavailable)."""
    if cloud is None or precip_mm is None or snow_cm is None:
        return None
    s = snow_cm / dt_hours
    if 0.01 <= s < 0.2: return 71
    if 0.2 <= s < 0.8: return 73
    if s >= 0.8:       return 75
    p = precip_mm / dt_hours
    if 0.01 <= p < 0.5: return 51
    if 0.5 <= p < 1.0:  return 53
    if 1.0 <= p < 1.3:  return 55
    if 1.3 <= p < 2.5:  return 61
    if 2.5 <= p < 7.6:  return 63
    if p >= 7.6:        return 65
    if cloud < 20:  return 0
    if cloud < 50:  return 1
    if cloud < 80:  return 2
    return 3

# ---- daily reference from the API
d = get({"latitude": LAT, "longitude": LON, "start_date": START, "end_date": END,
         "daily": ["weather_code", "cloud_cover_mean", "precipitation_sum",
                   "rain_sum", "snowfall_sum"], "timezone": "GMT"})
print("daily_units:", json.dumps(d["daily_units"]))
dd = d["daily"]
time.sleep(8)

# ---- hourly, to rebuild the code the way Open-Meteo does it
h = get({"latitude": LAT, "longitude": LON, "start_date": START, "end_date": END,
         "hourly": ["weather_code", "cloud_cover", "precipitation", "snowfall"],
         "timezone": "GMT"})
hh = h["hourly"]
print("hourly_units:", json.dumps(h["hourly_units"]))

# ---- (a) rebuild hourly code from hourly inputs -> check the rule itself
ok = tot = 0
for c, p, s, w in zip(hh["cloud_cover"], hh["precipitation"], hh["snowfall"], hh["weather_code"]):
    r = rule(c, p, s, 1.0)
    if r is None or w is None: continue
    tot += 1; ok += (r == w)
print(f"\n(a) hourly rule reproduces hourly weather_code : {100*ok/tot:.1f}%  (n={tot})")

# ---- (b) how is the daily code aggregated from the hourly codes?
by_day = collections.defaultdict(list)
for t, w in zip(hh["time"], hh["weather_code"]):
    if w is not None:
        by_day[t[:10]].append(int(w))
agg = {"max": 0, "mode": 0, "last": 0, "mean": 0}
tot = 0
for day, wc in zip(dd["time"], dd["weather_code"]):
    if wc is None or day not in by_day: continue
    v = by_day[day]; tot += 1
    agg["max"] += (max(v) == wc)
    agg["mode"] += (collections.Counter(v).most_common(1)[0][0] == wc)
    agg["last"] += (v[-1] == wc)
    agg["mean"] += (round(sum(v)/len(v)) == wc)
print(f"\n(b) daily code vs aggregation of hourly codes (n={tot}):")
for k, v in sorted(agg.items(), key=lambda x: -x[1]):
    print(f"      {k:<6} {100*v/tot:5.1f}%")

# ---- (c) the operation we would actually be forced to perform:
#          apply the rule to DAILY aggregates (all the Climate API offers)
res = collections.Counter()
tot = 0
for c, p, s, w in zip(dd["cloud_cover_mean"], dd["precipitation_sum"],
                      dd["snowfall_sum"], dd["weather_code"]):
    if w is None: continue
    tot += 1
    for lbl, dt in [("as 24h rate", 24.0), ("as 1h rate", 1.0)]:
        r = rule(c, p, s, dt)
        res[(lbl, r == w)] += 1
print(f"\n(c) rule applied to DAILY aggregates vs published daily code (n={tot}):")
for lbl in ["as 24h rate", "as 1h rate"]:
    print(f"      {lbl:<12} exact match {100*res[(lbl, True)]/tot:5.1f}%")

# ---- (d) same, but only comparing the coarse family (dry/rain/snow)
def fam(w):
    if w is None: return None
    if w >= 71 and w <= 77 or w in (85, 86): return "neige"
    if w >= 51: return "pluie"
    return "sec"
m = 0; tot = 0
for c, p, s, w in zip(dd["cloud_cover_mean"], dd["precipitation_sum"],
                      dd["snowfall_sum"], dd["weather_code"]):
    if w is None: continue
    tot += 1
    m += (fam(rule(c, p, s, 24.0)) == fam(w))
print(f"\n(d) same, collapsed to sec/pluie/neige : {100*m/tot:.1f}%  (n={tot})")
