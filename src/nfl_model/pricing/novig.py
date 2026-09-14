from __future__ import annotations
from .odds import american_to_implied


def two_way_novig(over_odds: float, under_odds: float) -> tuple[float, float]:
    po, pu = american_to_implied(over_odds), american_to_implied(under_odds)
    total = po + pu
    if total <= 0:
        raise ValueError("Invalid implied-probability total")
    return po / total, pu / total
