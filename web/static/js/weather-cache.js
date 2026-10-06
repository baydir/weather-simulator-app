/** Exact upstream payloads only; current server processing is never cached. */
const PREFIX = "weather-raw-v2:";
const MAX_CHARS = 1_500_000;

export class WeatherCache {
  constructor(storage = () => globalThis.localStorage, now = Date.now) {
    this.storage = storage;
    this.now = now;
  }

  read(url, maxAge) {
    if (maxAge !== null && !(maxAge > 0)) return null;
    try {
      const entry = JSON.parse(this.storage().getItem(PREFIX + url));
      const age = this.now() - entry.saved;
      const expired = entry.expires !== null &&
        (!Number.isFinite(entry.expires) || this.now() >= entry.expires);
      if (!Number.isFinite(age) || age < 0 || expired ||
          (maxAge !== null && age >= maxAge * 1000)) return null;
      return entry.payload ?? null;
    } catch { return null; }
  }

  write(url, payload, maxAge, saved = this.now()) {
    if (maxAge !== null && !(maxAge > 0)) return;
    try {
      const storage = this.storage();
      const key = PREFIX + url;
      const value = JSON.stringify({ saved, expires: maxAge === null ? null : saved + maxAge * 1000, payload });
      if (value.length > MAX_CHARS) return;
      const others = [];
      let size = value.length;
      for (let i = 0; i < storage.length; i++) {
        const other = storage.key(i);
        if (!other.startsWith(PREFIX) || other === key) continue;
        const raw = storage.getItem(other);
        let time = 0;
        try { time = JSON.parse(raw).saved || 0; } catch { /* Evict corrupt entries first. */ }
        others.push({ key: other, size: raw.length, time });
        size += raw.length;
      }
      others.sort((a, b) => a.time - b.time);
      while (size > MAX_CHARS && others.length) {
        const oldest = others.shift();
        storage.removeItem(oldest.key);
        size -= oldest.size;
      }
      for (;;) {
        try { storage.setItem(key, value); return; }
        catch {
          if (!others.length) return;
          storage.removeItem(others.shift().key);
        }
      }
    } catch { /* Private browsing and quota failures cannot prevent a search. */ }
  }
}

export const weatherCache = new WeatherCache();
