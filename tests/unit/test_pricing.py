import math
from nfl_model.pricing.odds import american_to_decimal, american_to_implied, probability_to_american
from nfl_model.pricing.ev import expected_value_per_dollar, ev_pct
from nfl_model.pricing.novig import two_way_novig
from nfl_model.pricing.buy_to import worst_acceptable_american


def test_american_odds_math():
    assert math.isclose(american_to_decimal(-200), 1.5)
    assert math.isclose(american_to_decimal(150), 2.5)
    assert math.isclose(american_to_implied(-110), 110/210)


def test_ev_framework_example():
    ev = expected_value_per_dollar(0.846, -219)
    assert abs(ev - 0.2327) < 0.001
    assert abs(ev_pct(0.846, -219) - 23.27) < 0.1


def test_two_way_novig():
    po, pu = two_way_novig(-110, -110)
    assert math.isclose(po, 0.5, abs_tol=1e-12)
    assert math.isclose(pu, 0.5, abs_tol=1e-12)


def test_push_ev():
    # 50% win, 10% push, 40% lose at even money = +10% EV.
    assert math.isclose(ev_pct(0.5, 100, 0.1), 10.0, abs_tol=1e-9)


def test_buy_to_meets_floor():
    price = worst_acceptable_american(0.60, 0.04)
    assert ev_pct(0.60, price) >= 3.7  # integer American rounding tolerance


def _pricing_fixture(critical_ok=True, entity_status="RESOLVED", old=False):
    import numpy as np
    import pandas as pd
    from datetime import datetime, timezone, timedelta
    from nfl_model.pricing.engine import price_prop_rows
    ts = datetime.now(timezone.utc) - (timedelta(hours=4) if old else timedelta(minutes=1))
    odds = pd.DataFrame([{
        "aita_player_id": "P1", "market_key": "player_receptions", "side": "OVER", "line": 4.5,
        "american_odds": -110, "market_novig_prob": .50, "market_last_update": ts.isoformat(),
        "entity_status": entity_status,
    }])
    pm = pd.DataFrame([{
        "aita_player_id": "P1", "position": "WR", "role_certainty_score": 90.0,
        "model_agreement_score": 90.0, "data_freshness_score": 95.0,
        "critical_current_state_ok": critical_ok,
    }])
    draws = {"PLAYER|P1|receptions": np.array([4,5,5,6,7,3,8,5,6,4] * 100)}
    out = price_prop_rows(
        odds, draws, pm, {"player_receptions": .04}, {"player_receptions": .46},
        {"week1_multiplier": 1.35, "max_edge_haircut_fraction": .8},
        allowed_positions={"player_receptions": ["WR", "TE", "RB"]}, week=1, max_market_age_minutes=90,
    )
    return out.iloc[0]


def test_pricing_stale_odds_gate():
    row = _pricing_fixture(old=True)
    assert row["model_status"] == "REJECTED"
    assert row["rejection_reason"] == "STALE_ODDS"


def test_pricing_current_state_quality_gate():
    row = _pricing_fixture(critical_ok=False)
    assert row["model_status"] == "REJECTED"
    assert row["rejection_reason"] == "DATA_QUALITY"


def test_entity_quarantine_gate():
    row = _pricing_fixture(entity_status="ENTITY_QUARANTINE")
    assert row["model_status"] == "REJECTED"
    assert row["rejection_reason"] == "ENTITY_FAILURE"
