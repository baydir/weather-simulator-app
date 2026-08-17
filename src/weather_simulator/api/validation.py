"""What a request has to satisfy before anything is fetched or computed.

Two rules are worth stating out loud, the rest being bounds checks.

**Ninety-two days at most.** One whole season, and docs/application.md asks for
the bound in the interface *and* in the API, never in the browser alone — a limit
only the browser enforces is not a limit.

**The refusal outside the grid depends on the range, not on the place.** A
request reaching the climate model needs a correction and is refused where there
is none: showing an uncorrected future would mean showing an artificially sunny
one, and quietly borrowing the nearest node's coefficients would be worse still
— wrong without saying so.

**It stops there, and the boundary is the plan's own.** A range lying wholly in
the past calls for no coefficient, and neither does the fortnight ahead — that
one is ECMWF IFS, which needs no debiasing — so both are served everywhere in
the world, as docs/application.md requires. What decides is therefore not
"does this range pass today", which would refuse a forecast nothing corrects; it
is whether the plan carries a simulated segment at all. :func:`split_range` is
asked, rather than the horizon being worked out a second time here.

The refusal happens here, before the plan is handed out, so that a visitor does
not spend their Open-Meteo quota on a search that was never going to be served.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator

from weather_simulator.api import errors
from weather_simulator.calibration.grid import CorrectionGrid
from weather_simulator.sources import openmeteo
from weather_simulator.sources.series import split_range

# One season, and the number is measured rather than rounded: at the astronomical
# bounds the interface offers — the 21st — winter runs 90 days, autumn 91, spring
# and summer 92. Ninety was one season only by approximation, and it cut the two
# longest short. The bound is on the number of days shown, not on the span asked
# for, so both ends count.
MAX_DAYS = 92


class Search(BaseModel):
    """A location and a range of dates. What the accueil form produces."""

    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    start: date
    end: date

    @model_validator(mode="after")
    def _check_range(self) -> Search:
        if self.start > self.end:
            raise errors.EmptyRange(self.start, self.end)
        if self.start < openmeteo.COVERAGE_START or self.end > openmeteo.COVERAGE_END:
            raise errors.OutsideCoverageDates(self.start, self.end)
        days = (self.end - self.start).days + 1
        if days > MAX_DAYS:
            raise errors.RangeTooLong(days, MAX_DAYS)
        return self


class Fetched(Search):
    """The same search, with what the browser brought back.

    ``today`` comes from the plan the server handed out and is echoed back
    rather than recomputed, so that both halves of the exchange agree on where
    the observed stops and the simulated starts. It is checked, not trusted.
    """

    today: date
    payloads: dict[str, dict[str, Any]]


def refuse_uncovered(search: Search, today: date, grid: CorrectionGrid) -> None:
    """Refuse a range that needs a correction where the grid has none.

    The range is cut by the same function the plan is built from, and only its
    third part — the days the climate model would answer for — decides. A search
    reaching no further than the forecast carries none, so it is served wherever
    it is asked from.
    """
    _, _, simulated = split_range(search.start, search.end, today)
    if simulated is None:
        return
    if not grid.covers(search.latitude, search.longitude):
        raise errors.OutOfGrid(search.latitude, search.longitude)
