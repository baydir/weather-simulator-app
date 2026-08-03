"""What is compared, where, and over which years.

Settled here rather than in the collector so that the choices are visible in one
place and a re-run cannot silently drift from what produced the figures.

**Period — 1979 to 2014.** Both ends are constrained, neither is a round number.
HighResMIP historical runs stop at the end of 2014; from 2015 the models are on
their future scenario, and comparing a scenario segment against a reanalysis
would confound the model with its forcing. At the other end, ERA5 before 1979 is
the preliminary back extension, of lesser and unevenly documented quality — and
it is the reference here, so its own weaknesses would pass for model error. The
36 years that remain are enough to place a p99 on daily data.

**The overlap period cannot be escaped.** Open-Meteo fits monthly linear
correction coefficients against ERA5-Land over a 50-year window, so every year
a model and the reanalysis have in common is a year the coefficients saw. There
is no hold-out. This is why the mean is not compared: a linear monthly
correction sets it by construction, and the five models would be ranked on
Open-Meteo's coefficients rather than on themselves. What such a correction
leaves untouched — spread, day-to-day persistence, distribution shape — carries
the signal, and that is what the metrics read.

**Sites.** Five in France, where the correction grid of step 4 starts, chosen
for contrasting climates rather than for population; five elsewhere, so that a
model is not selected on Europe alone — the grid is meant to widen, and the
southern hemisphere has already caught out one rule (the snow gaps of section 2).
Continuity with the verification scripts is deliberate: these are the same points
the design figures were measured at.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

# Where the raw payloads are kept. Collection is slow and rate-limited; the
# analysis has to be re-runnable without touching the network, and the figures
# have to stay traceable to the bytes that produced them.
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "model_selection"

START = date(1979, 1, 1)
END = date(2014, 12, 31)

SITES: dict[str, tuple[float, float]] = {
    # France — the five climates the grid of step 4 has to cover first.
    "brest": (48.39, -4.49),  # oceanic
    "marseille": (43.30, 5.37),  # mediterranean
    "strasbourg": (48.58, 7.75),  # semi-continental
    "pontarlier": (46.90, 6.35),  # mid-mountain, in a valley
    "chamonix": (45.92, 6.87),  # high mountain, where every source degrades
    # Elsewhere — enough spread that a model cannot win on Europe alone.
    "reykjavik": (64.15, -21.94),  # subpolar
    "bamako": (12.65, -8.00),  # sahel, monsoon
    "singapore": (1.35, 103.82),  # wet tropical
    "christchurch": (-43.53, 172.63),  # southern hemisphere, temperate
    "ushuaia": (-54.80, -68.30),  # subantarctic
}
