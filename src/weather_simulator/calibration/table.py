"""The shipped correction table: what is in it, and what it refuses to hide.

One entry per grid node, and inside each, twelve months carrying the three
quantile vectors quantile delta mapping needs — the reanalysis over the
calibration period, the model over that same period, and the model over the
projection. The design document calls this a table of coefficients; it is not
quite that, and the difference is the method's doing. A correction that works
quantile by quantile cannot be summarised as one number per month.

The metadata is not decoration. A table says which period it was calibrated on,
which model it corrects, when it was generated and how far it reaches — because
a table read without knowing those things is a silent source of error, and the
grid is precisely the piece a future maintainer will inherit without having
watched it being built.

**A placeholder table is marked as such and shouts about it.** Development needs
the pipeline to run before the collection ends, so a neutral table — one whose
correction returns its input untouched — exists for that. But an uncorrected
future is an artificially sunny future, which is the very thing docs/regles.md
exists to prevent, so the flag travels with the data and the loader refuses to let it
pass unnoticed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from weather_simulator.domain.correction import (
    LEVELS,
    CloudCorrection,
    MonthlyCorrection,
)

# How many decimals a node's coordinates carry, in the file and in memory alike.
#
# **One number for two operations that have to agree.** :meth:`CorrectionTable.write`
# spells a key with it and :func:`grid.surrounding` rounds a computed corner with
# it; a node whose two spellings differ is a node the lookup cannot find, and the
# symptom is a place refused for no visible reason. It stood as a bare ``.1f``
# here and a bare ``1`` there, which is CLAUDE.md rule 3 across two modules — and
# the pair only happens to hold because the grid steps by half a degree.
NODE_DECIMALS = 1


class GridError(Exception):
    """Base class for every failure the correction grid raises."""


class OutsideCoverage(GridError):
    """The point is not surrounded by four known nodes.

    Raised rather than falling back on the nearest node. Section 4 is explicit:
    outside the covered area the search is refused with a message, because
    showing an uncorrected future would not be neutral and quietly borrowing a
    neighbour's correction would be worse — it would be wrong without saying so.
    """

    def __init__(self, latitude: float, longitude: float, missing: int) -> None:
        super().__init__(
            f"{latitude:.4f}, {longitude:.4f} is not covered: "
            f"{missing} of the 4 surrounding nodes are missing"
        )
        self.latitude = latitude
        self.longitude = longitude
        self.missing = missing


@dataclass(frozen=True, slots=True)
class Metadata:
    """What a reader needs to judge the table without having built it."""

    model: str
    calibration_start: date
    calibration_end: date
    projection_start: date
    projection_end: date
    step: float
    generated: date
    node_count: int
    # True when the corrections are identity. Development fixture, never shipped.
    placeholder: bool = False
    note: str = ""

    def as_json(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "calibration_start": self.calibration_start.isoformat(),
            "calibration_end": self.calibration_end.isoformat(),
            "projection_start": self.projection_start.isoformat(),
            "projection_end": self.projection_end.isoformat(),
            "step": self.step,
            "generated": self.generated.isoformat(),
            "node_count": self.node_count,
            "placeholder": self.placeholder,
            "note": self.note,
        }

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> Metadata:
        return cls(
            model=raw["model"],
            calibration_start=date.fromisoformat(raw["calibration_start"]),
            calibration_end=date.fromisoformat(raw["calibration_end"]),
            projection_start=date.fromisoformat(raw["projection_start"]),
            projection_end=date.fromisoformat(raw["projection_end"]),
            step=float(raw["step"]),
            generated=date.fromisoformat(raw["generated"]),
            node_count=int(raw["node_count"]),
            placeholder=bool(raw.get("placeholder", False)),
            note=raw.get("note", ""),
        )


@dataclass(frozen=True, slots=True)
class CorrectionTable:
    """Nodes keyed by their exact coordinates, plus the metadata."""

    metadata: Metadata
    nodes: dict[tuple[float, float], CloudCorrection] = field(default_factory=dict)

    def write(self, path: Path) -> None:
        """Serialise. Quantiles are rounded to a tenth of a point of cloud.

        Cloud cover is a percentage of sky read against thresholds ten points
        apart; a tenth is already finer than anything downstream can use, and
        it keeps the shipped file to a size worth loading into memory.
        """
        payload = {
            "metadata": self.metadata.as_json(),
            "levels": list(LEVELS),
            "nodes": {
                f"{lat:.{NODE_DECIMALS}f},{lon:.{NODE_DECIMALS}f}": {
                    str(month): {
                        "reference": [round(v, 1) for v in monthly.reference],
                        "model_past": [round(v, 1) for v in monthly.model_past],
                        "model_future": [round(v, 1) for v in monthly.model_future],
                    }
                    for month, monthly in correction.months.items()
                }
                for (lat, lon), correction in self.nodes.items()
            },
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> CorrectionTable:
        raw = json.loads(path.read_text(encoding="utf-8"))
        levels = tuple(raw["levels"])
        nodes: dict[tuple[float, float], CloudCorrection] = {}
        for key, months in raw["nodes"].items():
            latitude, longitude = (float(part) for part in key.split(","))
            nodes[(latitude, longitude)] = CloudCorrection(
                {
                    int(month): MonthlyCorrection(
                        reference=grids["reference"],
                        model_past=grids["model_past"],
                        model_future=grids["model_future"],
                        levels=levels,
                    )
                    for month, grids in months.items()
                }
            )
        return cls(Metadata.from_json(raw["metadata"]), nodes)
