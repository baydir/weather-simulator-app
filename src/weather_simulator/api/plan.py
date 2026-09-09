"""The request plan: what the browser is told to fetch, and how it is read back.

The browser fetches the data because Open-Meteo limits per IP address — a server
doing it would funnel every visitor through one address and hit the ceiling at
once, which happened from a single machine during the preparatory work. But
*choosing* what to ask for stays here: :func:`build` is called again from
``/api/days`` to check the payloads against the search, so a copy of it in
JavaScript would be a second live version of the same rule — cutting the range at
tonight, picking the models, knowing that the old past takes two requests because
the source is chosen per variable.

So the server does the choosing and hands over finished URLs. The browser calls
``fetch`` on each and posts the answers back, and ``openmeteo.py`` stays the only
place that knows this API exists.

**Each segment carries both how to ask and how to read.** They sit in one object
on purpose: a plan and a parser that disagree about which variables a request
carried would fail in the least visible way possible — a column silently absent.

**Two segments are asked for in overlap, for the same reason.** Neither seam's
position is knowable while the plan is being built, and the browser executes the
plan in one go — there is no second round trip to be had. So both boundaries are
settled on the way back, by :func:`sources.series.resume_after`, and the earlier
source wins wherever it served.

- IFS is asked for the whole post-2017 stretch of the range, rather than a
  hard-coded latency that docs/donnees.md forbids. The reanalyses win.
- The climate model is asked from tomorrow, rather than from the end of the
  fortnight the forecast was asked for: IFS may return fewer days than that, and
  the seam belongs where it actually stopped. The forecast wins.

Same series either way, and the overlap costs nothing — one request covers it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from weather_simulator.domain.records import DailyRecord, Origin
from weather_simulator.sources import openmeteo
from weather_simulator.sources.client import get_json
from weather_simulator.sources.errors import FetchError
from weather_simulator.sources.parse import DailyColumns, merge_columns, parse_daily
from weather_simulator.sources.series import (
    build_series,
    forecast_overlap,
    resume_after,
    split_range,
    today_in_reference_zone,
)

# What an offline caller has to supply to run a plan: a finished URL in, the
# decoded payload out. The browser's own contract, which is the point — the
# segment carries a URL and nothing else, so nothing downstream can ask for a
# request that was not planned.
Fetcher = Callable[[str], dict[str, Any]]

TEMPERATURE = "reanalysis_temperature"
SURFACE = "reanalysis_surface"
RECENT = "recent"
FORECAST = "forecast"
PROJECTION = "projection"


@dataclass(frozen=True, slots=True)
class Segment:
    """One planned request: the URL to call, and the way to read the answer."""

    id: str
    url: str
    variables: dict[str, str]
    model: str
    origin: Origin
    allow_trailing_gap: bool = False


@dataclass(frozen=True, slots=True)
class Plan:
    """Everything the browser needs, and everything needed to read it back."""

    today: date
    model: str
    segments: tuple[Segment, ...]

    @property
    def ids(self) -> set[str]:
        return {segment.id for segment in self.segments}


def build(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    today: date,
    *,
    model: str = openmeteo.DEFAULT_MODEL,
    timezone: str = openmeteo.DEFAULT_TIMEZONE,
) -> Plan:
    """The requests covering ``[start, end]`` at one point — one to five of them.

    Only the segments the range actually meets are planned. A range lying wholly
    before 2017 gets no IFS request; one lying wholly inside the fortnight ahead
    gets nothing but the forecast, and therefore needs no correction table.
    """
    observed, ahead, simulated = split_range(start, end, today)
    segments: list[Segment] = []

    if observed is not None:
        first, last = observed

        # The reanalyses stop at yesterday at the latest — today is not a day
        # they have any claim on, and IFS serves it with no latency.
        reanalysed_end = min(last, today - timedelta(days=1))
        if first <= reanalysed_end:
            segments.append(
                Segment(
                    id=TEMPERATURE,
                    url=openmeteo.encode(
                        *openmeteo.archive_temperature_request(
                            latitude, longitude, first, reanalysed_end, timezone
                        )
                    ),
                    variables=openmeteo.TEMPERATURE_REQUEST_VARIABLES,
                    model=openmeteo.TEMPERATURE_MODEL,
                    origin=Origin.OBSERVED,
                    allow_trailing_gap=True,
                )
            )
            segments.append(
                Segment(
                    id=SURFACE,
                    url=openmeteo.encode(
                        *openmeteo.archive_surface_request(
                            latitude, longitude, first, reanalysed_end, timezone
                        )
                    ),
                    variables=openmeteo.SURFACE_VARIABLES,
                    model=openmeteo.SURFACE_MODEL,
                    origin=Origin.OBSERVED,
                    allow_trailing_gap=True,
                )
            )

        # Asked for in overlap: where the reanalyses stop is not knowable here.
        resume = max(first, openmeteo.RECENT_START)
        if resume <= last:
            segments.append(
                Segment(
                    id=RECENT,
                    url=openmeteo.encode(
                        *openmeteo.archive_recent_request(
                            latitude, longitude, resume, last, timezone
                        )
                    ),
                    variables=openmeteo.ALL_VARIABLES,
                    model=openmeteo.RECENT_MODEL,
                    origin=Origin.OBSERVED,
                )
            )

    if ahead is not None:
        first, last = ahead
        segments.append(
            Segment(
                id=FORECAST,
                url=openmeteo.encode(
                    *openmeteo.forecast_request(latitude, longitude, first, last, timezone)
                ),
                variables=openmeteo.ALL_VARIABLES,
                model=openmeteo.FORECAST_MODEL,
                origin=Origin.FORECAST,
                # A forecast cut short of the fortnight is the seam moving, not
                # a gap: the climate model resumes from wherever it stopped.
                allow_trailing_gap=True,
            )
        )

    # Asked for from tomorrow, not from the end of the forecast: where IFS
    # actually stops is not knowable here.
    overlap = forecast_overlap(start, end, today, simulated)
    if overlap is not None:
        first, last = overlap
        segments.append(
            Segment(
                id=PROJECTION,
                url=openmeteo.encode(
                    *openmeteo.climate_request(latitude, longitude, first, last, model, timezone)
                ),
                variables=openmeteo.ALL_VARIABLES,
                model=model,
                origin=Origin.SIMULATED,
            )
        )

    return Plan(today=today, model=model, segments=tuple(segments))


def assemble(plan: Plan, payloads: dict[str, dict[str, Any]]) -> list[DailyRecord]:
    """Read the fetched payloads back into one chronological series.

    The same assembly the offline path performs, reached from the other side:
    the two reanalyses joined on the date, IFS trimmed to what they did not
    reach, the forecast appended, the projection trimmed to what the forecast
    did not reach.
    """
    parsed: dict[str, DailyColumns] = {
        segment.id: parse_daily(
            payloads[segment.id],
            segment.variables,
            source=segment.model,
            model=segment.model,
            allow_trailing_gap=segment.allow_trailing_gap,
            optional=openmeteo.OPTIONAL_VARIABLES,
        )
        for segment in plan.segments
    }

    reanalysed: DailyColumns | None = None
    if TEMPERATURE in parsed:
        reanalysed = merge_columns(parsed[TEMPERATURE], parsed[SURFACE], source="archive")

    recent = parsed.get(RECENT)
    if recent is not None and reanalysed is not None and reanalysed.dates:
        recent = resume_after(recent, reanalysed.dates[-1])

    forecast = parsed.get(FORECAST)
    projected = parsed.get(PROJECTION)
    if projected is not None and forecast is not None and forecast.dates:
        projected = resume_after(projected, forecast.dates[-1])

    return build_series(
        (reanalysed, Origin.OBSERVED, "reanalysis"),
        (recent, Origin.OBSERVED, openmeteo.RECENT_MODEL),
        (forecast, Origin.FORECAST, openmeteo.FORECAST_MODEL),
        (projected, Origin.SIMULATED, plan.model),
    )


def fetch_series(
    latitude: float,
    longitude: float,
    start: date,
    end: date,
    *,
    model: str = openmeteo.DEFAULT_MODEL,
    timezone: str = openmeteo.DEFAULT_TIMEZONE,
    today: date | None = None,
    fetch: Fetcher = get_json,
) -> list[DailyRecord]:
    """Retrieve ``[start, end]`` at one point as a single homogeneous series.

    **The offline path, and it is the online one with the round trip closed
    here.** It used to be a second implementation living in ``sources.series``:
    the same range split the same way, the same models chosen, the same two
    seams settled — written out twice, once for the browser to execute and once
    for a script. They had already begun to drift where nothing yet depended on
    it. CLAUDE.md rule 3 asks for one live version of a rule, and this is what
    that costs: three lines instead of seventy.

    **It fetches the plan's own URLs**, not requests rebuilt from the same
    arguments, so there is no second spelling either. What a script gets is
    therefore exactly what a visitor gets, down to the query string.

    ``fetch`` is injected so the assembly can be tested without a network, and
    so a caller doing bulk collection can slot in its own pacing. It receives a
    finished URL and returns the decoded payload — the browser's contract.

    The requests are run in order and one at a time, as the browser runs them:
    three or four of them landing at once from a single address is what
    Open-Meteo's rate limiter watches for.
    """
    built = build(
        latitude,
        longitude,
        start,
        end,
        today or today_in_reference_zone(),
        model=model,
        timezone=timezone,
    )
    series = assemble(built, {segment.id: fetch(segment.url) for segment in built.segments})
    if not series:
        # Not reachable through the API, which raises earlier and in French.
        # Kept for the caller that has no visitor to answer to: a script asking
        # for a range every source declined should say so, not print nothing.
        raise FetchError(f"no source returned any day for {start}..{end}")
    return series
