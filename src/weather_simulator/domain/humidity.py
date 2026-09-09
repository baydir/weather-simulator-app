"""Wet-bulb temperature, and the humid-heat level the card turns on.

**Derived here rather than fetched, and not by preference.** Open-Meteo serves
``wet_bulb_temperature_2m_mean`` as a daily variable on ERA5-Land, ERA5 and
ECMWF IFS, forecast included. The Climate API accepts it, answers HTTP 200 and
returns a column of nulls — the same silent absence it gives for
``weather_code``. Three segments of four is exactly the case CLAUDE.md rule 2
refuses: a quantity available on one side of a seam is dropped, never exploited.
So it is rebuilt from variables all four sources do serve.

**The same formula Open-Meteo runs, deliberately.** Stull (2011), with their
``min(twet, t)`` guard, transcribed from ``Meteorology.swift``. That matters more
than being right: the error of an empirical fit is inherited identically on the
four segments, so it produces no step at either seam, which is the whole of rule
2. Being *wrong the same way everywhere* is the requirement; being right is not.
What Stull costs, against exact psychrometry, is -1.0 to +0.65 °C with a mean
absolute error under 0.3 °C, outside the cold-and-dry corner the paper excludes,
plus a missing pressure term that reaches 0.9 °C at 1500 m in hot dry air. Both
land where the thresholds do not: on the humid columns that decide a level, the
fit and the exact solution agree to better than 0.5 °C.

**Fed the dew point, though Open-Meteo feeds relative humidity.** Their function
runs hourly, where relative humidity is the real thing. Ours runs on daily
aggregates, and within a day relative humidity swings inversely with
temperature, so its daily mean summarises the day badly. The dew point tracks
the moisture actually present, which is close to conserved over the day.
Measured against Open-Meteo's own hourly-resolved daily mean, five climates and
1826 days each: 0.04 to 0.08 °C RMSE through the dew point, against 0.07 to 0.42
through relative humidity. The formula error cancels in that comparison, both
sides running Stull, so what is left is the aggregation and nothing else.

**The daily mean, never the maximum.** Two reasons, and either would be enough.
The maximum reconstructs from daily aggregates only to 0.75-0.95 °C, ten times
worse. And the mean is the better quantity anyway: heat kills by dose rather
than by peak, the mean over twenty-four hours *is* the exposure integral, and it
includes the night, whose absence as a recovery window is what the epidemiology
of heatwaves identifies. A day peaking at 34 with a mean of 26 is survived; a
day averaging 32 is not.

The reading is one-sided, and the interface must respect that: a high value is
certain danger, a moderate one does not exclude a difficult few hours. The level
below is therefore a floor on severity, never a certificate of safety.
"""

from __future__ import annotations

import math

from weather_simulator.domain import thresholds
from weather_simulator.domain.records import DailyRecord

# Magnus over water, WMO coefficients. Used for one thing only: turning a dew
# point back into the relative humidity Stull's fit expects, at the day's mean
# temperature. Saturation vapour pressure in hPa.
_MAGNUS_A = 17.62
_MAGNUS_B = 243.12
_MAGNUS_E0 = 6.112


def _saturation_pressure(temperature: float) -> float:
    return _MAGNUS_E0 * math.exp(_MAGNUS_A * temperature / (_MAGNUS_B + temperature))


def relative_humidity(temperature: float, dew_point: float) -> float:
    """Relative humidity in percent, from a temperature and a dew point.

    Capped at 100 and not floored. The cap is physical and it is also what keeps
    the input inside the domain Open-Meteo's own values come from, hourly
    relative humidity being bounded by construction. There is no floor because
    Stull's fit has none either, and adding one here would be a second
    difference from the reference for no gain: a day dry enough to reach the
    bottom of the fit's validated range sits tens of degrees below any level.
    """
    return min(100.0, 100.0 * _saturation_pressure(dew_point) / _saturation_pressure(temperature))


def wet_bulb(temperature_mean: float | None, dew_point_mean: float | None) -> float | None:
    """The day's mean wet-bulb temperature in degrees Celsius, or ``None``.

    ``None`` when either input is missing, for the reason :func:`sky.classify`
    returns it: a gap is a gap, and substituting a value would be a
    data-treatment decision taken in passing, which CLAUDE.md reserves for
    validation.

    The trailing ``min`` is Open-Meteo's, not a correction of it. The fit can
    exceed the air temperature at saturation, which is unphysical, and their
    code clamps it. Ours clamps it identically or the two would part company on
    exactly the foggy days where the level is closest to firing.
    """
    if temperature_mean is None or dew_point_mean is None:
        return None

    t = temperature_mean
    rh = relative_humidity(t, dew_point_mean)
    value = (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * rh**1.5 * math.atan(0.023101 * rh)
        - 4.686035
    )
    return min(value, t)


def humid_heat(wet_bulb_mean: float | None) -> int | None:
    """The level a day carries: 0, 1, 2 — or ``None`` when there is no reading.

    Zero and null say different things and the interface needs both. Zero is an
    answer: this day was measured and there is nothing to report. Null is the
    absence of one, and a card must no more invent a level than it invents a
    sky class.

    Two levels and not five. A wet bulb means nothing to a reader as a number —
    31 °C is lethal and reads as mild — so the card shows a word, and a word
    scale finer than "marked" and "beyond what a body compensates" would claim
    a gradation the daily mean cannot support.
    """
    if wet_bulb_mean is None:
        return None
    if wet_bulb_mean >= thresholds.HUMID_HEAT_EXTREME_C:
        return 2
    if wet_bulb_mean >= thresholds.HUMID_HEAT_C:
        return 1
    return 0


def wet_bulb_of_record(record: DailyRecord) -> float | None:
    """The same rule, applied to a day of the assembled series."""
    return wet_bulb(record.temperature_mean, record.dew_point_mean)
