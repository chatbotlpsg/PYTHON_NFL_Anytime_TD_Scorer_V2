from __future__ import annotations
import numpy as np
import pandas as pd


def correlation_matrix(draws: dict[str, np.ndarray], keys: list[str] | None = None, max_columns: int = 80) -> pd.DataFrame:
    selected = keys or [k for k in draws if k.startswith("PLAYER|")]
    selected = [k for k in selected if k in draws][:max_columns]
    if len(selected) < 2:
        return pd.DataFrame()
    matrix = np.column_stack([draws[k].astype(float) for k in selected])
    corr = np.corrcoef(matrix, rowvar=False)
    return pd.DataFrame(corr, index=selected, columns=selected)
