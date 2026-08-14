/**
 * The chart under the strip: the shape of the period, which a card cannot show.
 *
 * A card says one day. Ninety cards say ninety days, one at a time, and never
 * what the period *looks like* — where the heat sits, which fortnight is wet.
 * That is the whole reason this exists, and it is what settles its width: drawn
 * column by column under the cards it would be perfectly aligned and useless,
 * since eight days of curve is exactly what the strip already shows.
 *
 * **Two panels sharing one axis of dates, never two vertical scales on one
 * plot.** Where the two scales meet is arbitrary, and a reader takes the
 * crossing of a curve and a bar for a fact about the weather. So the
 * temperatures are drawn above and the rain below, in a panel of its own with
 * its own baseline.
 *
 * **Nothing here decides anything about the data.** No average, no count of
 * rainy days, no total: one mark per day and nothing above them, which is what
 * docs/application.md asks of the strip and asks of this. The two axes are the
 * one thing this file does settle, and both were arbitrated:
 *
 * - *Temperatures* are framed on the served band ladder — the axis runs from the
 *   multiple of five below the coldest reading to the multiple above the
 *   warmest, half a step of air at each end. Inside the ladder every gridline is
 *   a band boundary, the same five degrees the cards are tinted by, so a height
 *   here and a colour up there are the same reading; past its two open ends the
 *   ruling carries on at the same interval, which is what puts a line on zero.
 *
 *   The nine tints were laid behind the curves at first and taken back out: the
 *   drawing said the level twice, and the second saying was the loud one.
 *   Nothing is coloured by value here — what carries the absolute level is the
 *   numbered axis, and the strip above carries it in colour.
 * - *Rain* is framed on the wettest day of the period, and on ten millimetres
 *   when the period is drier than that. The floor is what keeps a drizzle from
 *   drawing the same bar as a downpour: without it, a period whose wettest day
 *   is 0,3 mm would fill the panel.
 *
 * The boundaries themselves are served by /api/config and passed in: they are
 * what the axis is graduated on. Writing the ladder out here would be the second
 * copy CLAUDE.md rule 3 is about.
 *
 * **A second year may be laid under the first**, and it changes one thing about
 * the drawing that is worth knowing before reading the code: the temperature
 * window is then framed on **both** series at once. Two windows would put each
 * year on its own scale, and two curves on two scales say nothing about each
 * other — which is the same reason docs/application.md gives for refusing a
 * fixed absolute axis, applied inside one panel instead of between two searches.
 * The compared year contributes nothing to the rain panel: it is not drawn there.
 *
 * Nothing in here fetches or holds state: a series and a scale go in, one node
 * comes out. Which is what lets `node --test` check the geometry.
 */

import { svg } from "./dom.js";
import { texts } from "./i18n.js";
import * as present from "./present.js";
import { seamIndex } from "./series.js";

/**
 * The drawing, in its own units. The page scales it; nothing here is pixels.
 *
 * `left` is the room the axis numbers need, `bottom` the room the month names
 * need, and `top` and `gap` the room the two titles need above their panels.
 *
 * The rain panel is the shorter of the two and stays so: it carries one quantity
 * against a baseline where the other carries two curves and the spread between
 * them. It was a third of the temperature panel at first, which was too little
 * for its own graduation to breathe — three lines in fifty-six units.
 *
 * **The two panels were raised together, keeping their ratio at exactly 1,75.**
 * They were 168 and 96. A season of ninety-two days over a window of thirty-five
 * degrees gave a degree a little under five units, and once a compared year was
 * laid underneath, the whole question — does the day sit inside the old band or
 * above it — was being answered in three or four units of height. At 245 and 140
 * a degree is seven, and the same reading is made at a glance. The margins did
 * not follow: `top`, `gap` and `bottom` are room for titles and month names, so
 * they are typographic and not measured in degrees.
 */
export const BOX = {
  width: 1000,
  // Wide enough for the longest thing the axis can say — "-10 °C", the unit
  // riding on the topmost number. Measured on the rendering, not guessed: at 42
  // the label began outside the viewBox and came out beheaded.
  left: 56,
  right: 14,
  top: 30,
  temperature: 245,
  // **The gap stopped being empty, and that is what sets it.** It holds the
  // temperature panel's own row of dates, fourteen below its foot, and the rain
  // title, which hangs twelve above its panel. At 36 the capitals landed on the
  // digits' descenders; at 48 they cleared by twenty-two, which the geometry
  // called separate and the eye read as one block — a title has to belong
  // visibly to the panel under it, not to the axis over it. At 72 there are
  // forty-six units between the two lines, and the title has plainly crossed
  // over to the panel it names.
  gap: 72,
  rain: 140,
  // Room for two rows under the baseline — the days, then the months — where it
  // used to hold one. At 26 the month names sat 18 below the baseline with eight
  // to spare; the second row needs thirty and its descenders need the rest.
  bottom: 40,
};

/** How far a panel's title sits above it. */
const TITLE_LIFT = 12;

/** Below this, the rain axis stops following the period. */
export const RAIN_FLOOR_MM = 10;

/** Two decimals is more than a coordinate needs, and keeps the markup small. */
const round = (value) => Math.round(value * 100) / 100;

/** The one test for a hole in the series, written once. */
const missing = (value) => value === null || value === undefined;

/** What the panels sit in, once the number of days is known. */
export function frame(count, box = BOX) {
  const plot = { from: box.left, to: box.width - box.right };
  const temperature = { top: box.top, bottom: box.top + box.temperature };
  const rain = { top: temperature.bottom + box.gap };

  return {
    box,
    height: box.top + box.temperature + box.gap + box.rain + box.bottom,
    plot,
    // Zero days would divide by zero. It cannot happen — a served series has at
    // least one day — but a column of zero width is a nicer failure than NaN.
    column: count === 0 ? 0 : (plot.to - plot.from) / count,
    // Each panel is dated at its own foot. **The two rows are one axis read
    // twice, not two axes**: the same days, at the same x, from one function
    // called twice — which is what CLAUDE.md rule 3 asks for and the opposite of
    // what it forbids. Repeating them is the whole point. The temperature panel
    // is 245 units tall, and dating a point on it meant carrying the eye down
    // past the rain panel to find the row underneath.
    temperature: { ...temperature, dates: temperature.bottom + 14 },
    rain: { top: rain.top, base: rain.top + box.rain },
    // Under the lower panel the row is doubled by the months, numbers over
    // words, in the order a French date is said. The months are named once
    // where they turn and only here: repeated under both panels they would be
    // four words too many, and a number above a name is already a date.
    dates: rain.top + box.rain + 14,
    months: rain.top + box.rain + 30,
  };
}

/** The left edge of a day's column, and its middle, where a point is placed. */
export const edgeOf = (frame, index) => frame.plot.from + index * frame.column;
export const middleOf = (frame, index) => edgeOf(frame, index) + frame.column / 2;

/**
 * The window the temperature panel frames, snapped to the band boundaries.
 *
 * `null` when not one day of the period carries a temperature, which is a page
 * with no curve to draw rather than an axis from nowhere to nowhere.
 */
export function temperatureWindow(days, step) {
  const values = days
    .flatMap((day) => [day.temperature_min, day.temperature_max])
    .filter((value) => !missing(value));
  if (values.length === 0) return null;

  // Half a step of air at each end, so that the warmest reading of the period
  // does not draw itself on the frame.
  return {
    bottom: Math.floor(Math.min(...values) / step) * step - step / 2,
    top: Math.ceil(Math.max(...values) / step) * step + step / 2,
  };
}

/** The top of the rain axis: the wettest day, or the floor. */
export function rainCeiling(days) {
  const values = days.map((day) => day.precipitation).filter((value) => !missing(value));
  return Math.max(RAIN_FLOOR_MM, ...values);
}

/**
 * Where the temperature panel is ruled.
 *
 * **Inside the ladder, the graduation is the ladder** — every line is one of the
 * served boundaries, so a height here and a tint on a card are the same step.
 * Beyond it the ladder has nothing to give: the coldest band is everything under
 * the first boundary and the warmest everything over the last, both open by
 * construction. A frozen period would be a panel with one line in it. So the
 * ruling carries on at the same interval past each end — which is what puts a
 * line on zero, and on the far side would put one on 45.
 */
export function ticks(span, edges, step) {
  const values = [...edges];
  for (let value = edges[0] - step; value > span.bottom - step; value -= step) values.push(value);
  for (let value = edges.at(-1) + step; value < span.top + step; value += step) values.push(value);

  return values.filter((value) => value > span.bottom && value < span.top).sort((a, b) => a - b);
}

/**
 * Where the rain panel is ruled: two or three lines, on round millimetres.
 *
 * Nothing is served to graduate this one on — the ceiling follows the period, so
 * the interval has to be chosen for the height it happens to have. The choice is
 * the smallest round step that leaves at most four intervals, which is what
 * keeps the labels to numbers a reader recognises: 5 and 10 on a quiet period,
 * 10 and 20 on a wet one.
 */
const RAIN_STEPS = [1, 2, 5, 10, 20, 25, 50, 100, 200];

export function rainTicks(ceiling) {
  const step = RAIN_STEPS.find((candidate) => ceiling / candidate <= 4) ?? RAIN_STEPS.at(-1);
  const values = [];
  for (let value = step; value <= ceiling; value += step) values.push(value);
  return values;
}

/**
 * The stretches of consecutive days that carry a value.
 *
 * **A gap stays a gap.** Joining across a missing day would draw a line where
 * there is no reading, which is inventing data at the one place the series
 * admits it has none — present.js refuses the same thing on a number.
 */
export function runs(days, read) {
  const found = [];
  let current = null;

  for (const [index, day] of days.entries()) {
    const value = read(day);
    if (missing(value)) {
      current = null;
      continue;
    }
    if (current === null) {
      current = [];
      found.push(current);
    }
    current.push({ index, value });
  }
  return found;
}

/** The radius of a day's mark, small enough that a whole season does not touch. */
const POINT = 1.8;

/**
 * One stretch of a curve: the segments, then the readings they join.
 *
 * **Every day is a dot, and the dots are drawn over the line.** A polyline alone
 * says where the temperature went; it does not say what was measured and what
 * was merely passed through on the way. The daily reading is the datum here, and
 * the segment between two of them is an eye's convenience — it is drawn straight
 * for that reason, since anything smoothed would invent a Tuesday afternoon the
 * series has no reading for.
 *
 * A lone reading needs no special case for the same reason: it draws its dot
 * like every other, and simply has no segment to draw.
 *
 * **`points` is what tells the compared year apart from the one asked for.** The
 * dot is the mark of a reading, and the reading this page is about is the one the
 * visitor searched for; the older year is a ground to read it against. Drawn with
 * its own dots it would claim the same standing, and two hundred marks on one
 * panel stop being marks. The cost is that a lone compared day draws nothing at
 * all — a segment needs two ends — which is the right silence: one grey dot in a
 * season would be noise, not a reading.
 */
function stroke(frame, run, y, className, { points = true } = {}) {
  const at = ({ index, value }) => [round(middleOf(frame, index)), round(y(value))];
  const marks = [];

  if (run.length > 1) {
    const d = run.map((point, step) => `${step === 0 ? "M" : "L"}${at(point).join(" ")}`).join(" ");
    marks.push(svg("path", { className: `chart-line ${className}`, attrs: { d } }));
  }
  if (!points) return marks;
  for (const point of run) {
    const [cx, cy] = at(point);
    marks.push(
      svg("circle", { className: `chart-point ${className}`, attrs: { cx, cy, r: POINT } }),
    );
  }
  return marks;
}

/**
 * The compared year as a band: the room between its two readings, filled.
 *
 * **Only the compared year is ever filled, and that is a change from what this
 * panel used to do.** The spread of the drawn year was filled too, very pale, as
 * a way of making its amplitude a thickness. It was taken back out: a fill on
 * this panel now means one thing and one thing only — *this is the older year* —
 * and a second wash, however faint, made the reader ask which of the two a shade
 * of grey belonged to. The amplitude of the drawn year is not lost, it is simply
 * no longer painted: it is still the room between two curves both of which are
 * on the panel, in colour, carrying their dots.
 *
 * What the band buys is the reading the whole feature exists for. The compared
 * year stops being two lines to follow and becomes a ground: the question is
 * whether the day sits inside what used to be ordinary or climbs out of it, and
 * that is answered by looking, not by comparing two wiggles.
 *
 * A day the compared year has no counterpart for reads `undefined` here, and
 * breaks the band exactly as it breaks the line.
 */
function pastBand(frame, compared, y) {
  const paired = runs(compared, (day) =>
    missing(day?.temperature_min) || missing(day?.temperature_max) ? null : day,
  );

  return paired
    .filter((run) => run.length > 1)
    .map((run) => {
      const at = (point, key) =>
        `${round(middleOf(frame, point.index))} ${round(y(point.value[key]))}`;
      const out = run.map((point) => at(point, "temperature_max"));
      const back = [...run].reverse().map((point) => at(point, "temperature_min"));

      return svg("path", {
        className: "chart-past-band",
        attrs: { d: `M${out.join(" L")} L${back.join(" L")} Z` },
      });
    });
}

/**
 * The chart, as one node.
 *
 * `scale` is what /api/config serves: the band boundaries and their step.
 *
 * `compared` is the other year, already laid alongside by `compare.js` — one slot
 * per day drawn, `null` where that year has no such day. It is aligned before it
 * arrives here, so this file never reads a date to place a mark.
 */
export function chart(days, scale, { compared = null, box = BOX } = {}) {
  const geometry = frame(days.length, box);
  // One window over both years, or the two curves would each be drawn on their
  // own scale and the gap between them would be a picture of the framing.
  const framed = compared ? [...days, ...compared.filter(Boolean)] : days;
  const span = temperatureWindow(framed, scale.step);
  const ceiling = rainCeiling(days);
  const year = comparedYear(compared);

  const y = (value) =>
    geometry.temperature.top +
    ((span.top - value) / (span.top - span.bottom)) * box.temperature;
  const height = (value) => (value / ceiling) * box.rain;

  // The order of this list is the stacking order: the graduation under
  // everything, then the compared year — its band, then its two edges — then the
  // two curves of the year asked for, and the seam last so that no mark crosses
  // it.
  //
  // **Nothing is filled unless a year is compared.** A panel showing one year
  // shows two curves and the air between them, and that is all it needs to; the
  // one fill this drawing has left is reserved for saying *older year*.
  const marks = [
    title(geometry, geometry.temperature.top, texts.chart.temperatures),
    title(geometry, geometry.rain.top, texts.chart.precipitation),
    ...(span ? [graduation(geometry, span, scale.edges, scale.step, y)] : []),
    ...(span && compared ? pastBand(geometry, compared, y) : []),
    ...(span && compared ? pastCurves(geometry, compared, y) : []),
    ...(span ? curves(geometry, days, y) : []),
    rain(geometry, days, ceiling, height),
    ...(span
      ? [dates(geometry, days, geometry.temperature.bottom, geometry.temperature.dates)]
      : []),
    dates(geometry, days, geometry.rain.base, geometry.dates),
    months(geometry, days),
    seamMark(geometry, days),
    year ? pastLegend(geometry, year) : null,
  ].filter(Boolean);

  return svg(
    "svg",
    {
      className: "chart",
      attrs: {
        viewBox: `0 0 ${box.width} ${geometry.height}`,
        role: "img",
        // The one sentence, and it names the compared year when there is one:
        // a reader who gets nothing from a drawing must at least be told what
        // the drawing now holds.
        "aria-label": texts.chart.label(year),
      },
    },
    marks,
  );
}

/** The year the compared series belongs to, read off its first real day. */
function comparedYear(compared) {
  return compared?.find(Boolean)?.date.slice(0, 4) ?? null;
}

/**
 * The band's own name, on the drawing: a sample of it and the year beside.
 *
 * **This is the first text on this panel that is not a title, an axis or the
 * seam, and putting it here was a deliberate widening of a rule.**
 * docs/application.md forbids the chart writing anything above the days — no
 * total, no average, no count, no extreme of the range — and a test enforces it
 * by refusing every string on the drawing that is not on a short list. A year is
 * none of those things: it names a mark, in the same way the seam label names a
 * crossing. It computes nothing and it says nothing about the period. So the
 * list gained an entry rather than the rule losing its point, and the test still
 * catches the aggregate it was written for.
 *
 * **It is set in the margin above the plot**, on the title's own line and
 * right-anchored, which is the one strip of the panel where no mark can ever be:
 * the window is framed half a band clear of the warmest reading. Anchored to the
 * band itself it would have to dodge a curve, and which curve depends on the
 * weather.
 */
const LEGEND = { swatch: 18, gap: 6, year: 26 };

function pastLegend(frame, year) {
  const left = frame.plot.to - (LEGEND.swatch + LEGEND.gap + LEGEND.year);
  const baseline = frame.temperature.top - TITLE_LIFT;
  // The sample is centred on the text rather than sat on its baseline: a band
  // hanging under the digits would read as an underline.
  const top = baseline - 8;
  const bottom = baseline - 1;
  const edge = (at) =>
    svg("line", {
      className: "chart-line past",
      attrs: { x1: round(left), x2: round(left + LEGEND.swatch), y1: at, y2: at },
    });

  return svg("g", { className: "chart-legend" }, [
    svg("rect", {
      className: "chart-past-band",
      attrs: {
        x: round(left),
        y: top,
        width: LEGEND.swatch,
        height: bottom - top,
      },
    }),
    edge(top),
    edge(bottom),
    svg("text", {
      className: "chart-legend-year",
      text: year,
      attrs: { x: round(left + LEGEND.swatch + LEGEND.gap), y: round(baseline) },
    }),
  ]);
}

/**
 * The two curves, each broken wherever its own readings are.
 *
 * The maximum is drawn first and the minimum over it, which only matters where
 * they meet: a day whose two readings are equal shows the cool mark, and the
 * cards say the same thing in the same order.
 */
function curves(frame, days, y) {
  return [
    ["temperature_max", "high"],
    ["temperature_min", "low"],
  ].flatMap(([key, className]) =>
    runs(days, (day) => day[key]).flatMap((run) => stroke(frame, run, y, className)),
  );
}

/**
 * The other year, under the one that was asked for.
 *
 * The same two readings and the same breaks, drawn without dots and in one
 * colour: it is a ground, not a second subject. The classes carry `past` first
 * so the stylesheet can override the warm and the cool it would otherwise
 * inherit from `high` and `low` — the two names are kept because a reader who
 * inspects the drawing should find the maximum called a maximum in both years.
 *
 * A slot the compared year has no day for reads `undefined`, which `runs` treats
 * as a hole exactly as it treats a missing reading. Nothing is joined across it.
 */
function pastCurves(frame, compared, y) {
  return [
    ["temperature_max", "high"],
    ["temperature_min", "low"],
  ].flatMap(([key, className]) =>
    runs(compared, (day) => day?.[key]).flatMap((run) =>
      stroke(frame, run, y, `past ${className}`, { points: false }),
    ),
  );
}

/**
 * What a panel plots, said above it.
 *
 * Two panels sharing an axis of dates need saying apart, and the units alone do
 * not do it: degrees and millimetres tell a reader what is measured, not what
 * they are looking at. Set over the plot rather than beside it, so the eye meets
 * the word before the marks.
 */
function title(frame, top, text) {
  return svg("text", {
    className: "chart-title",
    text,
    attrs: { x: frame.plot.from, y: round(top - TITLE_LIFT) },
  });
}

/**
 * The graduation: a hairline at each step the window shows, numbered, and the
 * axis of dates the panel stands on.
 *
 * These are the same five degrees the cards are tinted by, which is what lets a
 * height on this panel and a colour on the strip be read as one thing.
 *
 * **The line along the foot is a frame, not a zero, and the difference is worth
 * knowing before reading either panel.** The rain panel's baseline is the datum
 * itself: bars stand on it and it is nought millimetres. This one falls on
 * whatever half-step the window happened to snap to — 7,5 °C on a summer, −12,5
 * on a frozen period — and the curves float clear of it. It is drawn because a
 * panel closed on three sides reads as unfinished and the eye keeps looking for
 * the fourth; it carries no number for the same reason it means nothing, the
 * lowest value written on the axis being the lowest boundary the ladder has
 * inside the window, one hairline above.
 */
function graduation(frame, span, edges, step, y) {
  const inside = ticks(span, edges, step);
  const rules = inside.map((edge) =>
    svg("line", {
      className: "chart-rule",
      attrs: {
        x1: frame.plot.from,
        x2: frame.plot.to,
        y1: round(y(edge)),
        y2: round(y(edge)),
      },
    }),
  );
  const labels = inside.map((edge, index) =>
    svg("text", {
      className: "chart-axis",
      // The unit on the topmost only: repeated down the axis it would be nine
      // times the same word, and the numbers are what is read.
      text:
        index === inside.length - 1
          ? `${present.temperature(edge)} ${texts.units.celsius}`
          : present.temperature(edge),
      attrs: { x: frame.plot.from - 8, y: round(y(edge) + 3), "text-anchor": "end" },
    }),
  );

  const axis = svg("line", {
    className: "chart-baseline",
    attrs: {
      x1: frame.plot.from,
      x2: frame.plot.to,
      y1: frame.temperature.bottom,
      y2: frame.temperature.bottom,
    },
  });

  return svg("g", { className: "chart-graduation" }, [...rules, axis, ...labels]);
}

/** The bars, ruled and numbered like the panel above them. */
function rain(frame, days, ceiling, height) {
  const bars = days.flatMap((day, index) => {
    if (missing(day.precipitation)) {
      // A missing reading and a dry day both draw no bar, so the missing one
      // says so: a notch under the baseline, where nothing else sits.
      return [
        svg("rect", {
          className: "chart-gap",
          attrs: {
            x: round(edgeOf(frame, index) + frame.column * 0.3),
            y: round(frame.rain.base + 1),
            width: round(frame.column * 0.4),
            height: 1.5,
          },
        }),
      ];
    }
    if (day.precipitation === 0) return [];
    return [
      svg("rect", {
        className: "chart-bar",
        attrs: {
          x: round(edgeOf(frame, index) + frame.column * 0.15),
          y: round(frame.rain.base - height(day.precipitation)),
          width: round(frame.column * 0.7),
          height: round(height(day.precipitation)),
        },
      }),
    ];
  });

  const marks = rainTicks(ceiling);
  const rules = marks.map((value) =>
    svg("line", {
      className: "chart-rule",
      attrs: {
        x1: frame.plot.from,
        x2: frame.plot.to,
        y1: round(frame.rain.base - height(value)),
        y2: round(frame.rain.base - height(value)),
      },
    }),
  );
  // The unit on the topmost only, as on the panel above. The tenth is kept even
  // though a gridline is round by construction: docs/application.md settles the
  // rounding of millimetres, and an axis writing them one way while the cards
  // write them another would be two rules for one quantity.
  const labels = marks.map((value, index) =>
    svg("text", {
      className: "chart-axis",
      text:
        index === marks.length - 1
          ? `${present.precipitation(value)} ${texts.units.millimetres}`
          : present.precipitation(value),
      attrs: {
        x: frame.plot.from - 8,
        y: round(frame.rain.base - height(value) + 3),
        "text-anchor": "end",
      },
    }),
  );

  return svg("g", { className: "chart-rain" }, [
    ...rules,
    ...bars,
    svg("line", {
      className: "chart-baseline",
      attrs: {
        x1: frame.plot.from,
        x2: frame.plot.to,
        y1: frame.rain.base,
        y2: frame.rain.base,
      },
    }),
    ...labels,
  ]);
}

/**
 * The days a reader counts from: the 1st, the 10th and the 20th.
 *
 * **A month name says which month, and nothing about where inside it.** Over
 * ninety-two days a month is three hundred units wide, and finding the second
 * week of August meant measuring by eye against the two names either side. These
 * are the marks that make a date on the drawing findable, and they are the fewest
 * that do it: at three a month they never crowd, whatever the period — nine days
 * apart at the closest, which is ninety units on a full season and still room
 * for two digits on the shortest range the form allows.
 *
 * **Nothing is derived here.** A mark is placed on a day the series carries,
 * read off its own date; no day is invented to hold a round number, and the
 * first of a month the range does not reach simply has no mark. That is the same
 * discipline the months follow, and the reason both walk the days rather than
 * the calendar.
 *
 * **Drawn at the foot of each panel**, from one call apiece. The temperature
 * panel is the taller of the two by far, and dating a point on it used to mean
 * carrying the eye down past the whole rain panel to the only row that said
 * which day was which. The two rows are the same days at the same x — one axis
 * read twice, which is why it is one function called twice rather than a second
 * set of marks.
 *
 * The number sits over the middle of its column, where the day's own dot is, so
 * the mark and the reading it names are on one vertical. The month keeps the
 * left edge: it names a turn, which is a boundary and not a day.
 */
const MILESTONES = [1, 10, 20];

/** How far the tick reaches below the baseline, before the number. */
const TICK = 4;

function dates(frame, days, base, row) {
  const marks = [];

  for (const [index, day] of days.entries()) {
    const number = Number(day.date.slice(8, 10));
    if (!MILESTONES.includes(number)) continue;

    const x = round(middleOf(frame, index));
    marks.push(
      svg("line", {
        className: "chart-tick",
        attrs: { x1: x, x2: x, y1: round(base), y2: round(base + TICK) },
      }),
      svg("text", {
        className: "chart-date",
        text: String(number),
        attrs: { x, y: round(row), "text-anchor": "middle" },
      }),
    );
  }
  return svg("g", { className: "chart-dates" }, marks);
}

/** The months, named where they turn — the strip's own reading mark, under it. */
function months(frame, days) {
  let month = null;
  const labels = [];

  for (const [index, day] of days.entries()) {
    const key = present.monthKey(day.date);
    if (key === month) continue;
    month = key;

    const x = edgeOf(frame, index);
    // A name that would run off the right edge is left off: it belongs to a
    // handful of days there, and the strip names that month anyway.
    if (x > frame.plot.to - 60) continue;
    labels.push(
      svg("text", {
        className: "chart-month",
        text: present.monthLabel(day.date),
        attrs: { x: round(x), y: round(frame.months) },
      }),
    );
  }
  return svg("g", { className: "chart-months" }, labels);
}

/**
 * The same crossing the strip marks, at the same day.
 *
 * A rule across both panels, not a change of colour: it is the one mark on this
 * page that says the ground has changed under the numbers.
 */
function seamMark(frame, days) {
  const index = seamIndex(days);
  if (index < 0) return null;

  const x = edgeOf(frame, index);
  const room = frame.plot.to - x > 170;

  return svg("g", { className: "chart-seam" }, [
    svg("line", {
      className: "chart-seam-rule",
      attrs: {
        x1: round(x),
        x2: round(x),
        y1: frame.temperature.top,
        y2: round(frame.rain.base),
      },
    }),
    svg("text", {
      className: "chart-seam-label",
      text: texts.results.seam,
      attrs: {
        x: round(room ? x + 5 : x - 5),
        y: round(frame.temperature.top + 11),
        "text-anchor": room ? "start" : "end",
      },
    }),
  ]);
}
