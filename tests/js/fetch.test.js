/**
 * Transport failures, and the sentence each one earns.
 *
 * The first tests this file has ever had, and they exist for one regression in
 * particular: a request that carries no clock does not fail, it hangs, and a
 * page that hangs shows no error at all — it sits on "Récupération des
 * données…" for as long as the visitor is willing to look at it.
 *
 * Nothing here waits for a real timeout. What is checkable without waiting is
 * whether a request goes out under a clock, and whether a clock that has run
 * out is told apart from the other ways a call fails — which is the whole of
 * what this module decides.
 */

import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";

import { geocode, loadConfig, search, SearchError } from "../../web/static/js/fetch.js";
import { texts } from "../../web/static/js/i18n.js";

const CONFIG = { geocoding_url: "https://geocoding-api.open-meteo.com/v1/search" };
const SEARCH = { latitude: 48.85, longitude: 2.35, start: "2046-07-01", end: "2046-07-20" };

/** Every call the module made, so a test can look at what it asked for. */
let calls = [];

function stubFetch(answer) {
  calls = [];
  globalThis.fetch = (url, options = {}) => {
    calls.push({ url: String(url), options });
    return answer(url, options);
  };
}

/** What a browser throws when AbortSignal.timeout runs out. */
const timedOut = () => Promise.reject(new DOMException("signal timed out", "TimeoutError"));

/** What it throws when the connection fails outright. */
const refused = () => Promise.reject(new TypeError("Failed to fetch"));

const answers = (body, { ok = true, status = 200 } = {}) =>
  Promise.resolve({ ok, status, json: () => Promise.resolve(body) });

afterEach(() => {
  delete globalThis.fetch;
});

describe("every request goes out under a clock", () => {
  it("puts a signal on a call to our own API", async () => {
    stubFetch(() => answers({ max_days: 92 }));
    await loadConfig();
    assert.equal(calls.length, 1);
    assert.ok(calls[0].options.signal instanceof AbortSignal, "aucun signal sur /api/config");
  });

  it("puts one on an upstream call too", async () => {
    stubFetch(() => answers({ results: [] }));
    await geocode("Pontarlier", CONFIG);
    assert.ok(calls[0].options.signal instanceof AbortSignal, "aucun signal sur Open-Meteo");
  });

  it("puts one on a POST, which is where a search starts", async () => {
    stubFetch(() => answers({ today: "2026-08-19", requests: [] }));
    await search(SEARCH).catch(() => {});
    assert.equal(calls[0].options.method, "POST");
    assert.ok(calls[0].options.signal instanceof AbortSignal, "aucun signal sur /api/plan");
  });
});

describe("a clock that ran out is told apart", () => {
  it("says so rather than blaming the rate limit", async () => {
    stubFetch(timedOut);
    await assert.rejects(geocode("Pontarlier", CONFIG), (error) => {
      assert.ok(error instanceof SearchError);
      assert.equal(error.message, texts.transport.tookTooLong);
      // The advice differs, which is the whole reason for a fourth sentence:
      // nothing was refused here, so there is no rate limit to sit out.
      assert.notEqual(error.message, texts.transport.upstreamFailed);
      return true;
    });
  });

  it("says so on our own API as well", async () => {
    stubFetch(timedOut);
    await assert.rejects(loadConfig(), (error) => {
      assert.equal(error.message, texts.transport.tookTooLong);
      return true;
    });
  });

  it("says so when a search stalls on its first call", async () => {
    stubFetch(timedOut);
    await assert.rejects(search(SEARCH), (error) => {
      assert.equal(error.message, texts.transport.tookTooLong);
      return true;
    });
  });
});

describe("the other failures keep their own words", () => {
  it("leaves a refused connection with the caller's sentence", async () => {
    stubFetch(refused);
    await assert.rejects(geocode("Pontarlier", CONFIG), (error) => {
      assert.equal(error.message, texts.transport.upstreamFailed);
      return true;
    });
  });

  it("leaves a rate limit with the caller's sentence, and its status", async () => {
    stubFetch(() => answers(null, { ok: false, status: 429 }));
    await assert.rejects(geocode("Pontarlier", CONFIG), (error) => {
      assert.equal(error.message, texts.transport.upstreamFailed);
      assert.equal(error.status, 429);
      return true;
    });
  });

  it("lets the API's own refusal through, worded by the server", async () => {
    stubFetch(() => answers({ message: "Ce lieu n'est pas encore couvert." }, { ok: false, status: 400 }));
    await assert.rejects(search(SEARCH), (error) => {
      assert.equal(error.message, "Ce lieu n'est pas encore couvert.");
      return true;
    });
  });
});

it("reuses exact raw data on a later search and reruns current server processing", async () => {
  const { search } = await import("../../web/static/js/fetch.js?raw-cache-check");
  const data = new Map();
  globalThis.localStorage = {
    get length() { return data.size; }, key: (i) => [...data.keys()][i],
    getItem: (key) => data.get(key) ?? null, setItem: (key, value) => data.set(key, value),
    removeItem: (key) => data.delete(key),
  };
  let processed = 0;
  const raw = { daily: { temperature_2m_max: [30.12345, null] } };
  stubFetch((url, options) => {
    if (url === "/api/plan") return answers({ today: "2026-10-06", requests: [
      { id: "projection", url: "https://fixture.invalid/stable", cache_max_age_seconds: null },
    ] });
    if (url === "/api/days") {
      assert.deepEqual(JSON.parse(options.body).payloads.projection, raw);
      return answers({ revision: ++processed, days: [] });
    }
    return answers(raw);
  });
  try {
    assert.equal((await search(SEARCH)).revision, 1);
    assert.equal((await search(SEARCH)).revision, 2);
    assert.equal(calls.filter((call) => call.url.startsWith("https:")).length, 1);
  } finally { delete globalThis.localStorage; }
});

it("halts after 429 and does not send another upstream request during cooldown", async () => {
  const { search } = await import("../../web/static/js/fetch.js?quota-check");
  stubFetch((url) => url === "/api/plan" ? answers({ today: "2026-10-06", requests: [
    { id: "first", url: "https://fixture.invalid/limited" },
    { id: "second", url: "https://fixture.invalid/unused" },
  ] }) : answers(null, { ok: false, status: 429 }));
  await assert.rejects(search(SEARCH), (error) => error.status === 429);
  await assert.rejects(search(SEARCH), (error) => error.status === 429);
  assert.equal(calls.filter((call) => call.url.startsWith("https:")).length, 1);
});
