from __future__ import annotations

from dataclasses import dataclass
import pandas as pd
import numpy as np

from nfl_model.ids.resolver import make_aita_player_id
from nfl_model.ids.teams import canonical_team
from nfl_model.utils import normalize_name


@dataclass(frozen=True)
class StarterOverride:
    team: str
    position: str
    player_name: str


def parse_starter_override(text: str) -> StarterOverride:
    parts = [x.strip() for x in str(text).split(":", 2)]
    if len(parts) != 3 or not all(parts):
        raise ValueError(f"Invalid starter override '{text}'. Use TEAM:POS:PLAYER, e.g. CHI:QB:Case Keenum")
    team, pos, name = canonical_team(parts[0]), parts[1].upper(), parts[2]
    if pos not in {"QB", "RB", "WR", "TE"}:
        raise ValueError(f"Invalid scorer position in starter override: {pos}")
    return StarterOverride(team, pos, name)


def parse_inactive(text: str) -> tuple[str, str]:
    parts = [x.strip() for x in str(text).split(":", 1)]
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Invalid inactive override '{text}'. Use TEAM:PLAYER, e.g. CHI:Caleb Williams")
    return canonical_team(parts[0]), parts[1]


def apply_game_day_overrides(
    player_map: pd.DataFrame,
    starter_overrides: list[str] | None = None,
    inactive_players: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    p = player_map.copy()
    audit: list[dict] = []
    if p.empty:
        return p, pd.DataFrame()
    if "normalized_name" not in p.columns:
        p["normalized_name"] = p["full_name"].fillna("").map(normalize_name)
    p["current_team"] = p["current_team"].fillna("").map(canonical_team)

    for raw in inactive_players or []:
        team, name = parse_inactive(raw)
        norm = normalize_name(name)
        mask = p["current_team"].eq(team) & p["normalized_name"].eq(norm)
        if not mask.any():
            audit.append({"override_type":"INACTIVE","team":team,"position":None,"player_name":name,"status":"NOT_FOUND"})
            continue
        p.loc[mask, "availability_status"] = "MANUAL_GAMEDAY_OUT"
        p.loc[mask, "available_for_simulation"] = False
        p.loc[mask, "primary_scorer_eligible"] = False
        p.loc[mask, "starter_role_verified"] = False
        p.loc[mask, "starter_gate_status"] = "MANUAL_GAMEDAY_OUT"
        p.loc[mask, "role_certainty_score"] = 0.0
        p.loc[mask, "game_day_override_applied"] = True
        p.loc[mask, "game_day_override_source"] = "CLI_MANUAL_GAMEDAY"
        for _, r in p.loc[mask].iterrows():
            audit.append({"override_type":"INACTIVE","team":team,"position":r.get("position"),"player_name":r.get("full_name"),"status":"APPLIED"})

    for raw in starter_overrides or []:
        ov = parse_starter_override(raw)
        norm = normalize_name(ov.player_name)
        mask = p["current_team"].eq(ov.team) & p["position"].fillna("").eq(ov.position) & p["normalized_name"].eq(norm)
        if not mask.any():
            # Re-home a known historical identity when an elevated/new-team player is missing from the current provider snapshot.
            old = p[p["position"].fillna("").eq(ov.position) & p["normalized_name"].eq(norm)]
            if not old.empty:
                rec = old.iloc[-1].to_dict()
                rec["current_team"] = ov.team
                rec["aita_player_id"] = make_aita_player_id(rec.get("gsis_id"), rec.get("espn_athlete_id"), ov.team, ov.player_name)
                rec["full_name"] = ov.player_name
                rec["normalized_name"] = norm
                p = pd.concat([p, pd.DataFrame([rec])], ignore_index=True, sort=False)
                mask = p.index == p.index[-1]
            else:
                rec = {c: np.nan for c in p.columns}
                rec.update({
                    "aita_player_id": make_aita_player_id(None, None, ov.team, ov.player_name),
                    "full_name": ov.player_name, "normalized_name": norm, "position": ov.position,
                    "current_team": ov.team, "role_certainty_score": 99.0, "model_agreement_score": 50.0,
                    "data_freshness_score": 100.0,
                })
                p = pd.concat([p, pd.DataFrame([rec])], ignore_index=True, sort=False)
                mask = p.index == p.index[-1]

        # For single-starter positions demote other same-position players from primary status, while keeping them available as backups.
        if ov.position in {"QB", "RB", "TE"}:
            others = p["current_team"].eq(ov.team) & p["position"].fillna("").eq(ov.position) & ~mask
            p.loc[others, "starter_role_verified"] = False
            p.loc[others, "primary_scorer_eligible"] = False
            p.loc[others, "starter_gate_status"] = "MANUAL_BACKUP_AFTER_OVERRIDE"
            if "depth_rank" in p.columns:
                p.loc[others & pd.to_numeric(p["depth_rank"], errors="coerce").fillna(99).le(1), "depth_rank"] = 2

        p.loc[mask, "roster_snapshot_available"] = True
        p.loc[mask, "roster_verified_current"] = True
        p.loc[mask, "roster_active_flag"] = True
        p.loc[mask, "roster_gate_reason"] = "MANUAL_GAMEDAY_STARTER_OVERRIDE"
        p.loc[mask, "availability_status"] = "MANUAL_GAMEDAY_ACTIVE"
        p.loc[mask, "available_for_simulation"] = True
        p.loc[mask, "depth_rank"] = 1
        p.loc[mask, "depth_chart_verified"] = True
        p.loc[mask, "primary_depth_eligible"] = True
        p.loc[mask, "starter_role_verified"] = True
        p.loc[mask, "starter_gate_status"] = "MANUAL_CONFIRMED_STARTER"
        p.loc[mask, "primary_scorer_eligible"] = True
        p.loc[mask, "role_certainty_score"] = 99.0
        p.loc[mask, "data_freshness_score"] = 100.0
        p.loc[mask, "game_day_override_applied"] = True
        p.loc[mask, "game_day_override_source"] = "CLI_MANUAL_GAMEDAY"
        audit.append({"override_type":"STARTER","team":ov.team,"position":ov.position,"player_name":ov.player_name,"status":"APPLIED"})

    if "game_day_override_applied" not in p.columns:
        p["game_day_override_applied"] = False
    p["game_day_override_applied"] = p["game_day_override_applied"].fillna(False).astype(bool)
    return p, pd.DataFrame(audit)
