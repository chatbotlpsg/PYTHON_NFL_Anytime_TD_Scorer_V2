from __future__ import annotations
import pandas as pd


def infer_thesis(row: pd.Series) -> str:
    market = str(row.get("market_key", ""))
    side = str(row.get("side", "")).upper()
    direction = "UP" if side == "OVER" else "DOWN"
    if market in {"player_pass_attempts", "player_pass_completions"}:
        return f"PASS_VOLUME_{direction}"
    if market == "player_rush_attempts":
        return f"RUN_VOLUME_{direction}"
    if market == "player_receptions":
        return f"RECEIVER_ROLE_{direction}"
    if market in {"player_pass_yds", "player_reception_yds"}:
        return f"PASS_PRODUCTION_{direction}"
    if market == "player_rush_yds":
        return f"RUN_PRODUCTION_{direction}"
    return f"OTHER_{direction}"


def optimize_theses(board: pd.DataFrame) -> pd.DataFrame:
    if board.empty:
        return pd.DataFrame(columns=["thesis_id", "best_candidate_id", "secondary_candidate_id", "redundant_candidate_ids"])
    b = board.copy()
    b["thesis_id"] = b.apply(infer_thesis, axis=1)
    rows = []
    for (event_id, thesis), g in b.groupby(["aita_event_id", "thesis_id"], dropna=False):
        g = g.sort_values(["ev_conservative_pct", "role_certainty_score", "model_agreement_score"], ascending=False)
        ids = g["candidate_id"].astype(str).tolist()
        rows.append({
            "aita_event_id": event_id,
            "thesis_id": thesis,
            "best_candidate_id": ids[0] if ids else None,
            "secondary_candidate_id": ids[1] if len(ids) > 1 else None,
            "redundant_candidate_ids": ";".join(ids[2:]) if len(ids) > 2 else "",
            "candidate_count": len(ids),
        })
    return pd.DataFrame(rows)
