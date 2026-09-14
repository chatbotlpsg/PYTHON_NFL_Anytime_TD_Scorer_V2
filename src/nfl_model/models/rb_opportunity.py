from __future__ import annotations
import numpy as np


def allocate_rb_carries(rng: np.random.Generator, team_rushes: np.ndarray, carry_means: list[float]) -> list[np.ndarray]:
    if not carry_means:
        return []
    prior = np.asarray(carry_means, dtype=float) + 0.75
    shares = prior / prior.sum()
    concentration = np.clip(prior.sum() * 1.8, 8.0, 65.0)
    draws = rng.dirichlet(shares * concentration, size=len(team_rushes))
    alloc = np.floor(draws * team_rushes[:, None]).astype(np.int16)
    remainder = team_rushes - alloc.sum(axis=1)
    top = int(np.argmax(shares))
    alloc[:, top] += remainder.astype(np.int16)
    return [alloc[:, i] for i in range(alloc.shape[1])]
