"""Measure the contrast of every text on either page, on each of its grounds.

Nothing here asserts. It prints the tables `scripts/ink_contrast.md` publishes —
one column per season on the results page, one per state of the form on the
accueil — so that a palette which moves is re-measured by a command rather than by
hand. Four seasons of thirteen lines is not a thing anyone checks twice with an
eyedropper, and the accueil's were checked by hand exactly once, which is how the
*Lieu* label came to spend a while at 4,4:1 after the page was tightened.

**Both pages are anchored to the document, and that is what makes this a
command.** A gradient fixed to the window would give every reader a different
ground; fixed to the document it gives one, and a page that grows by a row of
buttons slides every text below it onto another part of the sunset. Layout and
legibility are one question here, so a change to either is a reason to run this.

**Where each number comes from.** The *positions* are read off a real render:
the page is served, driven by a real Chromium and asked where each element
actually sits and what colour it computes to. The *ground* is then worked out
from the gradient itself — the stops are read back from the stylesheet through
``getComputedStyle``, never copied into this file, and interpolated in sRGB,
which is what the browser does with a plain ``linear-gradient`` of opaque
colours. So the two halves of every ratio come from the page: one measured on
the render, the other from the declaration that painted it.

That is also the check on the method: run it on summer and the numbers must come
back as scripts/ink_contrast.md already publishes them.

**One geometry, four palettes.** The page measured is the ``results`` view —
ten days back and forty ahead, which is what puts a warning at the top and a
seam in the middle — and the season is then forced on the body, four times over.
Not a trick: a range crossing today in January *is* a winter page with a warning
and a seam. It is the only way to compare four grounds on the same page, since
which season a real crossing lands on depends on the day the script is run.

**A text on a card is measured against the card**, not against the sky behind
it. The cards are opaque and the two temperatures live on them — that is why
those two are the same on all four seasons.

**It needs a browser, and by default the network too.** ``--offline`` answers
Open-Meteo from this process, exactly as ``screenshots.py`` does — the ground and
the geometry are what is being measured here, and both are the real thing
whether the weather behind them is invented or not.

    ./venv/bin/python scripts/ink_contrast.py --offline
    ./venv/bin/python scripts/ink_contrast.py --offline --season winter
    ./venv/bin/python scripts/ink_contrast.py --offline --size 1280x720
    ./venv/bin/python scripts/ink_contrast.py --offline --page home
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright  # noqa: E402
from screenshots import (  # noqa: E402
    SEASON_RANGES,
    free_port,
    results,
    serve,
    stub_openmeteo,
)
from screenshots import home as accueil  # noqa: E402

# The rows of the published table, in its order. The label is French because it
# is what the table prints; the selector is what the page calls the thing.
ROWS = [
    ("le lieu", "#place"),
    ("la plage", "#range"),
    ("nouvelle recherche", "header.banner a"),
    ("l'avertissement", "#warning p:first-of-type"),
    ("le scénario", "#warning p:last-of-type"),
    ("le mois", ".card-month"),
    ("le jour", ".card-day"),
    # **The two temperatures are not rows here any more**, and taking them out
    # was a correction rather than a tidy-up. They sit on their band, not on the
    # card, since the ramp landed; measured against the card this reported a
    # white number on white paper at 1,0:1 and made it the floor of the page.
    # The ratio that means something is the ink against its own band, and the
    # ramp table below publishes all nine of them.
    ("les deux mesures", ".card-measure"),
    ("la couture", ".seam span"),
    # The chart is drawn on the card's own paper, so these come back the same on
    # all four seasons — the same reason the ramp does. One row for everything
    # the drawing writes in the soft ink — the graduation, the date marks, the
    # months, the compared year's name, the name of the cumulative curve — since
    # they are one ink on one paper and five rows would print the same number
    # five times; the seam label is the page's own, a shade stronger.
    ("les repères du graphe", ".chart-axis"),
    ("la couture du graphe", ".chart-seam-label"),
    # The one control on this page, measured closed — which is how a reader
    # meets it. What it opens is not a row here and does not need to be: the
    # panel is on the card's own paper, for the reason the chart is, so its
    # texts are read against an opaque ground and not against the sky. Opening
    # it to measure would also make the page taller and slide every row above
    # onto another part of the gradient, which would be measuring a page nobody
    # is looking at.
    ("comparer", "#compare-toggle"),
    ("la provenance", ".provenance summary"),
]

# What each element sits on. Anything inside a card body — or on the chart, or on
# the comparison block, which are the same paper — is on an opaque ground;
# everything else is on the sky, at its own height.
#
# The comparison block joined that list the day this script measured it at 1,1:1
# on the gradient. It sits wherever the chart ends, which the window height
# decides, so no fixed ink could have been right for it: it went onto paper, and
# paper is a ground that does not move.
#
# The chart's own texts are SVG, where the ink is `fill` and not `color`. They
# are written `fill: currentColor` in the stylesheet precisely so that the probe
# below, which asks for `color`, reads the ink that is actually painted.
ON_THE_CARD = ".card-body, .chart, .compare"

# The accueil's rows, in page order, which is also the order its table prints.
#
# **Two of them are new and one is a pair**, because the form now asks its
# question two ways: the switch between them is measured in both its states, and
# each panel's label and field is measured in the panel that shows it. A row
# whose panel is hidden measures nothing and prints an em dash — the probe drops
# a box of zero height rather than reporting it at the top of the page.
HOME_ROWS = [
    ("la question", "#prompt"),
    ("la promesse", "header.banner .tagline"),
    ("l'étiquette Lieu", 'label[for="lieu"]'),
    ("le champ Lieu", "#lieu"),
    ("la bascule choisie", '.mode[aria-pressed="true"]'),
    ("la bascule au repos", '.mode[aria-pressed="false"]'),
    ("l'étiquette Du", 'label[for="debut"]'),
    ("le champ Du", "#debut"),
    ("l'étiquette Saison", 'label[for="saison"]'),
    ("le champ Saison", "#saison"),
    ("le bouton", 'button[type="submit"]'),
    ("l'avertissement", "footer .tagline"),
]

# The accueil has no card and no chart; nothing on it is on an opaque ground.
# A selector that matches nothing is what says so.
NOTHING = ":not(*)"


def channel(value: float) -> float:
    value /= 255
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def luminance(colour: tuple[float, float, float]) -> float:
    red, green, blue = (channel(c) for c in colour)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def ratio(one, other) -> float:
    first, second = luminance(one), luminance(other)
    high, low = max(first, second), min(first, second)
    return (high + 0.05) / (low + 0.05)


def over(ink, ground):
    """A translucent ink on its ground, as the compositor lays it.

    The provenance is written at 72 % white and the rule above it at 30 %, so
    reading their colour and stopping there would report the contrast of a white
    that is not on the page. It is what the ratio is *for*: the colour the eye
    actually receives.
    """
    colour, alpha = ink
    return tuple(colour[i] * alpha + ground[i] * (1 - alpha) for i in range(3))


def parse_colour(text: str):
    """ "#rrggbb", "rgb(r, g, b)" or "rgba(r, g, b, a)" — what the page hands back.

    Returns the three channels and the alpha separately: the alpha has a ground
    to be laid on before it means anything.
    """
    if text.startswith("#"):
        digits = text[1:]
        return tuple(int(digits[i : i + 2], 16) for i in (0, 2, 4)), 1.0
    numbers = [float(n) for n in re.findall(r"[\d.]+", text)]
    return tuple(numbers[:3]), numbers[3] if len(numbers) > 3 else 1.0


def parse_stops(gradient: str) -> list[tuple[float, tuple[float, float, float]]]:
    """The stops of a `linear-gradient(to bottom, …)`, as read from the page.

    A custom property comes back as its token stream with every ``var()``
    already substituted — so the stop written as ``var(--sky-head)`` arrives
    here as the colour it stands for, which is the point of asking the browser
    rather than reading the file. The tokens themselves are untouched, hence the
    two spellings.
    """
    found = re.findall(r"(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))\s+([\d.]+)%", gradient)
    if not found:
        raise SystemExit(f"no stops read in this gradient:\n{gradient}")
    return [(float(percent), parse_colour(colour)[0]) for colour, percent in found]


def ground_at(stops, fraction: float) -> tuple[float, float, float]:
    """The gradient's colour at a fraction of its height, interpolated in sRGB."""
    percent = max(0.0, min(100.0, fraction * 100))
    for (low, first), (high, second) in zip(stops, stops[1:], strict=False):
        if low <= percent <= high:
            share = 0.0 if high == low else (percent - low) / (high - low)
            return tuple(first[i] + (second[i] - first[i]) * share for i in range(3))
    return stops[-1][1]


# Read in the page: where every row sits, what colour it is, and what the sky is
# made of. One round trip rather than twelve, and no selector resolved twice.
#
# A row with no box is left out rather than reported at the top of the page: an
# element that is `hidden` measures zero everywhere, and a zero divided by the
# page height is a perfectly plausible-looking 0 %, near-white, flattering and
# false.
PROBE = """
([rows, onTheCard]) => {
  const body = document.body;
  const sky = document.querySelector('.sky');
  const seen = [];
  for (const [label, selector] of rows) {
    const node = document.querySelector(selector);
    if (!node) continue;
    const box = node.getBoundingClientRect();
    if (box.height === 0) continue;
    const card = node.closest(onTheCard);
    seen.push({
      label,
      colour: getComputedStyle(node).color,
      middle: (box.top + window.scrollY + box.height / 2) / sky.offsetHeight,
      card: card ? getComputedStyle(card).backgroundColor : null,
      // The element's *own* fill, which on the accueil is the whole question for
      // one row: the button is a translucent brown the sunset shows through, so
      // its ink sits neither on the sky nor on an opaque slab but on the two
      // composited. Every other field there is transparent and this reads as
      // zero alpha, which lays the ink straight back onto the gradient.
      fill: getComputedStyle(node).backgroundColor,
    });
  }
  return {
    season: body.dataset.season,
    height: sky.offsetHeight,
    gradient: getComputedStyle(body).getPropertyValue('--sky'),
    rows: seen,
  };
}
"""


# The temperature ramp, read the same way: the browser resolves each band class
# to a colour, and the two card papers are read off a real card. Asking the page
# rather than the file is what keeps this from becoming a second copy of the
# ramp — the numbers here come from whatever the stylesheet currently says.
RAMP_PROBE = """
(count) => {
  const card = document.querySelector('.card-body');
  const probe = document.createElement('span');
  probe.className = 'card-degrees';
  card.append(probe);
  const bands = [];
  for (let i = 0; i < count; i++) {
    probe.setAttribute('data-band', String(i));
    const style = getComputedStyle(probe);
    bands.push({ ground: style.backgroundColor, ink: style.color });
  }
  probe.remove();
  return bands;
}
"""

BAND_COUNT = 9


def measure_ramp(page) -> list[tuple[int, str, str, float]]:
    """Every band of the temperature scale, under the ink it actually carries.

    The number sits *on* the band, so the ratio that matters is the ink against
    its own ground — the card behind it never shows through. The ink is read
    rather than assumed: it turns over with the ground, white on the dark bands
    and near-black on the light ones, and reading it here is what keeps this
    from being a second opinion about which is which.
    """
    rows = []
    for index, band in enumerate(page.evaluate(RAMP_PROBE, BAND_COUNT)):
        ground = parse_colour(band["ground"])[0]
        ink = parse_colour(band["ink"])
        as_hex = lambda colour: "#" + "".join(f"{round(c):02x}" for c in colour)  # noqa: E731
        rows.append((index, as_hex(ground), as_hex(ink[0]), ratio(over(ink, ground), ground)))
    return rows


def read_rows(page, rows, on_the_card: str) -> dict:
    """Every row's ratio against whatever it actually sits on.

    Three grounds, and which one applies is read off the page rather than
    decided here: an opaque card wins outright; failing that, the element's own
    fill is composited over the gradient at its height, which for a transparent
    field is the gradient itself and for the accueil's button is the brown the
    sunset shows through.
    """
    read = page.evaluate(PROBE, [rows, on_the_card])
    stops = parse_stops(read["gradient"])
    measured = {}
    for row in read["rows"]:
        if row["card"]:
            ground = parse_colour(row["card"])[0]
        else:
            ground = over(parse_colour(row["fill"]), ground_at(stops, row["middle"]))
        measured[row["label"]] = ratio(over(parse_colour(row["colour"]), ground), ground)
    return {"height": read["height"], "rows": measured}


def measure(page, season: str) -> dict:
    """The results page as it stands, repainted in one season and read."""
    page.evaluate("(season) => { document.body.dataset.season = season; }", season)
    return read_rows(page, ROWS, ON_THE_CARD)


def measure_home(page, mode: str) -> dict:
    """The accueil in one of its three states.

    **Three, because the page opens on neither panel.** Which one is open
    changes the page's height, and the sunset is anchored to the document — so
    every row below the switch lands on a different part of the gradient. They
    are three geometries, exactly as the window sizes are, and the one the
    visitor meets first is the one with nothing open.
    """
    page.reload()
    page.wait_for_function("() => document.getElementById('debut').min !== ''")
    if mode != "rien d'ouvert":
        page.click("#mode-season" if mode == "saison entière" else "#mode-dates")
        page.wait_for_selector("#go:not([hidden])")
    return read_rows(page, HOME_ROWS, NOTHING)


HOME_MODES = ["rien d'ouvert", "plage de dates", "saison entière"]

# The geometry each table was published at. The accueil's is shorter, and that is
# not an oversight: it is the window the figures in scripts/ink_contrast.md were
# taken on, and a table remeasured at another size is not a correction of it.
DEFAULT_SIZE = {"results": "1440x960", "home": "1440x900"}


def table(rows, columns, measured) -> None:
    """The published shape, and the floor under it."""
    print("\n| Texte | " + " | ".join(columns) + " |")
    print("|---|" + "---|" * len(columns))
    floor = (None, 99.0)
    for label, _ in rows:
        cells = []
        for column in columns:
            value = measured[column]["rows"].get(label)
            cells.append("—" if value is None else f"{value:.1f}:1".replace(".", ","))
            if value is not None and value < floor[1]:
                floor = (f"{label}, {column}", value)
        print(f"| {label} | " + " | ".join(cells) + " |")
    print(f"\nplancher : {floor[0]}, à {floor[1]:.1f}:1".replace(".", ","))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--page",
        choices=sorted(DEFAULT_SIZE),
        default="results",
        help="la page mesurée : results (quatre saisons) ou home (deux modes)",
    )
    parser.add_argument("--season", choices=sorted(SEASON_RANGES), help="one of the four")
    parser.add_argument("--size", help="the window, as WIDTHxHEIGHT")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="inventer les données au lieu d'appeler Open-Meteo — les positions restent vraies",
    )
    parser.add_argument("--lag", type=int, default=6, help="retard des réanalyses, avec --offline")
    chosen = parser.parse_args()

    width, _, height = (chosen.size or DEFAULT_SIZE[chosen.page]).partition("x")
    size = {"width": int(width), "height": int(height)}
    home = chosen.page == "home"
    columns = HOME_MODES if home else ([chosen.season] if chosen.season else list(SEASON_RANGES))

    port = free_port()
    server = serve(port)
    base = f"http://127.0.0.1:{port}"
    ramp = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=["--lang=fr-FR"])
            context = browser.new_context(viewport=size, locale="fr-FR")
            page = context.new_page()
            if chosen.offline:
                stub_openmeteo(page, date.today(), chosen.lag)
            if home:
                # The form as it comes up, both panels in turn. No place is
                # chosen: the field then shows its placeholder, which is the ink
                # the published row is about.
                accueil(page, base)
                measured = {mode: measure_home(page, mode) for mode in columns}
            else:
                # The reference geometry, and the same call the screenshots make:
                # a range spanning today, so the warning and the seam are both
                # there.
                results(page, base)
                measured = {season: measure(page, season) for season in columns}
                ramp = measure_ramp(page)
            browser.close()
    finally:
        server.terminate()

    heights = {reading["height"] for reading in measured.values()}
    sizes = " / ".join(str(h) for h in sorted(heights))
    print(f"\nfenêtre {size['width']} × {size['height']}, page {sizes} px")
    table(HOME_ROWS if home else ROWS, columns, measured)

    if ramp is None:
        return
    # The two temperatures are no longer one colour each, so they cannot be one
    # row each: what has to hold is the whole ramp, on both papers a card takes.
    print("\nLa rampe des températures : le chiffre sur son aplat\n")
    print("| bande | aplat | encre | chiffre |")
    print("|---|---|---|---|")
    for index, hexa, ink, on_band in ramp:
        print(f"| {index} | `{hexa}` | `{ink}` | {on_band:.2f}:1 |".replace(".", ","))
    print(f"\nplancher de la rampe : {min(r[3] for r in ramp):.2f}:1".replace(".", ","))


if __name__ == "__main__":
    main()
