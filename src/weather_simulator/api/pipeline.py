"""From an assembled series to the JSON contract: three steps, in this order.

1. **Cloud-cover correction, on the simulated days alone.** The past is what
   happened; only the projection is corrected.
2. **The transformation block**, on the whole series. Neutral by default, and
   the project owner's to fill.
3. **The sky class, on all four segments, through one function.** That single
   call site is the point of the module. The old past, the recent past, the
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
needs comes out with ``sky: null`` rather than a guess, and a simulated day that
finds no correction waiting for it stops the request instead of being served
raw.
"""

from __future__ import annotations

from dataclasses import replace

from weather_simulator.api import errors
from weather_simulator.api.contract import Day, Grid, Series
from weather_simulator.calibration.table import Metadata
from weather_simulator.domain.correction import CloudCorrection
from weather_simulator.domain.records import DailyRecord, Origin
from weather_simulator.domain.sky import classify_record
from weather_simulator.transform import block


def correct(records: list[DailyRecord], correction: CloudCorrection | None) -> list[DailyRecord]:
    """Apply the cloud-cover correction to the simulated days, and to those only.

    ``correction`` is resolved once for the whole request — the four surrounding
    nodes are blended, then the result is applied day by day. That order matters
    and docs/application.md fixes it: correcting at the four nodes and averaging
    the outcomes would give a different, discontinuous field, in which moving a
    few hundred metres could flip a day's sky class.

    A missing correction is not treated as an identity. Serving a simulated day
    uncorrected shows a future that is artificially sunny by 8 to 11 points, so
    it raises instead.
    """
    simulated = [record for record in records if record.origin is Origin.SIMULATED]
    if not simulated:
        return records
    if correction is None:
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
) -> Series:
    """The whole chain, from the assembled series to what the browser receives.

    ``metadata`` describes the table ``correction`` came from and is reported as
    it stands. It is left out when nothing was corrected, which is the honest
    answer for a range lying entirely in the past: no table applied to it.

    The reported range is the one the sources actually served, not the one that
    was asked for. The two differ whenever a source stops short, and saying so
    is better than implying a coverage that is not there.
    """
    if not records:
        raise ValueError("no records to serve")

    corrected = correct(records, correction)
    transformed = block.apply(corrected)
    days = [Day.from_record(record, classify_record(record)) for record in transformed]

    has_simulated = any(record.origin is Origin.SIMULATED for record in transformed)
    return Series(
        latitude=latitude,
        longitude=longitude,
        start=days[0].date,
        end=days[-1].date,
        has_simulated=has_simulated,
        grid=Grid.from_metadata(metadata) if has_simulated and metadata else None,
        days=days,
    )
