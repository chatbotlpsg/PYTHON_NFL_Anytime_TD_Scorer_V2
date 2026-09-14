from __future__ import annotations
import numpy as np


def calibrate_probability(p_raw: float, strength: float = 0.92) -> float:
    """Initial identity-near shrinkage. Replace coefficients with walk-forward calibration artifacts."""
    return float(np.clip(0.5 + (p_raw - 0.5) * strength, 0.01, 0.99))


def blend_with_market(p_calibrated: float, p_market_novig: float | None, market_trust: float) -> float:
    if p_market_novig is None or np.isnan(p_market_novig):
        return p_calibrated
    w_market = float(np.clip(market_trust, 0.0, 0.95))
    return float(np.clip((1 - w_market) * p_calibrated + w_market * p_market_novig, 0.01, 0.99))
