/** Share completed and pending annual searches between both comparison views. */
export function periodLoader(cache, fetchYear) {
  const pending = new Map();
  return (year) => {
    if (cache.has(year)) return Promise.resolve(cache.get(year));
    if (!pending.has(year)) {
      pending.set(year, Promise.resolve().then(() => fetchYear(year)).then((series) => {
        cache.set(year, series);
        return series;
      }).finally(() => pending.delete(year)));
    }
    return pending.get(year);
  };
}

/** Explicit, sequential loading. Stop after the active period; never retry automatically. */
export class PeriodBatch {
  constructor({ years, cache, load, changed = () => {} }) {
    Object.assign(this, { years, cache, load, changed });
    this.running = false;
    this.stopping = false;
    this.started = false;
    this.active = null;
    this.error = null;
  }

  stop() { this.stopping = true; this.changed(); }

  async run() {
    if (this.running) return;
    this.started = true;
    this.running = true;
    this.stopping = false;
    this.error = null;
    this.changed();
    try {
      for (const year of this.years) {
        if (this.stopping) break;
        if (this.cache.has(year)) continue;
        this.active = year;
        this.changed();
        try { await this.load(year); }
        catch (error) { this.error = error; break; }
        this.active = null;
        this.changed();
      }
    } finally {
      this.active = null;
      this.running = false;
      this.changed();
    }
  }
}
