"""Finding the four nodes around a point, and blending their corrections.

The table is read once at start-up and kept in memory. Nothing here touches the
disk or the network afterwards: the server is stateless by design, and a few
megabytes resident is what buys that.

**The table is interpolated, then applied** — not applied at the four nodes and
the results averaged. The two differ, the correction not being linear, and this
order is the one that gives a continuous correction field: moving a few hundred
metres cannot flip the sky class of a day, which the other order would allow at
a cell boundary.

Interpolation carries an error of its own and it is not nothing. Measured along
three transects crossing the French coast at quarter-degree steps: 0.3 point of
cloud cover on average, 0.7 at worst, and the worst sits on rising ground rather
than at the shoreline — the coast turns out not to disturb the bias field at
all, while relief does.
"""

from __future__ import annotations

import math

from weather_simulator.calibration.table import NODE_DECIMALS, CorrectionTable, OutsideCoverage
from weather_simulator.domain.correction import CloudCorrection, MonthlyCorrection


def _corner(latitude: float, longitude: float, step: float) -> tuple[float, float]:
    """The south-west node of the cell a point falls in.

    Both functions below start here, and they used to start with their own copy
    of these two lines. They have to agree exactly: :func:`surrounding` names the
    nodes and :func:`_weights` measures the distance to them, so a cell chosen
    one way and measured another would weight a point against nodes it does not
    sit between — silently, and only near a boundary.
    """
    return math.floor(latitude / step) * step, math.floor(longitude / step) * step


def surrounding(latitude: float, longitude: float, step: float) -> list[tuple[float, float]]:
    """The four lattice nodes enclosing a point, south-west first.

    A point sitting exactly on a node still gets four of them, three of which
    carry zero weight. That keeps one code path instead of two.

    Rounded to the decimals the table writes its keys with — the lookup is by
    exact coordinates, so ``48.5`` and ``48.500000000000004`` are two different
    nodes and only one of them is in the file.
    """
    south, west = _corner(latitude, longitude, step)
    return [
        (round(south, NODE_DECIMALS), round(west, NODE_DECIMALS)),
        (round(south, NODE_DECIMALS), round(west + step, NODE_DECIMALS)),
        (round(south + step, NODE_DECIMALS), round(west, NODE_DECIMALS)),
        (round(south + step, NODE_DECIMALS), round(west + step, NODE_DECIMALS)),
    ]


def _weights(latitude: float, longitude: float, step: float) -> list[float]:
    """Bilinear weights, in the same order as :func:`surrounding`."""
    south, west = _corner(latitude, longitude, step)
    y = (latitude - south) / step
    x = (longitude - west) / step
    return [(1 - y) * (1 - x), (1 - y) * x, y * (1 - x), y * x]


def _blend(grids: list[list[float]], weights: list[float]) -> list[float]:
    return [
        sum(g[i] * w for g, w in zip(grids, weights, strict=True)) for i in range(len(grids[0]))
    ]


class CorrectionGrid:
    """The shipped table, ready to answer for an arbitrary point."""

    def __init__(self, table: CorrectionTable) -> None:
        self.table = table
        self.step = table.metadata.step

    @property
    def is_placeholder(self) -> bool:
        """True when the corrections are identity — a fixture, not a grid."""
        return self.table.metadata.placeholder

    def covers(self, latitude: float, longitude: float) -> bool:
        return all(node in self.table.nodes for node in surrounding(latitude, longitude, self.step))

    def correction_at(self, latitude: float, longitude: float) -> CloudCorrection:
        """The correction for one point, or a refusal.

        Only the months all four nodes carry are kept. A month one of them
        lacks would otherwise be corrected from three nodes and a hole, which
        is a different correction wearing the same name.
        """
        corners = surrounding(latitude, longitude, self.step)
        missing = [node for node in corners if node not in self.table.nodes]
        if missing:
            raise OutsideCoverage(latitude, longitude, len(missing))

        corrections = [self.table.nodes[node] for node in corners]
        weights = _weights(latitude, longitude, self.step)

        shared = set(corrections[0].months)
        for correction in corrections[1:]:
            shared &= set(correction.months)

        months: dict[int, MonthlyCorrection] = {}
        for month in sorted(shared):
            parts = [correction.months[month] for correction in corrections]
            months[month] = MonthlyCorrection(
                reference=_blend([p.reference for p in parts], weights),
                model_past=_blend([p.model_past for p in parts], weights),
                model_future=_blend([p.model_future for p in parts], weights),
                levels=parts[0].levels,
            )
        return CloudCorrection(months)
