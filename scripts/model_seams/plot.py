"""Draw the two daily temperatures around today, and say which dataset served
each day.

Reads ``data/model_seams/<place>.json`` — no network. Collect once with
``collect.py``, redraw as often as you like.

**The axis counts days from today, and carries no date.** This figure is meant
for a page that will be read for years, so a January reading of a chart whose
axis says "20 août" is a chart that has plainly gone off. What the figure is
actually about is invariant: the reanalyses stop about six days back, ECMWF's
analysis covers the gap to today, its forecast runs a fortnight out, and the
climate model takes everything after. Those positions are the same every day of
every year, and a relative axis is what shows them.

**What is not invariant is the weather itself**, and the figure says so rather
than pretending otherwise. The curve is one particular collection; another day
would draw other temperatures between the same seams.

**The window is one a visitor could actually search.** Eighty-three days is
inside the 92 the API allows, so this is not a diagnostic view of something
nobody can reach — it is a picture of an ordinary search that happens to cross
all four sources.

    ./venv/bin/python scripts/model_seams/plot.py
    ./venv/bin/python scripts/model_seams/plot.py --before 31 --after 51
"""

from __future__ import annotations

import argparse
import itertools
import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.patheffects as patheffects  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter, MultipleLocator  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "model_seams"
OUT = ROOT / "shots"

# Cool for what was measured, warm for what was modelled, and the two ECMWF
# segments in between — the reading order of the series is the reading order of
# the ramp.
COLOURS = {
    "reanalysis": "#3b6ea5",
    "ecmwf_ifs": "#2e8b74",
    "ecmwf_ifs025": "#d98c2b",
    "simulated": "#b4453c",
}

# What each stretch is, in French, next to the identifier the API answers to.
# The identifier alone is opaque; the word alone is imprecise.
KINDS = {
    "reanalysis": "réanalyse",
    "ecmwf_ifs": "analyse",
    "ecmwf_ifs025": "prévision",
    "simulated": "simulation",
}

INK = "#17140f"
SOFT = "#4a443c"


def load(place: str) -> dict:
    path = DATA / f"{place}.json"
    if not path.is_file():
        raise SystemExit(
            f"{path} est absent — lancez d'abord :\n"
            f"    ./venv/bin/python scripts/model_seams/collect.py --place {place}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def runs(days: list[dict]) -> list[tuple[str, list[dict]]]:
    """The series cut into consecutive stretches of one dataset."""
    return [(key, list(group)) for key, group in itertools.groupby(days, key=lambda d: d["source"])]


def key_of(source: str, series: dict) -> str:
    """The colour and label key for a record's ``source``.

    Everything is itself except the climate model, whose name is a parameter of
    the application: keying on it would give the palette a hole the day the
    model changes.
    """
    return "simulated" if source == series["model"] else source


def name_of(source: str, series: dict) -> str:
    """The dataset to put on the legend, for *these* variables.

    "reanalysis" covers two, and only one of them served the temperatures: they
    come from ERA5-Land, everything else from ERA5. The name is read from the
    collected file rather than typed here — ``collect.py`` wrote down what
    ``openmeteo.py`` said at the time.
    """
    return series["reanalysis_temperature"] if source == "reanalysis" else source


def offsets(days: list[dict], today: date) -> list[int]:
    return [(date.fromisoformat(d["date"]) - today).days for d in days]


def label_offset(value: float, _position: int = 0) -> str:
    day = int(round(value))
    if day == 0:
        return "aujourd'hui"
    return f"J{day:+d}"


def draw(axes, days: list[dict], series: dict, today: date) -> None:
    """One band per stretch: the day's range filled, its two bounds drawn.

    Colour carries the dataset, which is what this figure is for; the two
    temperatures are told apart by position, which needs no key — the maximum is
    the upper bound of a band and there is nowhere else for it to be. Labelling
    them by colour instead would have cost the dataset its own dimension.

    **Each stretch runs to the seam, not to its last day.** Plotted as disjoint
    runs the curves would open a one-day hole at every seam, which reads as
    missing data and is the opposite of what this chart is about. Carrying the
    neighbour's last day into the stretch closes the hole but moves the colour: a
    day belongs to one dataset, so the boundary lies halfway between two days —
    at ``seam - 0.5``, where the bars above change and where the dashed line is
    — while a segment drawn from the neighbour's day is wholly in the new colour
    and switches half a day early. Small, and visible: it left the three dashed
    lines looking offset to the right of the colour they mark.

    So each stretch is extended to the midpoint on either side, with the value
    interpolated between the two days it falls between. Every colour then owns
    exactly its half of the connecting segment, and the change lands on the
    boundary itself.
    """
    cut = runs(days)
    for index, (source, group) in enumerate(cut):
        colour = COLOURS[key_of(source, series)]
        x = [float(day) for day in offsets(group, today)]
        high = [d["temperature_max"] for d in group]
        low = [d["temperature_min"] for d in group]

        if index > 0:
            before = cut[index - 1][1][-1]
            x.insert(0, x[0] - 0.5)
            high.insert(0, (before["temperature_max"] + high[0]) / 2)
            low.insert(0, (before["temperature_min"] + low[0]) / 2)
        if index < len(cut) - 1:
            after = cut[index + 1][1][0]
            x.append(x[-1] + 0.5)
            high.append((high[-1] + after["temperature_max"]) / 2)
            low.append((low[-1] + after["temperature_min"]) / 2)

        axes.fill_between(x, low, high, color=colour, alpha=0.16, linewidth=0)
        axes.plot(x, high, color=colour, linewidth=1.7, solid_joinstyle="round")
        axes.plot(x, low, color=colour, linewidth=1.7, solid_joinstyle="round")


def draw_bands(axes, days: list[dict], series: dict, today: date) -> None:
    """The strip of horizontal bars: one per stretch, on the same line."""
    for source, group in runs(days):
        first = (date.fromisoformat(group[0]["date"]) - today).days
        last = (date.fromisoformat(group[-1]["date"]) - today).days
        axes.barh(
            0,
            width=(last - first) + 1,
            left=first - 0.5,
            height=0.55,
            color=COLOURS[key_of(source, series)],
        )
    axes.set_yticks([])
    axes.set_ylim(-0.5, 0.5)
    for side in ("left", "right", "top", "bottom"):
        axes.spines[side].set_visible(False)
    axes.tick_params(labelbottom=False, length=0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--place", default="paris")
    parser.add_argument("--before", type=int, default=31, help="jours avant aujourd'hui")
    parser.add_argument("--after", type=int, default=51, help="jours après aujourd'hui")
    parser.add_argument("--out", type=Path, default=None, help="le fichier à écrire, .png ou .svg")
    parser.add_argument("--dpi", type=int, default=170, help="sans effet sur une sortie SVG")
    chosen = parser.parse_args()

    series = load(chosen.place)
    # The day the series was collected is the only "today" this file has. Read
    # from the file rather than from the clock: a chart drawn six months later
    # would otherwise put its origin where the data has nothing to say.
    today = date.fromisoformat(series["collected"])

    days = [
        d
        for d in series["days"]
        if d["temperature_max"] is not None
        and d["temperature_min"] is not None
        and -chosen.before <= (date.fromisoformat(d["date"]) - today).days <= chosen.after
    ]
    if not days:
        raise SystemExit("la fenêtre demandée ne rencontre aucun jour de la série collectée")

    figure = plt.figure(figsize=(12.5, 5.6), layout="constrained")
    grid = figure.add_gridspec(2, 1, height_ratios=[0.4, 6], hspace=0.04)
    bands = figure.add_subplot(grid[0])
    axes = figure.add_subplot(grid[1], sharex=bands)

    draw_bands(bands, days, series, today)
    draw(axes, days, series, today)

    # Today, and the two seams that do not fall on it. Drawn under the curves.
    for _source, group in runs(days)[1:]:
        seam = (date.fromisoformat(group[0]["date"]) - today).days
        axes.axvline(seam - 0.5, color=SOFT, linewidth=0.8, linestyle=(0, (4, 3)), zorder=0)

    axes.set_xlim(-chosen.before - 0.5, chosen.after + 0.5)
    axes.xaxis.set_major_locator(MultipleLocator(10))
    axes.xaxis.set_major_formatter(FuncFormatter(label_offset))
    axes.set_ylabel("température (°C)", color=SOFT)
    axes.grid(axis="y", color="#e0dbd1", linewidth=0.6)
    axes.set_axisbelow(True)
    axes.tick_params(colors=SOFT)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color("#cfc8bc")

    # The two curves, named where they are rather than in a key: the maximum is
    # the upper bound of a band and there is nowhere else for it to be.
    first = runs(days)[0][1]
    anchor = offsets(first, today)[0]
    for value, text, align in (
        (first[0]["temperature_max"], "maximale", "bottom"),
        (first[0]["temperature_min"], "minimale", "top"),
    ):
        axes.annotate(
            text,
            (anchor, value),
            textcoords="offset points",
            xytext=(2, 9 if align == "bottom" else -9),
            ha="left",
            va=align,
            fontsize=9,
            color=COLOURS[key_of(first[0]["source"], series)],
            # The label sits on the curve it names, and on a day the curve
            # happens to be climbing it sits *in* it. A stroke of the page's own
            # white keeps the word legible without moving it off the thing it
            # points at, which is the whole advantage of labelling in place.
            path_effects=[patheffects.withStroke(linewidth=3.5, foreground="white")],
        )

    seen: list[str] = []
    for source, _ in runs(days):
        if source not in seen:
            seen.append(source)
    bands.legend(
        handles=[
            Line2D(
                [],
                [],
                color=COLOURS[key_of(source, series)],
                linewidth=7,
                solid_capstyle="butt",
                label=f"{name_of(source, series)} — {KINDS[key_of(source, series)]}",
            )
            for source in seen
        ],
        loc="lower left",
        bbox_to_anchor=(0, 1.25),
        ncols=4,
        frameon=False,
        fontsize=9.5,
        handlelength=1.4,
        labelcolor=INK,
    )

    # No title and no note above the legend: the figure is placed with a caption
    # under it, and a caption is where both of those belong.
    #
    # **Two sentences left this file and must arrive in that caption.** CLAUDE.md
    # rule 1: most of this picture is simulated days, and anything showing them
    # says so — "au-delà de la prévision, ce n'est pas le temps qu'il fera :
    # c'est une trajectoire plausible, sous un scénario d'émissions haut". And
    # the other half of the honesty, which the relative axis makes necessary
    # rather than optional: the temperatures are one collection's, only the
    # place of the seams holds from one day to the next. An axis reading "J+30"
    # with no such note invites the figure to be read as a property of J+30.

    # `shots/` by default, which is where the working copies go and which the
    # repository ignores. `--out` is how the figure becomes a page asset
    # instead: putting it under `web/static/` has to be a deliberate act, since
    # that copy is committed and served, and nothing should land there by the
    # side effect of a redraw.
    path = chosen.out or OUT / f"model-seams-{chosen.place}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=chosen.dpi, bbox_inches="tight", facecolor="white")
    print(
        f"{len(days)} jours, J-{chosen.before} → J+{chosen.after}, "
        f"{len(runs(days))} segments  →  {path}"
    )


if __name__ == "__main__":
    main()
