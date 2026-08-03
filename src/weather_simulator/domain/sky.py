"""The sky class: one day of numbers turned into one of five words.

**One function, called three times.** That is the whole point of this module,
and it is a requirement of section 3 of the design document rather than a
stylistic preference. The old past, the recent past and the future must be
classified by the same code path, or the seam the whole of ``sources`` works to
erase would reappear here, one branch at a time. The earlier prototype held this
logic twice, once in JavaScript and once in Python, and they drifted.

The tree reads daily aggregates and nothing else. Not because more would not
help — it would — but because the climate model serves nothing else. The Climate
API accepts ``hourly`` and answers HTTP 200 with no hourly block at all, the
same silent absence it gives for ``weather_code``. Anything richer would exist
on one side of the seam only.

What the classes are worth is measured, and the measurement is what fixes the
thresholds — see ``scripts/sky_thresholds/``. On the days each class captures,
the light actually reaching the ground is around 90 %, 80 % and 60 % of what a
clear sky would deliver. Three clear steps, in the right order at all ten sites
tested.

What no threshold can fix is that a daily mean hides the shape of the day. A
morning under cloud followed by a radiant afternoon carries the same number as
an evenly grey day, and at equal cloud cover the light received spreads by 20 to
49 points. The pictogram is therefore the least certain thing on the card: the
temperatures and the millimetres describe that day, the icon describes the kind
of day. That is the same trade section 3 already accepted in refusing any
intensity grading for rain.
"""

from __future__ import annotations

from enum import StrEnum

from weather_simulator.domain import thresholds
from weather_simulator.domain.records import DailyRecord


class SkyClass(StrEnum):
    """The five classes. Carried through the JSON contract; the pictogram is not.

    Section 4 keeps the emoji on the display side alone, so that moving to a
    drawn icon set later touches nothing but the rendering.
    """

    CLEAR = "clear"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    RAIN = "rain"
    SNOW = "snow"


def classify(
    precipitation: float | None,
    temperature_mean: float | None,
    cloud_cover: float | None,
) -> SkyClass | None:
    """The class of one day, or ``None`` when the day cannot be classified.

    ``None`` is returned rather than a guess. A missing value is a gap in the
    data, and substituting a class for it would be a data-treatment decision
    made in passing — precisely what section 1 reserves for validation.

    The wet gate is crossed first, and rules 1 and 2 share it, so they partition
    the same set of days rather than overlap: among wet days, the temperature
    decides the phase. Snow *depth* deliberately plays no part, though it was
    the original basis. The climate model serves it in patches that are neither
    seasonal nor regular — none of the five eligible models serves it at the
    tropical sites, and half a year is missing at Christchurch — while the
    reanalyses serve it faithfully. Reading it on one side only would move the
    seam instead of removing it.
    """
    if precipitation is None:
        return None

    if precipitation >= thresholds.PRECIPITATION_MM:
        if temperature_mean is None:
            return None
        if temperature_mean < thresholds.SNOW_TEMPERATURE_C:
            return SkyClass.SNOW
        return SkyClass.RAIN

    if cloud_cover is None:
        return None
    if cloud_cover >= thresholds.OVERCAST_PERCENT:
        return SkyClass.OVERCAST
    if cloud_cover >= thresholds.CLOUDY_PERCENT:
        return SkyClass.CLOUDY
    return SkyClass.CLEAR


def classify_record(record: DailyRecord) -> SkyClass | None:
    """The same rule, applied to a day of the assembled series."""
    return classify(record.precipitation, record.temperature_mean, record.cloud_cover)
