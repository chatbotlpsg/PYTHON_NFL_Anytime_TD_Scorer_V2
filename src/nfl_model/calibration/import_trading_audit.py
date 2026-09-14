"""Research-only Dataset B importer.

This module may READ completed trading-agent audits for later calibration.
It never creates, monitors, grades, or mutates Dataset B.
"""
from __future__ import annotations
import pandas as pd

REQUIRED = {"candidate_id", "handoff_run_id"}


def load_completed_trading_audit(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(f"Trading audit missing required join keys: {sorted(missing)}")
    return df
