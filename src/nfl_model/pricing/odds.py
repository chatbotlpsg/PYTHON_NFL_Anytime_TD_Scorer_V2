from __future__ import annotations
import math


def american_to_decimal(odds: float) -> float:
    if odds == 0:
        raise ValueError("American odds cannot be zero")
    return 1.0 + (100.0 / abs(odds) if odds < 0 else odds / 100.0)


def american_to_implied(odds: float) -> float:
    return 1.0 / american_to_decimal(odds)


def decimal_to_american(decimal_odds: float) -> int:
    if decimal_odds <= 1:
        raise ValueError("Decimal odds must be > 1")
    b = decimal_odds - 1.0
    return int(round(100 * b)) if b >= 1 else int(round(-100 / b))


def probability_to_american(prob: float) -> int:
    if not 0 < prob < 1:
        raise ValueError("Probability must be in (0,1)")
    return decimal_to_american(1.0 / prob)


def profit_per_dollar(odds: float) -> float:
    return american_to_decimal(odds) - 1.0
