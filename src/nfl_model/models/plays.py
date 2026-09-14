from __future__ import annotations
import numpy as np


def sample_team_plays(rng: np.random.Generator, mean: float, sd: float, n: int, uncertainty: float = 1.0) -> np.ndarray:
    latent_mean = rng.normal(mean, max(1.0, sd * 0.18 * uncertainty), size=n)
    plays = rng.normal(latent_mean, max(4.5, sd), size=n)
    return np.rint(np.clip(plays, 42, 86)).astype(np.int16)
