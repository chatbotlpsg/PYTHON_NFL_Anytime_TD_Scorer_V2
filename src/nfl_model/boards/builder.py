from __future__ import annotations
import hashlib
import pandas as pd

from nfl_model.boards.schemas import PROP_BOARD_COLUMNS
from nfl_model.portfolio.thesis_optimizer import infer_thesis, optimize_theses

OPPORTUNITY = {"player_receptions", "player_rush_attempts", "player_pass_attempts", "player_pass_completions"}
PRODUCTION = {"player_reception_yds", "player_rush_yds", "player_pass_yds"}


def candidate_id(row: pd.Series, run_id: str) -> str:
    raw = "|".join(map(str, [run_id, row.get("aita_event_id"), row.get("aita_player_id"), row.get("market_key"), row.get("side"), row.get("line"), row.get("bookmaker")]))
    return f"NFL-CAND-{hashlib.sha1(raw.encode()).hexdigest()[:18].upper()}"


def classify_edge(row: pd.Series) -> str:
    market = row.get("market_key")
    if market == "player_receptions":
        return "ROLE_EDGE;VOLUME_EDGE"
    if market == "player_rush_attempts":
        return "VOLUME_EDGE;GAME_SCRIPT_EDGE"
    if market in {"player_pass_attempts", "player_pass_completions"}:
        return "PASS_VOLUME_EDGE;GAME_SCRIPT_EDGE"
    if market in {"player_reception_yds", "player_rush_yds", "player_pass_yds"}:
        return "VOLUME_EDGE;EFFICIENCY_EDGE"
    return "MULTI_FACTOR_EDGE"


def build_boards(priced: pd.DataFrame, run_id: str) -> dict[str, pd.DataFrame]:
    if priced.empty:
        empty = pd.DataFrame(columns=PROP_BOARD_COLUMNS)
        return {"opportunity": empty.copy(), "production": empty.copy(), "ev": empty.copy(),
                "leaderboard": empty.copy(), "rejection": empty.copy(),
                "thesis": pd.DataFrame(columns=["thesis_id", "expression_rank", "candidate_id", "expression_status"])}
    b = priced.copy()
    b["candidate_id"] = b.apply(lambda r: candidate_id(r, run_id), axis=1)
    b["run_id"] = run_id
    b["edge_type"] = b.apply(classify_edge, axis=1)
    b["thesis_id"] = b.apply(infer_thesis, axis=1)
    opportunity = b[b["market_key"].isin(OPPORTUNITY)].copy()
    production = b[b["market_key"].isin(PRODUCTION)].copy()
    ev = b[b["model_status"].eq("ACTIONABLE_AT_REFERENCE_PRICE")].copy()
    leaderboard = ev.sort_values(["ev_conservative_pct", "role_certainty_score", "model_agreement_score"], ascending=False).copy()
    rejection = b[~b["model_status"].eq("ACTIONABLE_AT_REFERENCE_PRICE")].copy()
    thesis = optimize_theses(ev)
    return {"opportunity": opportunity, "production": production, "ev": ev, "leaderboard": leaderboard, "rejection": rejection, "thesis": thesis}
