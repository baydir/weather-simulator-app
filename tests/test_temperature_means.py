"""Exact period means, strict coverage and equal annual weighting across regimes."""
from dataclasses import replace
from datetime import date, timedelta

import pytest

from weather_simulator.api import pipeline
from weather_simulator.domain.records import DailyRecord, Origin
from weather_simulator.domain.temperature_means import (
    WINDOW_YEARS,
    PeriodMeans,
    compare,
    period_means,
    window_means,
)


def records(first=date(2020, 7, 1), high=(30.01, 30.09), low=(20.0, 22.0), origin=Origin.OBSERVED):
    return [DailyRecord(first + timedelta(days=i), origin,
                        temperature_max=value, temperature_min=low[i])
            for i, value in enumerate(high)]


def annual(year, high=30.0, low=20.0, days=31):
    first = date(year, 1, 1)
    return PeriodMeans(first, first + timedelta(days=days - 1), days, days, days, high, low)


@pytest.mark.parametrize("origin", list(Origin))
def test_full_precision_and_identical_rules_on_every_source(origin):
    days = records(origin=origin)
    mean = period_means(days, days[0].date, days[-1].date)
    assert mean.temperature_max == pytest.approx(30.05)
    assert mean.temperature_min == 21.0
    assert mean.available_max_days == mean.requested_days == 2


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf")])
def test_one_missing_reading_withholds_only_that_variables_mean(bad):
    days = records(high=(30, bad))
    mean = period_means(days, days[0].date, days[-1].date)
    assert mean.temperature_max is None
    assert mean.available_max_days == 1
    assert mean.temperature_min == 21
    assert mean.requested_days == 2


def test_absent_dates_at_either_end_and_interior_gaps_remain_missing():
    first = date(2020, 7, 1)
    days = records(first)
    for start, end in [(first - timedelta(days=1), days[-1].date),
                       (first, days[-1].date + timedelta(days=1))]:
        result = period_means(days, start, end)
        assert result.temperature_max is None
        assert result.available_max_days == 2
        assert result.requested_days == 3
    days[1] = replace(days[1], date=first + timedelta(days=2))
    assert period_means(days, first, days[-1].date).temperature_max is None


def test_zero_is_a_valid_mean_and_duplicate_dates_are_refused():
    days = records(high=(-1, 1), low=(-3, -1))
    assert period_means(days, days[0].date, days[-1].date).temperature_max == 0
    with pytest.raises(ValueError, match="duplicate"):
        period_means([days[0], days[0]], days[0].date, days[0].date)


def test_decade_has_equal_annual_weights_not_equal_daily_weights():
    periods = [annual(year, high=0, days=28) for year in range(2010, 2020)]
    periods[-1] = annual(2019, high=100, days=29)
    summary = window_means(periods)
    assert summary.temperature_max == 10
    assert summary.complete_max_years == WINDOW_YEARS
    assert summary.temperature_min == 20


def test_partial_decades_and_incomplete_years_are_never_extrapolated():
    periods = [annual(year) for year in range(2010, 2020)]
    assert window_means(periods[:-1]).temperature_max is None
    periods[-1] = replace(periods[-1], temperature_min=None, available_min_days=30)
    summary = window_means(periods)
    assert summary.temperature_max == 30
    assert summary.temperature_min is None
    assert summary.complete_min_years == 9
    with pytest.raises(ValueError, match="distinct"):
        window_means([periods[0]] * WINDOW_YEARS)


def test_difference_uses_full_means_and_requires_both_windows():
    past = [annual(year, high=27.24, low=16.83) for year in range(2010, 2020)]
    future = [annual(year, high=28.56, low=18.02) for year in range(2030, 2040)]
    result = compare(past, future)
    assert result.difference.temperature_max == pytest.approx(1.32)
    assert result.difference.temperature_min == pytest.approx(1.19)
    assert compare(past[:-1], future).difference.temperature_max is None


def test_pipeline_uses_requested_coverage_not_just_returned_days():
    days = records()
    result = pipeline.run(days, latitude=0, longitude=0,
                          requested_start=days[0].date - timedelta(days=1),
                          requested_end=days[-1].date)
    assert result.start == days[0].date
    assert result.temperature_means.requested_days == 3
    assert result.temperature_means.temperature_max is None


def test_period_means_follow_the_existing_transformation_step(monkeypatch):
    from weather_simulator.transform import block

    days = records()
    monkeypatch.setattr(block, "apply", lambda items: [
        replace(item, temperature_max=item.temperature_max + 1.234) for item in items
    ])
    result = pipeline.run(days, latitude=0, longitude=0)
    assert result.temperature_means.temperature_max == pytest.approx(31.284)
    assert result.temperature_means.temperature_min == 21
