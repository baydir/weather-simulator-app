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

**Nothing here fetches, and nothing here knows how many requests a range takes.**
This module holds the arithmetic of the two seams and nothing else — where a
range is cut, what a segment resumes after, how parsed columns become records.
Which requests cover a range, and running them, is ``api.plan``, and it is one
place rather than two: an offline copy of the same choices lived here until it
had begun to drift from the one the browser executes.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from weather_simulator.domain.records import DailyRecord, Origin
from weather_simulator.sources import openmeteo
from weather_simulator.sources.errors import CoverageError
from weather_simulator.sources.parse import DailyColumns

# Today is settled server-side, in one fixed zone, so that the seam does not
# move with the visitor's clock. This is not the zone the data is aggregated in
# — that one follows the location, see openmeteo.DEFAULT_TIMEZONE.
REFERENCE_ZONE = ZoneInfo("Europe/Paris")

DateRange = tuple[date, date]


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


