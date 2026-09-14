from __future__ import annotations
from .odds import profit_per_dollar


def expected_value_per_dollar(p_win: float, american_odds: float, p_push: float = 0.0) -> float:
    if not 0 <= p_win <= 1 or not 0 <= p_push <= 1 or p_win + p_push > 1 + 1e-12:
        raise ValueError("Invalid probabilities")
    p_loss = 1.0 - p_win - p_push
    b = profit_per_dollar(american_odds)
    return p_win * b - p_loss


def ev_pct(p_win: float, american_odds: float, p_push: float = 0.0) -> float:
    return 100.0 * expected_value_per_dollar(p_win, american_odds, p_push)
