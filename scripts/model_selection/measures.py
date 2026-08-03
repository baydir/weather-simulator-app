"""What is measured on each series, and how a model's value is set against the reference.

Only quantities a monthly linear correction leaves alone. Open-Meteo fits such a
correction against ERA5-Land over a fifty-year window, so the mean of every
corrected variable is set by construction — ranking the models on it would rank
Open-Meteo's coefficients. Spread, persistence and distribution shape survive
that correction untouched, which is why they carry the whole comparison.

Two families, matching the two criteria retained for step 2. Each measure
declares how it is compared: a ``ratio`` for quantities where being twice too
large and half too large are the same failure, a ``diff`` for those already
expressed in the unit the reader thinks in — degrees, points of cloud cover,
days of drought.
"""

from __future__ import annotations

import math
import statistics as st
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from load import anomalies, seasonal_amplitude

from weather_simulator.domain import thresholds
from weather_simulator.sources.parse import DailyColumns

DISPERSION = "dispersion et persistance"
SHAPE = "forme des distributions"


@dataclass(frozen=True)
class Measure:
    key: str
    label: str
    family: str
    unit: str
    kind: str  # "ratio" or "diff"
    compute: Callable[[list[date], DailyColumns], float | None]

    def deviation(self, value: float | None, reference: float | None) -> float | None:
        """How far a model sits from the reference, on a scale comparable across sites.

        Ratios are read in logarithm so that 0.8 and 1.25 weigh the same; a
        difference is read as it stands. Both are returned unsigned — the
        direction is in the table, the ranking only needs the distance.
        """
        if value is None or reference is None:
            return None
        if self.kind == "ratio":
            if reference == 0 or value <= 0:
                return None
            return abs(math.log(value / reference))
        return abs(value - reference)


def _clean(column: list[float | None]) -> list[float]:
    return [value for value in column if value is not None]


def _quantile(values: list[float], q: float) -> float | None:
    """Linear interpolation between order statistics; enough for daily series."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = q * (len(ordered) - 1)
    lower = math.floor(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _lag1(column: list[float | None]) -> float | None:
    """Correlation between a day and the next, over consecutive pairs only."""
    values = _clean(column)
    if len(values) < 100:
        return None
    mean = st.mean(values)
    pairs = [
        (a - mean) * (b - mean)
        for a, b in zip(column, column[1:], strict=False)
        if a is not None and b is not None
    ]
    spread = sum((value - mean) ** 2 for value in values)
    return sum(pairs) / spread if spread else None


def _runs(column: list[float | None], *, wet: bool) -> list[int]:
    """Lengths of the consecutive stretches of wet — or dry — days.

    A missing day ends the run rather than bridging it: inventing continuity
    across a gap would lengthen exactly the statistic being measured.
    """
    lengths: list[int] = []
    current = 0
    for value in column:
        matches = value is not None and (
            value >= thresholds.PRECIPITATION_MM if wet else value < thresholds.PRECIPITATION_MM
        )
        if matches:
            current += 1
            continue
        if current:
            lengths.append(current)
        current = 0
    if current:
        lengths.append(current)
    return lengths


def _sd_of_anomalies(field: str) -> Callable[[list[date], DailyColumns], float | None]:
    def measure(dates: list[date], columns: DailyColumns) -> float | None:
        values = _clean(anomalies(dates, columns.columns[field]))
        return st.pstdev(values) if len(values) > 100 else None

    return measure


def _lag1_of_anomalies(field: str) -> Callable[[list[date], DailyColumns], float | None]:
    def measure(dates: list[date], columns: DailyColumns) -> float | None:
        return _lag1(anomalies(dates, columns.columns[field]))

    return measure


def _quantile_of_anomalies(
    field: str, q: float
) -> Callable[[list[date], DailyColumns], float | None]:
    def measure(dates: list[date], columns: DailyColumns) -> float | None:
        return _quantile(_clean(anomalies(dates, columns.columns[field])), q)

    return measure


def _interdecile(field: str) -> Callable[[list[date], DailyColumns], float | None]:
    """Spread between the first and ninth decile — the shape, not the level.

    Deliberately not the deciles themselves. Cloud cover carries a large offset
    that Open-Meteo's own correction is partly responsible for; ranking the
    models on where their cloud sits would settle, in passing, a question that
    belongs to step 4. How wide the distribution is says nothing about where it
    is centred, and is what this step is entitled to read.
    """

    def measure(dates: list[date], columns: DailyColumns) -> float | None:
        values = _clean(columns.columns[field])
        low, high = _quantile(values, 0.10), _quantile(values, 0.90)
        return None if low is None or high is None else high - low

    return measure


def _wet_day_share(dates: list[date], columns: DailyColumns) -> float | None:
    values = _clean(columns.columns["precipitation"])
    if not values:
        return None
    return 100 * sum(1 for v in values if v >= thresholds.PRECIPITATION_MM) / len(values)


def _wet_day_intensity(dates: list[date], columns: DailyColumns) -> float | None:
    wet = [v for v in _clean(columns.columns["precipitation"]) if v >= thresholds.PRECIPITATION_MM]
    return st.mean(wet) if len(wet) > 30 else None


def _wet_day_p99(dates: list[date], columns: DailyColumns) -> float | None:
    wet = [v for v in _clean(columns.columns["precipitation"]) if v >= thresholds.PRECIPITATION_MM]
    return _quantile(wet, 0.99) if len(wet) > 30 else None


def _spell(kind: str, statistic: str) -> Callable[[list[date], DailyColumns], float | None]:
    def measure(dates: list[date], columns: DailyColumns) -> float | None:
        lengths = _runs(columns.columns["precipitation"], wet=(kind == "wet"))
        if len(lengths) < 20:
            return None
        floats = [float(length) for length in lengths]
        return st.mean(floats) if statistic == "mean" else _quantile(floats, 0.95)

    return measure


def _amplitude(field: str) -> Callable[[list[date], DailyColumns], float | None]:
    def measure(dates: list[date], columns: DailyColumns) -> float | None:
        return seasonal_amplitude(dates, columns.columns[field])

    return measure


# The measures, in reading order. Kept short on purpose: a table nobody reads
# whole decides nothing, and each line here has to be one the choice can turn on.
MEASURES: tuple[Measure, ...] = (
    # Dispersion and persistence — does the model produce weather that varies,
    # and holds, the way the reanalysis does.
    Measure(
        "sd_tmax",
        "ecart-type anom. Tmax",
        DISPERSION,
        "C",
        "ratio",
        _sd_of_anomalies("temperature_max"),
    ),
    Measure(
        "sd_tmin",
        "ecart-type anom. Tmin",
        DISPERSION,
        "C",
        "ratio",
        _sd_of_anomalies("temperature_min"),
    ),
    Measure(
        "sd_cloud",
        "ecart-type anom. nebul.",
        DISPERSION,
        "pt",
        "ratio",
        _sd_of_anomalies("cloud_cover"),
    ),
    Measure(
        "ac1_tmax",
        "autocorr. j+1 Tmax",
        DISPERSION,
        "",
        "diff",
        _lag1_of_anomalies("temperature_max"),
    ),
    Measure(
        "ac1_cloud",
        "autocorr. j+1 nebul.",
        DISPERSION,
        "",
        "diff",
        _lag1_of_anomalies("cloud_cover"),
    ),
    Measure(
        "amp_tmax",
        "amplitude saisonniere Tmax",
        DISPERSION,
        "C",
        "diff",
        _amplitude("temperature_max"),
    ),
    Measure("dry_mean", "sequence seche moyenne", DISPERSION, "j", "ratio", _spell("dry", "mean")),
    Measure("dry_p95", "sequence seche p95", DISPERSION, "j", "ratio", _spell("dry", "p95")),
    Measure("wet_mean", "sequence humide moyenne", DISPERSION, "j", "ratio", _spell("wet", "mean")),
    # Distribution shape — does it rain as often, as hard, and are the tails of
    # the temperature where they should be.
    Measure("wet_freq", "jours humides", SHAPE, "%", "diff", _wet_day_share),
    Measure("wet_int", "intensite jour humide", SHAPE, "mm", "ratio", _wet_day_intensity),
    Measure("wet_p99", "p99 jour humide", SHAPE, "mm", "ratio", _wet_day_p99),
    Measure(
        "tmax_p99",
        "p99 anom. Tmax",
        SHAPE,
        "C",
        "diff",
        _quantile_of_anomalies("temperature_max", 0.99),
    ),
    Measure(
        "tmin_p01",
        "p1 anom. Tmin",
        SHAPE,
        "C",
        "diff",
        _quantile_of_anomalies("temperature_min", 0.01),
    ),
    Measure(
        "cloud_d9d1",
        "etendue interdecile nebul.",
        SHAPE,
        "pt",
        "ratio",
        _interdecile("cloud_cover"),
    ),
)
