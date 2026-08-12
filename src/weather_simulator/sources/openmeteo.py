"""What to ask Open-Meteo, and under which name each answer comes back.

Five ways to ask, and a range meets at most all of them. The old past needs two
because the source is chosen *per variable*: ERA5-Land serves temperature and
nothing else — every other variable comes back null — while ERA5 serves the rest
at a coarser 25 km. The recent past, the fortnight ahead and the far future need
one each, all variables from a single model.

The middle three are worth reading together: ECMWF IFS serves the days the
reanalyses have not caught up with *and* the days that have not happened yet.
Same system on both sides of today, which is why the series does not gain a seam
there — it gains one at the end of the forecast instead, where the climate model
takes over.

Forcing ``models`` explicitly is never optional. Left to itself the archive
endpoint picks its own source per variable and switches to ECMWF IFS in 2017,
which plants a second, undocumented seam inside the past, worth -1.8 to +0.9 °C
depending on site, season and hour. A constant offset could be corrected; that
one cannot.
"""

from __future__ import annotations

import urllib.parse
from datetime import date

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CLIMATE_URL = "https://climate-api.open-meteo.com/v1/climate"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

# Models covering 1950-2050 with cloud cover. CMCC_CM2_VHR4 (no cloud cover at
# all) and EC_Earth3P_HR (stops before 2050) are excluded for lack of data, not
# by preference.
ELIGIBLE_MODELS = (
    "MRI_AGCM3_2_S",
    "FGOALS_f3_H",
    "HiRAM_SIT_HR",
    "MPI_ESM1_2_XR",
    "NICAM16_8S",
)

# Settled at step 2 over 1979-2014, ten sites, fifteen measures — see
# scripts/model_selection/. Not for leading on average: the other four are
# indistinguishable from each other and from chance. For having no site where it
# fails. It ranks first or second at eight sites of ten and last at none, while
# each of the others collapses somewhere — NICAM16_8S at Singapore, MPI_ESM1_2_XR
# at Reykjavik, FGOALS_f3_H at Singapore, HiRAM_SIT_HR at Chamonix. An
# application answering anywhere on Earth needs the absence of a hole, not a good
# average.
#
# Still a default and not a constant: the comparison rests on ten sites, and a
# wider sample must be able to overturn it without touching anything but this
# line.
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

# The same forecasting system carried past today, which is the only reason this
# segment exists at all: a climate model is not initialised on the state of the
# atmosphere, so its first simulated day is as unrelated to tomorrow's weather as
# its last one is to 2050. Fourteen days of IFS put real weather where a reader
# can still check it, and move the seam to where they cannot.
#
# 0.25 degrees here against ~9 km on the archive, because that is the finest
# resolution ECMWF distributes in forecast mode — the archive's is an analysis,
# which is a different product. That step is the price of the segment, and it is
# small: measured at Toulouse over ten common days, the two sides sit 0.53 °C and
# 3.4 points of cloud apart on average. The undocumented archive seam that
# forcing ``models`` exists to prevent is worth -1.8 to +0.9 °C, and the climate
# model's cloud deficit, which justifies the whole correction grid, 8 to 11
# points. This is the smallest junction in the series.
FORECAST_MODEL = "ecmwf_ifs025"  # ~25 km, today -> today + FORECAST_DAYS

# How far past today the forecast is asked for. A policy choice, not a property
# of the data: skill decays continuously and nothing in the payload announces
# where it stops being worth serving. Fourteen days is where the project owner
# put the line, beyond which reliability is poor whatever one does.
#
# It bounds the *request*. Where the seam actually lands is read from the days
# IFS returned, never from this number — see plan.py, which asks the climate
# model in overlap and lets series.resume_after settle it.
FORECAST_DAYS = 14


def encode(url: str, params: dict[str, object]) -> str:
    """The request as it goes on the wire, query included.

    One spelling for two callers that must not diverge: the offline client
    fetches this, and the API hands the very same string to the browser to
    fetch on its own. ``doseq`` is what turns the ``daily`` and ``models`` lists
    into repeated keys, which is the form both endpoints expect.
    """
    return f"{url}?{urllib.parse.urlencode(params, doseq=True)}"


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


def forecast_request(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    timezone: str = DEFAULT_TIMEZONE,
) -> tuple[str, dict[str, object]]:
    """The days ahead, from the same forecasting system that served the last ones.

    One request for all eight variables, like IFS on the archive side. The
    endpoint accepts ``start_date``/``end_date`` as the other two do, so this
    builds on the same :func:`_params` — one spelling of a request for the whole
    project, and no place for a fourth to drift.
    """
    return FORECAST_URL, _params(
        latitude, longitude, start, end, ALL_VARIABLES, FORECAST_MODEL, timezone
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
