from nfl_model.simulation.monte_carlo import simulate_team


def test_joint_simulation_reconciles():
    team = {"plays_mean": 64, "plays_sd": 6, "pass_rate": 0.60}
    qb = {"aita_player_id": "QB1", "player_name": "QB", "completion_rate": .66, "pass_yards_per_attempt": 7.3, "sack_per_dropback": .06, "scramble_proxy_rate": .05}
    rbs = [
        {"aita_player_id": "RB1", "player_name": "RB1", "carries_mean": 15, "targets_mean": 3, "catch_rate": .75, "rush_yards_per_carry": 4.4, "rec_yards_per_reception": 7.0},
        {"aita_player_id": "RB2", "player_name": "RB2", "carries_mean": 6, "targets_mean": 1.5, "catch_rate": .70, "rush_yards_per_carry": 4.0, "rec_yards_per_reception": 6.5},
    ]
    recs = [
        {"aita_player_id": "WR1", "player_name": "WR1", "position": "WR", "targets_mean": 8, "route_share_median": .88, "route_share_sd": .08, "catch_rate": .66, "yards_per_reception": 12},
        {"aita_player_id": "TE1", "player_name": "TE1", "position": "TE", "targets_mean": 6, "route_share_median": .82, "route_share_sd": .09, "catch_rate": .70, "yards_per_reception": 10},
    ]
    sim = simulate_team("KC", team, qb, rbs, recs, n=10000, seed=7, week1_uncertainty=1.2)
    assert sim.reconciliation["status"] == "OK"
    assert sim.reconciliation["max_targets_minus_attempts"] <= 0
    assert sim.reconciliation["max_modeled_receptions_minus_qb_completions"] <= 0


def test_route_first_target_accounting():
    team = {"plays_mean": 63, "plays_sd": 6, "pass_rate": 0.59, "neutral_pass_rate": 0.57, "success_rate": .44}
    qb = {"aita_player_id": "QB1", "player_name": "QB", "completion_rate": .65, "pass_yards_per_attempt": 7.0, "sack_per_dropback": .07, "scramble_proxy_rate": .05}
    recs = [
        {"aita_player_id": "WR1", "player_name": "WR1", "position": "WR", "targets_mean": 9, "route_share_median": .90, "route_share_sd": .06, "catch_rate": .65, "yards_per_reception": 12.0, "adot": 9.5, "yac_per_reception": 4.0},
        {"aita_player_id": "TE1", "player_name": "TE1", "position": "TE", "targets_mean": 6, "route_share_median": .78, "route_share_sd": .08, "catch_rate": .68, "yards_per_reception": 10.0, "adot": 6.5, "yac_per_reception": 3.8},
    ]
    sim = simulate_team("KC", team, qb, [], recs, n=5000, seed=11)
    for pid in ("WR1", "TE1"):
        routes = sim.draws[f"PLAYER|{pid}|routes"]
        targets = sim.draws[f"PLAYER|{pid}|targets"]
        catches = sim.draws[f"PLAYER|{pid}|receptions"]
        assert (targets <= routes).all()
        assert (catches <= targets).all()
    assert sim.reconciliation["max_targets_minus_routes"] <= 0
