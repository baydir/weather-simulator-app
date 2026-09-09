"""The daily record: the single vocabulary shared by every layer.

One record is one day, whatever its origin. The three origins differ by the
``origin`` field alone — never by which fields carry a value, never by how a
value was computed. That is the whole point of the homogeneity rule in
CLAUDE.md: a quantity available on one side only would produce a step at the
seam, so it is dropped rather than exploited. All four sources serve the same
nine variables, which is what makes a single record type possible at all.

The ninth is the dew point, and it is the only one added after the fact. It
came in for the wet bulb, which Open-Meteo itself serves on three segments of
four and leaves null on the climate model — so the rule above sent it back to be
rebuilt from ingredients all four sources do carry.

Units follow Open-Meteo and are *not* normalised here:

- temperatures      degrees Celsius
- precipitation     millimetres
- rain              millimetres
- snowfall          **centimetres** — the classic mistake, and the sky-class
                    snow threshold is expressed in centimetres for that reason
- cloud cover       percent
- wind speed        kilometres per hour
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class Origin(StrEnum):
    """Where a day comes from — what happened, what is forecast, what is modelled.

    Three origins, still two seams. ``FORECAST`` is not a third kind of series
    sitting between the other two: it is the tail of the same ECMWF IFS run that
    serves the recent past, carried forward as far as it reaches. What separates
    it from ``OBSERVED`` is not the instrument but the tense — those days have
    not happened yet.

    The distinction is not cosmetic, and both consumers turn on it. The
    correction of step 4 applies to ``SIMULATED`` alone: IFS needs no debiasing,
    being an observation carried forward rather than a climate run. And the
    interface must warn on simulated days without warning on forecast ones,
    which it cannot do without being told which is which.
    """

    OBSERVED = "observed"
    FORECAST = "forecast"
    SIMULATED = "simulated"


@dataclass(frozen=True, slots=True)
class DailyRecord:
    """One day of the homogeneous series.

    Every measured field is optional: a source may legitimately return null for
    a given day, and silently substituting a value would be a data-treatment
    decision, not an implementation detail. Gaps are carried as ``None`` and
    left for the caller to face.
    """

    date: date
    origin: Origin
    # Which dataset actually served the day. ``origin`` is what the interface
    # needs — a simulated day must be flagged as such. This is for diagnosis:
    # without it the handover from the reanalyses to IFS is invisible, and
    # docs/regles.md requires that seam to be inspectable.
    source: str | None = None
    temperature_min: float | None = None
    temperature_max: float | None = None
    temperature_mean: float | None = None
    # Requested for the wet bulb and read by nothing else. A temperature, so
    # ERA5-Land serves it in the old past alongside the other three rather than
    # ERA5 at 25 km — which is what keeps the two inputs of one derived quantity
    # inside one physical system, an asymmetry the snow criterion has to live
    # with and this one does not.
    dew_point_mean: float | None = None
    precipitation: float | None = None
    # Served faithfully by the reanalyses, irregularly by the climate model.
    # Kept as the yardstick the derived snow criterion is calibrated against,
    # never as what the sky class reads.
    snowfall: float | None = None
    cloud_cover: float | None = None
    wind_speed_max: float | None = None
    wind_speed_mean: float | None = None
