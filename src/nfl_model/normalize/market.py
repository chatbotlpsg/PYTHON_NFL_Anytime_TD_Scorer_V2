from __future__ import annotations
import pandas as pd

from nfl_model.pricing.novig import two_way_novig
from nfl_model.pricing.odds import american_to_implied
from nfl_model.utils import normalize_name


def attach_player_ids(odds: pd.DataFrame, player_map: pd.DataFrame, event_teams: dict[str, set[str]] | None = None) -> pd.DataFrame:
    """Resolve prop players with name + event-team scope; never by display name alone."""
    if odds.empty: return odds.copy()
    out = odds.copy()
    out["normalized_player_name"] = out["player_name_raw"].fillna("").map(normalize_name)
    records = []
    for _, row in out.iterrows():
        q = player_map[player_map["normalized_name"].eq(row["normalized_player_name"])] if not player_map.empty else pd.DataFrame()
        teams = (event_teams or {}).get(str(row.get("odds_api_event_id")), set())
        if teams and not q.empty and "current_team" in q.columns:
            q = q[q["current_team"].isin(teams)]
        if len(q) == 1:
            p = q.iloc[0]
            records.append({**row.to_dict(), "aita_player_id": p.get("aita_player_id"), "player_name": p.get("full_name"),
                            "position": p.get("position"), "team": p.get("current_team"),
                            "role_certainty_score": p.get("role_certainty_score", 70.0),
                            "model_agreement_score": p.get("model_agreement_score", 75.0),
                            "data_freshness_score": p.get("data_freshness_score", 90.0),
                            "entity_status": "RESOLVED"})
        else:
            records.append({**row.to_dict(), "aita_player_id": None, "player_name": row.get("player_name_raw"),
                            "position": None, "team": None, "entity_status": "ENTITY_QUARANTINE"})
    return pd.DataFrame(records)


def add_novig_probabilities(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df.copy()
    out = df.copy()
    if "market_raw_implied_prob" not in out.columns:
        out["market_raw_implied_prob"] = pd.to_numeric(out.get("american_odds"), errors="coerce").map(
            lambda x: american_to_implied(float(x)) if pd.notna(x) else float("nan")
        )
    out["market_novig_prob"] = float("nan")
    group_cols = ["odds_api_event_id", "bookmaker", "market_key", "player_name_raw", "line"]
    for _, idx in out.groupby(group_cols, dropna=False).groups.items():
        sub = out.loc[idx]
        over = sub[sub["side"].eq("OVER")]
        under = sub[sub["side"].eq("UNDER")]
        if len(over) == 1 and len(under) == 1:
            po, pu = two_way_novig(float(over.iloc[0]["american_odds"]), float(under.iloc[0]["american_odds"]))
            out.loc[over.index, "market_novig_prob"] = po
            out.loc[under.index, "market_novig_prob"] = pu
    return out
