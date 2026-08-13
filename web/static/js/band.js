/**
 * The strip of days, built as nodes. Nothing here fetches or holds state.
 *
 * Split off from results.js so that it can be checked: give it a series and it
 * hands back nodes, which a test can walk without a browser. What is left in
 * results.js is the page's wiring — the URL, the call, the waiting.
 *
 * **Two reading marks are added, and only two.** The month name where the month
 * turns, and the seam where the observed stops. The server holds no version of
 * either — CLAUDE.md rule 3 turns on the double copy, and there is none here.
 * Everything else on a card arrived decided.
 *
 * What is deliberately *not* here: no average over the range, no count of rainy
 * days, no total, no extreme. An aggregate computed at display time falls under
 * the same validation as a rounding, and docs/application.md settles it — the
 * strip shows the days and nothing above them.
 */

import { el } from "./dom.js";
import { texts } from "./i18n.js";
import * as present from "./present.js";

/**
 * The days in order, with the seam marked where the simulated begins.
 *
 * The seam gets a card of its own rather than a colour: the tint on what
 * follows says the same thing, but colour alone must never be what carries it.
 *
 * It is only drawn where there is a crossing to draw. A range lying wholly in
 * the future has no observed day to leave, and a marker on the very first card
 * would announce a passage that never happens — the warning at the top of the
 * page is what covers that case.
 */
export function strip(days) {
  const nodes = [];
  let month = null;
  let observedSeen = false;
  let seamDrawn = false;

  for (const day of days) {
    if (day.origin === "simulated" && observedSeen && !seamDrawn) {
      seamDrawn = true;
      nodes.push(el("li", { className: "seam" }, [el("span", { text: texts.results.seam })]));
    }
    // Anything that is not simulated counts as a bank to leave, forecast days
    // included. Reading "observed" alone would miss the crossing on a range
    // that starts tomorrow: it runs forecast then simulated, never observed,
    // and the one seam it does have would go unmarked.
    observedSeen ||= day.origin !== "simulated";

    const turned = present.monthKey(day.date) !== month;
    month = present.monthKey(day.date);
    nodes.push(card(day, turned));
  }
  return nodes;
}

/**
 * One day, one card, with a hierarchy: the sky and the two temperatures lead,
 * the rain and the wind follow at equal weight to each other.
 *
 * Both of those are display decisions the project owner took on seeing the
 * first strip. Four measures at one rank left nothing for the eye to land on —
 * the card read as a table. And `wind_speed_mean` came off the card entirely:
 * five numbers were more than one can carry at a glance. It still travels in
 * the JSON contract, where keeping it costs nothing.
 *
 * `source` rides along as a title attribute: it is what tells one seam from the
 * other when something looks wrong, and it has no business on screen otherwise.
 */
export function card(day, namesMonth) {
  const { emoji, label } = present.sky(day.sky);
  const { celsius, millimetres, kilometresPerHour } = texts.units;

  return el("li", { className: `card card--${day.origin}`, attrs: { title: day.source } }, [
    // The tinted band. The month line is rendered on every card, empty where the
    // month has not turned, so the cards keep one height and the dates line up
    // across the strip.
    el("div", { className: "card-head" }, [
      el("p", {
        className: "card-month",
        text: namesMonth ? present.monthLabel(day.date) : "",
      }),
      el("p", { className: "card-day", text: present.dayLabel(day.date) }),
    ]),
    el("div", { className: "card-body" }, [
      // The emoji is hidden from screen readers and the written class carries it
      // instead. docs/application.md requires both, one for each way of reading.
      el("p", { className: "card-emoji", text: emoji, attrs: { "aria-hidden": "true" } }),
      // Straight under the pictogram, large, and unlabelled: two numbers beside
      // a degree sign on a weather card need no word to say what they are.
      // Which is the maximum *does* need saying — that is carried by colour and
      // by position on screen, and neither is information, so each is named for
      // anyone not reading them.
      //
      // **Maximum above minimum**, stacked rather than set side by side. The
      // earlier card ran "min · max" on one line, in the order projet.md and
      // the README write the pair; the results mock-up stacks them and leads
      // with the maximum, which is the figure a summer read is looking for.
      // The reading order follows the eye — a screen reader now hears the
      // maximum first too, and band.test.js pins that order.
      el("p", { className: "card-temperatures" }, [
        el("span", { className: "sr-only", text: texts.measure.high }),
        degrees(day.temperature_max, "high", celsius),
        el("span", { className: "sr-only", text: texts.measure.low }),
        degrees(day.temperature_min, "low", celsius),
      ]),
      el("p", { className: "card-sky", text: label }),
      el("dl", { className: "card-measures" }, [
        ...measure(texts.measure.precipitation, day.precipitation, present.precipitation, millimetres),
        // One wind, not two: the mean and the maximum side by side were more
        // than a card can carry and be read at a glance. The one kept is the
        // maximum, and its label says so — neither an average nor a gust.
        ...measure(texts.measure.windMax, day.wind_speed_max, present.wind, kilometresPerHour),
      ]),
    ]),
  ]);
}

/** One number, and what to say instead of it when there is none. */
function value(shown, raw, className) {
  return el("span", {
    className,
    text: shown,
    attrs: {
      "aria-label": present.isMissing(raw) ? texts.measure.missingLabel : undefined,
    },
  });
}

/**
 * One temperature on a line of its own, degree sign included.
 *
 * The unit rides on each of the two rather than once at the end, which is what
 * stacking costs: side by side, "14 · 28 °C" let one sign serve both, and one
 * above the other it would sit against the lower number alone.
 */
function degrees(raw, className, unit) {
  return el("span", { className: `card-degrees ${className}` }, [
    value(present.temperature(raw), raw, "value"),
    el("span", { className: "unit", text: unit }),
  ]);
}

/**
 * A measure: the word, then the number and its unit.
 *
 * **The word is carried but not shown.** The mock-up puts bare figures on the
 * card — "3,2 mm", "5 km/h" — and the units make them legible at a glance. A
 * screen reader gets no units to lean on, so the `dt` stays in the document and
 * goes off-screen instead of away: that is what keeps "Vent maximal" attached
 * to a number docs/application.md forbids reading as an average.
 */
function measure(label, raw, format, unit) {
  return [
    el("dt", { className: "sr-only", text: label }),
    el("dd", { className: "card-measure" }, [
      value(format(raw), raw, "value"),
      el("span", { className: "unit", text: unit }),
    ]),
  ];
}

/**
 * What corrected the simulated days, as label/value pairs.
 *
 * Empty when the grid is null, which is the honest answer for a range lying
 * wholly in the past: nothing was corrected, so there is no table to describe.
 */
export function sources(grid) {
  if (!grid) return [];
  const rows = [
    [texts.provenance.model, grid.model],
    [
      texts.provenance.calibration,
      texts.provenance.span(
        present.fullDate(grid.calibration_start),
        present.fullDate(grid.calibration_end),
      ),
    ],
    [
      texts.provenance.projection,
      texts.provenance.span(
        present.fullDate(grid.projection_start),
        present.fullDate(grid.projection_end),
      ),
    ],
    [texts.provenance.step, texts.provenance.degrees(present.decimal(grid.step))],
    [texts.provenance.generated, present.fullDate(grid.generated)],
  ];
  return rows.flatMap(([label, text]) => [el("dt", { text: label }), el("dd", { text })]);
}
