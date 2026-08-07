"""Facts underpinning docs/application.md (site specification):

  (A) payload sizes — a 90-day range is ~4 KB, so client-side fetching is
      not about bandwidth; it is about Open-Meteo's per-IP rate limit;
  (B) Open-Meteo exposes its own geocoding API, which Nominatim's usage
      policy makes necessary for any high-traffic site;
  (C) calibration cost per grid node, and per-call latency, which set the
      duration of the offline grid build;
  (D) the AWS Open Data mirror carries ERA5 but NOT the CMIP6 climate
      projections — so only half the calibration can be offloaded to it.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

A = "https://archive-api.open-meteo.com/v1/archive"
C = "https://climate-api.open-meteo.com/v1/climate"
G = "https://geocoding-api.open-meteo.com/v1/search"
S3 = "https://openmeteo.s3.us-west-2.amazonaws.com/"
MODEL = "MRI_AGCM3_2_S"
VARS = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum",
        "snowfall_sum", "cloud_cover_mean", "wind_speed_10m_max"]


def call(url, params):
    qs = urllib.parse.urlencode(params, doseq=True)
    t0 = time.time()
    try:
        with urllib.request.urlopen(f"{url}?{qs}", timeout=300) as r:
            body = r.read()
            return r.status, len(body), time.time() - t0, body
    except urllib.error.HTTPError as e:
        return e.code, 0, time.time() - t0, b"{}"


print("(A) Payload for a 90-day range, six variables")
s, n, d, _ = call(A, {"latitude": 46.90, "longitude": 6.35,
                      "start_date": "2015-01-01", "end_date": "2015-03-31",
                      "daily": VARS, "timezone": "Europe/Paris",
                      "models": ["era5"]})
print(f"    archive : {n / 1024:6.1f} KB  ({d:.2f} s, HTTP {s})")
time.sleep(4)
s, n, d, _ = call(C, {"latitude": 46.90, "longitude": 6.35,
                      "start_date": "2045-01-01", "end_date": "2045-03-31",
                      "daily": VARS, "models": [MODEL],
                      "timezone": "Europe/Paris"})
print(f"    climate : {n / 1024:6.1f} KB  ({d:.2f} s, HTTP {s})")
print("    -> bandwidth is a non-issue; the per-IP rate limit is the reason\n")

print("(B) Open-Meteo geocoding, as a Nominatim replacement")
s, n, d, body = call(G, {"name": "Pontarlier", "count": 3,
                         "language": "fr", "format": "json"})
for r in json.loads(body).get("results", [])[:3]:
    print(f"    {r['name']:<24} {r.get('admin1', ''):<16} "
          f"lat={r['latitude']:.3f} lon={r['longitude']:.3f} "
          f"alt={r.get('elevation')}")
time.sleep(4)

print("\n(C) Calibration cost per grid node — 45 years, cloud cover only")
total = 0.0
for lat, lon in [(43.60, 1.44), (46.90, 6.35)]:
    p = {"latitude": lat, "longitude": lon, "start_date": "1980-01-01",
         "end_date": "2024-12-31", "daily": ["cloud_cover_mean"],
         "timezone": "GMT"}
    s, n, d, _ = call(C, {**p, "models": [MODEL]})
    print(f"    climate : {n / 1024:6.1f} KB  {d:.2f} s")
    total += d
    time.sleep(4)
    s, n, d, _ = call(A, {**p, "models": ["era5"]})
    print(f"    archive : {n / 1024:6.1f} KB  {d:.2f} s")
    total += d
    time.sleep(4)
print(f"    -> ~{total / 4:.2f} s per call; two calls per node")
print("    0.5deg land grid, Antarctica excluded: ~65 000 nodes -> ~130 000 calls")

print("\n(D) Does the AWS mirror carry the CMIP6 projections?")
try:
    with urllib.request.urlopen(
            f"{S3}?list-type=2&delimiter=/&prefix=data/", timeout=120) as r:
        import re
        prefixes = re.findall(r"<Prefix>([^<]+)</Prefix>", r.read().decode())
    era5 = [p for p in prefixes if "era5" in p.lower()]
    cmip = [p for p in prefixes if any(k in p.lower() for k in
            ("cmip", "climate", "mri_", "cmcc", "fgoals", "hiram", "nicam"))]
    print(f"    datasets listed : {len(prefixes)}")
    print(f"    ERA5 family     : {era5}")
    print(f"    CMIP6 / climate : {cmip or 'NONE'}")
    print("    -> ERA5 can be bulk-downloaded; the model hindcast cannot.")
except Exception as e:  # noqa: BLE001 - diagnostic script
    print(f"    listing failed: {e}")
