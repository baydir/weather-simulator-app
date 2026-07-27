"""
Processing layer for the web app: takes raw JSON already fetched by the
client (browser) from the Open-Meteo APIs, and turns it into a clean,
homogeneous DataFrame — mirroring the logic in get_meteo.py, but without
making any HTTP calls itself.
"""
import pandas as pd

VARIABLES = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"]


def parse_archive(raw_json):
    """
    Raw JSON from the archive (ERA5) API -> DataFrame indexed by date.
    Mirrors the parsing done in get_meteo_passe, without the HTTP call.
    """
    daily = raw_json["daily"]
    df = pd.DataFrame(daily)
    df["time"] = pd.to_datetime(df["time"])
    return df.set_index("time").rename_axis("date")


def parse_climate(raw_json, model):
    """
    Raw JSON from the climate (CMIP6) API -> DataFrame indexed by date.
    Mirrors the parsing done in get_meteo_projete, without the HTTP call.
    """
    daily = raw_json["daily"]
    dates = pd.to_datetime(daily["time"])
    data = {}
    for var in VARIABLES:
        key = f"{var}_{model}" if f"{var}_{model}" in daily else var
        data[var] = daily[key]
    return pd.DataFrame(data, index=dates).rename_axis("date")


def combine(raw_archive, raw_climate, model):
    """
    Assembles both pieces (one may be missing if the requested date range
    only covered a single period, past or future).
    """
    pieces = []
    if raw_archive is not None:
        pieces.append(parse_archive(raw_archive))
    if raw_climate is not None:
        pieces.append(parse_climate(raw_climate, model))
    if not pieces:
        raise ValueError("No data received.")
    return pd.concat(pieces).sort_index()


def transform_data(df):
    """
    The customizable processing block: currently a no-op.
    Any future transformation (smoothing, thresholds, etc.) goes here,
    without touching the rest of the pipeline.
    """
    return df
