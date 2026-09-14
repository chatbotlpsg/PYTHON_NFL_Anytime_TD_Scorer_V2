from __future__ import annotations
from .odds import probability_to_american


def fair_american_odds(p_win: float, p_push: float = 0.0) -> int:
    if p_push <= 0:
        return probability_to_american(p_win)
    non_push = 1.0 - p_push
    if non_push <= 0:
        raise ValueError("All outcomes cannot be pushes")
    conditional = p_win / non_push
    return probability_to_american(conditional)
