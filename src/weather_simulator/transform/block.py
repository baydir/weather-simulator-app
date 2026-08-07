"""The transformation block: the control point over the weather data.

**This module is deliberately empty of behaviour.** It exists so that later
adjustments to the data have one obvious place to live, rather than being
scattered through the pipeline where nobody would find them again. Whatever
goes in here is a data-treatment decision and belongs to the project owner —
CLAUDE.md rule 4 reserves that, and an empty function is how the reservation is
made visible in the code.

**Where it sits, and why there.** The pipeline calls it after the cloud-cover
correction and before the sky class. That placement is the one that gives it the
most reach: a value it changes still flows into the decision tree, so a
transformation can change a pictogram. Placing it after the classification would
have made it cosmetic.

**What it must preserve**, since the rest of the chain assumes it:

- one record per day of the input, in the same chronological order — the
  contract promises the range that was asked for;
- ``origin`` untouched. It is what tells the interface a day is simulated, and
  the warning on future dates hangs off it;
- the homogeneity rule of CLAUDE.md. A quantity adjusted on the observed days
  only, or on the simulated days only, would reintroduce a step at the very seam
  the whole of ``sources`` works to erase. Whatever this block does, it must do
  it the same way on both sides — the cloud correction is the single, documented
  exception, and it is applied before this point rather than here.
"""

from __future__ import annotations

from weather_simulator.domain.records import DailyRecord


def apply(records: list[DailyRecord]) -> list[DailyRecord]:
    """Return the series unchanged.

    The neutral block. Every day of the assembled series passes through here,
    observed and simulated alike, and comes out as it went in.
    """
    return records
