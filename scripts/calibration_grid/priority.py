"""In which order the nodes are collected, and why the order matters.

Section 4 of the design document asks for progressive filling ordered by
decreasing population density, so that the collection is interruptible and
"covers most real searches within its first hours". Collecting by latitude, as
the first attempt did, spends the first hours on the open Mediterranean south of
the Pyrenees — the least useful nodes on the grid, and no search will ever touch
them.

The ordering is coarse on purpose. It decides what gets collected first, not
what gets computed, so being roughly right is enough and no external dataset is
worth the dependency. The populations below are those of the French urban areas
(*aires d'attraction*), rounded, which is the scale a 0.5-degree node covers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nodes import Node  # noqa: E402

# name -> (latitude, longitude, inhabitants in thousands)
CITIES: dict[str, tuple[float, float, float]] = {
    "Paris": (48.86, 2.35, 13100),
    "Lyon": (45.76, 4.84, 2300),
    "Marseille-Aix": (43.30, 5.37, 1900),
    "Toulouse": (43.60, 1.44, 1500),
    "Lille": (50.63, 3.06, 1500),
    "Bordeaux": (44.84, -0.58, 1400),
    "Nice": (43.70, 7.27, 1000),
    "Nantes": (47.22, -1.55, 1000),
    "Strasbourg": (48.58, 7.75, 850),
    "Montpellier": (43.61, 3.88, 810),
    "Rennes": (48.11, -1.68, 750),
    "Grenoble": (45.19, 5.72, 690),
    "Rouen": (49.44, 1.10, 660),
    "Toulon": (43.12, 5.93, 600),
    "Avignon": (43.95, 4.81, 530),
    "Saint-Etienne": (45.44, 4.39, 520),
    "Tours": (47.39, 0.69, 510),
    "Clermont-Ferrand": (45.78, 3.08, 500),
    "Douai-Lens": (50.37, 3.08, 500),
    "Orleans": (47.90, 1.90, 450),
    "Nancy": (48.69, 6.18, 440),
    "Angers": (47.47, -0.55, 430),
    "Caen": (49.18, -0.37, 420),
    "Dijon": (47.32, 5.04, 390),
    "Metz": (49.12, 6.18, 390),
    "Le Havre": (49.49, 0.11, 390),
    "Reims": (49.26, 4.03, 320),
    "Brest": (48.39, -4.49, 320),
    "Perpignan": (42.70, 2.90, 320),
    "Bayonne": (43.49, -1.48, 310),
    "Limoges": (45.83, 1.26, 310),
    "Besancon": (47.24, 6.02, 280),
    "Pau": (43.30, -0.37, 250),
    "Poitiers": (46.58, 0.34, 260),
    "La Rochelle": (46.16, -1.15, 210),
    "Amiens": (49.89, 2.30, 250),
    "Chambery": (45.56, 5.92, 220),
    "Bastia": (42.70, 9.45, 110),
    "Ajaccio": (41.93, 8.74, 100),
}


def reach(node: Node) -> float:
    """How many people a node serves, discounted by distance.

    Inverse-square in degrees, with a floor so that a node sitting on a city
    does not dominate by division. What matters is the ranking, not the number.
    """
    return sum(
        people / (0.25 + (node.latitude - lat) ** 2 + (node.longitude - lon) ** 2)
        for lat, lon, people in CITIES.values()
    )


def in_priority_order(candidates: list[Node]) -> list[Node]:
    """Most-served nodes first, ties broken geographically so runs are repeatable."""
    return sorted(candidates, key=lambda node: (-reach(node), node.latitude, node.longitude))
