"""The correction grid: the four nodes, the blend, and the refusal."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from weather_simulator.calibration.grid import CorrectionGrid, surrounding
from weather_simulator.calibration.table import (
    CorrectionTable,
    Metadata,
    OutsideCoverage,
)
from weather_simulator.domain.correction import CloudCorrection, MonthlyCorrection, quantiles

STEP = 0.5
SAMPLE = [float(v) for v in range(0, 101, 2)] * 3


def _correction(shift: float) -> CloudCorrection:
    """A node whose model runs ``shift`` points short of the reference."""
    biased = quantiles([max(0.0, v - shift) for v in SAMPLE])
    months = {
        month: MonthlyCorrection(
            reference=quantiles(SAMPLE), model_past=biased, model_future=biased
        )
        for month in range(1, 13)
    }
    return CloudCorrection(months)


def _metadata(**overrides) -> Metadata:
    base = {
        "model": "MRI_AGCM3_2_S",
        "calibration_start": date(1985, 1, 1),
        "calibration_end": date(2014, 12, 31),
        "projection_start": date(2021, 1, 1),
        "projection_end": date(2050, 12, 31),
        "step": STEP,
        "generated": date(2026, 8, 4),
        "node_count": 4,
    }
    return Metadata(**{**base, **overrides})


def _grid(shifts: dict[tuple[float, float], float] | None = None) -> CorrectionGrid:
    """A square of four nodes around 48.5-49.0 N, 2.0-2.5 E."""
    corners = [(48.5, 2.0), (48.5, 2.5), (49.0, 2.0), (49.0, 2.5)]
    shifts = shifts or dict.fromkeys(corners, 10.0)
    return CorrectionGrid(
        CorrectionTable(_metadata(), {node: _correction(shifts[node]) for node in corners})
    )


def test_the_four_nodes_enclose_the_point() -> None:
    assert surrounding(48.7, 2.3, STEP) == [(48.5, 2.0), (48.5, 2.5), (49.0, 2.0), (49.0, 2.5)]


def test_a_point_on_a_node_still_gets_four() -> None:
    """One code path, three of the weights being zero."""
    assert surrounding(48.5, 2.0, STEP) == [(48.5, 2.0), (48.5, 2.5), (49.0, 2.0), (49.0, 2.5)]


def test_negative_coordinates_round_the_right_way() -> None:
    """Below zero the enclosing node is the one further from zero, not nearer.

    Brittany and the southern hemisphere both live there, and rounding towards
    zero would hand back a square the point is not inside.
    """
    assert surrounding(48.39, -4.49, STEP)[0] == (48.0, -4.5)

    corners = surrounding(-43.53, 172.63, STEP)
    assert corners[0] == (-44.0, 172.5)
    assert corners[3] == (-43.5, 173.0)
    # The point really is enclosed, which is the property that matters.
    assert corners[0][0] <= -43.53 <= corners[3][0]
    assert corners[0][1] <= 172.63 <= corners[3][1]


def test_a_point_inside_the_square_is_corrected() -> None:
    grid = _grid()
    correction = grid.correction_at(48.7, 2.3)
    assert set(correction.months) == set(range(1, 13))
    # Every node is short by ten points, so the corrected value lands on the
    # reference wherever inside the square the point sits.
    biased_median = quantiles([max(0.0, v - 10) for v in SAMPLE])[19]
    reference_median = quantiles(SAMPLE)[19]
    assert correction.apply(biased_median, 7) == pytest.approx(reference_median, abs=2.0)


def test_the_blend_follows_the_position() -> None:
    """Nodes disagreeing, a point near one of them leans that way."""
    corners = [(48.5, 2.0), (48.5, 2.5), (49.0, 2.0), (49.0, 2.5)]
    grid = _grid({corners[0]: 20.0, corners[1]: 0.0, corners[2]: 20.0, corners[3]: 0.0})

    west = grid.correction_at(48.75, 2.05).months[7].model_past
    east = grid.correction_at(48.75, 2.45).months[7].model_past
    middle = grid.correction_at(48.75, 2.25).months[7].model_past

    # The model_past grid is what the bias lives in: heavily shifted west,
    # untouched east, and halfway in between at the centre.
    assert west[19] < middle[19] < east[19]


def test_a_point_outside_the_square_is_refused() -> None:
    """No falling back on the nearest node: the refusal has to be visible."""
    grid = _grid()
    with pytest.raises(OutsideCoverage) as raised:
        grid.correction_at(43.30, 5.37)
    assert raised.value.missing == 4
    assert not grid.covers(43.30, 5.37)


def test_one_missing_corner_is_enough_to_refuse() -> None:
    """Three nodes and a hole would be a different correction under the same name."""
    table = CorrectionTable(
        _metadata(node_count=3),
        {node: _correction(10.0) for node in [(48.5, 2.0), (48.5, 2.5), (49.0, 2.0)]},
    )
    with pytest.raises(OutsideCoverage) as raised:
        CorrectionGrid(table).correction_at(48.7, 2.3)
    assert raised.value.missing == 1


def test_only_the_months_every_corner_carries_survive() -> None:
    corners = [(48.5, 2.0), (48.5, 2.5), (49.0, 2.0), (49.0, 2.5)]
    nodes = {node: _correction(10.0) for node in corners}
    nodes[corners[3]] = CloudCorrection(
        {m: c for m, c in nodes[corners[3]].months.items() if m != 7}
    )
    grid = CorrectionGrid(CorrectionTable(_metadata(), nodes))
    assert 7 not in grid.correction_at(48.7, 2.3).months
    assert 6 in grid.correction_at(48.7, 2.3).months


def test_a_placeholder_table_says_so(tmp_path: Path) -> None:
    """The flag has to survive the round trip, or it protects nothing."""
    table = CorrectionTable(
        _metadata(placeholder=True, note="identite"),
        {(48.5, 2.0): _correction(0.0)},
    )
    path = tmp_path / "table.json"
    table.write(path)
    assert CorrectionGrid(CorrectionTable.read(path)).is_placeholder


def test_a_real_table_does_not(tmp_path: Path) -> None:
    path = tmp_path / "table.json"
    CorrectionTable(_metadata(), {(48.5, 2.0): _correction(10.0)}).write(path)
    assert not CorrectionGrid(CorrectionTable.read(path)).is_placeholder


def test_the_table_survives_being_written_and_read(tmp_path: Path) -> None:
    path = tmp_path / "table.json"
    _grid().table.write(path)
    reloaded = CorrectionGrid(CorrectionTable.read(path))

    assert reloaded.table.metadata.model == "MRI_AGCM3_2_S"
    assert reloaded.table.metadata.calibration_start == date(1985, 1, 1)
    assert reloaded.step == STEP
    assert reloaded.covers(48.7, 2.3)
    original = _grid().correction_at(48.7, 2.3).apply(30.0, 7)
    assert reloaded.correction_at(48.7, 2.3).apply(30.0, 7) == pytest.approx(original, abs=0.2)
