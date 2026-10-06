/** Present server-computed counts without duplicating their thresholds or rules. */
import { el } from "./dom.js";
import { span } from "./calendar.js";
import { texts } from "./i18n.js";

export function heatCounts(counts, range) {
  if (!counts?.length) return el("p", { className: "reading-note", text: texts.heatCounts.unavailable });
  // The requested calendar span can exceed the returned range when a source
  // stops early. Its length is navigation metadata, not a weather aggregate.
  const requestedDays = span(range.start, range.end);
  return el("section", { className: "heat-counts" }, [
    el("h4", { text: texts.heatCounts.title }),
    el("dl", { className: "heat-count-grid" }, counts.map((metric) => el("div", { className: "heat-count" }, [
      el("dt", { text: `${texts.heatCounts.reading[metric.reading]} ${texts.heatCounts.comparison[metric.comparison]} ${metric.threshold} °C` }),
      el("dd", { className: "heat-count-value", text: metric.count === null ? "—" : texts.heatCounts.days(metric.count) }),
      el("dd", { className: "heat-count-coverage", text: texts.heatCounts.coverage(metric.available_days, requestedDays) }),
    ]))),
    el("p", { className: "heat-count-note", text: texts.heatCounts.note }),
  ]);
}
