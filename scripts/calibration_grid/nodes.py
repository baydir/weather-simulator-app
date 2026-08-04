"""Which nodes the grid holds, and which of them are worth collecting.

The mesh is a fixed worldwide 0.5-degree lattice anchored on exact multiples
from -180 and -90. That anchoring is not a detail: centring the grid on France
would mean recomputing everything at the first extension, and the table is
expensive enough to build once.

Half a degree rather than one was settled by measurement. Along three transects
crossing the coast at 0.25-degree steps, linear interpolation between nodes one
degree apart errs by up to 1.02 points of cloud cover, against 0.73 at half a
degree. Small on average — France is mostly flat — but the error concentrates
where the ground rises, and that is exactly where the model is least reliable
already. The coast itself turns out to be innocent: the bias does not jump when
crossing it. Relief does.

**Sea nodes are kept.** A town on the coast has sea nodes among the four
surrounding it, and refusing to collect them would leave the interpolation
short precisely where people live. Only open sea more than one cell from land
is dropped, which is what the elevation probe is for.
"""

from __future__ import annotations

from dataclasses import dataclass

STEP = 0.5

# Metropolitan France including Corsica, widened to the enclosing nodes so that
# any point inside has its four neighbours available.
SOUTH, NORTH = 41.0, 51.5
WEST, EAST = -5.5, 10.0


@dataclass(frozen=True, slots=True, order=True)
class Node:
    """A grid node. Latitude and longitude are exact multiples of ``STEP``."""

    latitude: float
    longitude: float

    @property
    def key(self) -> str:
        """Filename-safe identifier, stable across runs and platforms."""
        return f"{self.latitude:+06.1f}_{self.longitude:+06.1f}"


def _steps(low: float, high: float) -> list[float]:
    count = round((high - low) / STEP)
    return [round(low + STEP * i, 1) for i in range(count + 1)]


def bounding_nodes() -> list[Node]:
    """Every node of the worldwide lattice falling inside the French box."""
    return [
        Node(latitude, longitude)
        for latitude in _steps(SOUTH, NORTH)
        for longitude in _steps(WEST, EAST)
    ]


def neighbours(node: Node) -> list[Node]:
    """The eight nodes around one, used to keep the coastal ring."""
    return [
        Node(round(node.latitude + STEP * dy, 1), round(node.longitude + STEP * dx, 1))
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
        if (dy, dx) != (0, 0)
    ]


def worth_collecting(elevations: dict[Node, float]) -> list[Node]:
    """Land nodes, plus the ring of sea nodes touching them.

    ERA5 reports an elevation of zero over the sea, so the probe separates the
    two at the cost of one one-day request per node. A node kept only because
    it touches land is what makes a seaside town interpolable.
    """
    land = {node for node, elevation in elevations.items() if elevation > 0}
    kept = set(land)
    for node in land:
        kept.update(n for n in neighbours(node) if n in elevations)
    return sorted(kept)
