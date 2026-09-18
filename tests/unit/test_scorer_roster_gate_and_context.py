import pandas as pd

from nfl_model.features.current_role import enrich_player_map_with_current_context
from nfl_model.boards.scorers import build_scorer_probability_boards
from nfl_model.features.td_context import build_defensive_td_vulnerability_state, build_player_td_style_state


def test_historical_player_not_on_current_roster_is_blocked():
    players = pd.DataFrame([{
        "aita_player_id":"OLD1","full_name":"Old Player","normalized_name":"old player","position":"WR",
        "current_team":"KC","espn_athlete_id":"999","role_certainty_score":80.0,"data_freshness_score":90.0,
    }])
    rosters = pd.DataFrame([{
        "espn_athlete_id":"100","full_name":"Current Player","position":"WR","current_team":"KC","active_flag":True,
    }])
    out = enrich_player_map_with_current_context(players, rosters, pd.DataFrame(), pd.DataFrame())
    old = out[out["aita_player_id"].eq("OLD1")].iloc[0]
    assert bool(old["roster_verified_current"]) is False
    assert bool(old["available_for_simulation"]) is False
    assert old["roster_gate_reason"] == "NOT_ON_CURRENT_ESPN_ROSTER"


def test_primary_board_excludes_unverified_and_deep_lottery_names():
    summary = pd.DataFrame([
        {"aita_event_id":"E1","team":"KC","aita_player_id":"A","player_name":"Starter","position":"RB","p_anytime_td_raw":.50,"p_2plus_td_raw":.10},
        {"aita_event_id":"E1","team":"KC","aita_player_id":"B","player_name":"Stale","position":"WR","p_anytime_td_raw":.70,"p_2plus_td_raw":.20},
        {"aita_event_id":"E1","team":"KC","aita_player_id":"C","player_name":"Deep","position":"WR","p_anytime_td_raw":.60,"p_2plus_td_raw":.15},
    ])
    pm = pd.DataFrame([
        {"aita_player_id":"A","roster_verified_current":True,"primary_scorer_eligible":True,"role_certainty_score":90,"data_freshness_score":100},
        {"aita_player_id":"B","roster_verified_current":False,"primary_scorer_eligible":False,"role_certainty_score":0,"data_freshness_score":0},
        {"aita_player_id":"C","roster_verified_current":True,"primary_scorer_eligible":False,"role_certainty_score":40,"data_freshness_score":100},
    ])
    slate = pd.DataFrame([{"aita_event_id":"E1","home_team":"KC","away_team":"BUF","kickoff_utc":"2026-09-14T00:00:00Z"}])
    boards = build_scorer_probability_boards(summary, slate, pm, "RUN", "NOW")
    assert list(boards["slate"]["aita_player_id"]) == ["A"]
    assert set(boards["all"]["aita_player_id"]) == {"A","B","C"}


def test_td_context_distinguishes_red_zone_and_explosive():
    hist = pd.DataFrame([
        {"player_id":"P1","player_name":"P","position":"WR","defense":"BUF","game_id":"G1","season":2025,"td_origin":"INSIDE_5","td_type":"RECEIVING"},
        {"player_id":"P1","player_name":"P","position":"WR","defense":"BUF","game_id":"G2","season":2025,"td_origin":"RED_ZONE_6_20","td_type":"RECEIVING"},
        {"player_id":"P2","player_name":"Q","position":"WR","defense":"BUF","game_id":"G3","season":2025,"td_origin":"EXPLOSIVE_21_PLUS","td_type":"RECEIVING"},
    ])
    d = build_defensive_td_vulnerability_state(hist)
    assert not d.empty
    p = build_player_td_style_state(hist)
    row = p[p["player_id"] if "player_id" in p.columns else p["gsis_id"] == "P1"] if False else p[p["gsis_id"].eq("P1")]
    assert row.iloc[0]["td_style"] == "GOAL_LINE_RED_ZONE_SCORER"
