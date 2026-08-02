"""Open-Meteo access and assembly of the homogeneous 1950-2050 series.

This package is the tool the design document calls for at step 1: it retrieves
the two regimes and joins them into a single daily series, so that the model
comparison of step 2 and the threshold calibration of step 3 have something to
work on.

It is *offline* tooling. On the request path the browser does the fetching —
Open-Meteo rate-limits per IP address, so a server that fetched on behalf of
every visitor would concentrate all the traffic on one address. Only the
parsing and assembly here are shared with the server; :mod:`client` is not.
"""

from weather_simulator.sources.errors import (
    CoverageError,
    FetchError,
    MissingVariableError,
    SourceError,
)
from weather_simulator.sources.series import build_series, fetch_series, split_range

__all__ = [
    "CoverageError",
    "FetchError",
    "MissingVariableError",
    "SourceError",
    "build_series",
    "fetch_series",
    "split_range",
]
