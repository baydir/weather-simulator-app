/**
 * Every sentence the visitor reads, in one place.
 *
 * docs/application.md asks for this from the first line rather than later:
 * extracting the strings once the pages exist costs a sweep through every file,
 * and one always survives. There is one language today; the shape is what
 * matters.
 *
 * **The warning keys are named, and the naming is load-bearing.** CLAUDE.md
 * rule 1 forbids the vocabulary of forecasting on a future date, and a test
 * walks this object to enforce it — every string is checked, except the two
 * under `warning`, which exist precisely to deny the thing. Adding a third
 * exception means widening that list, which is the moment to notice.
 */

export const texts = {
  site: {
    skip: "Aller au formulaire",
    skipToDays: "Aller aux journées",
  },

  // The banner asks before it explains. A site name at the top said what the
  // thing is called and nothing about what it is for; a question says both at
  // once, and the promise underneath settles it.
  //
  // The name is not lost — it stays in <title>, so in the tab and in a search
  // result, which is where a name is actually read.
  home: {
    // **Provisoire — à réécrire par le porteur du projet.** Un seul endroit.
    //
    // Deux contraintes. Une question porte un lieu et un horizon, sans quoi
    // elle n'évoque pas ce que le site sait faire. Et le vocabulaire de la
    // prévision reste proscrit : `present.test.js` parcourt ce tableau et
    // signalera la fautive sous `home.questions.<rang>`.
    //
    // Le test cherche la chaîne « il fera ». Il ne rattrapera donc pas « Quel
    // temps fera-t-il à Nice en 2050 ? », qui viole pourtant la règle 1 — ce
    // qu'aucune formulation ne doit faire, c'est promettre la journée.
    questions: [
      "Les étés seront ils supportables dans 20 ans ?",
      "Comment seront les hivers dans les années 2040 ?",
      "Faut-il se marier en avril plutôt qu'en juin ?",
      "Faut-il passer ses vieux jours à Nice ou à Lille ?",
      "Cet été, vacances à Ajaccio ou à Berck-plage ?",
      "Investir dans un appartement sous les toits à Paris : bonne ou mauvaise idée ?",
      "Vélo ou rando cet hiver à la montagne ?",
      "Noël au balcon, Pâques avec glaçons ?",
      "Team canicule d’été ou inondation d’hiver ?"
    ],
    // The verb is what keeps this within rule 1: "simulez" is one of the three
    // terms it names as kept, and the sentence promises an exercise rather than
    // an outcome. It carries none of the forbidden words, and present.test.js
    // walks it like the rest.
    promise: "Simulez la météo du futur. N'importe où. N'importe quand.",
  },

  form: {
    place: "Lieu",
    placeHint: "Une commune, une ville",
    from: "Du",
    to: "Au",
    submit: "Afficher la météo",
    searching: "Recherche du lieu…",
    candidates: (n) =>
      n === 1 ? "1 lieu trouvé, à choisir" : `${n} lieux trouvés, à choisir`,
    chosen: (label) => `Lieu : ${label}`,
    change: "changer",
    notFound: "Aucun lieu ne correspond à ce nom.",
    placeRequired: "Choisissez un lieu dans la liste.",

    // Two ways of asking for the same thing — a start and an end — so the
    // switch names the shape of the question, not what it will show. "Saison
    // entière" and not "Une saison" : the point is that none of it is missing.
    modeLabel: "Comment indiquer la période",
    modeDates: "Plage de dates",
    modeSeason: "Saison entière",
    season: "Saison",
    year: "Année",
    // The submit band is hidden until a panel is open, so this is only ever
    // reached by pressing Enter in the place field — which submits a form
    // whether or not it has a button on screen.
    periodRequired: "Choisissez une plage de dates ou une saison entière.",

    // Caught while the form is being filled in, so they are worded as
    // corrections rather than as refusals of a search that was really made.
    datesRequired: "Indiquez les deux dates.",
    rangeInverted: "La date de fin précède la date de début.",
    rangeOutsideCoverage: (first, last) => `Les dates vont de ${first} à ${last}.`,
    rangeTooLong: (max, asked) =>
      `${asked} jours demandés. Une recherche en porte ${max} au plus, soit une saison.`,
  },

  results: {
    range: (from, to) => `du ${from} au ${to}`,
    count: (n) => (n === 1 ? "1 journée" : `${n} journées`),
    loading: "Récupération des données…",
    progress: (done, total) => `Récupération des données : ${done} sur ${total}`,
    back: "Nouvelle recherche",
    bandLabel: "Les journées, dans l'ordre. Défilement horizontal.",
    seam: "À partir d'ici, simulation",
  },

  // The chart says the same days as the strip, in the other reading. Its one
  // sentence points at the strip rather than repeating the numbers: every value
  // it draws is written out up there, which is what makes a drawing acceptable
  // to a reader who gets nothing from a drawing.
  chart: {
    // A function of one argument, and the argument is the compared year or
    // nothing. Two separate sentences would be the same sentence written twice,
    // to drift the day either is reworded.
    label: (year) =>
      "Températures et précipitations de la période, jour par jour, " +
      "puis le cumul des précipitations dans un troisième panneau. " +
      "Les valeurs sont écrites dans la bande de journées ci-dessus." +
      (year ? ` Les températures de ${year} y sont superposées en gris.` : ""),

    // What each panel plots, over it. The second says the same word as
    // `measure.precipitation` and is written twice on purpose: that one names a
    // number on a card, this one names a panel, and the day one of them is
    // reworded the other has no reason to follow.
    temperatures: "Températures",
    precipitation: "Précipitations",

    // The third panel, under the two above. It names the quantity in full
    // rather than saying "Cumul" alone: the word on its own would be read
    // against the panel it sits under, and there is more than one thing on this
    // drawing a total could be adding up.
    cumulative: "Cumul des précipitations",
  },

  // The other year, and the two sentences that keep it honest.
  //
  // **`ordinary` is not a caption, it is a condition of the feature.** The
  // default year was *selected* for being unremarkable, while the year on screen
  // was not selected at all and may well carry a heatwave. Offering "1991" bare
  // would let a reader take a chosen year for a drawn one, and conclude that the
  // old climate had no extremes — when it is the selection that removed them.
  //
  // **`rainAside` says the second thing the measurement obliges.** The year was
  // picked on temperature alone, so its rain is nobody's idea of typical. Rather
  // than draw it and have to explain that, it is not drawn, and the note says so
  // — better assumed than discovered.
  compare: {
    open: "Comparer avec une autre année",
    close: "Masquer la comparaison",
    year: "Année de comparaison",
    loading: "Récupération de l'année comparée…",
    legend: (year) => `Températures de ${year}`,
    ordinaryLegend: (year) => `Températures de ${year}, une année sans particularité`,
    ordinary:
      "1991 est proposée parce qu'elle a été mesurée comme ordinaire : " +
      "ni chaude ni froide pour sa période, sur cinq sites français. " +
      "La période affichée, elle, n'a pas été choisie — elle peut porter une canicule.",
    rainAside:
      "Seules les températures sont superposées : l'année a été retenue sur la " +
      "température, sa pluie n'a rien de typique.",
    seeYear: (year) => `Voir ${year} en détail`,
  },

  // Folded, but there. A corrected series read without knowing which model was
  // corrected, over which period, and when the table was built is a silent
  // source of error — docs/application.md says so, and this is the answer.
  provenance: {
    summary: "D'où viennent ces journées",
    model: "Modèle climatique",
    calibration: "Période de calibration",
    projection: "Période de projection",
    step: "Pas de la grille",
    generated: "Table de correction générée le",
    span: (from, to) => `${from} – ${to}`,
    degrees: (value) => `${value}°`,
    observed:
      "Les journées passées viennent de réanalyses météorologiques, non d'un modèle.",
    // No number here, deliberately: how far the forecast reaches is a server
    // constant, and CLAUDE.md rule 3 has it served rather than copied. Each
    // card already carries the dataset that answered for it.
    forecast:
      "Les premiers jours à venir viennent d'une prévision météorologique ; " +
      "au-delà commence la simulation climatique.",
    noGrid: "Aucune journée simulée : cette recherche n'a demandé aucune correction.",
  },

  // The two obligations, kept to two lines. The first is CLAUDE.md rule 1; the
  // second is docs/science.md, which requires the emissions scenario to be
  // stated as a high hypothesis rather than an expected trajectory.
  warning: {
    notAForecast:
      "Simulation, pas une prévision. La date situe la journée dans une saison, " +
      "elle n'engage rien sur ce jour-là.",
    scenario: "Scénario d'émissions haut.",
  },

  // The four names, in the order the form offers them, which is the order a
  // French year is recited in. The keys are the ones `season.js` writes and the
  // stylesheet paints — a test joins the three, because a season one of them
  // knows and another does not leaves the page with no ground and no word.
  season: {
    spring: "Printemps",
    summer: "Été",
    autumn: "Automne",
    winter: "Hiver",
  },

  sky: {
    clear: "Dégagé",
    cloudy: "Nuageux",
    overcast: "Couvert",
    rain: "Pluie",
    snow: "Neige",
    unknown: "Ciel indéterminé",
  },

  measure: {
    // Read aloud, not shown: the card carries "39 · 21", and warm against cool
    // is what says which is which — which is nothing at all to a screen reader,
    // or to anyone who does not separate the two colours. There is no
    // "Températures" label any more: the pair needs no word on screen.
    high: "Maximale",
    low: "Minimale",
    precipitation: "Précipitations",
    // The only wind on the card, and the label has to carry that: never
    // "rafale", because wind_speed_10m_max is the strongest *sustained* wind of
    // the day and a gust commonly runs to twice it — and never plain "Vent"
    // either, which would read as an average.
    windMax: "Vent maximal",
    missing: "—",
    missingLabel: "donnée manquante",
  },

  units: {
    celsius: "°C",
    millimetres: "mm",
    kilometresPerHour: "km/h",
  },

  // Handed to fetch.js, which transports and does not write. Two sentences
  // because the two failures are not the visitor's to confuse: Open-Meteo
  // answering badly is the common one, and its rate limit counts against their
  // own address, so waiting is something they can actually do.
  transport: {
    upstreamFailed:
      "Les données météo n'ont pas pu être récupérées. " +
      "Le service Open-Meteo limite le nombre de recherches ; réessayez dans un moment.",
    serviceFailed: "L'application est momentanément indisponible.",
    searchFailed: "La recherche n'a pas abouti.",
  },
};
