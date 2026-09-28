from __future__ import annotations

import numpy as np
import pandas as pd

from nfl_model.ids.teams import canonical_team
from nfl_model.utils import normalize_name


def _prep(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    out["normalized_name"] = out["player_name"].fillna("").map(normalize_name)
    out["team"] = out["team"].fillna("").map(canonical_team)
    out["position"] = out["position"].fillna("").astype(str).str.upper()
    return out


def _rank_score(series: pd.Series, ascending: bool = False) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    if x.notna().sum() <= 1:
        return pd.Series(0.5, index=series.index, dtype=float).where(x.notna(), np.nan)
    # Higher score always means stronger external signal.
    pct = x.rank(pct=True, ascending=ascending, method="average")
    return pct.astype(float)


def build_external_fantasy_consensus(
    player_map: pd.DataFrame,
    fftoday: pd.DataFrame | None,
    fantasypros: pd.DataFrame | None,
    pfr: pd.DataFrame | None,
    fftoday_weight: float = 0.45,
    fantasypros_weight: float = 0.35,
    pfr_weight: float = 0.20,
    multiplier_min: float = 0.90,
    multiplier_max: float = 1.10,
    disagreement_threshold: float = 0.30,
    strong_threshold: float = 0.68,
    moderate_threshold: float = 0.45,
    minimum_sources_for_rejection: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Attach public third-party consensus as a bounded challenger/rejection layer.

    The external layer never overrides ESPN current-roster eligibility and never replaces the
    Monte Carlo model probability. Its multiplier is deliberately narrow and disagreement is
    primarily used to block weak longshot/lottery EV promotions.
    """
    p = player_map.copy()
    if p.empty:
        return p, pd.DataFrame()
    p["normalized_name"] = p["full_name"].fillna("").map(normalize_name)
    p["current_team"] = p["current_team"].fillna("").map(canonical_team)
    p["position"] = p["position"].fillna("").astype(str).str.upper()

    ff = _prep(fftoday)
    fp = _prep(fantasypros)
    pf = _prep(pfr)

    # Provider-specific normalized strength scores are position-relative, not cross-position.
    if not ff.empty:
        td_strength = ff.groupby("position", group_keys=False)["fftoday_anytime_td_signal"].apply(lambda s: _rank_score(s, ascending=True))
        fp_strength = ff.groupby("position", group_keys=False)["fftoday_proj_fpts"].apply(lambda s: _rank_score(s, ascending=True))
        ff["fftoday_context_score"] = (0.65 * td_strength + 0.35 * fp_strength).clip(0.0, 1.0)
    if not fp.empty:
        rank = pd.to_numeric(fp["fantasypros_pos_rank"], errors="coerce")
        max_rank = fp.groupby("position")["fantasypros_pos_rank"].transform(lambda s: max(pd.to_numeric(s, errors="coerce").max(), 2))
        fp["fantasypros_context_score"] = (1.0 - ((rank - 1.0) / (max_rank - 1.0))).clip(0.0, 1.0)
        dispersion = pd.to_numeric(fp.get("fantasypros_rank_stddev"), errors="coerce").fillna(0.0)
        fp["fantasypros_context_score"] *= (1.0 - (dispersion / 25.0).clip(0.0, 0.20))
    if not pf.empty:
        fpts = pd.to_numeric(pf["pfr_fantasy_points"], errors="coerce")
        ppr = pd.to_numeric(pf["pfr_ppr_points"], errors="coerce")
        actual = ppr.where(ppr.notna(), fpts)
        pf["_pfr_actual_for_score"] = actual
        pf["pfr_context_score"] = pf.groupby("position", group_keys=False)["_pfr_actual_for_score"].apply(lambda s: _rank_score(s, ascending=True)).clip(0.0, 1.0)

    key = ["normalized_name", "team", "position"]
    ff_cols = [c for c in [
        *key, "opponent", "fftoday_proj_fpts", "fftoday_proj_rush_td", "fftoday_proj_rec_td",
        "fftoday_proj_scorer_td_lambda", "fftoday_anytime_td_signal", "fftoday_context_score",
        "scraped_at_utc", "source_url"
    ] if c in ff.columns]
    fp_cols = [c for c in [
        *key, "fantasypros_pos_rank", "fantasypros_best_rank", "fantasypros_worst_rank",
        "fantasypros_avg_rank", "fantasypros_rank_stddev", "fantasypros_context_score",
        "scraped_at_utc", "source_url"
    ] if c in fp.columns]
    pf_cols = [c for c in [
        *key, "pfr_games", "pfr_rush_td", "pfr_rec_td", "pfr_targets", "pfr_receptions",
        "pfr_fantasy_points", "pfr_ppr_points", "pfr_dk_points", "pfr_fd_points", "pfr_pos_rank",
        "pfr_context_score", "scraped_at_utc", "source_url"
    ] if c in pf.columns]

    base = p.copy()
    if ff_cols:
        x = ff[ff_cols].drop_duplicates(key, keep="last").rename(columns={
            "scraped_at_utc": "fftoday_scraped_at_utc", "source_url": "fftoday_source_url",
            "opponent": "fftoday_opponent",
        })
        base = base.merge(x, left_on=["normalized_name", "current_team", "position"], right_on=key, how="left", suffixes=("", "_fftoday"))
        base = base.drop(columns=[c for c in ["team"] if c in base.columns], errors="ignore")
    if fp_cols:
        x = fp[fp_cols].drop_duplicates(key, keep="last").rename(columns={
            "scraped_at_utc": "fantasypros_scraped_at_utc", "source_url": "fantasypros_source_url",
        })
        base = base.merge(x, left_on=["normalized_name", "current_team", "position"], right_on=key, how="left", suffixes=("", "_fantasypros"))
        base = base.drop(columns=[c for c in ["team"] if c in base.columns], errors="ignore")
    if pf_cols:
        x = pf[pf_cols].drop_duplicates(key, keep="last").rename(columns={
            "scraped_at_utc": "pfr_scraped_at_utc", "source_url": "pfr_source_url",
        })
        base = base.merge(x, left_on=["normalized_name", "current_team", "position"], right_on=key, how="left", suffixes=("", "_pfr"))
        base = base.drop(columns=[c for c in ["team"] if c in base.columns], errors="ignore")

    # Merge helpers above can create repeated key columns; keep canonical player-map fields.
    for c in ["normalized_name_fftoday", "position_fftoday", "normalized_name_fantasypros", "position_fantasypros", "normalized_name_pfr", "position_pfr"]:
        base = base.drop(columns=c, errors="ignore")

    score_cols = {
        "fftoday_context_score": float(fftoday_weight),
        "fantasypros_context_score": float(fantasypros_weight),
        "pfr_context_score": float(pfr_weight),
    }
    scores = []
    source_counts = []
    for _, row in base.iterrows():
        total_w = 0.0
        total_s = 0.0
        count = 0
        for col, w in score_cols.items():
            val = pd.to_numeric(pd.Series([row.get(col)]), errors="coerce").iloc[0]
            if pd.notna(val):
                total_w += w
                total_s += w * float(np.clip(val, 0.0, 1.0))
                count += 1
        scores.append(total_s / total_w if total_w > 0 else np.nan)
        source_counts.append(count)
    base["external_consensus_score"] = scores
    base["external_source_count"] = source_counts

    def _status(row: pd.Series) -> str:
        n = int(row.get("external_source_count") or 0)
        s = row.get("external_consensus_score")
        if n == 0 or pd.isna(s):
            return "MODEL_ONLY_SIGNAL"
        if n < int(minimum_sources_for_rejection):
            return "INSUFFICIENT_DATA"
        s = float(s)
        if s >= strong_threshold:
            return "STRONG_AGREEMENT"
        if s >= moderate_threshold:
            return "MODERATE_AGREEMENT"
        if s < disagreement_threshold:
            return "EXTERNAL_DISAGREEMENT"
        return "WEAK_AGREEMENT"

    base["external_consensus_status"] = base.apply(_status, axis=1)
    neutral = (float(multiplier_min) + float(multiplier_max)) / 2.0
    score = pd.to_numeric(base["external_consensus_score"], errors="coerce")
    base["external_consensus_multiplier"] = (
        float(multiplier_min) + score.fillna(0.5) * (float(multiplier_max) - float(multiplier_min))
    ).clip(float(multiplier_min), float(multiplier_max))
    base.loc[base["external_source_count"].eq(0), "external_consensus_multiplier"] = neutral
    base["external_consensus_rejection_flag"] = (
        base["external_source_count"].ge(int(minimum_sources_for_rejection))
        & base["external_consensus_status"].eq("EXTERNAL_DISAGREEMENT")
    )
    # Sharp/EV promotion requires starter eligibility, current-season scoring context eligibility,
    # and no multi-source external disagreement. Probability audit rows remain visible.
    scoring_ok = base.get("current_scoring_sharp_eligible", base.get("primary_scorer_eligible", False))
    base["sharp_board_eligible"] = (
        base.get("primary_scorer_eligible", False).fillna(False).astype(bool)
        & scoring_ok.fillna(False).astype(bool)
        & ~base["external_consensus_rejection_flag"]
    )
    base["external_role_agreement"] = np.where(
        base["external_consensus_rejection_flag"], "DISAGREES_WITH_MODEL_ROLE",
        np.where(base["external_source_count"].ge(2), "CORROBORATES_OR_NEUTRAL", "NOT_ENOUGH_EXTERNAL_SOURCES"),
    )

    # Preserve original column order first, then append external fields.
    added = [c for c in base.columns if c not in p.columns]
    board_cols = [c for c in [
        "aita_player_id", "full_name", "current_team", "position", "roster_verified_current", "depth_rank",
        "starter_role_verified", "starter_gate_status", "primary_scorer_eligible", "current_scoring_sharp_eligible",
        "current_scoring_suppression_flag", "current_season_scorer_tds", "current_season_scorer_td_per_game",
        "current_season_td_multiplier", "current_season_offense_tier", "current_season_offense_score",
        "current_season_offense_multiplier", "current_season_ppg", "current_season_offensive_td_per_game",
        "sharp_board_eligible", "fftoday_proj_fpts", "fftoday_proj_rush_td",
        "fftoday_proj_rec_td", "fftoday_proj_scorer_td_lambda", "fftoday_anytime_td_signal",
        "fantasypros_pos_rank", "fantasypros_best_rank", "fantasypros_worst_rank", "fantasypros_avg_rank",
        "fantasypros_rank_stddev", "pfr_fantasy_points", "pfr_ppr_points", "pfr_pos_rank",
        "external_source_count", "external_consensus_score", "external_consensus_multiplier",
        "external_consensus_status", "external_consensus_rejection_flag", "external_role_agreement",
        "fftoday_scraped_at_utc", "fantasypros_scraped_at_utc", "pfr_scraped_at_utc",
    ] if c in base.columns]
    board = base[board_cols].copy()
    board = board.sort_values(["position", "external_consensus_score"], ascending=[True, False], na_position="last")
    return base[p.columns.tolist() + added], board.reset_index(drop=True)


def attach_external_consensus_to_scorer_state(scorer_state: pd.DataFrame, player_map: pd.DataFrame) -> pd.DataFrame:
    if scorer_state is None or scorer_state.empty or player_map is None or player_map.empty:
        return scorer_state
    s = scorer_state.copy()
    cols = [c for c in [
        "aita_player_id", "fftoday_proj_fpts", "fftoday_proj_rush_td", "fftoday_proj_rec_td",
        "fftoday_proj_scorer_td_lambda", "fftoday_anytime_td_signal", "fantasypros_pos_rank",
        "fantasypros_avg_rank", "fantasypros_rank_stddev", "pfr_fantasy_points", "pfr_ppr_points",
        "pfr_pos_rank", "external_source_count", "external_consensus_score", "external_consensus_multiplier",
        "external_consensus_status", "external_consensus_rejection_flag", "sharp_board_eligible",
        "starter_role_verified", "starter_gate_status", "current_scoring_sharp_eligible",
        "current_scoring_suppression_flag", "current_season_scorer_tds", "current_season_scorer_td_per_game",
        "current_season_td_multiplier", "current_season_offense_tier", "current_season_offense_score",
        "current_season_offense_multiplier", "current_season_ppg", "current_season_offensive_td_per_game",
    ] if c in player_map.columns]
    if not cols:
        return s
    return s.merge(player_map[cols].drop_duplicates("aita_player_id"), on="aita_player_id", how="left")
