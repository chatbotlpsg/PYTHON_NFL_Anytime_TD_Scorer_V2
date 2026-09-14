import numpy as np
import pandas as pd

from nfl_model.boards.forecast import (
    build_full_forecast_boards,
    build_market_lined_pick_boards,
)


def _slate():
    return pd.DataFrame([
        {
            "aita_event_id": "NFL-EVT-TEST",
            "kickoff_utc": "2026-09-13T17:00:00Z",
            "home_team": "KC",
            "away_team": "BUF",
        }
    ])


def _player_map():
    return pd.DataFrame([
        {
            "aita_player_id": "P-WR",
            "full_name": "Receiver One",
            "position": "WR",
            "current_team": "KC",
            "role_certainty_score": 88.0,
            "model_agreement_score": 82.0,
            "data_freshness_score": 96.0,
            "availability_status": "ACTIVE_OR_UNLISTED",
            "depth_rank": 1,
        },
        {
            "aita_player_id": "P-RB",
            "full_name": "Runner One",
            "position": "RB",
            "current_team": "BUF",
            "role_certainty_score": 86.0,
            "model_agreement_score": 80.0,
            "data_freshness_score": 96.0,
            "availability_status": "ACTIVE_OR_UNLISTED",
            "depth_rank": 1,
        },
        {
            "aita_player_id": "P-QB",
            "full_name": "Quarterback One",
            "position": "QB",
            "current_team": "KC",
            "role_certainty_score": 92.0,
            "model_agreement_score": 85.0,
            "data_freshness_score": 96.0,
            "availability_status": "ACTIVE_OR_UNLISTED",
            "depth_rank": 1,
        },
    ])


def test_full_forecast_boards_pick_side_for_every_modeled_prop_series():
    draws = {
        "PLAYER|P-WR|receptions": np.array([4, 5, 6, 7, 8, 8, 9, 10]),
        "PLAYER|P-WR|receiving_yards": np.array([45, 50, 61, 70, 80, 88, 95, 110]),
        "PLAYER|P-RB|rushing_attempts": np.array([10, 12, 14, 15, 16, 18, 20, 22]),
        "PLAYER|P-RB|rushing_yards": np.array([35, 42, 50, 60, 65, 75, 90, 105]),
        "PLAYER|P-QB|passing_attempts": np.array([28, 30, 31, 32, 34, 35, 38, 40]),
        "PLAYER|P-QB|completions": np.array([18, 19, 20, 21, 22, 23, 24, 26]),
        "PLAYER|P-QB|passing_yards": np.array([210, 225, 240, 255, 270, 285, 310, 330]),
    }
    summary_rows = []
    meta = {
        "P-WR": ("KC", "Receiver One", "WR"),
        "P-RB": ("BUF", "Runner One", "RB"),
        "P-QB": ("KC", "Quarterback One", "QB"),
    }
    for key, values in draws.items():
        _, pid, stat = key.split("|")
        team, name, pos = meta[pid]
        q = np.quantile(values, [.10, .25, .50, .75, .90])
        summary_rows.append({
            "team": team,
            "player_id": pid,
            "player_name": name,
            "position": pos,
            "stat": stat,
            "mean": float(np.mean(values)),
            "sd": float(np.std(values)),
            "p10": q[0], "p25": q[1], "median": q[2], "p75": q[3], "p90": q[4],
        })
    summary = pd.DataFrame(summary_rows)

    boards = build_full_forecast_boards(
        draws, summary, _slate(), _player_map(), "SNAP-1", "2026-09-02T00:00:00Z"
    )

    assert len(boards["receiving"]) == 2
    assert len(boards["rushing"]) == 2
    assert len(boards["passing"]) == 3
    assert len(boards["all"]) == 7
    assert boards["all"]["model_pick_side"].isin(["OVER", "UNDER"]).all()
    assert boards["all"]["model_pick_probability_raw"].ge(.5).all()
    assert boards["all"]["market_blind"].all()
    assert boards["all"]["forecast_id"].is_unique
    assert boards["all"]["reference_line_source"].eq("MODEL_NATIVE").all()


def test_market_lined_board_chooses_more_probable_side_even_when_only_over_is_posted():
    values = np.array([0, 1, 1, 2, 2, 2, 3, 3, 4, 4])
    draws = {"PLAYER|P-WR|receptions": values}
    priced = pd.DataFrame([
        {
            "aita_event_id": "NFL-EVT-TEST",
            "odds_api_event_id": "ODDS-1",
            "aita_player_id": "P-WR",
            "player_name_raw": "Receiver One",
            "team": "KC",
            "market_key": "player_receptions",
            "bookmaker": "betrivers",
            "side": "OVER",
            "line": 3.5,
            "american_odds": 120,
        },
        {
            "aita_event_id": "NFL-EVT-TEST",
            "odds_api_event_id": "ODDS-1",
            "aita_player_id": "P-WR",
            "player_name_raw": "Receiver One",
            "team": "KC",
            "market_key": "player_receptions",
            "bookmaker": "draftkings",
            "side": "OVER",
            "line": 3.5,
            "american_odds": 110,
        },
    ])

    boards = build_market_lined_pick_boards(
        priced, draws, _slate(), _player_map(), "SNAP-1", "2026-09-02T00:00:00Z"
    )

    assert len(boards["all"]) == 1
    row = boards["all"].iloc[0]
    assert row["model_pick_side"] == "UNDER"
    assert row["p_under_raw"] > row["p_over_raw"]
    assert row["pick_price_status"] == "PICK_SIDE_NOT_POSTED_AT_CONSENSUS_LINE"
    assert row["market_pick_status"] == "DIRECTIONAL_FORECAST_NOT_EV_PLAY"
