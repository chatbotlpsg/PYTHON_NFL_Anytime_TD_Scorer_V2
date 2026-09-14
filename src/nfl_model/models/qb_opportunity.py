from __future__ import annotations
import numpy as np


def simulate_qb(rng: np.random.Generator, pass_plays: np.ndarray, sack_rate: float, scramble_rate: float,
                completion_rate: float, yards_per_attempt: float) -> dict[str, np.ndarray]:
    n = len(pass_plays)
    non_attempt_rate = float(np.clip(sack_rate + scramble_rate, 0.0, 0.28))
    attempts = rng.binomial(pass_plays, 1.0 - non_attempt_rate).astype(np.int16)
    comp_p = np.clip(rng.normal(completion_rate, 0.025, n), 0.42, 0.82)
    completions = rng.binomial(attempts, comp_p).astype(np.int16)
    ypa = np.clip(rng.normal(yards_per_attempt, 0.75, n), 3.5, 13.0)
    pass_yards = np.rint(np.maximum(0, attempts * ypa + rng.normal(0, 28, n))).astype(np.int16)
    return {"passing_attempts": attempts, "completions": completions, "passing_yards": pass_yards}
