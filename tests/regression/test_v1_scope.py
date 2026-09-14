from pathlib import Path
from nfl_model.config import load_config

APPROVED = {
    "player_receptions", "player_rush_attempts", "player_pass_attempts", "player_pass_completions",
    "player_reception_yds", "player_rush_yds", "player_pass_yds",
}


def test_no_scope_creep():
    cfg = load_config(Path(__file__).resolve().parents[2])
    assert set(cfg.markets["markets"]) == APPROVED
