from __future__ import annotations

import numpy as np
import pandas as pd

from nfl_model.ids.teams import canonical_team


def _num(df: pd.DataFrame, name: str, default: float = 0.0) -> pd.Series:
    if name not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[name], errors="coerce").fillna(default)


def _ewm_last(values: pd.Series, halflife: float, default: float) -> float:
    s = pd.to_numeric(values, errors="coerce").dropna()
    if s.empty:
        return default
    return float(s.ewm(halflife=halflife, adjust=False).mean().iloc[-1])


def build_team_state(pbp: pd.DataFrame, halflife_weeks: float = 6.0) -> pd.DataFrame:
    """Build opponent-aware, time-decayed team state from historical play-by-play.

    All feature derivation is time-ordered. The function intentionally falls back cleanly
    when a historical provider release omits an optional field.
    """
    if pbp.empty:
        return pd.DataFrame(columns=["team", "plays_mean", "pass_rate", "epa_per_play", "success_rate"])
    df = pbp.copy()
    if "posteam" not in df.columns:
        raise ValueError("PBP missing posteam")
    df["team"] = df["posteam"].fillna("").map(canonical_team)
    df["def_team"] = df.get("defteam", pd.Series("", index=df.index)).fillna("").map(canonical_team)
    df = df[df["team"].ne("")]
    if "play_type" in df.columns:
        df = df[df["play_type"].isin(["pass", "run"])].copy()
    if df.empty:
        return pd.DataFrame()

    df["is_pass"] = _num(df, "qb_dropback", np.nan)
    if df["is_pass"].isna().all():
        df["is_pass"] = _num(df, "pass", 0)
    df["is_pass"] = df["is_pass"].fillna(0).clip(0, 1)
    df["is_run"] = 1.0 - df["is_pass"]
    df["success_num"] = _num(df, "success", np.nan)
    df["epa_num"] = _num(df, "epa", np.nan)
    down = _num(df, "down", 0)
    qtr = _num(df, "qtr", 0)
    score_diff = _num(df, "score_differential", 0)
    yardline = _num(df, "yardline_100", 100)
    yards = _num(df, "yards_gained", 0)
    passing_yards = _num(df, "passing_yards", yards.where(df["is_pass"].eq(1), 0))
    rushing_yards = _num(df, "rushing_yards", yards.where(df["is_run"].eq(1), 0))
    df["early_down"] = down.isin([1, 2]).astype(float)
    df["neutral"] = ((score_diff.abs() <= 8) & (qtr <= 3) & down.isin([1, 2])).astype(float)
    df["third_down"] = down.eq(3).astype(float)
    first_down = _num(df, "first_down", 0).clip(0, 1)
    df["third_down_conversion"] = df["third_down"] * first_down
    df["red_zone"] = yardline.le(20).astype(float)
    touchdown = _num(df, "touchdown", 0).clip(0, 1)
    df["red_zone_td"] = df["red_zone"] * touchdown
    df["explosive_pass"] = ((df["is_pass"] == 1) & (passing_yards >= 20)).astype(float)
    df["explosive_run"] = ((df["is_run"] == 1) & (rushing_yards >= 10)).astype(float)
    df["sack"] = _num(df, "sack", 0).clip(0, 1)
    df["turnover"] = ((_num(df, "interception", 0) > 0) | (_num(df, "fumble_lost", 0) > 0)).astype(float)
    df["early_epa"] = df["epa_num"].where(df["early_down"].eq(1))
    df["early_success"] = df["success_num"].where(df["early_down"].eq(1))
    df["pass_epa"] = df["epa_num"].where(df["is_pass"].eq(1))
    df["rush_epa"] = df["epa_num"].where(df["is_run"].eq(1))
    df["neutral_pass"] = df["is_pass"].where(df["neutral"].eq(1))

    if "season" not in df.columns:
        df["season"] = 0
    if "week" not in df.columns:
        df["week"] = 0
    df = df.sort_values(["season", "week"])

    def weekly_for(group_col: str, prefix: str = "") -> pd.DataFrame:
        weekly = df[df[group_col].ne("")].groupby([group_col, "season", "week"], dropna=False).agg(
            plays=("team", "size"),
            pass_rate=("is_pass", "mean"),
            neutral_pass_rate=("neutral_pass", "mean"),
            epa_per_play=("epa_num", "mean"),
            success_rate=("success_num", "mean"),
            early_down_epa=("early_epa", "mean"),
            early_down_success=("early_success", "mean"),
            pass_epa=("pass_epa", "mean"),
            rush_epa=("rush_epa", "mean"),
            third_down_rate=("third_down_conversion", "sum"),
            third_down_plays=("third_down", "sum"),
            red_zone_td=("red_zone_td", "sum"),
            red_zone_plays=("red_zone", "sum"),
            explosive_pass_rate=("explosive_pass", "mean"),
            explosive_run_rate=("explosive_run", "mean"),
            sack_rate=("sack", "mean"),
            turnover_rate=("turnover", "mean"),
        ).reset_index().rename(columns={group_col: "team"})
        weekly["third_down_rate"] = weekly["third_down_rate"] / weekly["third_down_plays"].replace(0, np.nan)
        weekly["red_zone_td_rate"] = weekly["red_zone_td"] / weekly["red_zone_plays"].replace(0, np.nan)
        return weekly

    offense = weekly_for("team")
    defense = weekly_for("def_team")

    def collapse(w: pd.DataFrame, defense_mode: bool = False) -> pd.DataFrame:
        rows = []
        for team, g in w.groupby("team"):
            g = g.sort_values(["season", "week"])
            row = {"team": team, "games_observed": int(len(g))}
            for col, default in [
                ("plays", 63.0), ("pass_rate", .58), ("neutral_pass_rate", .58), ("epa_per_play", 0.0),
                ("success_rate", .43), ("early_down_epa", 0.0), ("early_down_success", .43),
                ("pass_epa", 0.0), ("rush_epa", 0.0), ("third_down_rate", .40), ("red_zone_td_rate", .55),
                ("explosive_pass_rate", .08), ("explosive_run_rate", .10), ("sack_rate", .065), ("turnover_rate", .025),
            ]:
                name = f"{col}_allowed" if defense_mode and col not in {"plays", "pass_rate", "neutral_pass_rate"} else col
                row[name] = _ewm_last(g[col], halflife_weeks, default)
            if not defense_mode:
                row["plays_mean"] = row.pop("plays")
                row["plays_sd"] = max(5.0, float(pd.to_numeric(g["plays"], errors="coerce").std(ddof=0) or 7.0))
                row["pass_rate"] = float(np.clip(row["pass_rate"], .35, .78))
                row["neutral_pass_rate"] = float(np.clip(row["neutral_pass_rate"], .35, .78))
            rows.append(row)
        return pd.DataFrame(rows)

    off = collapse(offense, False)
    deff = collapse(defense, True)
    if deff.empty:
        return off
    if "epa_per_play_allowed" in deff.columns:
        deff = deff.rename(columns={"epa_per_play_allowed": "epa_allowed_per_play"})
    keep = [c for c in deff.columns if c == "team" or c.endswith("_allowed") or c == "epa_allowed_per_play"]
    out = off.merge(deff[keep], on="team", how="left")
    return out
