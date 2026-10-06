"""Approved daily heat counts, computed identically across all source segments."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from weather_simulator.domain.records import DailyRecord


@dataclass(frozen=True, slots=True)
class HeatCount:
    """A count and its definition, shipped together so labels cannot drift."""

    reading: Literal["temperature_max", "temperature_min"]
    threshold: float
    comparison: Literal["above", "at_least"]
    count: int | None
    available_days: int
    total_days: int


# Scientific choices approved by the project owner; never repeat them in JS.
DEFINITIONS = (
    ("temperature_max", 30.0, "above"),
    ("temperature_max", 35.0, "above"),
    ("temperature_min", 25.0, "at_least"),
)


def summarize(records: list[DailyRecord]) -> list[HeatCount]:
    """Count full-precision readings; unavailable values never count as cool days."""
    result = []
    for reading, threshold, comparison in DEFINITIONS:
        values = [getattr(record, reading) for record in records]
        available = [value for value in values if value is not None and isfinite(value)]
        matches = sum(
            value > threshold if comparison == "above" else value >= threshold
            for value in available
        )
        result.append(
            HeatCount(
                reading=reading,
                threshold=threshold,
                comparison=comparison,
                count=matches if available else None,
                available_days=len(available),
                total_days=len(records),
            )
        )
    return result
