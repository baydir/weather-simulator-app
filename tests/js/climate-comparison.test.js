import assert from "node:assert/strict";
import { it } from "node:test";
import { install, reads, byClass } from "./dom-stub.js";
import { climateWindows, climateCards, climateChart } from "../../web/static/js/climate-comparison.js";
install();
const config = { coverage_start: "1950-01-01", coverage_end: "2050-12-31", max_days: 92, climate_window_years: 10 };
const scale = { step: 5, edges: [5, 10, 15, 20, 25, 30, 35, 40] };

it("selects complete recent calendar years and future years from the server's today", () => {
  const range = { start: "2040-07-01", end: "2040-07-31" };
  const windows = climateWindows(range, config, "2026-10-06");
  assert.deepEqual(windows.past, Array.from({ length: 10 }, (_, i) => 2016 + i));
  assert.deepEqual(windows.future, Array.from({ length: 10 }, (_, i) => 2027 + i));
  const nearEnd = climateWindows(range, config, "2048-01-01");
  assert.deepEqual(nearEnd.future, [2049, 2050]);
});

it("keeps winter entirely within the past window and respects future coverage", () => {
  const winter = { start: "2025-12-21", end: "2026-03-20" };
  const windows = climateWindows(winter, config, "2026-01-10");
  assert.equal(windows.past.at(-1), 2024);
  assert.equal(climateWindows(winter, config, "2026-10-06").past.at(-1), 2025);
  assert.equal(climateWindows(winter, config, "2048-10-06").future.at(-1), 2049);
});

it("renders server summaries and differences without recomputing them", () => {
  const windows = { past: [2016, 2025], future: [2027, 2036], required: 10 };
  const summary = { past: { temperature_max: 27.2, temperature_min: 16.8, complete_max_years: 10, complete_min_years: 10 },
    future: { temperature_max: 28.6, temperature_min: null, complete_max_years: 10, complete_min_years: 9 },
    difference: { temperature_max: 1.4, temperature_min: null },
  };
  const text = reads(climateCards(summary, windows));
  assert.match(text, /27,2 °C/);
  assert.match(text, /9\/10/);
  assert.match(text, /Écart années à venir − passé : \+1,4 °C.*—/);
});

it("draws one axis, continues into simulation, and never bridges a missing requested year", () => {
  const entries = [
    { year: 2024, side: "past", means: { temperature_max: 27, temperature_min: 17 } },
    { year: 2025, side: "past", means: { temperature_max: 28, temperature_min: 18 } },
    { year: 2027, side: "future", hasSimulated: true, means: { temperature_max: 29, temperature_min: 19 } },
    { year: 2028, side: "future", hasSimulated: true, means: null },
    { year: 2029, side: "future", hasSimulated: true, means: { temperature_max: 30, temperature_min: 20 } },
  ];
  const graph = climateChart(entries, scale, 320);
  assert.equal(graph.tag, "svg");
  assert.equal(byClass(graph, "climate-line").length, 4);
  assert.equal(byClass(graph, "simulated").length, 2);
  assert.equal(byClass(graph, "climate-point").length, 8);
});

it("formats differences with a sign but never displays a rounded negative zero", () => {
  const windows = { past: [2016, 2025], future: [2027, 2036], required: 10 };
  assert.match(reads(climateCards({ difference: { temperature_max: -0.01, temperature_min: 1.2 } }, windows)),
    /Écart années à venir − passé : 0,0 °C.*\+1,2 °C/);
});
