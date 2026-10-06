import assert from "node:assert/strict";
import { it } from "node:test";
import { install, reads } from "./dom-stub.js";
import { heatCounts } from "../../web/static/js/heat-counts.js";
install();
const range = { start: "2050-07-01", end: "2050-07-31" };
it("renders the server definition and distinguishes missing counts from zero", () => {
  const view = reads(heatCounts([
    { reading: "temperature_max", threshold: 33, comparison: "above", count: 0, available_days: 20 },
    { reading: "temperature_min", threshold: 24, comparison: "at_least", count: null, available_days: 0 },
  ], range));
  assert.match(view, /Maximale > 33 °C/);
  assert.match(view, /Minimale ≥ 24 °C/);
  assert.match(view, /0 jours/);
  assert.match(view, /20 \/ 31 journées renseignées/);
  assert.match(view, /—/);
});
it("does not invent counts for an old server response", () => {
  assert.match(reads(heatCounts(undefined, range)), /Données indisponibles/);
});
