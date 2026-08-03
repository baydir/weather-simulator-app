"""Reading the cached payloads back, and taking the season out of them.

The reference is assembled exactly as the application assembles its past:
ERA5-Land for the temperatures, ERA5 for the rest, joined on the date. Anything
else would compare the models against a series the application never shows.

The deseasonalisation matters more than it looks. Raw daily temperature is
dominated by the annual cycle: its lag-1 autocorrelation sits around 0.97 in any
series that has a summer and a winter, model or reanalysis, and comparing those
numbers would say nothing about weather persistence. The same holds for the
spread — a standard deviation computed on raw values mostly measures how far
apart July and January are. Both are therefore computed on anomalies, once the
day-of-year climatology has been removed, and the amplitude of that climatology
is reported separately as a measure in its own right.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from weather_simulator.sources import openmeteo
from weather_simulator.sources.parse import DailyColumns, merge_columns, parse_daily

Column = list[float | None]

# A leap year enumerated once, so that every (month, day) has a slot and the
# 29th of February is not silently dropped in the four years that have one.
CALENDAR = [date(2000, 1, 1) + timedelta(days=offset) for offset in range(366)]
SLOT = {(day.month, day.day): index for index, day in enumerate(CALENDAR)}

# Half-width of the window the climatology is smoothed over. Thirty-six samples
# per calendar day is thin; a centred month is the usual remedy and blurs
# nothing the daily series is asked to resolve here.
WINDOW = 15


def load_reference(cache_dir: Path, site: str) -> DailyColumns:
    """The past as the application builds it: two reanalyses, one per variable set."""
    temperature = parse_daily(
        _read(cache_dir, site, openmeteo.TEMPERATURE_MODEL),
        openmeteo.TEMPERATURE_VARIABLES,
        source=openmeteo.TEMPERATURE_MODEL,
        model=openmeteo.TEMPERATURE_MODEL,
    )
    surface = parse_daily(
        _read(cache_dir, site, openmeteo.SURFACE_MODEL),
        openmeteo.SURFACE_VARIABLES,
        source=openmeteo.SURFACE_MODEL,
        model=openmeteo.SURFACE_MODEL,
        optional=openmeteo.OPTIONAL_VARIABLES,
    )
    return merge_columns(temperature, surface, source="reference")


def load_model(cache_dir: Path, site: str, model: str) -> DailyColumns:
    """One model's hindcast, all variables from the single climate request.

    Every variable is tolerated missing here, which the request path must never
    do. A gap is fatal in the application — a day half-served is a day whose
    fields depend on which source answered. In a comparison it is a result: two
    of the five models serve no daily maximum wind at all, and a loader that
    refused them would have dropped both from the ranking instead of reporting
    it. What is absent is measured and printed by ``coverage``.
    """
    return parse_daily(
        _read(cache_dir, site, model),
        openmeteo.ALL_VARIABLES,
        source=model,
        model=model,
        optional=frozenset(openmeteo.ALL_VARIABLES),
    )


def coverage(columns: DailyColumns) -> dict[str, float]:
    """Share of days actually served, per field."""
    return {
        field: (100 * sum(1 for v in column if v is not None) / len(column) if column else 0.0)
        for field, column in columns.columns.items()
    }


def _read(cache_dir: Path, site: str, source: str) -> dict:
    return json.loads((cache_dir / f"{site}__{source}.json").read_text(encoding="utf-8"))


def climatology(dates: list[date], values: Column) -> list[float | None]:
    """Mean value per calendar day, smoothed over a centred month.

    Circular at the year boundary: the 1st of January borrows from December, as
    it must, or the anomaly series would carry a step every new year.
    """
    buckets: list[list[float]] = [[] for _ in CALENDAR]
    for day, value in zip(dates, values, strict=True):
        if value is not None:
            buckets[SLOT[(day.month, day.day)]].append(value)

    smoothed: list[float | None] = []
    for index in range(len(CALENDAR)):
        pooled = [
            value
            for offset in range(-WINDOW, WINDOW + 1)
            for value in buckets[(index + offset) % len(CALENDAR)]
        ]
        smoothed.append(sum(pooled) / len(pooled) if pooled else None)
    return smoothed


def anomalies(dates: list[date], values: Column) -> Column:
    """``values`` with the day-of-year climatology removed."""
    reference = climatology(dates, values)
    result: Column = []
    for day, value in zip(dates, values, strict=True):
        expected = reference[SLOT[(day.month, day.day)]]
        result.append(None if value is None or expected is None else value - expected)
    return result


def seasonal_amplitude(dates: list[date], values: Column) -> float | None:
    """Warmest minus coldest day of the smoothed annual cycle."""
    reference = [value for value in climatology(dates, values) if value is not None]
    return max(reference) - min(reference) if reference else None
