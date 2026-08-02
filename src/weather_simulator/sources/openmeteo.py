"""What to ask Open-Meteo, and under which name each answer comes back.

Three requests, never fewer. The past needs two because the source is chosen
*per variable*: ERA5-Land serves temperature and nothing else — every other
variable comes back null — while ERA5 serves the rest at a coarser 25 km. The
future needs one, all variables from a single model.

Forcing ``models`` explicitly is never optional. Left to itself the archive
endpoint picks its own source per variable and switches to ECMWF IFS in 2017,
which plants a second, undocumented seam inside the past, worth -1.8 to +0.9 °C
depending on site, season and hour. A constant offset could be corrected; that
one cannot.
"""

from __future__ import annotations

from datetime import date

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
CLIMATE_URL = "https://climate-api.open-meteo.com/v1/climate"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Models covering 1950-2050 with cloud cover. CMCC_CM2_VHR4 (no cloud cover at
# all) and EC_Earth3P_HR (stops before 2050) are excluded for lack of data, not
# by preference. MRI_AGCM3_2_S is provisional, pending step 2: nothing may
# hard-code it.
ELIGIBLE_MODELS = (
    "MRI_AGCM3_2_S",
    "FGOALS_f3_H",
    "HiRAM_SIT_HR",
    "MPI_ESM1_2_XR",
    "NICAM16_8S",
)
DEFAULT_MODEL = "MRI_AGCM3_2_S"

# The day boundary. Both APIs honour this parameter and re-aggregate
# accordingly — measured at Singapore, where GMT and local time are eight hours
# apart and the daily series shifts by a full day between the two. So the choice
# is free, but it must be the same everywhere: a seam holds only as long as both
# sides are cut on the same hour, and the correction grid of step 4 must be built
# under this same setting.
#
# Local days, because the application shows a weather bulletin: a daily maximum
# spanning 09:00 to 09:00 local, as GMT would give in Tokyo, means nothing to a
# reader. The cost is that a daylight-saving day is 23 or 25 hours long, which is
# what the reader actually lived through.
DEFAULT_TIMEZONE = "auto"

COVERAGE_START = date(1950, 1, 1)
COVERAGE_END = date(2050, 12, 31)

# Open-Meteo variable name -> DailyRecord field.
#
# The daily mean is carried alongside the extremes because the snow criterion
# rests on it: the climate model serves snowfall irregularly, so precipitation
# phase is settled from precipitation and temperature instead — the same way on
# both regimes, since a rule applied on one side only would move the seam rather
# than remove it. All four sources serve the mean, ERA5-Land included.
#
# rain_sum is not requested: nothing uses it, and it carries the same gaps as
# snowfall.
TEMPERATURE_VARIABLES = {
    "temperature_2m_max": "temperature_max",
    "temperature_2m_min": "temperature_min",
    "temperature_2m_mean": "temperature_mean",
}
SURFACE_VARIABLES = {
    "precipitation_sum": "precipitation",
    "snowfall_sum": "snowfall",
    "cloud_cover_mean": "cloud_cover",
    "wind_speed_10m_max": "wind_speed_max",
    "wind_speed_10m_mean": "wind_speed_mean",
}
ALL_VARIABLES = {**TEMPERATURE_VARIABLES, **SURFACE_VARIABLES}

# Snowfall is kept — the reanalyses serve it faithfully, and step 3 needs that
# record to calibrate the derived criterion against. But nothing depends on it
# any more, so its absence is no longer fatal: the climate model leaves holes in
# it that are neither seasonal nor regular, from 61 scattered days at Marseille
# to half a year at Christchurch, winter included.
OPTIONAL_VARIABLES = frozenset({"snowfall_sum"})

TEMPERATURE_MODEL = "era5_land"  # ~11 km, temperature only
SURFACE_MODEL = "era5"  # ~25 km, everything else

# The reanalyses run five to six days behind — a documented latency, not an
# outage. ECMWF's operational analysis has none, and serves all eight variables
# in one request, so it covers the tail they leave open.
#
# It covers 2017 onwards only, and it is deliberately *not* used before that:
# it is the more accurate instrument on any given day, but it changes version
# once or twice a year, so its series is the less homogeneous of the two. The
# past stays on the reanalyses for as long as they reach, and the handover is
# placed wherever they actually stop — never on a hard-coded number of days.
RECENT_MODEL = "ecmwf_ifs"  # ~9 km, 2017 -> today, no latency
RECENT_START = date(2017, 1, 1)


def _params(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    variables: dict[str, str],
    model: str,
    timezone: str,
) -> dict[str, object]:
    return {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": list(variables),
        "models": [model],
        "timezone": timezone,
    }


def archive_temperature_request(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    timezone: str = DEFAULT_TIMEZONE,
) -> tuple[str, dict[str, object]]:
    """Past temperatures, forced onto ERA5-Land.

    The projections were calibrated against ERA5-Land, which is why this is
    also the right choice for the seam: the model sits within +0.02 to +0.20 °C
    of it, against -0.75 to +0.43 °C of plain ERA5.
    """
    return ARCHIVE_URL, _params(
        latitude, longitude, start, end, TEMPERATURE_VARIABLES, TEMPERATURE_MODEL, timezone
    )


def archive_surface_request(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    timezone: str = DEFAULT_TIMEZONE,
) -> tuple[str, dict[str, object]]:
    """Past precipitation, snow, cloud cover and wind, forced onto ERA5."""
    return ARCHIVE_URL, _params(
        latitude, longitude, start, end, SURFACE_VARIABLES, SURFACE_MODEL, timezone
    )


def archive_recent_request(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    timezone: str = DEFAULT_TIMEZONE,
) -> tuple[str, dict[str, object]]:
    """The days the reanalyses have not caught up with, from ECMWF IFS.

    One request for all eight variables — unlike the reanalyses, IFS serves
    every one of them.
    """
    return ARCHIVE_URL, _params(
        latitude, longitude, start, end, ALL_VARIABLES, RECENT_MODEL, timezone
    )


def climate_request(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    model: str = DEFAULT_MODEL,
    timezone: str = DEFAULT_TIMEZONE,
) -> tuple[str, dict[str, object]]:
    """The future, all variables from one model.

    The API takes a single model at a time here, deliberately: mixing outputs
    would break the homogeneity the whole design rests on.
    """
    return CLIMATE_URL, _params(latitude, longitude, start, end, ALL_VARIABLES, model, timezone)
