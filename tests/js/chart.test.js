/**
 * The chart: its two axes, its holes, and the mark it shares with the strip.
 *
 * What is checked here is what a look at the page cannot check. A curve drawn
 * across a missing day looks exactly like a curve drawn across a real one — the
 * failure is invisible by construction, which is the reason the geometry is
 * built by a module that answers outside a browser.
 *
 * The band ladder is passed in as the API serves it. Written out as a literal it
 * would be a second copy of the scale, and these tests would go on passing the
 * day the boundaries moved.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { byClass, install, walk } from "./dom-stub.js";

install();

const chartModule = await import("../../web/static/js/chart.js");
const {
  BOX,
  RAIN_FLOOR_MM,
  chart,
  edgeOf,
  frame,
  rainCeiling,
  rainTicks,
  runs,
  temperatureWindow,
  ticks,
} = chartModule;
const { texts } = await import("../../web/static/js/i18n.js");

/** The ladder as /api/config serves it: eight boundaries, five degrees apart. */
const SCALE = { edges: [5, 10, 15, 20, 25, 30, 35, 40], step: 5 };

/** A day of the series, as /api/days serves one. */
function day(date, origin, extra = {}) {
  return {
    date,
    origin,
    source: origin === "simulated" ? "MRI_AGCM3_2_S" : "era5",
    temperature_min: 14.2,
    temperature_max: 27.6,
    precipitation: 0.4,
    cloud_cover: 22.4,
    wind_speed_max: 31.0,
    sky: "cloudy",
    temperature_min_band: 2,
    temperature_max_band: 5,
    ...extra,
  };
}

/** A run of days from the same month, all observed. */
function series(count, extra = () => ({})) {
  return Array.from({ length: count }, (_, index) =>
    day(`2026-08-${String(index + 1).padStart(2, "0")}`, "observed", extra(index)),
  );
}

describe("the temperature axis", () => {
  it("snaps to the boundaries around the period, with half a step of air", () => {
    const days = series(3, (index) =>
      index === 0
        ? { temperature_min: 12.4, temperature_max: 21.0 }
        : { temperature_min: 16.0, temperature_max: 28.9 },
    );

    // 12,4 sits in the 10-15 band and 28,9 in the 25-30 one.
    assert.deepEqual(temperatureWindow(days, SCALE.step), { bottom: 7.5, top: 32.5 });
  });

  it("keeps a reading that lands exactly on a boundary off the frame", () => {
    const days = series(1, () => ({ temperature_min: 15.0, temperature_max: 30.0 }));

    assert.deepEqual(temperatureWindow(days, SCALE.step), { bottom: 12.5, top: 32.5 });
  });

  it("frames a freezing period below zero, the cold band being open", () => {
    const days = series(2, () => ({ temperature_min: -6.2, temperature_max: 2.0 }));

    assert.deepEqual(temperatureWindow(days, SCALE.step), { bottom: -12.5, top: 7.5 });
  });

  it("has nothing to frame when no day carries a temperature", () => {
    const days = series(4, () => ({ temperature_min: null, temperature_max: null }));

    assert.equal(temperatureWindow(days, SCALE.step), null);
  });
});

describe("the graduation", () => {
  it("rules the boundaries the window shows, and no other", () => {
    // The window runs 7,5 to 32,5.
    assert.deepEqual(ticks({ bottom: 7.5, top: 32.5 }, SCALE.edges, SCALE.step), [10, 15, 20, 25, 30]);
  });

  it("carries on under the ladder, whose coldest band has no boundary to rule", () => {
    // Everything below five degrees is one band, so a frozen period would be a
    // panel ruled once — at five — with nothing on zero.
    assert.deepEqual(ticks({ bottom: -12.5, top: 7.5 }, SCALE.edges, SCALE.step), [-10, -5, 0, 5]);
  });

  it("carries on over it too, the hottest band being open as well", () => {
    assert.deepEqual(ticks({ bottom: 32.5, top: 52.5 }, SCALE.edges, SCALE.step), [35, 40, 45, 50]);
  });

  it("writes the unit on the topmost number alone", () => {
    const days = series(2, () => ({ temperature_min: 12.4, temperature_max: 28.9 }));
    const numbers = byClass(chart(days, SCALE), "chart-axis").map((node) => node.textContent);

    assert.ok(numbers.includes(`30 ${texts.units.celsius}`));
    assert.equal(numbers.filter((text) => text.includes(texts.units.celsius)).length, 1);
  });
});

describe("the rain graduation", () => {
  it("rules on round millimetres, at most four intervals", () => {
    assert.deepEqual(rainTicks(RAIN_FLOOR_MM), [5, 10]);
    assert.deepEqual(rainTicks(23.8), [10, 20]);
    assert.deepEqual(rainTicks(12), [5, 10]);
    assert.deepEqual(rainTicks(96), [25, 50, 75]);
  });

  it("never rules above the wettest day, which is where the panel stops", () => {
    for (const ceiling of [10, 11.2, 23.8, 40, 96, 250]) {
      assert.ok(Math.max(...rainTicks(ceiling)) <= ceiling, `ruled over ${ceiling}`);
    }
  });
});

describe("the rain axis", () => {
  it("takes the wettest day of the period", () => {
    const days = series(3, (index) => ({ precipitation: [0.4, 23.8, 2.0][index] }));

    assert.equal(rainCeiling(days), 23.8);
  });

  it("does not follow a dry period down, which would make a drizzle a downpour", () => {
    const damp = series(3, (index) => ({ precipitation: [0, 0.3, 0][index] }));
    const dry = series(3, () => ({ precipitation: 0 }));

    assert.equal(rainCeiling(damp), RAIN_FLOOR_MM);
    assert.equal(rainCeiling(dry), RAIN_FLOOR_MM);
  });

  it("stands on the floor when every reading is missing", () => {
    assert.equal(rainCeiling(series(2, () => ({ precipitation: null }))), RAIN_FLOOR_MM);
  });
});

describe("a hole in the series", () => {
  it("breaks a curve in two rather than drawing across it", () => {
    const days = series(5, (index) => (index === 2 ? { temperature_max: null } : {}));

    const stretches = runs(days, (item) => item.temperature_max);
    assert.deepEqual(
      stretches.map((run) => run.map(({ index }) => index)),
      [
        [0, 1],
        [3, 4],
      ],
    );
  });

  it("leaves a lone reading its dot and no segment to join it to anything", () => {
    const days = series(3, (index) => (index === 1 ? {} : { temperature_max: null }));
    const node = chart(days, SCALE);

    const high = (name) => byClass(node, name).filter((mark) => mark.className.includes("high"));
    assert.equal(high("chart-point").length, 1);
    assert.equal(high("chart-line").length, 0);
  });

  it("marks every day it drew, on both curves", () => {
    const days = series(12, (index) => (index === 4 ? { temperature_min: null } : {}));
    const node = chart(days, SCALE);

    const points = (name) => byClass(node, "chart-point").filter((m) => m.className.includes(name));
    assert.equal(points("high").length, 12);
    assert.equal(points("low").length, 11);
  });

  it("tells a missing reading from a dry day in the rain panel", () => {
    const days = series(3, (index) => ({ precipitation: [null, 0, 4.2][index] }));
    const node = chart(days, SCALE);

    // The dry day draws nothing, so the missing one has to draw something.
    assert.equal(byClass(node, "chart-gap").length, 1);
    assert.equal(byClass(node, "chart-bar").length, 1);
  });
});

describe("the seam", () => {
  it("falls on the same day the strip marks, and only where there is a crossing", () => {
    const crossing = [
      day("2026-08-01", "observed"),
      day("2026-08-02", "forecast"),
      day("2026-08-03", "simulated"),
    ];
    const geometry = frame(crossing.length);
    const [rule] = byClass(chart(crossing, SCALE), "chart-seam-rule");

    // Coordinates are written to the hundredth: a column edge rarely lands on a
    // round number, and the trailing digits are markup and nothing else.
    assert.ok(Math.abs(Number(rule.attrs.x1) - edgeOf(geometry, 2)) < 0.01);
    assert.equal(rule.attrs.x1, rule.attrs.x2);
  });

  it("is not drawn on a range that never leaves a bank", () => {
    const ahead = [day("2046-07-14", "simulated"), day("2046-07-15", "simulated")];
    const past = [day("2001-07-14", "observed"), day("2001-07-15", "observed")];

    assert.equal(byClass(chart(ahead, SCALE), "chart-seam-rule").length, 0);
    assert.equal(byClass(chart(past, SCALE), "chart-seam-rule").length, 0);
  });

  it("carries the words, the rule alone saying nothing to a reader", () => {
    const days = [day("2026-08-01", "observed"), day("2026-08-02", "simulated")];
    const [label] = byClass(chart(days, SCALE), "chart-seam-label");

    assert.equal(label.textContent, texts.results.seam);
  });
});

describe("the drawing as a whole", () => {
  it("is one SVG node carrying its own name", () => {
    const node = chart(series(10), SCALE);

    assert.equal(node.tag, "svg");
    assert.equal(node.attrs.role, "img");
    assert.equal(node.attrs["aria-label"], texts.chart.label);
    assert.equal(node.attrs.viewBox, `0 0 ${BOX.width} ${frame(10).height}`);
  });

  it("builds every mark in the SVG namespace", () => {
    const marks = walk(chart(series(6), SCALE)).filter((node) => node.tag !== undefined);

    assert.ok(marks.length > 6);
    for (const mark of marks) {
      assert.equal(mark.namespace, "http://www.w3.org/2000/svg", `${mark.tag} is not SVG`);
    }
  });

  it("says what each panel plots, over it", () => {
    const titles = byClass(chart(series(8), SCALE), "chart-title");

    assert.deepEqual(
      titles.map((node) => node.textContent),
      [texts.chart.temperatures, texts.chart.precipitation],
    );
    // Over the plot, not in it: both sit above the panel they name.
    assert.ok(Number(titles[0].attrs.y) < frame(8).temperature.top);
    assert.ok(Number(titles[1].attrs.y) < frame(8).rain.top);
  });

  it("names the months where they turn, once each", () => {
    const days = [
      ...series(3),
      day("2026-09-01", "observed"),
      day("2026-09-02", "observed"),
    ];
    const names = byClass(chart(days, SCALE), "chart-month").map((node) => node.textContent);

    assert.deepEqual(names, ["août", "septembre"]);
  });

  it("says nothing above the days: no total, no average, no count", () => {
    const node = chart(series(20), SCALE);
    const written = walk(node)
      .map((child) => child.textContent)
      .filter(Boolean);

    // What is written on the chart is the two titles, the axes, the months and
    // the seam. Any other number would be an aggregate, which
    // docs/application.md refuses.
    const allowed = new Set([
      texts.results.seam,
      texts.chart.temperatures,
      texts.chart.precipitation,
      ...byClass(node, "chart-axis").map((child) => child.textContent),
      ...byClass(node, "chart-month").map((child) => child.textContent),
    ]);
    for (const text of written) {
      assert.ok(allowed.has(text), `unexpected text on the chart: "${text}"`);
    }
  });
});
