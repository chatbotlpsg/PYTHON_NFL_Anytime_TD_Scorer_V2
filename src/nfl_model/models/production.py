from __future__ import annotations
import numpy as np


def simulate_rushing_yards(rng: np.random.Generator, carries: np.ndarray, ypc: float) -> np.ndarray:
    n = len(carries)
    latent_ypc = np.clip(rng.lognormal(np.log(max(1.5, ypc)) - 0.08, 0.30, n), 1.0, 12.0)
    noise = rng.normal(0, 9 + np.sqrt(np.maximum(carries, 1)) * 2.2, n)
    return np.rint(np.maximum(0, carries * latent_ypc + noise)).astype(np.int16)
