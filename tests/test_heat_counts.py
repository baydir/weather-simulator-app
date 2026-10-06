"""Approved threshold boundaries, missing readings and cross-source consistency."""
from datetime import date

import pytest

from weather_simulator.api import pipeline
from weather_simulator.domain.heat_counts import summarize
from weather_simulator.domain.records import DailyRecord, Origin


def record(high=None, low=None, origin=Origin.OBSERVED):
    return DailyRecord(date(2024, 7, 1), origin, temperature_max=high, temperature_min=low)


def test_boundaries_use_unrounded_values_and_the_approved_operators():
    counts = summarize([
        record(30, 24.99), record(30.01, 25), record(35, 25.01), record(35.01, 24),
    ])
    assert [count.count for count in counts] == [3, 1, 2]
    assert [count.available_days for count in counts] == [4, 4, 4]


def test_missing_values_are_not_zero_or_cool_readings():
    counts = summarize([record(None, 25), record(36, None), record(float("nan"))])
    assert [count.count for count in counts] == [1, 1, 1]
    assert [count.available_days for count in counts] == [1, 1, 1]
    assert all(count.total_days == 3 for count in counts)
    assert all(count.count is None for count in summarize([record()]))
    assert [count.count for count in summarize([record(20, 10)])] == [0, 0, 0]


@pytest.mark.parametrize("origin", list(Origin))
def test_every_source_regime_uses_the_same_counts(origin):
    assert [count.count for count in summarize([record(36, 25, origin)])] == [1, 1, 1]


def test_pipeline_ships_counts_and_their_definitions():
    response = pipeline.run([record(35.01, 25)], latitude=0, longitude=0)
    counts = response.model_dump(mode="json")["heat_counts"]
    assert counts[1]["count"] == 1
    assert counts[1]["threshold"] == 35
    assert counts[1]["comparison"] == "above"
    assert counts[2]["reading"] == "temperature_min"
    assert counts[2]["comparison"] == "at_least"
