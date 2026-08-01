"""Throwaway: verify the factual claims the docs will rest on."""
import json
import urllib.parse
import urllib.request

LAT, LON = 46.90, 6.35  # Pontarlier, the README's example location
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
CLIMATE = "https://climate-api.open-meteo.com/v1/climate"

MODELS = ["CMCC_CM2_VHR4", "FGOALS_f3_H", "HiRAM_SIT_HR", "MRI_AGCM3_2_S",
          "EC_Earth3P_HR", "MPI_ESM1_2_XR", "NICAM16_8S"]


def get(url, params):
    qs = urllib.parse.urlencode(params, doseq=True)
    try:
        with urllib.request.urlopen(f"{url}?{qs}", timeout=60) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


print("=" * 70)
print("CLAIM 1: Historical API exposes weather_code")
status, js = get(ARCHIVE, {
    "latitude": LAT, "longitude": LON,
    "start_date": "2020-06-01", "end_date": "2020-06-05",
    "daily": ["weather_code", "cloud_cover_mean", "temperature_2m_max",
              "precipitation_sum", "rain_sum", "snowfall_sum"],
    "timezone": "Europe/Paris",
})
print(f"  HTTP {status}")
print(f"  daily keys: {list(js.get('daily', {}).keys())}")
print(f"  weather_code values: {js.get('daily', {}).get('weather_code')}")

print("=" * 70)
print("CLAIM 2: Climate API does NOT expose weather_code")
status, js = get(CLIMATE, {
    "latitude": LAT, "longitude": LON,
    "start_date": "2045-06-01", "end_date": "2045-06-05",
    "models": ["MRI_AGCM3_2_S"], "daily": ["weather_code"],
    "timezone": "Europe/Paris",
})
print(f"  HTTP {status} -> {js.get('reason', list(js.keys()))}")

print("=" * 70)
print("CLAIM 3: Climate API DOES expose cloud_cover_mean + precip family")
status, js = get(CLIMATE, {
    "latitude": LAT, "longitude": LON,
    "start_date": "2045-06-01", "end_date": "2045-06-03",
    "models": ["MRI_AGCM3_2_S"],
    "daily": ["cloud_cover_mean", "precipitation_sum", "rain_sum",
              "snowfall_sum", "temperature_2m_max", "temperature_2m_min",
              "relative_humidity_2m_mean", "wind_speed_10m_mean",
              "shortwave_radiation_sum"],
    "timezone": "Europe/Paris",
})
print(f"  HTTP {status}")
print(f"  daily keys: {list(js.get('daily', {}).keys())}")

print("=" * 70)
print("CLAIM 4: upper bound of the Climate API")
for end in ["2049-12-31", "2050-01-01", "2050-06-30", "2050-12-31"]:
    status, js = get(CLIMATE, {
        "latitude": LAT, "longitude": LON,
        "start_date": "2049-12-25", "end_date": end,
        "models": ["MRI_AGCM3_2_S"], "daily": ["temperature_2m_max"],
        "timezone": "Europe/Paris",
    })
    if status == 200:
        t = js["daily"]["time"]
        print(f"  end={end}: HTTP 200, last date returned = {t[-1]} ({len(t)} days)")
    else:
        print(f"  end={end}: HTTP {status} -> {js.get('reason')}")

print("=" * 70)
print("CLAIM 5: all 7 model names are accepted")
for m in MODELS:
    status, js = get(CLIMATE, {
        "latitude": LAT, "longitude": LON,
        "start_date": "2040-07-01", "end_date": "2040-07-02",
        "models": [m], "daily": ["temperature_2m_max"],
        "timezone": "Europe/Paris",
    })
    keys = list(js.get("daily", {}).keys()) if status == 200 else js.get("reason")
    print(f"  {m:<16} HTTP {status}  {keys}")

print("=" * 70)
print("CLAIM 6: Historical API earliest date (ERA5 from 1940, 1950 usable)")
for start in ["1940-01-01", "1950-01-01"]:
    status, js = get(ARCHIVE, {
        "latitude": LAT, "longitude": LON,
        "start_date": start, "end_date": start,
        "daily": ["weather_code", "temperature_2m_max"],
        "timezone": "Europe/Paris",
    })
    print(f"  start={start}: HTTP {status} -> "
          f"{js.get('daily') if status == 200 else js.get('reason')}")
