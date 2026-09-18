from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

POSITION_ID = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "DST"}


def _as_players(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    players = payload.get("players") or payload.get("playerPool") or []
    if isinstance(players, dict):
        players = list(players.values())
    return [x for x in players if isinstance(x, dict)]


def _extract_week_points(stats: list[dict[str, Any]], week: int, projected: bool) -> float | None:
    vals: list[float] = []
    for s in stats or []:
        if not isinstance(s, dict):
            continue
        source = s.get("statSourceId")
        # ESPN convention: 0 actual, 1 projection.
        if projected and source not in {1, "1"}:
            continue
        if not projected and source not in {0, "0", None}:
            continue
        sp = s.get("scoringPeriodId")
        if sp not in {None, 0, "0", week, str(week)}:
            continue
        raw = s.get("appliedTotal", s.get("appliedStatTotal", s.get("points")))
        try:
            if raw is not None:
                vals.append(float(raw))
        except (TypeError, ValueError):
            pass
    if not vals:
        return None
    # Week-specific records are normally one row; max avoids double counting season + week rows.
    return float(max(vals))


def normalize_fantasy_players(payload: Any, team_id_to_abbr: dict[str, str], week: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in _as_players(payload):
        p = item.get("player") if isinstance(item.get("player"), dict) else item
        pid = str(p.get("id", item.get("id", "")))
        name = p.get("fullName") or p.get("displayName") or item.get("fullName")
        pro_team_id = str(p.get("proTeamId", item.get("proTeamId", "")))
        pos_id = p.get("defaultPositionId", item.get("defaultPositionId"))
        try:
            pos_id_int = int(pos_id)
        except (TypeError, ValueError):
            pos_id_int = -1
        position = POSITION_ID.get(pos_id_int)
        stats = p.get("stats") or item.get("stats") or []
        ratings = p.get("ratings") or item.get("ratings") or {}
        if isinstance(ratings, list):
            rating_vals = [x.get("positionalRanking") for x in ratings if isinstance(x, dict) and x.get("positionalRanking") is not None]
            positional_rank = min(rating_vals) if rating_vals else None
        elif isinstance(ratings, dict):
            vals = [v.get("positionalRanking") for v in ratings.values() if isinstance(v, dict) and v.get("positionalRanking") is not None]
            positional_rank = min(vals) if vals else None
        else:
            positional_rank = None
        proj = _extract_week_points(stats, week, projected=True)
        actual = _extract_week_points(stats, week, projected=False)
        rows.append({
            "espn_athlete_id": pid,
            "player_name": name,
            "team": team_id_to_abbr.get(pro_team_id),
            "position": position,
            "espn_fantasy_projected_points": proj,
            "espn_fantasy_actual_points": actual,
            "espn_fantasy_positional_rank": positional_rank,
            "espn_fantasy_percent_owned": p.get("percentOwned", item.get("percentOwned")),
            "espn_fantasy_injury_status": p.get("injuryStatus", item.get("injuryStatus")),
            "espn_fantasy_active": bool(p.get("active", item.get("active", True))),
            "fantasy_scoring_period": int(week),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out[out["position"].isin(["QB", "RB", "WR", "TE"])].copy()
    for col in ["espn_fantasy_projected_points", "espn_fantasy_actual_points", "espn_fantasy_positional_rank", "espn_fantasy_percent_owned"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out
