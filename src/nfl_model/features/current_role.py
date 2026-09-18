from __future__ import annotations

import numpy as np
import pandas as pd

from nfl_model.ids.resolver import make_aita_player_id
from nfl_model.ids.teams import canonical_team
from nfl_model.utils import normalize_name

OUT_STATUSES = {"OUT", "INJURED RESERVE", "IR", "PUP", "SUSPENDED", "RESERVE/INJURED"}
QUESTION_STATUSES = {"QUESTIONABLE", "DOUBTFUL"}
SKILL_POSITIONS = {"QB", "RB", "WR", "TE"}
PRIMARY_DEPTH_LIMIT = {"QB": 1, "RB": 3, "WR": 3, "TE": 2}


def _valid_id(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.lower() != "nan"


def enrich_player_map_with_current_context(
    player_map: pd.DataFrame,
    rosters: pd.DataFrame,
    depth: pd.DataFrame,
    injuries: pd.DataFrame,
) -> pd.DataFrame:
    """Attach current ESPN roster/depth/injury state and fail closed on roster identity.

    A historical player is NOT eligible merely because nflverse still has a recent-team row.
    For teams with a healthy ESPN roster snapshot, the player must be explicitly present on
    that current roster. This prevents released, retired, practice-squad-only, or stale-team
    identities from receiving touchdown probability.
    """
    p = player_map.copy()
    if p.empty:
        p = pd.DataFrame(columns=[
            "aita_player_id", "full_name", "normalized_name", "position", "current_team",
            "espn_athlete_id", "gsis_id", "nflverse_id", "pfr_id", "birth_date", "active_flag",
            "last_verified_at", "role_certainty_score", "model_agreement_score", "data_freshness_score",
        ])

    for col in ["full_name", "normalized_name", "position", "current_team", "espn_athlete_id"]:
        if col not in p.columns:
            p[col] = None
    p["normalized_name"] = p["normalized_name"].fillna(p["full_name"].fillna("").map(normalize_name))
    p["current_team"] = p["current_team"].fillna("").map(canonical_team)

    # ------------------------------------------------------------------
    # CURRENT ROSTER GATE
    # ------------------------------------------------------------------
    roster_teams: set[str] = set()
    roster_by_id: dict[str, dict] = {}
    roster_by_name_team_pos: dict[tuple[str, str, str], dict] = {}

    if rosters is not None and not rosters.empty:
        r = rosters.copy()
        r["current_team"] = r["current_team"].fillna("").map(canonical_team)
        r["normalized_name"] = r["full_name"].fillna("").map(normalize_name)
        roster_teams = set(r["current_team"].dropna().astype(str))
        for _, rr in r.iterrows():
            rec = rr.to_dict()
            eid = str(rr.get("espn_athlete_id") or "").strip()
            if _valid_id(eid):
                roster_by_id[eid] = rec
            key = (str(rr.get("normalized_name") or ""), str(rr.get("current_team") or ""), str(rr.get("position") or ""))
            if key[0] and key[1] and key[2]:
                roster_by_name_team_pos[key] = rec

        # Add current ESPN skill players absent from historical data (rookies/new entrants).
        for _, rr in r.iterrows():
            pos = str(rr.get("position") or "")
            if pos not in SKILL_POSITIONS:
                continue
            name = str(rr.get("full_name") or "")
            team = canonical_team(str(rr.get("current_team") or ""))
            eid = str(rr.get("espn_athlete_id") or "")
            norm = normalize_name(name)
            q = p[(p["normalized_name"].eq(norm)) & (p["current_team"].eq(team)) & (p["position"].fillna("").eq(pos))]
            if len(q) == 0:
                p.loc[len(p)] = {
                    "aita_player_id": make_aita_player_id(None, eid or None, team, name),
                    "full_name": name,
                    "normalized_name": norm,
                    "position": pos,
                    "current_team": team,
                    "espn_athlete_id": eid,
                    "gsis_id": None,
                    "nflverse_id": None,
                    "pfr_id": None,
                    "birth_date": None,
                    "active_flag": bool(rr.get("active_flag", True)),
                    "last_verified_at": None,
                    "role_certainty_score": 44.0,
                    "model_agreement_score": 48.0,
                    "data_freshness_score": 98.0,
                }
            elif len(q) == 1 and _valid_id(eid):
                p.loc[q.index, "espn_athlete_id"] = eid

    p["roster_snapshot_available"] = p["current_team"].isin(roster_teams)
    p["roster_verified_current"] = False
    p["roster_active_flag"] = False
    p["roster_gate_reason"] = "NO_CURRENT_ROSTER_SNAPSHOT"

    for idx, row in p.iterrows():
        team = canonical_team(str(row.get("current_team") or ""))
        pos = str(row.get("position") or "")
        eid = str(row.get("espn_athlete_id") or "").strip()
        norm = str(row.get("normalized_name") or normalize_name(str(row.get("full_name") or "")))
        match = roster_by_id.get(eid) if _valid_id(eid) else None
        if match is None:
            match = roster_by_name_team_pos.get((norm, team, pos))
        if match is not None:
            p.at[idx, "roster_verified_current"] = True
            active = bool(match.get("active_flag", True))
            p.at[idx, "roster_active_flag"] = active
            p.at[idx, "roster_gate_reason"] = "CURRENT_ESPN_ROSTER_ACTIVE" if active else "CURRENT_ESPN_ROSTER_INACTIVE"
            match_eid = str(match.get("espn_athlete_id") or "")
            if _valid_id(match_eid):
                p.at[idx, "espn_athlete_id"] = match_eid
        elif team in roster_teams:
            p.at[idx, "roster_gate_reason"] = "NOT_ON_CURRENT_ESPN_ROSTER"

    # ------------------------------------------------------------------
    # OFFENSIVE DEPTH CHART
    # ------------------------------------------------------------------
    p["depth_rank"] = np.nan
    p["depth_chart_verified"] = False
    if depth is not None and not depth.empty:
        d = depth.copy()
        d["espn_athlete_id"] = d["espn_athlete_id"].astype(str)
        d["team"] = d["team"].fillna("").map(canonical_team)
        if "unit" in d.columns:
            offense_mask = d["unit"].astype(str).str.contains("off", case=False, na=False)
            if offense_mask.any():
                d = d[offense_mask].copy()
        d = d[d["espn_athlete_id"].map(_valid_id)].copy()
        rank_map = d.groupby("espn_athlete_id")["rank"].min().to_dict()
        p["depth_rank"] = p["espn_athlete_id"].astype(str).map(rank_map)
        p["depth_chart_verified"] = p["depth_rank"].notna()
        p.loc[p["depth_rank"].eq(1), "role_certainty_score"] = np.minimum(
            98.0, pd.to_numeric(p.loc[p["depth_rank"].eq(1), "role_certainty_score"], errors="coerce").fillna(50) + 7
        )
        p.loc[p["depth_rank"].ge(3), "role_certainty_score"] = np.maximum(
            25.0, pd.to_numeric(p.loc[p["depth_rank"].ge(3), "role_certainty_score"], errors="coerce").fillna(50) - 10
        )

    # ------------------------------------------------------------------
    # INJURY GATE
    # ------------------------------------------------------------------
    p["availability_status"] = "ACTIVE_OR_UNLISTED"
    if injuries is not None and not injuries.empty:
        i = injuries.copy()
        i["espn_athlete_id"] = i["espn_athlete_id"].astype(str)
        i = i[i["espn_athlete_id"].map(_valid_id)].copy()
        status_map = i.groupby("espn_athlete_id")["status"].last().to_dict()
        p["availability_status"] = p["espn_athlete_id"].astype(str).map(status_map).fillna("ACTIVE_OR_UNLISTED")

    upper = p["availability_status"].astype(str).str.upper()
    injury_available = ~upper.isin(OUT_STATUSES)
    qmask = upper.isin(QUESTION_STATUSES)
    p.loc[qmask, "role_certainty_score"] = np.maximum(
        20.0, pd.to_numeric(p.loc[qmask, "role_certainty_score"], errors="coerce").fillna(50) - 15
    )

    # Fail closed: a player must be on the current ESPN roster and active there.
    p["available_for_simulation"] = (
        p["roster_verified_current"].astype(bool)
        & p["roster_active_flag"].astype(bool)
        & injury_available.astype(bool)
        & p["position"].isin(SKILL_POSITIONS)
    )

    # Primary board gate suppresses lotto/deep-chart names. Fantasy projection can later
    # promote a verified player through `fantasy_primary_override` in the fantasy layer.
    def depth_ok(row: pd.Series) -> bool:
        pos = str(row.get("position") or "")
        limit = PRIMARY_DEPTH_LIMIT.get(pos, 0)
        try:
            rank = int(row.get("depth_rank"))
        except (TypeError, ValueError):
            return False
        return rank <= limit

    p["primary_depth_eligible"] = p.apply(depth_ok, axis=1)
    p["fantasy_primary_override"] = False
    p["primary_scorer_eligible"] = p["available_for_simulation"] & p["primary_depth_eligible"]
    p.loc[~p["available_for_simulation"], "role_certainty_score"] = 0.0
    p.loc[~p["roster_verified_current"], "data_freshness_score"] = 0.0
    return p


def bootstrap_missing_role_states(
    player_map: pd.DataFrame,
    qb: pd.DataFrame,
    rb: pd.DataFrame,
    rec: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    qb_out, rb_out, rec_out = qb.copy(), rb.copy(), rec.copy()
    existing = set()
    for f in [qb_out, rb_out, rec_out]:
        if not f.empty and "aita_player_id" in f.columns:
            existing |= set(f["aita_player_id"].dropna().astype(str))

    for _, p in player_map.iterrows():
        pid = str(p.get("aita_player_id") or "")
        if not pid or pid in existing or not bool(p.get("available_for_simulation", False)):
            continue
        pos = str(p.get("position") or "")
        if pos not in SKILL_POSITIONS:
            continue
        rank = p.get("depth_rank")
        try:
            rank = int(rank) if not pd.isna(rank) else 99
        except Exception:
            rank = 99
        common = {
            "aita_player_id": pid,
            "gsis_id": p.get("gsis_id"),
            "player_name": p.get("full_name"),
            "team": p.get("current_team"),
            "position": pos,
            "games_observed": 0,
            "prior_source": "CURRENT_ESPN_ROSTER_DEPTH_BOOTSTRAP",
        }
        # Priors are intentionally conservative for unobserved players. Deep-chart players
        # receive very little opportunity instead of the old generic role assumptions.
        if pos == "QB":
            attempts = {1: 32.0, 2: 2.0}.get(rank, 0.5)
            qb_out = pd.concat([qb_out, pd.DataFrame([{**common, "attempts_mean": attempts, "completion_rate": 0.62,
                "pass_yards_per_attempt": 6.7, "sack_per_dropback": 0.08, "scramble_proxy_rate": 0.04}])], ignore_index=True, sort=False)
        elif pos == "RB":
            carries = {1: 12.5, 2: 6.0, 3: 2.5}.get(rank, 0.5)
            targets = {1: 2.8, 2: 1.6, 3: 0.8}.get(rank, 0.2)
            rb_out = pd.concat([rb_out, pd.DataFrame([{**common, "carries_mean": carries, "targets_mean": targets, "catch_rate": 0.70,
                "rush_yards_per_carry": 4.0, "rec_yards_per_reception": 6.8, "adot": 1.5, "yac_per_reception": 4.6,
                "route_share_median": float(min(.68, .10 + targets / 16.0)), "route_share_sd": .15}])], ignore_index=True, sort=False)
        else:
            if pos == "WR":
                targets = {1: 6.8, 2: 5.0, 3: 3.2}.get(rank, 0.9)
                route = {1: .86, 2: .76, 3: .61}.get(rank, .24)
            else:
                targets = {1: 4.7, 2: 2.1}.get(rank, 0.6)
                route = {1: .75, 2: .43}.get(rank, .20)
            rec_out = pd.concat([rec_out, pd.DataFrame([{**common, "targets_mean": targets, "route_share_median": route,
                "route_share_sd": .15, "catch_rate": .64 if pos == "WR" else .68,
                "yards_per_reception": 11.2 if pos == "WR" else 9.2,
                "adot": 8.2 if pos == "WR" else 6.2, "yac_per_reception": 4.0 if pos == "WR" else 3.7,
                "target_rate_per_route": .18 if pos == "WR" else .16}])], ignore_index=True, sort=False)
    return qb_out, rb_out, rec_out
