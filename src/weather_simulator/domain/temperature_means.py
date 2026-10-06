"""Period means and equally weighted decade means, shared by all source regimes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from statistics import fmean

from weather_simulator.domain.records import DailyRecord

WINDOW_YEARS = 10


@dataclass(frozen=True, slots=True)
class PeriodMeans:
    start: date
    end: date
    requested_days: int
    available_max_days: int
    available_min_days: int
    temperature_max: float | None
    temperature_min: float | None


@dataclass(frozen=True, slots=True)
class WindowMeans:
    temperature_max: float | None
    temperature_min: float | None
    complete_max_years: int
    complete_min_years: int
    required_years: int = WINDOW_YEARS


@dataclass(frozen=True, slots=True)
class TemperatureDifference:
    temperature_max: float | None
    temperature_min: float | None


@dataclass(frozen=True, slots=True)
class ComparisonMeans:
    past: WindowMeans
    future: WindowMeans
    difference: TemperatureDifference


def period_means(records: list[DailyRecord], start: date, end: date) -> PeriodMeans:
    """Average only complete daily readings, using full precision after transformation.

    Coverage is the requested interval, including absent leading/trailing dates.
    Highs and lows have independent coverage. Missing or non-finite readings are
    never filled, rounded before averaging, or counted as zero.
    """
    requested_days = (end - start).days + 1
    if requested_days <= 0:
        raise ValueError("empty period")
    selected = [record for record in records if start <= record.date <= end]
    if len({record.date for record in selected}) != len(selected):
        raise ValueError("duplicate daily dates")

    def read(field: str) -> tuple[float | None, int]:
        values = [getattr(record, field) for record in selected]
        available = [value for value in values if value is not None and isfinite(value)]
        mean = fmean(available) if len(available) == requested_days else None
        return mean, len(available)

    high, high_days = read("temperature_max")
    low, low_days = read("temperature_min")
    return PeriodMeans(start, end, requested_days, high_days, low_days, high, low)


def window_means(periods: list[PeriodMeans]) -> WindowMeans:
    """Each complete year gets one vote, regardless of leap days or period length."""
    if len(periods) > WINDOW_YEARS or len({item.start.year for item in periods}) != len(periods):
        raise ValueError("a window requires distinct annual periods")

    def read(field: str, coverage: str) -> tuple[float | None, int]:
        available = [
            getattr(item, field) for item in periods
            if getattr(item, coverage) == item.requested_days
            and getattr(item, field) is not None and isfinite(getattr(item, field))
        ]
        mean = fmean(available) if len(available) == WINDOW_YEARS else None
        return mean, len(available)

    high, high_years = read("temperature_max", "available_max_days")
    low, low_years = read("temperature_min", "available_min_days")
    return WindowMeans(high, low, high_years, low_years)


def compare(past: list[PeriodMeans], future: list[PeriodMeans]) -> ComparisonMeans:
    """Serve differences too: the browser never subtracts scientific quantities."""
    before, after = window_means(past), window_means(future)

    def difference(field: str) -> float | None:
        a, b = getattr(before, field), getattr(after, field)
        return None if a is None or b is None else b - a

    return ComparisonMeans(before, after, TemperatureDifference(
        difference("temperature_max"), difference("temperature_min"),
    ))
