/**
 * Transport, and nothing else.
 *
 * The browser fetches the data because Open-Meteo limits per IP address: a
 * server doing it would funnel every visitor through one address and reach the
 * ceiling immediately. So the calls happen here — and what to call is decided
 * there.
 *
 * **Nothing in this file reads a value.** No date is cut, no model is chosen, no
 * threshold is compared, no average is taken. The server hands over finished
 * URLs; this calls fetch on each and posts the answers back untouched. Not
 * because a browser may derive nothing — CLAUDE.md rule 3 asks something
 * narrower, that a rule the server already holds not be kept a second time here
 * — but because a transport module that reads its cargo stops being one. The
 * earlier prototype held the sky-class logic twice, once here and once in
 * Python, and the two drifted, on five lines of threshold comparisons.
 *
 * The one thing worth knowing about the exchange: /api/plan and /api/days are
 * two halves of the same search, and `today` travels from the first to the
 * second so that both agree on where the observed stops and the simulated
 * starts. It is echoed back verbatim, never recomputed here — a browser clock
 * is the visitor's, and the seam is not.
 *
 * It does not write, either: the sentences it hands to the visitor come from
 * i18n.js, where docs/application.md asks that every visible string live.
 */

import { texts } from "./i18n.js";

/** A refusal from the API, carrying the sentence meant for the visitor. */
export class SearchError extends Error {
  constructor(message, status, options) {
    super(message, options);
    this.name = "SearchError";
    this.status = status;
  }
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new SearchError(
      payload?.message ?? texts.transport.searchFailed,
      response.status,
    );
  }
  return payload;
}

async function getJson(url, message) {
  let response;
  try {
    response = await fetch(url);
  } catch (cause) {
    // A dropped connection, a DNS failure, a blocked request: no status at all.
    throw new SearchError(message, 0, { cause });
  }
  if (!response.ok) {
    throw new SearchError(message, response.status);
  }
  return response.json();
}

// Two sentences, because the two failures are not the visitor's to confuse.
// Why they read the way they do is explained where they are written, in i18n.js.
const { upstreamFailed: UPSTREAM_FAILED, serviceFailed: SERVICE_FAILED } = texts.transport;

/**
 * The constants the API enforces, so the form can refuse the same things it
 * does rather than keeping its own copy of the rules.
 */
export function loadConfig() {
  return getJson("/api/config", SERVICE_FAILED);
}

/**
 * Turn a place name into candidate locations.
 *
 * The geocoding address comes from the config rather than being written here,
 * so this file holds no knowledge of Open-Meteo at all. Nominatim is not used:
 * its terms forbid intensive use.
 */
export async function geocode(name, config, { count = 5, language = "fr" } = {}) {
  const url = new URL(config.geocoding_url);
  url.searchParams.set("name", name);
  url.searchParams.set("count", String(count));
  url.searchParams.set("language", language);
  url.searchParams.set("format", "json");

  const payload = await getJson(url.toString(), UPSTREAM_FAILED);
  // Absent rather than empty when nothing matches. Not a decision about the
  // data — an empty list and a missing key mean the same thing here.
  return payload.results ?? [];
}

/**
 * One search, end to end: ask what to fetch, fetch it, send it back.
 *
 * Returns the daily series exactly as the server built it. Every value in it
 * was computed there.
 *
 * `onProgress` is called with how many of the planned requests have come back,
 * so a caller can show something during the wait. It is told a count, not what
 * the count means.
 */
export async function search({ latitude, longitude, start, end }, onProgress = () => {}) {
  const query = { latitude, longitude, start, end };
  const plan = await postJson("/api/plan", query);

  const payloads = {};
  let done = 0;
  // Sequentially rather than in parallel: three or four requests hitting
  // Open-Meteo at once from one address is exactly the burst its rate limiter
  // watches for, and the wait saved would not be noticed.
  for (const request of plan.requests) {
    payloads[request.id] = await getJson(request.url, UPSTREAM_FAILED);
    onProgress(++done, plan.requests.length);
  }

  return postJson("/api/days", { ...query, today: plan.today, payloads });
}
