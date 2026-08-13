"""Failures the request path raises, and the French sentence each one shows.

The interface displays these verbatim. They are held here rather than in the
endpoint so that a refusal reads the same wherever it is raised, and so that the
one refusal that matters — a future served without a correction — cannot be
worded away in passing.
"""

from __future__ import annotations

from datetime import date


class ApiError(Exception):
    """Base class for every refusal the request path raises.

    ``message`` is what the visitor reads, in French. The exception string stays
    in English like the rest of the code, for logs and tracebacks.
    """

    status_code = 400

    def __init__(self, detail: str, message: str) -> None:
        super().__init__(detail)
        self.message = message


class EmptyRange(ApiError):
    """The range ends before it starts."""

    def __init__(self, start: date, end: date) -> None:
        super().__init__(
            f"empty range: {start} is after {end}",
            "La date de fin précède la date de début.",
        )


class OutsideCoverageDates(ApiError):
    """The range reaches outside 1950-2050."""

    def __init__(self, start: date, end: date) -> None:
        super().__init__(
            f"{start}..{end} reaches outside the covered period",
            "L'application couvre les dates du 1ᵉʳ janvier 1950 au 31 décembre 2050.",
        )


class RangeTooLong(ApiError):
    """More than one season at a time.

    The bound is enforced here as well as in the interface. A limit only the
    browser applies is not a limit.
    """

    def __init__(self, days: int) -> None:
        super().__init__(
            f"{days} days requested, at most 90 are served",
            "Une recherche porte sur 90 jours au plus, soit une saison. "
            "Réduisez la plage de dates.",
        )
        self.days = days


class OutOfGrid(ApiError):
    """A simulated segment was asked for where the correction grid has no nodes.

    The wording says the place is not covered *yet*, which is true — step 8
    widens the grid to the world — and it does not offer to show the future
    uncorrected, because there is no honest version of that.

    **It no longer says the past alone remains available.** Only the simulated
    days need the grid, so the fortnight ahead is served here as anywhere: it is
    ECMWF IFS, which needs no debiasing. Naming no number, per rule 3 — how far
    the forecast reaches is the server's to know.
    """

    def __init__(self, latitude: float, longitude: float) -> None:
        super().__init__(
            f"{latitude:.4f}, {longitude:.4f} is not covered by the correction grid",
            "Ce lieu n'est pas encore couvert pour les dates lointaines. "
            "La simulation y serait faussée, elle n'est donc pas proposée. "
            "Les dates passées et les jours à venir restent consultables.",
        )
        self.latitude = latitude
        self.longitude = longitude


class StalePlan(ApiError):
    """The plan was built on another day than the one being served.

    Only ever seen at midnight, and it matters: the cut between what happened
    and what might have has moved, so the days fetched no longer answer the
    question being asked of them.
    """

    status_code = 409

    def __init__(self, planned: date, current: date) -> None:
        super().__init__(
            f"plan built for {planned}, served on {current}",
            "La journée a changé pendant la recherche. Relancez-la.",
        )


class PayloadMismatch(ApiError):
    """The payloads sent back are not the ones the plan asked for."""

    def __init__(self, expected: set[str], received: set[str]) -> None:
        super().__init__(
            f"expected payloads {sorted(expected)}, received {sorted(received)}",
            "Les données transmises ne correspondent pas à la recherche. Relancez-la.",
        )


class UncorrectedFuture(ApiError):
    """Simulated days reached the pipeline with no correction to apply.

    A programming error rather than a bad request, and it fails loudly for the
    reason docs/application.md gives: an uncorrected future is a future that is
    artificially sunny by 8 to 11 points of cloud cover, and three of the five
    sky classes hang off that number. Serving one silently is the single outcome
    the whole correction chain exists to prevent.
    """

    status_code = 500

    def __init__(self, count: int) -> None:
        super().__init__(
            f"{count} simulated days reached the pipeline without a cloud correction",
            "Une erreur interne empêche de simuler cette période. "
            "Aucun résultat n'est affiché plutôt qu'un résultat faux.",
        )
        self.count = count


class UncoveredMonth(ApiError):
    """The correction table has no entry for a month the range needs.

    Distinct from being outside the grid: the four nodes are there, but one of
    them is short of a month, and :class:`CorrectionGrid` keeps only the months
    all four share rather than correcting from three nodes and a hole.
    """

    status_code = 503

    def __init__(self, month: int) -> None:
        super().__init__(
            f"the correction table carries no entry for month {month}",
            "La correction n'est pas encore disponible pour cette période de l'année "
            "à cet endroit. Essayez une autre plage de dates.",
        )
        self.month = month
