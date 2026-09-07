"""What a request has to satisfy before anything is fetched or computed.

One rule is worth stating out loud, the rest being bounds checks — and one
absence, which used to be a rule and no longer is.

**Ninety-two days at most.** One whole season, and docs/application.md asks for
the bound in the interface *and* in the API, never in the browser alone — a limit
only the browser enforces is not a limit.

**Nothing here looks at the correction grid any more, and that is a deliberate
retreat.** A search reaching past the forecast used to be refused wherever the
grid had no nodes, which meant refused everywhere but metropolitan France. The
project owner chose an answer over a refusal: outside the grid the projection is
served raw. Where the days are corrected is therefore no longer a matter of
validation at all — it is decided at the moment the correction is resolved, in
:mod:`weather_simulator.api.app`, and carried explicitly to the pipeline.

What survives here is what a request must satisfy whatever the place: the two
bounds above. A search is now refused only for what it asks, never for where it
asks it.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, model_validator

from weather_simulator.api import errors
from weather_simulator.sources import openmeteo

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

