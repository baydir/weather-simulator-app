"""From an assembled series to the JSON contract: three steps, in this order.

1. **Cloud-cover correction, on the simulated days alone.** The past is what
   happened; only the projection is corrected.
2. **The transformation block**, on the whole series. Neutral by default, and
   the project owner's to fill.
3. **The sky class and the wet bulb, on all four segments, through one function
   each.** Those single call sites are the point of the module. The old past, the recent past, the
   fortnight ahead and the far future are classified by the same code path, or
   the seams that ``sources`` works to erase reappear here, one branch at a
   time. The count went from three to four the day the forecast became a
   segment, and nothing here had to change — which is the point.

The order is not interchangeable. The correction comes first because the class
turns on cloud cover, and classifying before correcting would fix the pictogram
to a number that is about to change. The transformation block comes second so
that what it changes can still reach the decision tree — placed after the
classification it would be cosmetic.

**What this module refuses to do is invent.** A day missing a variable the rule
needs comes out with ``sky: null`` rather than a guess.

**Outside the correction grid the projection is served raw, and only because the
caller says so.** The grid reaches metropolitan France and its surroundings;
everywhere else the alternative to a raw model was no answer at all, and the
project owner chose the answer. The shortfall is real and it is not hidden here:
the model runs 8 to 11 points short of cloud cover, so an uncorrected sky is too
bright, and the band lightens where the forecast hands over to the simulation.
What is refused is that this happen *silently* — see :func:`correct`.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from weather_simulator.api import errors
from weather_simulator.api.contract import Day, Grid, Series
from weather_simulator.calibration.table import Metadata
from weather_simulator.domain.correction import CloudCorrection
from weather_simulator.domain.heat_counts import summarize
from weather_simulator.domain.records import DailyRecord, Origin
from weather_simulator.domain.sky import classify_record
from weather_simulator.domain.temperature_means import period_means
from weather_simulator.transform import block


def correct(
    records: list[DailyRecord],
    correction: CloudCorrection | None,
    *,
    outside_grid: bool = False,
) -> list[DailyRecord]:
    """Apply the cloud-cover correction to the simulated days, and to those only.

    ``correction`` is resolved once for the whole request — the four surrounding
    nodes are blended, then the result is applied day by day. That order matters
    and docs/application.md fixes it: correcting at the four nodes and averaging
    the outcomes would give a different, discontinuous field, in which moving a
    few hundred metres could flip a day's sky class.

    **A missing correction is not treated as an identity, unless asked.** Serving
    a simulated day uncorrected shows a future artificially sunny by 8 to 11
    points, and three of the five sky classes hang off that number. Where the
    grid does reach, a correction that failed to arrive is a bug, and it stops
    the request.

    ``outside_grid`` is how the caller says the opposite: this place has no
    nodes, the raw model is what was chosen over refusing, and the pass-through
    is deliberate. The flag exists rather than a bare ``None`` because the two
    situations look identical from here and must not be confused — dropping the
    guard to serve the world would also mean serving a French search silently
    uncorrected the day something upstream broke.
    """
    simulated = [record for record in records if record.origin is Origin.SIMULATED]
    if not simulated:
        return records
    if correction is None:
        if outside_grid:
            return records
        raise errors.UncorrectedFuture(len(simulated))

    out: list[DailyRecord] = []
    for record in records:
        if record.origin is not Origin.SIMULATED:
            out.append(record)
            continue
        try:
            corrected = correction.apply(record.cloud_cover, record.date.month)
        except KeyError as error:
            raise errors.UncoveredMonth(record.date.month) from error
        out.append(replace(record, cloud_cover=corrected))
    return out


def run(
    records: list[DailyRecord],
    *,
    latitude: float,
    longitude: float,
    correction: CloudCorrection | None = None,
    metadata: Metadata | None = None,
    requested_start: date | None = None,
    requested_end: date | None = None,
    outside_grid: bool = False,
) -> Series:
    """The whole chain, from the assembled series to what the browser receives.

    ``metadata`` describes the table ``correction`` came from and is reported as
    it stands. It is left out when nothing was corrected, which is the honest
    answer in two cases now: a range lying entirely in the past, to which no
    table applied, and a place outside the grid, where none exists. The response
    carries ``grid: null`` in both, and that is the only signal the interface
    gets that a simulation was served raw — ``has_simulated`` stays true, so the
    warning rule 1 requires is unaffected.

    ``outside_grid`` travels through to :func:`correct` unchanged; the decision
    it carries is the caller's, this function only refuses to make it silently.

    The reported range is the one the sources actually served, not the one that
    was asked for. The two differ whenever a source stops short, and saying so
    is better than implying a coverage that is not there.
    """
    if not records:
        raise ValueError("no records to serve")

    corrected = correct(records, correction, outside_grid=outside_grid)
    transformed = block.apply(corrected)
    days = [Day.from_record(record, classify_record(record)) for record in transformed]

    has_simulated = any(record.origin is Origin.SIMULATED for record in transformed)
    # The strip reserves its humid-heat line on every card or on none, so what it
    # needs is one number for the whole range rather than a scan of the days it
    # already holds. Read here for the same reason has_simulated is: the server
    # has been through every day, and a second pass in the browser would be the
    # duplication rule 3 is about wearing a loop rather than a threshold.
    humid_heat_peak = max((day.humid_heat or 0 for day in days), default=0)
    return Series(
        latitude=latitude,
        longitude=longitude,
        start=days[0].date,
        end=days[-1].date,
        has_simulated=has_simulated,
        humid_heat_peak=humid_heat_peak,
        grid=Grid.from_metadata(metadata) if has_simulated and metadata else None,
        heat_counts=summarize(transformed),
        temperature_means=period_means(
            transformed, requested_start or days[0].date, requested_end or days[-1].date,
        ),
        days=days,
    )
