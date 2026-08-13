"""Correcting the model's cloud cover without flattening what it has to say.

The model is short of the reanalysis by 8 to 11 points of cloud cover, and the
shortfall is **not a constant**: measured decile by decile it spans 4 to 20
points, largest on clear days and vanishing on overcast ones — the model cannot
exceed 100 %, so it converges at the top and manufactures too many cloudless
days at the bottom. A single monthly offset would therefore leave the classes
wrong exactly where the clear/cloudy boundary sits.

So the correction works quantile by quantile. The naive way to do that is to
force the future distribution onto the observed one, and it is wrong for this
project: it would erase whatever change the model projects, which is the one
thing the application exists to show.

What is used instead is quantile delta mapping (Cannon, Sobie & Murdock, 2015).
A future day is placed in the model's *future* distribution; the shift the model
itself gives that quantile between its past and its future is measured; and that
shift is carried onto the reference distribution. The bias goes, the change
stays.

On the sites measured the change is small — one to two points of cloud over
thirty years, against a bias of eight to eleven. The method is not chosen for
what it wins here. It is chosen because a method picked on the grounds that the
trend happens to be negligible in France would silently erase a real signal in
the subtropics, where RCP8.5 dries the sky considerably, and the grid is meant
to reach them at step 8.

**Nothing here touches the observed segments.** The past is what happened; only
the projection is corrected.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass

# The quantile levels every distribution is summarised on. Fine enough to follow
# a bias that moves by 20 points across the deciles, coarse enough that the
# shipped table stays small — the grid carries three of these per month per node.
LEVELS: tuple[float, ...] = tuple(round(0.025 * i, 3) for i in range(1, 40))

CLOUD_MIN, CLOUD_MAX = 0.0, 100.0


def quantiles(values: list[float], levels: tuple[float, ...] = LEVELS) -> list[float]:
    """Summarise a sample on ``levels``, by linear interpolation between order statistics."""
    if not values:
        raise ValueError("no values to summarise")
    ordered = sorted(values)
    if len(ordered) == 1:
        return [ordered[0]] * len(levels)

    out = []
    for level in levels:
        position = level * (len(ordered) - 1)
        lower = int(position)
        upper = min(lower + 1, len(ordered) - 1)
        out.append(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower))
    return out


def _interpolate(grid: list[float], levels: tuple[float, ...], level: float) -> float:
    """Value of a distribution at ``level``, the inverse CDF."""
    if level <= levels[0]:
        return grid[0]
    if level >= levels[-1]:
        return grid[-1]
    index = bisect_left(levels, level)
    lower, upper = levels[index - 1], levels[index]
    span = upper - lower
    weight = 0.0 if span == 0 else (level - lower) / span
    return grid[index - 1] + (grid[index] - grid[index - 1]) * weight


def _level_of(grid: list[float], levels: tuple[float, ...], value: float) -> float:
    """Where ``value`` falls in a distribution, the CDF.

    Flat stretches are common here: cloud cover piles up at 0 and at 100, so a
    run of identical quantiles is the rule rather than the exception. The middle
    of such a run is returned, which keeps the mapping single-valued.
    """
    if value <= grid[0]:
        return levels[0]
    if value >= grid[-1]:
        return levels[-1]
    for index in range(1, len(grid)):
        if grid[index] >= value:
            span = grid[index] - grid[index - 1]
            if span == 0:
                return (levels[index - 1] + levels[index]) / 2
            weight = (value - grid[index - 1]) / span
            return levels[index - 1] + (levels[index] - levels[index - 1]) * weight
    return levels[-1]


@dataclass(frozen=True, slots=True)
class MonthlyCorrection:
    """The three distributions one calendar month needs, at one point.

    ``reference`` is the reanalysis over the calibration period; ``model_past``
    the model over that same period, which is what makes the two comparable; and
    ``model_future`` the model over the projection period, which is what carries
    the change. Dropping the third would turn this into the naive mapping.
    """

    reference: list[float]
    model_past: list[float]
    model_future: list[float]
    levels: tuple[float, ...] = LEVELS

    def apply(self, value: float) -> float:
        """Correct one day's cloud cover.

        Reads: place the day in the model's future distribution, take the shift
        the model gives that quantile since its own past, and add it to the
        reference. Clipped, cloud cover being a share of sky.
        """
        level = _level_of(self.model_future, self.levels, value)
        drift = value - _interpolate(self.model_past, self.levels, level)
        corrected = _interpolate(self.reference, self.levels, level) + drift
        return min(CLOUD_MAX, max(CLOUD_MIN, corrected))


@dataclass(frozen=True, slots=True)
class CloudCorrection:
    """One point's correction, twelve months of it.

    Monthly because the bias is: Open-Meteo fits its own coefficients per
    calendar month, and the sky itself is not biased the same way in January and
    in July.
    """

    months: dict[int, MonthlyCorrection]

    def apply(self, value: float | None, month: int) -> float | None:
        """Correct a day, or pass a gap through untouched.

        A month absent from the table is an error rather than a silent identity:
        serving an uncorrected value would show an artificially sunny future,
        which is precisely what this module exists to prevent.
        """
        if value is None:
            return None
        if month not in self.months:
            raise KeyError(f"no correction for month {month}")
        return self.months[month].apply(value)


def build(
    reference: dict[int, list[float]],
    model_past: dict[int, list[float]],
    model_future: dict[int, list[float]],
    levels: tuple[float, ...] = LEVELS,
) -> CloudCorrection:
    """Summarise three samples, month by month, into a correction.

    Every month present in all three is kept; any month one of them lacks is
    left out, so that the caller meets a ``KeyError`` at request time rather
    than a quietly uncorrected day.
    """
    months = {}
    for month in range(1, 13):
        if month in reference and month in model_past and month in model_future:
            months[month] = MonthlyCorrection(
                reference=quantiles(reference[month], levels),
                model_past=quantiles(model_past[month], levels),
                model_future=quantiles(model_future[month], levels),
                levels=levels,
            )
    return CloudCorrection(months)
