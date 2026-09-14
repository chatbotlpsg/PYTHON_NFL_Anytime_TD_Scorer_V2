from __future__ import annotations
import numpy as np


def sample_pass_plays(
    rng: np.random.Generator,
    team_plays: np.ndarray,
    base_pass_rate: float,
    script_shift: float | np.ndarray,
    concentration: float = 80.0,
    early_down_pass_rate: float | None = None,
    success_rate: float = 0.43,
) -> tuple[np.ndarray, np.ndarray]:
    """Aggregate stateful pass/run allocation.

    The simulation separates early-down/neutral opportunities from later-down conversion states and applies the
    game-state lead/trail shift to both. This preserves score/time/down-state behavior without allocating a gigantic
    per-play state matrix for every Monte Carlo draw.
    """
    n = len(team_plays)
    shift = np.asarray(script_shift, dtype=float)
    if shift.ndim == 0:
        shift = np.full(n, float(shift))
    success = float(np.clip(success_rate, .30, .58))
    # Better success rates generate fewer third/fourth-down snaps; poor success creates more obvious passing downs.
    late_down_share = float(np.clip(.27 + (.43 - success) * .32, .20, .36))
    late_down_plays = rng.binomial(team_plays, late_down_share).astype(np.int16)
    early_plays = (team_plays - late_down_plays).astype(np.int16)

    neutral = float(np.clip(early_down_pass_rate if early_down_pass_rate is not None else base_pass_rate, .32, .76))
    p_early = np.clip(neutral + shift * .92, .27, .84)
    p_late = np.clip(float(base_pass_rate) + .17 + shift * 1.12 + (.43 - success) * .10, .45, .94)

    # Beta uncertainty makes the pass rate a parameter distribution, not a single fixed number.
    a1 = np.maximum(p_early * concentration, 1e-3)
    b1 = np.maximum((1 - p_early) * concentration, 1e-3)
    a2 = np.maximum(p_late * concentration * .8, 1e-3)
    b2 = np.maximum((1 - p_late) * concentration * .8, 1e-3)
    pass_early = rng.binomial(early_plays, rng.beta(a1, b1))
    pass_late = rng.binomial(late_down_plays, rng.beta(a2, b2))
    pass_plays = (pass_early + pass_late).astype(np.int16)
    rush_plays = (team_plays - pass_plays).astype(np.int16)
    return pass_plays, rush_plays
