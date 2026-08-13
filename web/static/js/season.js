/**
 * Which season a search falls in, so the results page can be put on its ground.
 *
 * No DOM, no state, no fetching — the neighbour of `present.js` and `bounds.js`,
 * and `node --test` is enough to check it.
 *
 * **This is not a duplicated rule.** The server holds no version of the season:
 * it is derived here from `debut` and `fin`, which the URL already carries, and
 * it decides a background and nothing else. CLAUDE.md rule 3 sends that to the
 * browser — the criterion is the second copy, and there is no first one.
 *
 * **Astronomical bounds, not meteorological ones.** 21 December to 20 March, and
 * so on: the dates the visitor was asked about. They shift by a day from one year
 * to the next in the sky and do not here, which is the right trade for a wash of
 * colour — a page whose ground moved on 20 March one year and 21 March the next
 * would be answering a question nobody asked.
 *
 * **Reversed below the equator.** The latitude travels in the URL beside the
 * dates, and January in Santiago is a summer — a white-to-navy page under 30 °C
 * would be a picture of the calendar rather than of the weather the range holds.
 */

/** Winter first, and it is the one that wraps: December belongs to January's. */
const OPPOSITE = {
  winter: "summer",
  spring: "autumn",
  summer: "winter",
  autumn: "spring",
};

/**
 * The northern season of a month and a day, read as one number.
 *
 * `month * 100 + day` orders dates inside a year without parsing one, in the
 * same spirit as `bounds.js` comparing ISO strings: nothing here can slide a day
 * by reading it in the wrong zone, because nothing here reads a zone.
 */
function northern(month, day) {
  const stamp = month * 100 + day;
  if (stamp < 321) return "winter";
  if (stamp < 621) return "spring";
  if (stamp < 921) return "summer";
  if (stamp < 1221) return "autumn";
  return "winter";
}

/**
 * The season one day belongs to. `iso` is "2046-07-14".
 *
 * The hemisphere is settled here rather than in the count below, so that
 * counting has nothing to know about it. A missing or unreadable latitude
 * compares false against zero and lands on the northern reading, which is what a
 * hand-edited URL should get: the calendar, not an error.
 */
export function seasonOf(iso, latitude) {
  const season = northern(Number(iso.slice(5, 7)), Number(iso.slice(8, 10)));
  return latitude < 0 ? OPPOSITE[season] : season;
}

/**
 * Every day of the range, both ends counted.
 *
 * Read at noon UTC and stepped by exact days, for the reason `bounds.js` gives
 * where it measures a span: midnight in a local zone is 23 or 25 hours from the
 * next one twice a year, and the walk would skip or repeat a day. An unusable
 * range — either end missing, or running backwards — yields nothing rather than
 * throwing; the form and the API both refuse it long before this file sees it.
 */
function* days(start, end) {
  if (!start || !end || start > end) return;
  const DAY = 24 * 60 * 60 * 1000;
  const last = Date.parse(`${end}T12:00:00Z`);
  for (let stamp = Date.parse(`${start}T12:00:00Z`); stamp <= last; stamp += DAY) {
    yield new Date(stamp).toISOString().slice(0, 10);
  }
}

/**
 * The season the range spends most of its days in, or null if there is no range.
 *
 * **A search touches two seasons at most.** The shortest season is winter, at
 * ninety days, and a search is ninety days at most — so the count never has more
 * than two candidates, whatever it is asked.
 *
 * **Ties go to the season the range ends in.** The walk runs forward and `>=`
 * lets a later season take the lead on equal footing, so forty-five days of
 * winter followed by forty-five of spring come out spring. A range is read
 * towards its end, and that is the season it is heading into.
 */
export function dominantSeason({ start, end, latitude }) {
  const counts = new Map();
  let best = null;
  for (const iso of days(start, end)) {
    const season = seasonOf(iso, latitude);
    const count = (counts.get(season) ?? 0) + 1;
    counts.set(season, count);
    if (best === null || count >= counts.get(best)) best = season;
  }
  return best;
}
