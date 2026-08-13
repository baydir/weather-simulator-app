"""The temperature band: one degree reading turned into one of nine steps.

**One function, called twice a day** — once for the maximum, once for the
minimum. The same reasoning as the sky class, and the same requirement: the
observed, the forecast and the simulated days must be binned by the same code
path, or the seam that all of ``sources`` works to erase would reappear here.
A band is a rule a displayed quantity depends on, so it is settled in Python and
travels in the contract; the colours themselves stay in the stylesheet, exactly
as the pictogram stays out of the JSON.

**The two temperatures share one scale**, and that is what makes the two numbers
on a card comparable — 12 °C is the same colour whether it is a maximum or a
minimum. It also sends the minimum permanently into the cold half: over
1981-2010, a French daily minimum is below 15 °C on nine days in ten. That is a
fact about nights, not a fault in the scale.

Where the boundaries come from, and why they are five degrees apart, is written
where they are: ``thresholds.TEMPERATURE_BAND_EDGES``.
"""

from __future__ import annotations

from weather_simulator.domain import thresholds
from weather_simulator.domain.records import DailyRecord

# The number of bands the edges cut the line into: one below the first edge, one
# above the last, and one between each pair.
BAND_COUNT = len(thresholds.TEMPERATURE_BAND_EDGES) + 1


def band(temperature: float | None) -> int | None:
    """Which of the nine bands a temperature falls in, or ``None`` for a gap.

    Band 0 is everything below the first edge and band 8 everything at or above
    the last. A value sitting exactly on an edge falls in the warmer of the two
    bands, the same convention the cloud thresholds use.

    ``None`` rather than a guess, as everywhere else here: a missing temperature
    is a hole in the data, and giving it a colour would be inventing one.
    """
    if temperature is None:
        return None
    for index, edge in enumerate(thresholds.TEMPERATURE_BAND_EDGES):
        if temperature < edge:
            return index
    return len(thresholds.TEMPERATURE_BAND_EDGES)


def bands_of(record: DailyRecord) -> tuple[int | None, int | None]:
    """The two bands of one day of the assembled series, minimum first."""
    return band(record.temperature_min), band(record.temperature_max)
