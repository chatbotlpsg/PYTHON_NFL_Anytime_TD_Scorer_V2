from __future__ import annotations

import numpy as np
import pandas as pd

from nfl_model.ids.resolver import make_aita_player_id
from nfl_model.ids.teams import canonical_team
from nfl_model.utils import normalize_name

OUT_STATUSES = {"OUT", "INJURED RESERVE", "IR", "PUP", "SUSPENDED"}
QUESTION_STATUSES = {"QUESTIONABLE", "DOUBTFUL"}
SKILL_POSITIONS = {"QB", "RB", "WR", "TE"}


def enrich_player_map_with_current_context(player_map: pd.DataFrame, rosters: pd.DataFrame,
                                           depth: pd.DataFrame, injuries: pd.DataFrame) -> pd.DataFrame:
    p = player_map.copy()
    if p.empty:
        p = pd.DataFrame(columns=["aita_player_id", "full_name", "normalized_name", "position", "current_team",
                                  "espn_athlete_id", "gsis_id", "nflverse_id", "pfr_id", "birth_date", "active_flag", "last_verified_at",
                                  "role_certainty_score", "model_agreement_score", "data_freshness_score"])
    # Add active ESPN skill players missing from the historical map (rookies/new entrants).
    if not rosters.empty:
        for _, r in rosters.iterrows():
            pos = str(r.get("position") or "")
            if pos not in SKILL_POSITIONS:
                continue
            name = str(r.get("full_name") or "")
            team = canonical_team(str(r.get("current_team") or ""))
            eid = str(r.get("espn_athlete_id") or "")
            norm = normalize_name(name)
            q = p[(p["normalized_name"].eq(norm)) & (p["current_team"].eq(team)) & (p["position"].fillna("").eq(pos))] if not p.empty else pd.DataFrame()
            if len(q) == 0:
                p.loc[len(p)] = {
                    "aita_player_id": make_aita_player_id(None, eid or None, team, name),
                    "full_name": name, "normalized_name": norm, "position": pos, "current_team": team,
                    "espn_athlete_id": eid, "gsis_id": None, "nflverse_id": None, "pfr_id": None, "birth_date": None,
                    "active_flag": True, "last_verified_at": None,
                    "role_certainty_score": 48.0, "model_agreement_score": 52.0, "data_freshness_score": 96.0,
                }
            elif len(q) == 1 and eid:
                p.loc[q.index, "espn_athlete_id"] = eid

    p["depth_rank"] = np.nan
    if not depth.empty:
        d = depth.copy()
        d["espn_athlete_id"] = d["espn_athlete_id"].astype(str)

        # Player-prop role certainty must come from the
        # OFFENSIVE depth chart. A returner/special-teams
        # rank must not accidentally promote an RB/WR/TE.
        if "unit" in d.columns:
            offense_mask = (
                d["unit"]
                .astype(str)
                .str.contains(
                    "off",
                    case=False,
                    na=False,
                )
            )

            if offense_mask.any():
                d = d[
                    offense_mask
                ].copy()

        d = d[
            d["espn_athlete_id"]
            .astype(str)
            .str.strip()
            .ne("")
            &
            d["espn_athlete_id"]
            .astype(str)
            .str.lower()
            .ne("nan")
        ].copy()

        rank_map = (
            d.groupby(
                "espn_athlete_id"
            )["rank"]
            .min()
            .to_dict()
        )
        p["depth_rank"] = p["espn_athlete_id"].astype(str).map(rank_map)
        p.loc[p["depth_rank"].eq(1), "role_certainty_score"] = np.minimum(98.0, pd.to_numeric(p.loc[p["depth_rank"].eq(1), "role_certainty_score"], errors="coerce").fillna(50) + 5)
        p.loc[p["depth_rank"].ge(3), "role_certainty_score"] = np.maximum(30.0, pd.to_numeric(p.loc[p["depth_rank"].ge(3), "role_certainty_score"], errors="coerce").fillna(50) - 8)

    p["availability_status"] = "ACTIVE_OR_UNLISTED"
    if not injuries.empty:
        i = injuries.copy()
        i["espn_athlete_id"] = i["espn_athlete_id"].astype(str)

        # Unresolved injury rows remain preserved in the provider
        # snapshot for audit, but may NEVER match a blank player ID.
        i = i[
            i["espn_athlete_id"]
            .str.strip()
            .ne("")
            &
            i["espn_athlete_id"]
            .str.lower()
            .ne("nan")
        ].copy()

        status_map = (
            i.groupby(
                "espn_athlete_id"
            )["status"]
            .last()
            .to_dict()
        )
        p["availability_status"] = p["espn_athlete_id"].astype(str).map(status_map).fillna("ACTIVE_OR_UNLISTED")
    upper = p["availability_status"].astype(str).str.upper()
    p["available_for_simulation"] = ~upper.isin(OUT_STATUSES)
    qmask = upper.isin(QUESTION_STATUSES)
    p.loc[qmask, "role_certainty_score"] = np.maximum(20.0, pd.to_numeric(p.loc[qmask, "role_certainty_score"], errors="coerce").fillna(50) - 15)
    p.loc[~p["available_for_simulation"], "role_certainty_score"] = 0.0
    return p


def bootstrap_missing_role_states(player_map: pd.DataFrame, qb: pd.DataFrame, rb: pd.DataFrame, rec: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    qb_out, rb_out, rec_out = qb.copy(), rb.copy(), rec.copy()
    existing = set()
    for f in [qb_out, rb_out, rec_out]:
        if not f.empty and "aita_player_id" in f.columns:
            existing |= set(f["aita_player_id"].dropna().astype(str))
    for _, p in player_map.iterrows():
        pid = str(p.get("aita_player_id"))
        if pid in existing or not bool(p.get("available_for_simulation", True)):
            continue
        pos = str(p.get("position") or "")
        if pos not in SKILL_POSITIONS:
            continue
        rank = p.get("depth_rank")
        try: rank = int(rank) if not pd.isna(rank) else 3
        except Exception: rank = 3
        common = {"aita_player_id": pid, "gsis_id": p.get("gsis_id"), "player_name": p.get("full_name"),
                  "team": p.get("current_team"), "position": pos, "games_observed": 0, "prior_source": "CURRENT_DEPTH_BOOTSTRAP"}
        if pos == "QB":
            attempts = {1: 33.5, 2: 4.0}.get(rank, 1.0)
            qb_out = pd.concat([qb_out, pd.DataFrame([{**common, "attempts_mean": attempts, "completion_rate": 0.62,
                    "pass_yards_per_attempt": 6.8, "sack_per_dropback": 0.075, "scramble_proxy_rate": 0.045}])], ignore_index=True, sort=False)
        elif pos == "RB":
            carries = {1: 13.5, 2: 7.0, 3: 3.5}.get(rank, 1.5)
            targets = {1: 3.0, 2: 2.0, 3: 1.0}.get(rank, 0.5)
            rb_out = pd.concat([rb_out, pd.DataFrame([{**common, "carries_mean": carries, "targets_mean": targets, "catch_rate": 0.70,
                    "rush_yards_per_carry": 4.1, "rec_yards_per_reception": 7.0, "adot": 1.8, "yac_per_reception": 4.8,
                    "route_share_median": float(min(.72, .14 + targets / 15.0)), "route_share_sd": .14}])], ignore_index=True, sort=False)
        else:
            targets = ({1: 7.0, 2: 5.5, 3: 3.8}.get(rank, 2.0) if pos == "WR" else {1: 5.0, 2: 2.5}.get(rank, 1.2))
            route = ({1: .88, 2: .80, 3: .67}.get(rank, .45) if pos == "WR" else {1: .78, 2: .48}.get(rank, .30))
            rec_out = pd.concat([rec_out, pd.DataFrame([{**common, "targets_mean": targets, "route_share_median": route,
                    "route_share_sd": .14, "catch_rate": .64 if pos == "WR" else .68,
                    "yards_per_reception": 11.5 if pos == "WR" else 9.5,
                    "adot": 8.5 if pos == "WR" else 6.5, "yac_per_reception": 4.2 if pos == "WR" else 3.8,
                    "target_rate_per_route": .18 if pos == "WR" else .16}])], ignore_index=True, sort=False)
    return qb_out, rb_out, rec_out
