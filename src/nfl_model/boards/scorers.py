from __future__ import annotations

import hashlib
import itertools
import numpy as np
import pandas as pd

from nfl_model.pricing.fair_price import fair_american_odds
from nfl_model.pricing.odds import probability_to_american


def _id(prefix: str, *parts: object) -> str:
    raw = "|".join(map(str, parts))
    return f"{prefix}-{hashlib.sha1(raw.encode()).hexdigest()[:18].upper()}"


def build_scorer_probability_boards(
    scorer_summary: pd.DataFrame,
    slate: pd.DataFrame,
    player_map: pd.DataFrame,
    run_id: str,
    snapshot_time_utc: str,
) -> dict[str, pd.DataFrame]:
    if scorer_summary is None or scorer_summary.empty:
        empty = pd.DataFrame()
        return {"matchup": empty.copy(), "slate": empty.copy()}
    b = scorer_summary.copy()
    games = slate.set_index("aita_event_id") if not slate.empty else pd.DataFrame()
    pm = player_map.set_index("aita_player_id") if not player_map.empty else pd.DataFrame()
    rows = []
    for _, r in b.iterrows():
        eid = str(r["aita_event_id"])
        g = games.loc[eid] if isinstance(games, pd.DataFrame) and eid in games.index else None
        meta = pm.loc[str(r["aita_player_id"])] if isinstance(pm, pd.DataFrame) and str(r["aita_player_id"]) in pm.index else {}
        if isinstance(meta, pd.DataFrame):
            meta = meta.iloc[-1]
        home = g.get("home_team") if g is not None else None
        away = g.get("away_team") if g is not None else None
        p = float(r["p_anytime_td_raw"])
        rows.append({
            **r.to_dict(),
            "scorer_id": _id("NFL-SCORER", run_id, eid, r["aita_player_id"]),
            "run_id": run_id,
            "snapshot_time_utc": snapshot_time_utc,
            "game_label": f"{away} @ {home}" if home and away else eid,
            "opponent": away if str(r["team"]) == str(home) else home,
            "kickoff_utc": g.get("kickoff_utc") if g is not None else None,
            "fair_anytime_td_odds_raw": fair_american_odds(p),
            "role_certainty_score": float(meta.get("role_certainty_score", 50.0)) if hasattr(meta, "get") else 50.0,
            "data_freshness_score": float(meta.get("data_freshness_score", 50.0)) if hasattr(meta, "get") else 50.0,
            "availability_status": meta.get("availability_status", "UNKNOWN") if hasattr(meta, "get") else "UNKNOWN",
            "board_type": "MARKET_BLIND_SCORER_PROBABILITY",
        })
    out = pd.DataFrame(rows)
    out["matchup_rank"] = out.groupby("aita_event_id")["p_anytime_td_raw"].rank(method="first", ascending=False).astype(int)
    out["slate_rank"] = out["p_anytime_td_raw"].rank(method="first", ascending=False).astype(int)
    matchup = out.sort_values(["aita_event_id", "matchup_rank"]).reset_index(drop=True)
    slate_board = out.sort_values(["slate_rank"]).reset_index(drop=True)
    return {"matchup": matchup, "slate": slate_board}


def _phi(a: np.ndarray, b: np.ndarray) -> float:
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def build_joint_scorer_boards(
    scorer_slate_board: pd.DataFrame,
    draws: dict[str, np.ndarray],
    run_id: str,
    top_pair_candidates: int = 30,
    top_triple_candidates: int = 15,
) -> dict[str, pd.DataFrame]:
    if scorer_slate_board is None or scorer_slate_board.empty:
        return {"pairs": pd.DataFrame(), "triples": pd.DataFrame()}
    top = scorer_slate_board.sort_values("p_anytime_td_raw", ascending=False).head(top_pair_candidates).copy()
    recs = top.to_dict("records")
    pair_rows = []
    for a, b in itertools.combinations(recs, 2):
        ka = f"SCORER|{a['aita_player_id']}|anytime"
        kb = f"SCORER|{b['aita_player_id']}|anytime"
        if ka not in draws or kb not in draws:
            continue
        xa = np.asarray(draws[ka], dtype=np.int8)
        xb = np.asarray(draws[kb], dtype=np.int8)
        p_joint = float(np.mean((xa == 1) & (xb == 1)))
        p_ind = float(np.mean(xa) * np.mean(xb))
        pair_rows.append({
            "joint_id": _id("NFL-SCORER-PAIR", run_id, a["aita_player_id"], b["aita_player_id"]),
            "run_id": run_id,
            "leg1_player_id": a["aita_player_id"], "leg1_player": a["player_name"], "leg1_team": a["team"], "leg1_event_id": a["aita_event_id"],
            "leg2_player_id": b["aita_player_id"], "leg2_player": b["player_name"], "leg2_team": b["team"], "leg2_event_id": b["aita_event_id"],
            "same_game": str(a["aita_event_id"]) == str(b["aita_event_id"]),
            "p_joint_model_raw": p_joint,
            "p_independence_product": p_ind,
            "joint_probability_lift_pp": (p_joint - p_ind) * 100.0,
            "binary_phi_correlation": _phi(xa, xb),
            "fair_joint_decimal_raw": (1.0 / p_joint) if p_joint > 0 else np.inf,
            "fair_joint_american_raw": probability_to_american(p_joint) if p_joint > 0 else np.nan,
            "parlay_math_status": "EMPIRICAL_SHARED_MONTE_CARLO",
        })

    triple_rows = []
    top3 = scorer_slate_board.sort_values("p_anytime_td_raw", ascending=False).head(top_triple_candidates).to_dict("records")
    for a, b, c in itertools.combinations(top3, 3):
        keys = [f"SCORER|{x['aita_player_id']}|anytime" for x in (a, b, c)]
        if any(k not in draws for k in keys):
            continue
        x1, x2, x3 = (np.asarray(draws[k], dtype=np.int8) for k in keys)
        p_joint = float(np.mean((x1 == 1) & (x2 == 1) & (x3 == 1)))
        p_ind = float(np.mean(x1) * np.mean(x2) * np.mean(x3))
        triple_rows.append({
            "joint_id": _id("NFL-SCORER-TRIPLE", run_id, a["aita_player_id"], b["aita_player_id"], c["aita_player_id"]),
            "run_id": run_id,
            "leg1_player_id": a["aita_player_id"], "leg1_player": a["player_name"], "leg1_event_id": a["aita_event_id"],
            "leg2_player_id": b["aita_player_id"], "leg2_player": b["player_name"], "leg2_event_id": b["aita_event_id"],
            "leg3_player_id": c["aita_player_id"], "leg3_player": c["player_name"], "leg3_event_id": c["aita_event_id"],
            "same_game_all_three": len({str(a["aita_event_id"]), str(b["aita_event_id"]), str(c["aita_event_id"])}) == 1,
            "p_joint_model_raw": p_joint,
            "p_independence_product": p_ind,
            "joint_probability_lift_pp": (p_joint - p_ind) * 100.0,
            "fair_joint_decimal_raw": (1.0 / p_joint) if p_joint > 0 else np.inf,
            "fair_joint_american_raw": probability_to_american(p_joint) if p_joint > 0 else np.nan,
            "parlay_math_status": "EMPIRICAL_SHARED_MONTE_CARLO",
        })
    pairs = pd.DataFrame(pair_rows)
    triples = pd.DataFrame(triple_rows)
    if not pairs.empty:
        pairs = pairs.sort_values("p_joint_model_raw", ascending=False).reset_index(drop=True)
        pairs["joint_probability_rank"] = np.arange(1, len(pairs) + 1)
    if not triples.empty:
        triples = triples.sort_values("p_joint_model_raw", ascending=False).reset_index(drop=True)
        triples["joint_probability_rank"] = np.arange(1, len(triples) + 1)
    return {"pairs": pairs, "triples": triples}
