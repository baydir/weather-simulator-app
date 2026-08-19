"""Open-Meteo access and assembly of the homogeneous 1950-2050 series.

This package is the tool the design document calls for at step 1: it retrieves
the two regimes and joins them into a single daily series, so that the model
comparison of step 2 and the threshold calibration of step 3 have something to
work on.

On the request path the browser does the fetching — Open-Meteo rate-limits per
IP address, so a server that fetched on behalf of every visitor would
concentrate all the traffic on one address. What lives here is what both sides
share: how to spell a request, how to read an answer, where the seams fall.

**Which requests a range needs, and running them, is** :mod:`api.plan`. It sits
above this package rather than in it, because it is the one piece both the
browser and a script go through — and it went through neither for as long as
there were two of it. :mod:`client` is the offline half, and only a script
reaches it.
"""

from weather_simulator.sources.errors import (
    CoverageError,
    FetchError,
    MissingVariableError,
    SourceError,
)
from weather_simulator.sources.series import build_series, split_range

__all__ = [
    "CoverageError",
    "FetchError",
    "MissingVariableError",
    "SourceError",
    "build_series",
    "split_range",
]
