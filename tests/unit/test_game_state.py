import numpy as np

from nfl_model.simulation.game_state import simulate_game


def test_joint_game_state_and_market_anchor():
    h = {"epa_per_play": .08, "epa_allowed_per_play": -.02, "success_rate": .46, "success_rate_allowed": .42}
    a = {"epa_per_play": .03, "epa_allowed_per_play": .01, "success_rate": .44, "success_rate_allowed": .44}
    sim = simulate_game("E1", "KC", "BUF", h, a, 10000, 7, {"total": 50.0, "home_spread": -3.0}, .62)
    assert len(sim.draws["GAME|E1|margin"]) == 10000
    assert np.array_equal(sim.draws["GAME|E1|total"], sim.draws["GAME|E1|home_points"] + sim.draws["GAME|E1|away_points"])
    assert np.array_equal(sim.draws["GAME|E1|margin"], sim.draws["GAME|E1|home_points"] - sim.draws["GAME|E1|away_points"])
    # Each offense experiences score state at its own possession timestamps, so the shifts are
    # not exact mirrors; they should still be strongly anti-correlated within the same joint game.
    assert np.corrcoef(sim.home_script_shift, sim.away_script_shift)[0, 1] < -0.80
    assert sim.summary["engine"] == "POSSESSION_GAME_STATE_V2"
    assert sim.summary["home_plays_mean"] > 45
    assert sim.summary["away_plays_mean"] > 45
    assert abs(sim.summary["total_mean"] - 50.0) < 6.0
