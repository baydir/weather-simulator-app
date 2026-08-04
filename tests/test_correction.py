"""The cloud correction: does it remove the bias, and does it leave the trend alone.

Built on samples rather than on hand-written quantile grids, so the tests read
like the situations they describe.
"""

from __future__ import annotations

import pytest

from weather_simulator.domain.correction import (
    CLOUD_MAX,
    CloudCorrection,
    MonthlyCorrection,
    _interpolate,
    _level_of,
    build,
    quantiles,
)

# A stand-in for a month of observed cloud cover: spread over the whole range,
# with the piling-up at both ends that real cloud cover shows.
REFERENCE = [float(v) for v in range(0, 101, 2)] * 3


def _skew(value: float) -> float:
    """The bias as measured: 14 points short on clear days, 2 on overcast ones."""
    return value - (14 - 0.12 * value)


def _median(values: list[float]) -> float:
    grid = quantiles(values)
    return grid[len(grid) // 2]


def _monthly(reference, past, future) -> MonthlyCorrection:
    return MonthlyCorrection(
        reference=quantiles(reference),
        model_past=quantiles(past),
        model_future=quantiles(future),
    )


def test_an_unbiased_model_with_no_trend_is_left_alone() -> None:
    """Nothing to fix, nothing to carry: the value comes back as it went in."""
    correction = _monthly(REFERENCE, REFERENCE, REFERENCE)
    for value in (0.0, 12.0, 30.0, 55.0, 70.0, 88.0, 100.0):
        assert correction.apply(value) == pytest.approx(value, abs=1.0)


def test_a_constant_bias_is_removed() -> None:
    """A model ten points short everywhere comes back onto the reference."""
    shifted = [max(0.0, v - 10) for v in REFERENCE]
    correction = _monthly(REFERENCE, shifted, shifted)
    # A day sitting at the model's median must land on the reference's median.
    median_model = quantiles(shifted)[len(quantiles(shifted)) // 2]
    median_reference = quantiles(REFERENCE)[len(quantiles(REFERENCE)) // 2]
    assert correction.apply(median_model) == pytest.approx(median_reference, abs=2.0)


def test_a_bias_that_varies_with_the_quantile_is_removed_too() -> None:
    """The real case: short by 14 points on clear days, by 2 on overcast ones.

    A single monthly offset cannot do this, which is why the correction works
    quantile by quantile.
    """
    skewed = [max(0.0, v - (14 - 0.12 * v)) for v in REFERENCE]
    correction = _monthly(REFERENCE, skewed, skewed)
    grid_model, grid_reference = quantiles(skewed), quantiles(REFERENCE)
    for index in (5, 15, 25, 35):
        assert correction.apply(grid_model[index]) == pytest.approx(grid_reference[index], abs=2.0)


def test_the_trend_survives_the_correction() -> None:
    """The point of the method: the shift the model projects comes through intact.

    The bias here varies with the quantile, as the real one does. That matters:
    where the bias is a plain offset the mapping is linear and every method
    agrees. The methods part company only on a bias like this one.
    """
    biased_past = [_skew(v) for v in REFERENCE]
    biased_future = [_skew(v) - 5 for v in REFERENCE]  # five points clearer
    correction = _monthly(REFERENCE, biased_past, biased_future)

    median_future = _median(biased_future)
    assert correction.apply(median_future) == pytest.approx(_median(REFERENCE) - 5.0, abs=1.0)


def test_the_naive_mapping_rescales_the_trend() -> None:
    """Mapping through the model's *past* distribution shrinks the change.

    The first of the two things loosely called quantile mapping. It does not
    erase the trend — the design document overstates that — it multiplies it by
    the local slope of a mapping that is not linear. Here the bias falls by 0.12
    point per point of cloud, so five points of clearing come out as 5 x 0.88,
    and nothing in the output says it has been rescaled.

    The distortion is proportional to how much the bias varies with the
    quantile. Mild in France; not something to rely on elsewhere.
    """
    biased_past = [_skew(v) for v in REFERENCE]
    biased_future = [_skew(v) - 5 for v in REFERENCE]
    naive = _monthly(REFERENCE, biased_past, biased_past)

    shift = _median(REFERENCE) - naive.apply(_median(biased_future))
    assert shift == pytest.approx(5 * 0.88, abs=0.2)
    assert shift != pytest.approx(5.0, abs=0.2)


def test_the_other_naive_mapping_erases_the_trend_outright() -> None:
    """Mapping through the model's *future* distribution forces it onto the past.

    The second variant, and the one the design document warns against: the
    output distribution becomes the reference distribution by construction, so
    whatever the model projects lands back where the observed past was.
    """
    biased_past = [_skew(v) for v in REFERENCE]
    biased_future = [_skew(v) - 5 for v in REFERENCE]
    grids = _monthly(REFERENCE, biased_past, biased_future)

    level = _level_of(grids.model_future, grids.levels, _median(biased_future))
    erased = _interpolate(grids.reference, grids.levels, level)
    assert erased == pytest.approx(_median(REFERENCE), abs=1.0)


def test_the_result_stays_a_share_of_sky() -> None:
    """Cloud cover cannot leave 0-100, whatever the drift adds."""
    biased_past = [max(0.0, v - 30) for v in REFERENCE]
    correction = _monthly(REFERENCE, biased_past, REFERENCE)
    for value in (0.0, 50.0, 100.0):
        assert 0.0 <= correction.apply(value) <= CLOUD_MAX


def test_a_gap_stays_a_gap() -> None:
    correction = CloudCorrection({1: _monthly(REFERENCE, REFERENCE, REFERENCE)})
    assert correction.apply(None, 1) is None


def test_a_month_without_a_correction_is_an_error() -> None:
    """Silence here would mean serving an artificially sunny future."""
    correction = CloudCorrection({1: _monthly(REFERENCE, REFERENCE, REFERENCE)})
    with pytest.raises(KeyError):
        correction.apply(50.0, 7)


def test_build_keeps_only_the_months_all_three_samples_cover() -> None:
    correction = build(
        reference={1: REFERENCE, 2: REFERENCE},
        model_past={1: REFERENCE, 2: REFERENCE},
        model_future={1: REFERENCE},
    )
    assert set(correction.months) == {1}


def test_quantiles_refuses_an_empty_sample() -> None:
    with pytest.raises(ValueError):
        quantiles([])
