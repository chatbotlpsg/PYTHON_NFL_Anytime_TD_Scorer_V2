import pandas as pd

from nfl_model.features.team import build_team_state


def test_team_state_contains_offense_and_defense_features():
    rows = []
    for i in range(40):
        rows.append({
            "posteam": "KC", "defteam": "BUF", "season": 2025, "week": 1 + i // 20,
            "play_type": "pass" if i % 2 else "run", "qb_dropback": 1 if i % 2 else 0,
            "success": 1 if i % 3 else 0, "epa": .1 if i % 2 else -.02,
            "down": 1 + (i % 3), "qtr": 1 + (i % 4), "score_differential": 0,
            "yardline_100": 15 if i % 10 == 0 else 60, "yards_gained": 21 if i % 11 == 0 else 5,
            "passing_yards": 21 if i % 11 == 0 else 0, "rushing_yards": 5 if i % 2 == 0 else 0,
            "first_down": 1 if i % 4 == 0 else 0, "touchdown": 1 if i % 20 == 0 else 0,
            "sack": 0, "interception": 0, "fumble_lost": 0,
        })
        rows.append({**rows[-1], "posteam": "BUF", "defteam": "KC", "epa": -.05})
    out = build_team_state(pd.DataFrame(rows))
    assert {"KC", "BUF"}.issubset(set(out["team"]))
    for c in ["early_down_epa", "neutral_pass_rate", "third_down_rate", "red_zone_td_rate", "explosive_pass_rate", "epa_allowed_per_play", "success_rate_allowed"]:
        assert c in out.columns
