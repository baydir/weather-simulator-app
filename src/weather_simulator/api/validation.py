"""What a request has to satisfy before anything is fetched or computed.

Two rules are worth stating out loud, the rest being bounds checks.

**Ninety days at most.** One season, and docs/application.md asks for the bound
in the interface *and* in the API, never in the browser alone — a limit only the
browser enforces is not a limit.

**The refusal outside the grid depends on the range, not on the place.** A
request touching the future needs a correction and is refused where there is
none: showing an uncorrected future would mean showing an artificially sunny
one, and quietly borrowing the nearest node's coefficients would be worse still
— wrong without saying so. But a range lying wholly in the past calls for no
coefficient at all, so refusing it would be gratuitous, and would deny someone
in Santiago the weather history of their own city for no reason.

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

# One season. The bound is on the number of days shown, not on the span asked
# for, so both ends count.
MAX_DAYS = 90


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
            raise errors.RangeTooLong(days)
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
    """Refuse a range that needs a correction where the grid has none."""
    if search.end <= today:
        return
    if not grid.covers(search.latitude, search.longitude):
        raise errors.OutOfGrid(search.latitude, search.longitude)
