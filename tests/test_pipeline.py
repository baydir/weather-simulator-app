"""The chain from an assembled series to the JSON contract.

What is checked here is mostly what the pipeline refuses to do: correct the
past, serve an uncorrected future, invent a class for a day that has no cloud
cover, or classify the same day differently depending on which source served it.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from weather_simulator.api import errors, pipeline
from weather_simulator.api.contract import Series
from weather_simulator.calibration.table import Metadata
from weather_simulator.domain.correction import CloudCorrection, MonthlyCorrection, quantiles
from weather_simulator.domain.records import DailyRecord, Origin
from weather_simulator.domain.sky import SkyClass
from weather_simulator.transform import block

SAMPLE = [float(v) for v in range(0, 101, 2)] * 3
SHIFT = 10.0

PARIS = {"latitude": 48.8566, "longitude": 2.3522}


def _correction(months: range = range(1, 13)) -> CloudCorrection:
    """A node whose model runs ``SHIFT`` points short of the reference.

    Past and future distributions are the same, so the model projects no change
    and the correction reduces to removing the bias — which makes the expected
    output arithmetic rather than a fixture.
    """
    biased = quantiles([max(0.0, v - SHIFT) for v in SAMPLE])
    reference = quantiles(SAMPLE)
    return CloudCorrection(
        {
            month: MonthlyCorrection(reference=reference, model_past=biased, model_future=biased)
            for month in months
        }
    )


def _metadata() -> Metadata:
    return Metadata(
        model="MRI_AGCM3_2_S",
        calibration_start=date(1985, 1, 1),
        calibration_end=date(2014, 12, 31),
        projection_start=date(2021, 1, 1),
        projection_end=date(2050, 12, 31),
        step=0.5,
        generated=date(2026, 8, 4),
        node_count=594,
    )


def _record(day: date, origin: Origin, **fields) -> DailyRecord:
    base = {
        "temperature_min": 12.0,
        "temperature_max": 24.0,
        "temperature_mean": 18.0,
        "precipitation": 0.0,
        "cloud_cover": 40.0,
        "wind_speed_mean": 8.0,
        "wind_speed_max": 20.0,
    }
    base.update(fields)
    source = "era5" if origin is Origin.OBSERVED else "MRI_AGCM3_2_S"
    return DailyRecord(date=day, origin=origin, source=source, **base)


def _run(records: list[DailyRecord], **overrides) -> Series:
    kwargs = {"correction": _correction(), "metadata": _metadata(), **PARIS}
    kwargs.update(overrides)
    return pipeline.run(records, **kwargs)


# --- the correction reaches the future and nothing else ----------------------


def test_the_correction_leaves_the_observed_days_untouched() -> None:
    """The past is what happened. Only the projection is corrected."""
    records = [
        _record(date(2020, 6, 1), Origin.OBSERVED, cloud_cover=40.0),
        _record(date(2046, 6, 1), Origin.SIMULATED, cloud_cover=40.0),
    ]
    observed, simulated = _run(records).days

    assert observed.cloud_cover == 40.0
    assert simulated.cloud_cover == pytest.approx(50.0)


def test_the_shipped_cloud_cover_claims_no_precision_the_table_lacks() -> None:
    """Interpolating four nodes leaves 17 digits. The table stores tenths."""
    records = [_record(date(2046, 6, 1), Origin.SIMULATED, cloud_cover=37.3)]
    (day,) = _run(records).days

    assert day.cloud_cover == round(day.cloud_cover, 1)


def test_a_series_without_any_future_needs_no_correction() -> None:
    """An all-past request calls for no coefficient, so none is required."""
    records = [_record(date(2020, 6, 1), Origin.OBSERVED)]
    series = _run(records, correction=None, metadata=None)

    assert series.has_simulated is False
    assert series.grid is None


def test_the_grid_is_reported_only_when_something_was_corrected() -> None:
    """A table that applied to nothing is not described as if it had."""
    past = _run([_record(date(2020, 6, 1), Origin.OBSERVED)])
    future = _run([_record(date(2046, 6, 1), Origin.SIMULATED)])

    assert past.grid is None
    assert future.grid is not None
    assert future.grid.model == "MRI_AGCM3_2_S"
    assert future.grid.calibration_start == date(1985, 1, 1)


# --- what it refuses to serve ------------------------------------------------


def test_a_future_without_a_correction_stops_the_request() -> None:
    """An uncorrected future is a future sunny by 8 to 11 points. It is not served."""
    records = [_record(date(2046, 6, 1), Origin.SIMULATED)]

    with pytest.raises(errors.UncorrectedFuture) as raised:
        _run(records, correction=None)

    assert raised.value.count == 1
    assert raised.value.status_code == 500


def test_a_month_the_table_is_short_of_stops_the_request() -> None:
    """Correcting from a hole would be a different correction under the same name."""
    records = [_record(date(2046, 6, 1), Origin.SIMULATED)]

    with pytest.raises(errors.UncoveredMonth) as raised:
        _run(records, correction=_correction(range(1, 6)))

    assert raised.value.month == 6


# --- the sky class, one function over the four segments ----------------------


def test_the_same_day_gets_the_same_class_whatever_served_it() -> None:
    """The seam must not be visible in the class. One function, called four times."""
    fields = {"precipitation": 0.0, "cloud_cover": 85.0, "temperature_mean": 10.0}
    reanalysis = _record(date(2020, 6, 1), Origin.OBSERVED, **fields)
    recent = replace(_record(date(2026, 8, 1), Origin.OBSERVED, **fields), source="ecmwf_ifs")
    # 85 % of cloud in the model becomes 95 % once corrected: still overcast.
    projected = _record(date(2046, 6, 1), Origin.SIMULATED, **fields)

    days = _run([reanalysis, recent, projected]).days
    assert {day.sky for day in days} == {SkyClass.OVERCAST}


def test_a_day_missing_a_variable_carries_no_class() -> None:
    """``null`` rather than a guess — the interface must have a card for it."""
    records = [_record(date(2020, 6, 1), Origin.OBSERVED, cloud_cover=None)]
    (day,) = _run(records, correction=None, metadata=None).days

    assert day.sky is None
    assert day.cloud_cover is None


def test_a_gap_survives_the_correction_as_a_gap() -> None:
    """A missing value is not a value to correct. It stays missing."""
    records = [_record(date(2046, 6, 1), Origin.SIMULATED, cloud_cover=None)]
    (day,) = _run(records).days

    assert day.cloud_cover is None
    assert day.sky is None


# --- the transformation block ------------------------------------------------


def test_the_neutral_block_changes_nothing() -> None:
    records = [_record(date(2020, 6, 1), Origin.OBSERVED)]
    assert block.apply(records) == records


def test_the_block_sits_between_the_correction_and_the_class(monkeypatch) -> None:
    """It sees corrected values, and what it changes still reaches the tree.

    That is the whole reason for its placement: a block called after the
    classification could not change a pictogram, only the numbers beside it.
    """
    seen: list[float | None] = []

    def spy(records: list[DailyRecord]) -> list[DailyRecord]:
        seen.extend(record.cloud_cover for record in records)
        return [replace(record, cloud_cover=10.0) for record in records]

    monkeypatch.setattr(block, "apply", spy)
    records = [_record(date(2046, 6, 1), Origin.SIMULATED, cloud_cover=40.0)]
    (day,) = _run(records).days

    assert seen == [pytest.approx(50.0)]  # corrected before the block saw it
    assert day.cloud_cover == 10.0
    assert day.sky is SkyClass.CLEAR  # and the block's value drove the class


# --- the contract ------------------------------------------------------------


def test_the_contract_carries_the_class_and_not_the_pictogram() -> None:
    records = [_record(date(2020, 6, 1), Origin.OBSERVED)]
    payload = _run(records, correction=None, metadata=None).model_dump(mode="json")

    assert payload["days"][0]["sky"] == "cloudy"
    assert "temperature_mean" not in payload["days"][0]
    assert "snowfall" not in payload["days"][0]


def test_the_warning_flag_is_shipped_rather_than_derived() -> None:
    """Whether a warning is due is answered here, not a second time downstream."""
    records = [
        _record(date(2020, 6, 1), Origin.OBSERVED),
        _record(date(2046, 6, 1), Origin.SIMULATED),
    ]
    assert _run(records).has_simulated is True


def test_the_reported_range_is_what_the_sources_served() -> None:
    """Not what was asked for: a source stopping short must be visible."""
    records = [
        _record(date(2020, 6, 3), Origin.OBSERVED),
        _record(date(2020, 6, 1), Origin.OBSERVED),
    ]
    series = _run(sorted(records, key=lambda r: r.date), correction=None, metadata=None)

    assert (series.start, series.end) == (date(2020, 6, 1), date(2020, 6, 3))
