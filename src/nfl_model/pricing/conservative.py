from __future__ import annotations
import numpy as np


def conservative_probability(p_blend: float, p_market: float | None, role_certainty: float,
                             model_agreement: float, data_freshness: float,
                             week1_multiplier: float = 1.0, max_haircut_fraction: float = 0.8) -> tuple[float, float]:
    anchor = 0.5 if p_market is None or np.isnan(p_market) else float(p_market)
    confidence = np.clip((role_certainty * 0.45 + model_agreement * 0.35 + data_freshness * 0.20) / 100.0, 0.0, 1.0)
    uncertainty = np.clip((1.0 - confidence) * week1_multiplier, 0.0, 1.0)
    haircut_fraction = min(max_haircut_fraction, uncertainty)
    edge = p_blend - anchor
    p_cons = anchor + edge * (1.0 - haircut_fraction)
    return float(np.clip(p_cons, 0.01, 0.99)), float(haircut_fraction)
