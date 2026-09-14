from __future__ import annotations
import numpy as np


def simulate_receiver(rng: np.random.Generator, dropbacks: np.ndarray, route_share: float, route_share_sd: float,
                      target_rate: float, catch_rate: float, yards_per_reception: float) -> dict[str, np.ndarray]:
    n = len(dropbacks)
    rs = np.clip(rng.normal(route_share, route_share_sd, n), 0.05, 0.99)
    routes = rng.binomial(dropbacks, rs).astype(np.int16)
    tr = np.clip(rng.normal(target_rate, max(0.015, target_rate * 0.10), n), 0.03, 0.45)
    targets = rng.binomial(routes, tr).astype(np.int16)
    cp = np.clip(rng.normal(catch_rate, 0.025, n), 0.3, 0.97)
    receptions = rng.binomial(targets, cp).astype(np.int16)
    ypr = np.clip(rng.lognormal(np.log(max(3.0, yards_per_reception)) - 0.08, 0.28, n), 1.5, 45.0)
    yards = np.rint(receptions * ypr).astype(np.int16)
    return {"routes": routes, "targets": targets, "receptions": receptions, "receiving_yards": yards}
