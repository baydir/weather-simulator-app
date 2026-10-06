import assert from "node:assert/strict";
import { it } from "node:test";
import { WeatherCache } from "../../web/static/js/weather-cache.js";
function storage(limit = Infinity) {
  const data = new Map();
  return { get length() { return data.size; }, key: (i) => [...data.keys()][i],
    getItem: (key) => data.get(key) ?? null, removeItem: (key) => data.delete(key),
    setItem(key, value) { if (data.size >= limit && !data.has(key)) throw Error("full"); data.set(key, value); },
  };
}
it("preserves raw precision and nulls across visits and obeys the current expiry policy", () => {
  const store = storage();
  let now = 1000;
  const cache = new WeatherCache(() => store, () => now);
  const payload = { values: [30.123456, null, 0] };
  cache.write("same-url", payload, null);
  assert.deepEqual(new WeatherCache(() => store, () => now).read("same-url", null), payload);
  assert.equal(cache.read("another-url", null), null);
  assert.equal(cache.read("same-url", undefined), null);
  now += 900_000;
  assert.equal(cache.read("same-url", 900), null);
});
it("never revives an expired provisional response when the dates later become stable", () => {
  const store = storage();
  let now = 1000;
  const cache = new WeatherCache(() => store, () => now);
  cache.write("same-url", { provisional: true }, 900);
  now += 31 * 86400_000;
  assert.equal(cache.read("same-url", null), null);
});
it("handles denied or full storage and evicts only its own entries", () => {
  const denied = new WeatherCache(() => { throw Error("denied"); });
  denied.write("url", {}, null);
  assert.equal(denied.read("url", null), null);
  const store = storage(2);
  store.setItem("unrelated", "keep");
  const cache = new WeatherCache(() => store, () => 1);
  cache.write("old", { a: 1 }, null);
  cache.write("new", { a: 2 }, null);
  assert.equal(store.getItem("unrelated"), "keep");
  assert.equal(cache.read("old", null), null);
  assert.deepEqual(cache.read("new", null), { a: 2 });
});
