import pandas as pd

from nfl_model.features.current_season_scoring import (
    pregame_rows,
    build_current_season_scoring_context,
    attach_current_season_scoring_to_player_map,
)
from nfl_model.simulation.game_state import _baseline_means


def _player_stats():
    return pd.DataFrame([
        {"season":2026,"week":1,"player_id":"R1","player_display_name":"RB One","position":"RB","recent_team":"AAA","rushing_tds":0,"receiving_tds":0,"fantasy_points_ppr":10},
        {"season":2026,"week":2,"player_id":"R1","player_display_name":"RB One","position":"RB","recent_team":"AAA","rushing_tds":0,"receiving_tds":0,"fantasy_points_ppr":9},
        {"season":2026,"week":3,"player_id":"R1","player_display_name":"RB One","position":"RB","recent_team":"AAA","rushing_tds":4,"receiving_tds":0,"fantasy_points_ppr":40},
        {"season":2026,"week":1,"player_id":"R2","player_display_name":"RB Two","position":"RB","recent_team":"BBB","rushing_tds":1,"receiving_tds":0,"fantasy_points_ppr":24},
        {"season":2026,"week":2,"player_id":"R2","player_display_name":"RB Two","position":"RB","recent_team":"BBB","rushing_tds":1,"receiving_tds":0,"fantasy_points_ppr":25},
    ])


def _schedules():
    return pd.DataFrame([
        {"season":2026,"week":1,"home_team":"AAA","away_team":"BBB","home_score":10,"away_score":31},
        {"season":2026,"week":2,"home_team":"BBB","away_team":"AAA","home_score":28,"away_score":13},
        {"season":2026,"week":3,"home_team":"AAA","away_team":"BBB","home_score":45,"away_score":7},
    ])


def test_pregame_gate_excludes_requested_week_and_future():
    out = pregame_rows(_player_stats(), 2026, 3)
    assert set(out["week"]) == {1, 2}
    assert out["rushing_tds"].sum() == 2


def test_current_scoring_penalizes_zero_td_weak_offense_and_rewards_strong_offense():
    players, teams = build_current_season_scoring_context(_player_stats(), _schedules(), 2026, 3)
    a = players[players["gsis_id"].eq("R1")].iloc[0]
    b = players[players["gsis_id"].eq("R2")].iloc[0]
    assert a["current_season_scorer_tds"] == 0
    assert a["current_season_td_multiplier"] < 1.0
    assert b["current_season_scorer_tds"] == 2
    assert b["current_season_td_multiplier"] > 1.0
    ta = teams[teams["team"].eq("AAA")].iloc[0]
    tb = teams[teams["team"].eq("BBB")].iloc[0]
    assert ta["current_season_ppg"] == 11.5
    assert tb["current_season_ppg"] == 29.5
    assert ta["current_season_offense_multiplier"] < tb["current_season_offense_multiplier"]


def test_very_weak_zero_td_player_is_suppressed_from_sharp_promotion():
    players, teams = build_current_season_scoring_context(_player_stats(), _schedules(), 2026, 3, suppression_team_percentile=0.60)
    pm = pd.DataFrame([
        {"aita_player_id":"A","gsis_id":"R1","full_name":"RB One","current_team":"AAA","position":"RB","primary_scorer_eligible":True},
        {"aita_player_id":"B","gsis_id":"R2","full_name":"RB Two","current_team":"BBB","position":"RB","primary_scorer_eligible":True},
    ])
    out = attach_current_season_scoring_to_player_map(pm, players, teams, minimum_games_for_suppression=2)
    a = out[out["aita_player_id"].eq("A")].iloc[0]
    b = out[out["aita_player_id"].eq("B")].iloc[0]
    assert bool(a["current_scoring_suppression_flag"])
    assert not bool(a["current_scoring_sharp_eligible"])
    assert not bool(b["current_scoring_suppression_flag"])
    assert bool(b["current_scoring_sharp_eligible"])


def test_current_scoring_multiplier_changes_pregame_score_prior():
    base = {"epa_per_play":0.0,"success_rate":0.43,"epa_allowed_per_play":0.0,"success_rate_allowed":0.43}
    weak = {**base, "current_season_offense_multiplier":0.88}
    strong = {**base, "current_season_offense_multiplier":1.10}
    neutral_opp = {**base, "current_season_offense_multiplier":1.0}
    weak_mean, _ = _baseline_means(weak, neutral_opp)
    strong_mean, _ = _baseline_means(strong, neutral_opp)
    assert weak_mean < strong_mean
