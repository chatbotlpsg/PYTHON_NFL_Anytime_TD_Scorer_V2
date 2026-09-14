from __future__ import annotations
from .odds import decimal_to_american


def worst_acceptable_american(p_win: float, min_ev_fraction: float, p_push: float = 0.0) -> int:
    """Worst price satisfying EV >= floor. Pushes are neutral capital returns."""
    p_loss = 1.0 - p_win - p_push
    if p_win <= 0:
        raise ValueError("p_win must be positive")
    required_profit = (min_ev_fraction + p_loss) / p_win
    if required_profit <= 0:
        return -100000
    return decimal_to_american(1.0 + required_profit)
