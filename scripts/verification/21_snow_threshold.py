"""What temperature separates a snow day from a rain day, on daily aggregates?

The climate model holes its snowfall irregularly, so the sky class derives snow
from precipitation and temperature instead — the same way on both regimes. This
script calibrates that criterion where the truth is known: the archive, which
serves both an hourly-derived weather_code and a real snowfall depth.

The question is narrower than it looks. Rule 2 already gates on 1 mm, so the
only thing to settle is which of the wet days are snow. Sweep a threshold over
that subset and read where it separates best.

Two sites on purpose: Strasbourg, low and continental, where snow is occasional;
Briancon, at 1300 m, where it is ordinary. A threshold that suits both is one
that does not depend on the climate it was fitted to.
"""
import json, time, urllib.error, urllib.parse, urllib.request

A = "https://archive-api.open-meteo.com/v1/archive"
START, END = "1990-01-01", "2024-12-31"
WINTER = (12, 1, 2)
WET = 1.0  # mm, the gate rule 2 already applies
SNOW_DEPTH = 1.0  # cm, the depth the design document calls a snow day

# WMO codes Open-Meteo emits for snow. 66/67 are freezing rain: liquid falling,
# not snow, and shown as rain.
SNOW_CODES = {71, 73, 75, 77, 85, 86}

SITES = {"Strasbourg (140 m)": (48.58, 7.75), "Briancon (1300 m)": (44.90, 6.64)}
THRESHOLDS = [t / 2 for t in range(-6, 13)]  # -3.0 .. +6.0 by 0.5


def get(lat, lon, model, variables, tries=4):
    p = {"latitude": lat, "longitude": lon, "start_date": START, "end_date": END,
         "daily": variables, "models": [model], "timezone": "auto"}
    qs = urllib.parse.urlencode(p, doseq=True)
    for i in range(tries):
        try:
            with urllib.request.urlopen(f"{A}?{qs}", timeout=600) as r:
                return json.load(r).get("daily", {})
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(30 * (i + 1)); continue
            print(f"    ! HTTP {e.code}"); return {}
    return {}


def score(days, threshold, field, truth):
    tp = fp = fn = tn = 0
    for d in days:
        predicted = d[field] < threshold
        actual = d[truth]
        if predicted and actual: tp += 1
        elif predicted and not actual: fp += 1
        elif actual: fn += 1
        else: tn += 1
    total = tp + fp + fn + tn
    accuracy = (tp + tn) / total if total else 0
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1}


winters = {}
for site, (lat, lon) in SITES.items():
    surface = get(lat, lon, "era5",
                  ["weather_code", "precipitation_sum", "snowfall_sum"])
    time.sleep(10)
    temps = get(lat, lon, "era5_land",
                ["temperature_2m_mean", "temperature_2m_max", "temperature_2m_min"])
    time.sleep(10)
    if not surface or not temps:
        print(f"{site}: donnees manquantes"); continue
    if all(v is None for v in (surface.get("weather_code") or [None])):
        print(f"{site}: weather_code non servi par era5 force"); continue

    rows = []
    for i, day in enumerate(surface["time"]):
        if int(day[5:7]) not in WINTER:
            continue
        code = surface["weather_code"][i]
        precip = surface["precipitation_sum"][i]
        depth = surface["snowfall_sum"][i]
        mean = temps["temperature_2m_mean"][i]
        if None in (code, precip, mean):
            continue
        rows.append({"date": day, "precip": precip, "depth": depth,
                     "mean": mean, "max": temps["temperature_2m_max"][i],
                     "min": temps["temperature_2m_min"][i],
                     "code_snow": int(code) in SNOW_CODES,
                     "depth_snow": depth is not None and depth >= SNOW_DEPTH})
    winters[site] = rows

# ---------------------------------------------------------------- (1)
print(f"(1) Assiette, decembre-janvier-fevrier {START[:4]}-{END[:4]}\n")
print(f"    {'site':<20}{'jours DJF':>11}{'humides':>10}{'% humides':>11}"
      f"{'neige (code)':>14}{'neige >= 1 cm':>15}")
print("    " + "-" * 81)
for site, rows in winters.items():
    wet = [r for r in rows if r["precip"] >= WET]
    print(f"    {site:<20}{len(rows):>11}{len(wet):>10}"
          f"{100 * len(wet) / len(rows):>10.1f}%"
          f"{sum(r['code_snow'] for r in wet):>14}{sum(r['depth_snow'] for r in wet):>15}")

# ---------------------------------------------------------------- (2)
print("\n(2) Pourquoi le weather_code ne peut pas servir de verite terrain\n")
print(f"    {'site':<20}{'humides':>9}{'code neige':>12}{'>= 1 cm':>10}{'ecart':>8}")
print("    " + "-" * 59)
for site, rows in winters.items():
    wet = [r for r in rows if r["precip"] >= WET]
    c = sum(r["code_snow"] for r in wet)
    d = sum(r["depth_snow"] for r in wet)
    print(f"    {site:<20}{len(wet):>9}{100 * c / len(wet):>11.1f}%"
          f"{100 * d / len(wet):>9.1f}%{100 * (c - d) / len(wet):>+8.1f}")
print("\n    Le code journalier est le maximum des 24 codes horaires : une heure")
print("    de neige suffit a basculer la journee. En altitude il sature, et la")
print("    cible n'a plus rien a discriminer. La profondeur reelle sert donc de")
print("    reference — c'est aussi la definition du document, 1 cm.")


def sweep(rows, target, label):
    print(f"\n    {label}   ({len(rows)} jours humides, "
          f"{100 * sum(r[target] for r in rows) / len(rows):.0f}% de neige)")
    print(f"    {'seuil':>7}{'exactitude':>13}{'precision':>12}{'rappel':>10}{'F1':>8}"
          f"{'faux +':>9}{'faux -':>9}")
    best = None
    for t in THRESHOLDS:
        s = score(rows, t, "mean", target)
        print(f"    {t:>+7.1f}{100 * s['accuracy']:>12.1f}%{100 * s['precision']:>11.1f}%"
              f"{100 * s['recall']:>9.1f}%{s['f1']:>8.3f}{s['fp']:>9}{s['fn']:>9}")
        if best is None or s["f1"] > best[1]["f1"]:
            best = (t, s)
    print(f"    -> meilleur F1 a {best[0]:+.1f} C")
    return best[0]


print(f"\n(2b) Seuil sur la temperature moyenne, jours >= {WET} mm, cible >= {SNOW_DEPTH} cm")
for site, rows in winters.items():
    sweep([r for r in rows if r["precip"] >= WET and r["depth"] is not None],
          "depth_snow", site)

# ---------------------------------------------------------------- (3)
print("(3) Quelle temperature discrimine le mieux ? (au meilleur seuil de chacune)\n")
print(f"    {'site':<20}{'variable':<10}{'seuil':>8}{'exactitude':>13}{'F1':>8}")
print("    " + "-" * 59)
for site, rows in winters.items():
    wet = [r for r in rows if r["precip"] >= WET]
    for field in ["mean", "max", "min"]:
        if any(r[field] is None for r in wet):
            continue
        best = max(((t, score(wet, t, field, "code_snow")) for t in THRESHOLDS),
                   key=lambda p: p[1]["f1"])
        print(f"    {site:<20}{field:<10}{best[0]:>+8.1f}"
              f"{100 * best[1]['accuracy']:>12.1f}%{best[1]['f1']:>8.3f}")

# ---------------------------------------------------------------- (4)
print(f"\n(4) Meme exercice contre la profondeur reelle (>= {SNOW_DEPTH} cm)\n")
print(f"    {'site':<20}{'seuil':>8}{'exactitude':>13}{'precision':>12}{'rappel':>10}{'F1':>8}")
print("    " + "-" * 71)
for site, rows in winters.items():
    wet = [r for r in rows if r["precip"] >= WET and r["depth"] is not None]
    if not wet:
        continue
    best = max(((t, score(wet, t, "mean", "depth_snow")) for t in THRESHOLDS),
               key=lambda p: p[1]["f1"])
    t, s = best
    print(f"    {site:<20}{t:>+8.1f}{100 * s['accuracy']:>12.1f}%"
          f"{100 * s['precision']:>11.1f}%{100 * s['recall']:>9.1f}%{s['f1']:>8.3f}")

# ---------------------------------------------------------------- (5)
print(f"\n(5) Un seuil commun tient-il ? (cible >= {SNOW_DEPTH} cm)\n")
subsets = {
    site: [r for r in rows if r["precip"] >= WET and r["depth"] is not None]
    for site, rows in winters.items()
}
pooled = [r for rows in subsets.values() for r in rows]
print(f"    {'seuil':>7}{'exactitude':>13}{'F1':>8}   exactitude par site")
for t in THRESHOLDS:
    s = score(pooled, t, "mean", "depth_snow")
    per = "  ".join(
        f"{site.split()[0]}={100 * score(rows, t, 'mean', 'depth_snow')['accuracy']:.1f}%"
        for site, rows in subsets.items())
    print(f"    {t:>+7.1f}{100 * s['accuracy']:>12.1f}%{s['f1']:>8.3f}   {per}")

print("\n    Reference : predire « toujours neige » sur les jours humides donnerait")
for site, rows in subsets.items():
    base = 100 * sum(r["depth_snow"] for r in rows) / len(rows)
    print(f"      {site:<20}{base:>6.1f}%")

print("\nLecture :")
print("  un seuil dont l'exactitude reste haute sur les deux sites ne depend pas")
print("  du climat sur lequel il a ete cale ; s'il faut un seuil par site, la")
print("  regle devient une table et non une regle.")
