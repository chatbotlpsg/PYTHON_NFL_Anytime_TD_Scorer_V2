from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import pandas as pd

from nfl_model.utils import normalize_name


class EntityQuarantineError(RuntimeError):
    pass


@dataclass(frozen=True)
class Resolution:
    aita_player_id: str | None
    status: str
    method: str
    candidates: int


def make_aita_player_id(gsis_id: str | None, espn_id: str | None, team: str, name: str) -> str:
    if gsis_id:
        return f"NFL-GSIS-{gsis_id}"
    if espn_id:
        return f"NFL-ESPN-{espn_id}"
    return f"NFL-BOOTSTRAP-{team}-{normalize_name(name).replace(' ', '-') }"


def resolve_player(player_name: str, team: str | None, position: str | None, player_map: pd.DataFrame) -> Resolution:
    if player_map.empty:
        return Resolution(None, "ENTITY_QUARANTINE", "EMPTY_MAP", 0)
    norm = normalize_name(player_name)
    q = player_map[player_map["normalized_name"].eq(norm)]
    if team and "current_team" in q.columns:
        q = q[q["current_team"].fillna("").eq(team)]
    if position and "position" in q.columns:
        q = q[q["position"].fillna("").eq(position)]
    if len(q) == 1:
        return Resolution(str(q.iloc[0]["aita_player_id"]), "RESOLVED", "NAME_TEAM_POSITION", 1)
    return Resolution(None, "ENTITY_QUARANTINE", "AMBIGUOUS_OR_MISSING", len(q))


def build_player_map(rows: Iterable[dict]) -> pd.DataFrame:
    records = []
    for row in rows:
        name = row.get("full_name") or row.get("display_name") or row.get("player_name") or ""
        team = row.get("current_team") or row.get("team") or ""
        espn_id = row.get("espn_athlete_id") or row.get("espn_id")
        gsis_id = row.get("gsis_id") or row.get("player_id")
        records.append({
            "aita_player_id": make_aita_player_id(str(gsis_id) if gsis_id else None, str(espn_id) if espn_id else None, team, name),
            "full_name": name,
            "normalized_name": normalize_name(name),
            "position": row.get("position"),
            "current_team": team,
            "espn_athlete_id": espn_id,
            "gsis_id": gsis_id,
            "nflverse_id": row.get("nflverse_id") or gsis_id,
            "pfr_id": row.get("pfr_id"),
            "birth_date": row.get("birth_date"),
            "active_flag": row.get("active_flag", True),
            "last_verified_at": row.get("last_verified_at"),
        })
    df = pd.DataFrame.from_records(records)
    if not df.empty:
        df = df.drop_duplicates(subset=["aita_player_id"], keep="last")
    return df
