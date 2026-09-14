from __future__ import annotations
import numpy as np


def probability_convergence(values: np.ndarray, side: str, line: float, checkpoints: list[int], tolerance: float) -> dict:
    probs = []
    for n in checkpoints:
        if n > len(values):
            continue
        x = values[:n]
        p = float(np.mean(x > line if side.upper() == "OVER" else x < line))
        probs.append((n, p))
    if len(probs) < 2:
        return {"status": "INSUFFICIENT_CHECKPOINTS", "estimates": probs}
    diffs = [abs(probs[i][1] - probs[i - 1][1]) for i in range(1, len(probs))]
    return {"status": "CONVERGED" if max(diffs[-2:]) <= tolerance else "NOT_CONVERGED", "estimates": probs, "max_recent_delta": max(diffs[-2:])}
