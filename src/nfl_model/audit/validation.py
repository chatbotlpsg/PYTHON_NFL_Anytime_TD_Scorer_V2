from __future__ import annotations
import pandas as pd


def validate_slate(slate: pd.DataFrame) -> list[str]:
    errors = []
    if slate.empty:
        return ["EMPTY_SLATE"]
    if slate["aita_event_id"].duplicated().any(): errors.append("DUPLICATE_EVENT")
    if (slate["home_team"] == slate["away_team"]).any(): errors.append("HOME_AWAY_MISMATCH")
    if slate[["home_team", "away_team", "kickoff_utc"]].isna().any().any(): errors.append("MISSING_CRITICAL_EVENT_FIELD")
    return errors


def validate_player_map(player_map: pd.DataFrame) -> list[str]:
    if player_map.empty: return ["EMPTY_PLAYER_MAP"]
    errors = []
    if player_map["aita_player_id"].duplicated().any(): errors.append("DUPLICATE_AITA_PLAYER_ID")
    if player_map["normalized_name"].fillna("").eq("").any(): errors.append("EMPTY_NORMALIZED_PLAYER_NAME")
    return errors


def assert_simulation_reconciliation(reconciliation: list[dict]) -> None:
    bad = [r for r in reconciliation if r.get("status") != "OK"]
    if bad:
        raise RuntimeError(f"SIMULATION_GATE_FAILED: {bad[:3]}")
