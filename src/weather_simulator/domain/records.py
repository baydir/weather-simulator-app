"""The daily record: the single vocabulary shared by every layer.

One record is one day, whatever its origin. Past and future differ by the
``origin`` field alone — never by which fields carry a value, never by how a
value was computed. That is the whole point of section 3 of the design
document: a quantity available on one side only would produce a step at the
seam, so it is dropped rather than exploited.

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
    """Where a day comes from — reanalysis or climate model.

    Carried through to the JSON contract: the interface must warn on any
    simulated day, and cannot do so without knowing which days those are.
    """

    OBSERVED = "observed"
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
    # section 3 requires that seam to be inspectable.
    source: str | None = None
    temperature_min: float | None = None
    temperature_max: float | None = None
    temperature_mean: float | None = None
    precipitation: float | None = None
    # Served faithfully by the reanalyses, irregularly by the climate model.
    # Kept as the yardstick the derived snow criterion is calibrated against,
    # never as what the sky class reads.
    snowfall: float | None = None
    cloud_cover: float | None = None
    wind_speed_max: float | None = None
    wind_speed_mean: float | None = None
