/**
 * Raw value in, string ready to show out. No DOM, no state, no fetching.
 *
 * Everything that can be checked without a browser lives here, and `node --test`
 * is enough to check it. What is left elsewhere only places nodes.
 *
 * **Nothing here decides anything about the data.** The sky class arrives
 * decided by the server; the pictogram is picked from it, which is display and
 * display only — docs/application.md keeps the emoji off the JSON contract on
 * purpose, so that a drawn icon set would change this file and nothing else.
 *
 * The rounding is not a free choice either. docs/application.md settled it, and
 * CLAUDE.md rule 4 files rounding under data treatment: whole degrees, whole
 * km/h, **one decimal on millimetres**. That last one is the only one that is
 * not cosmetic — the 1 mm gate separates dry days from wet ones and commands
 * two of the five sky classes, so showing "0 mm" on a day carrying the rain
 * pictogram would be a contradiction on screen.
 */

import { texts } from "./i18n.js";

/** The five classes and the sixth case, which is the absence of one. */
export const SKY = {
  clear: { emoji: "☀️", label: texts.sky.clear },
  cloudy: { emoji: "⛅", label: texts.sky.cloudy },
  overcast: { emoji: "☁️", label: texts.sky.overcast },
  rain: { emoji: "🌧️", label: texts.sky.rain },
  snow: { emoji: "🌨️", label: texts.sky.snow },
};

/** No pictogram invented for a day the rule could not classify. */
const UNKNOWN_SKY = { emoji: "", label: texts.sky.unknown };

/**
 * The pictogram and its written equivalent, for any of the six cases.
 *
 * Both, always: an emoji alone is not readable by a screen reader, and
 * docs/application.md requires the written label beside it.
 */
export function sky(value) {
  return SKY[value] ?? UNKNOWN_SKY;
}

const WHOLE = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 });
const TENTH = new Intl.NumberFormat("fr-FR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

/** A gap stays a gap. Filling it would be a data-treatment decision. */
function present(value, format) {
  return value === null || value === undefined ? texts.measure.missing : format.format(value);
}

export function temperature(value) {
  return present(value, WHOLE);
}

export function precipitation(value) {
  return present(value, TENTH);
}

/** One decimal, for a number that is not a measurement — the grid step. */
export function decimal(value) {
  return present(value, TENTH);
}

export function wind(value) {
  return present(value, WHOLE);
}

export function isMissing(value) {
  return value === null || value === undefined;
}

// Dates arrive as "2046-07-14" and are read in UTC, deliberately. Left to the
// local zone, `new Date("2046-07-14")` lands on midnight UTC and slides back a
// day for any visitor west of Greenwich — the card would carry the wrong date
// while the server had it right.
const DAY = new Intl.DateTimeFormat("fr-FR", {
  weekday: "long",
  day: "numeric",
  timeZone: "UTC",
});
const MONTH = new Intl.DateTimeFormat("fr-FR", { month: "long", timeZone: "UTC" });
const FULL = new Intl.DateTimeFormat("fr-FR", {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

/** "samedi 14" — what a card carries. Spelled out: the card has the room. */
export function dayLabel(iso) {
  return DAY.format(new Date(iso));
}

/** "juillet" — shown only where the month changes. */
export function monthLabel(iso) {
  return MONTH.format(new Date(iso));
}

/** "14 juillet 2046" — the header, where there is room. */
export function fullDate(iso) {
  return FULL.format(new Date(iso));
}

/** "2046-07": what tells one month from the next, without parsing a date. */
export function monthKey(iso) {
  return iso.slice(0, 7);
}
