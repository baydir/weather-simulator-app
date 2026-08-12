"""Splitting the range, and assembling one series out of three sources.

Two seams, and they are not of the same kind.

The first sits wherever the reanalyses stop — five or six days back, a
documented latency rather than an outage. ECMWF IFS covers from there to today.
Both describe the same real days and differ only by a small offset, well inside
the day-to-day spread over so short a stretch. Its position is read from the
data, never assumed: a hard-coded number of days would be wrong as often as
right.

The second sits at the end of the forecast, a fortnight out. Beyond it the
climate model takes over, and what breaks there is not the level — the model is
bias-corrected — but the status of the series: it stops being weather and
becomes a plausible trajectory. No arithmetic hides that, and none should try.

**Tonight is not a seam.** IFS runs straight through it: the same system serves
the days the reanalyses missed and the days that have not happened. That is what
this segment is for. Putting the climate model at tomorrow, as this module used
to, meant the first simulated day was as unrelated to tomorrow's weather as the
last one is to 2050 — and unlike 2050, a reader can check tomorrow.

Its position is read from the data too. IFS may serve fewer days than asked for,
so the climate model is fetched in overlap from tomorrow onwards and trimmed to
what the forecast did not reach — the same treatment, and the same function, as
the first seam.

Neither the cloud-cover correction nor the sky class belongs here. They come at
steps 4 and 3, and both apply to the assembled series.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from weather_simulator.domain.records import DailyRecord, Origin
from weather_simulator.sources import openmeteo
from weather_simulator.sources.client import get_json
from weather_simulator.sources.errors import CoverageError, FetchError
from weather_simulator.sources.parse import DailyColumns, merge_columns, parse_daily

# Today is settled server-side, in one fixed zone, so that the seam does not
# move with the visitor's clock. This is not the zone the data is aggregated in
# — that one follows the location, see openmeteo.DEFAULT_TIMEZONE.
REFERENCE_ZONE = ZoneInfo("Europe/Paris")

DateRange = tuple[date, date]
Fetcher = Callable[[str, dict[str, object]], dict[str, Any]]


def today_in_reference_zone() -> date:
    return datetime.now(REFERENCE_ZONE).date()


def split_range(
    start: date, end: date, today: date
) -> tuple[DateRange | None, DateRange | None, DateRange | None]:
    """Cut ``[start, end]`` into what happened, what is forecast, and what is modelled.

    Today belongs to the observed part — IFS serves it with no latency, though
    the day is not over and its aggregate is therefore partly a forecast itself.

    The forecast part runs from tomorrow to ``FORECAST_DAYS`` out. The simulated
    part starts the day after, **but is deliberately asked for from tomorrow**:
    see :func:`forecast_overlap`. Callers wanting the request range use that;
    the third element here is where the climate model is expected to end up once
    the overlap has been settled.
    """
    if start > end:
        raise CoverageError(f"empty range: {start} is after {end}")
    if start < openmeteo.COVERAGE_START:
        raise CoverageError(f"{start} precedes the coverage start ({openmeteo.COVERAGE_START})")
    if end > openmeteo.COVERAGE_END:
        raise CoverageError(f"{end} exceeds the coverage end ({openmeteo.COVERAGE_END})")

    horizon = today + timedelta(days=openmeteo.FORECAST_DAYS)
    day = timedelta(days=1)

    def clipped(first: date, last: date) -> DateRange | None:
        """``[start, end]`` met with ``[first, last]``, or nothing if they miss.

        Written as an intersection rather than three separate conditions: a
        range wholly in 2047 clears ``end > today`` while beginning long after
        the forecast horizon, and the naive form yields an inverted interval —
        a request for a fortnight that ended twenty years before it started.
        """
        low, high = max(start, first), min(end, last)
        return (low, high) if low <= high else None

    return (
        clipped(openmeteo.COVERAGE_START, today),
        clipped(today + day, horizon),
        clipped(horizon + day, openmeteo.COVERAGE_END),
    )


def forecast_overlap(
    start: date, end: date, today: date, simulated: DateRange | None
) -> DateRange | None:
    """The range to actually ask the climate model for, forecast overlap included.

    IFS is asked for a fortnight but may return less, and where it stops is not
    knowable until it answers. Rather than a second round trip — impossible for
    the browser, which executes a plan built in one go — the climate model is
    asked from tomorrow and :func:`resume_after` drops whatever the forecast
    already covered. **The forecast wins wherever it served.**

    The extra fortnight costs nothing: it is one request either way.
    """
    if simulated is None:
        return None
    return (max(start, today + timedelta(days=1)), end)


def resume_after(columns: DailyColumns, boundary: date | None) -> DailyColumns:
    """Trim ``columns`` to the days strictly after ``boundary``.

    This is how the first seam is closed when the two segments were fetched
    without waiting for one another — the browser executes a plan built in one
    go, so IFS is asked for the whole stretch the reanalyses might not reach,
    and the overlap is settled here instead.

    **The reanalyses win wherever they served**, and the boundary is read from
    the days they actually returned, never from a number of days: the latency is
    five or six days, but a constant would be wrong as often as right. The
    outcome is the same series the sequential fetch produces; only the order of
    operations differs.
    """
    if boundary is None:
        return columns
    kept = sum(1 for day in columns.dates if day <= boundary)
    if not kept:
        return columns
    return DailyColumns(
        columns.dates[kept:],
        {field: column[kept:] for field, column in columns.columns.items()},
    )


def build_series(*segments: tuple[DailyColumns | None, Origin, str]) -> list[DailyRecord]:
    """Turn parsed columns into one chronological list of days."""
    records: list[DailyRecord] = []
    for columns, origin, source in segments:
        if columns is None:
            continue
        for index, day in enumerate(columns.dates):
            records.append(
                DailyRecord(
                    date=day,
                    origin=origin,
                    source=source,
                    **{field: values[index] for field, values in columns.columns.items()},
                )
            )
    records.sort(key=lambda record: record.date)
    return records


def _fetch_reanalyses(
    latitude: float,
    longitude: float,
    first: date,
    last: date,
    timezone: str,
    fetch: Fetcher,
) -> DailyColumns:
    """The two forced reanalyses, joined on the date.

    Two requests because the source is chosen per variable: ERA5-Land serves
    temperature and nothing else. Trailing days neither has caught up with are
    dropped, so the caller can see where they actually stop.
    """
    url, params = openmeteo.archive_temperature_request(latitude, longitude, first, last, timezone)
    temperature = parse_daily(
        fetch(url, params),
        openmeteo.TEMPERATURE_VARIABLES,
        source=openmeteo.TEMPERATURE_MODEL,
        model=openmeteo.TEMPERATURE_MODEL,
        allow_trailing_gap=True,
    )
    url, params = openmeteo.archive_surface_request(latitude, longitude, first, last, timezone)
    surface = parse_daily(
        fetch(url, params),
        openmeteo.SURFACE_VARIABLES,
        source=openmeteo.SURFACE_MODEL,
        model=openmeteo.SURFACE_MODEL,
        allow_trailing_gap=True,
        optional=openmeteo.OPTIONAL_VARIABLES,
    )
    return merge_columns(temperature, surface, source="archive")


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

    Up to five requests, and only for the segments the range actually meets:
    two for the reanalyses, one for IFS on the archive, one for IFS ahead, one
    for the climate model.

    ``fetch`` is injected so the assembly can be tested without a network, and
    so a caller doing bulk collection can slot in its own pacing.
    """
    today = today or today_in_reference_zone()
    observed, ahead, simulated = split_range(start, end, today)

    reanalysed: DailyColumns | None = None
    recent: DailyColumns | None = None
    if observed is not None:
        first, last = observed
        reanalysed_end = min(last, today - timedelta(days=1))
        if first <= reanalysed_end:
            reanalysed = _fetch_reanalyses(
                latitude, longitude, first, reanalysed_end, timezone, fetch
            )

        # Wherever the reanalyses stopped, IFS resumes the next day.
        served = reanalysed.dates if reanalysed else []
        resume = served[-1] + timedelta(days=1) if served else first
        resume = max(resume, openmeteo.RECENT_START)
        if resume <= last:
            url, params = openmeteo.archive_recent_request(
                latitude, longitude, resume, last, timezone
            )
            recent = parse_daily(
                fetch(url, params),
                openmeteo.ALL_VARIABLES,
                source=openmeteo.RECENT_MODEL,
                model=openmeteo.RECENT_MODEL,
                optional=openmeteo.OPTIONAL_VARIABLES,
            )

    forecast: DailyColumns | None = None
    if ahead is not None:
        first, last = ahead
        url, params = openmeteo.forecast_request(latitude, longitude, first, last, timezone)
        forecast = parse_daily(
            fetch(url, params),
            openmeteo.ALL_VARIABLES,
            source=openmeteo.FORECAST_MODEL,
            model=openmeteo.FORECAST_MODEL,
            # The forecast may be cut short of the fortnight asked for. That is
            # the seam moving, not a gap: the climate model picks up from there.
            allow_trailing_gap=True,
            optional=openmeteo.OPTIONAL_VARIABLES,
        )

    projected: DailyColumns | None = None
    overlap = forecast_overlap(start, end, today, simulated)
    if overlap is not None:
        first, last = overlap
        url, params = openmeteo.climate_request(latitude, longitude, first, last, model, timezone)
        projected = parse_daily(
            fetch(url, params),
            openmeteo.ALL_VARIABLES,
            source=model,
            model=model,
            optional=openmeteo.OPTIONAL_VARIABLES,
        )
        # The forecast wins wherever it served, exactly as the reanalyses do
        # against IFS at the first seam.
        if forecast is not None and forecast.dates:
            projected = resume_after(projected, forecast.dates[-1])

    series = build_series(
        (reanalysed, Origin.OBSERVED, "reanalysis"),
        (recent, Origin.OBSERVED, openmeteo.RECENT_MODEL),
        (forecast, Origin.FORECAST, openmeteo.FORECAST_MODEL),
        (projected, Origin.SIMULATED, model),
    )
    if not series:
        raise FetchError(f"no source returned any day for {start}..{end}")
    return series
