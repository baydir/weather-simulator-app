import assert from "node:assert/strict";
import { it } from "node:test";
import { periodLoader, PeriodBatch } from "../../web/static/js/period-loader.js";

it("shares both pending and completed periods between views", async () => {
  const cache = new Map();
  let calls = 0;
  const load = periodLoader(cache, async () => { calls++; return { days: [] }; });
  const [a, b] = await Promise.all([load(2020), load(2020)]);
  assert.equal(a, b);
  assert.equal(await load(2020), a);
  assert.equal(calls, 1);
});

it("retains completed periods on failure and resumes only on explicit request", async () => {
  const cache = new Map();
  const calls = [];
  let failed = true;
  const batch = new PeriodBatch({ years: [2020, 2021, 2022], cache,
    load: periodLoader(cache, async (year) => {
      calls.push(year);
      if (year === 2021 && failed) throw Object.assign(Error("quota"), { status: 429 });
      return {};
    }),
  });
  await batch.run();
  assert.deepEqual(calls, [2020, 2021]);
  assert.equal(cache.size, 1);
  assert.equal(batch.error.status, 429);
  assert.equal(batch.running, false);
  failed = false;
  await batch.run();
  assert.deepEqual(calls, [2020, 2021, 2021, 2022]);
  assert.equal(cache.size, 3);
});

it("stops after the active period and keeps its result", async () => {
  const cache = new Map();
  let finish;
  const batch = new PeriodBatch({ years: [2020, 2021], cache,
    load: periodLoader(cache, () => new Promise((resolve) => { finish = resolve; })),
  });
  const loading = batch.run();
  await Promise.resolve();
  batch.stop();
  finish({ days: [] });
  await loading;
  assert.equal(cache.size, 1);
  assert.equal(batch.running, false);
});
