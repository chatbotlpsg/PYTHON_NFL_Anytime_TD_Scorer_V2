import pytest
from nfl_model.providers.odds_api.quota import bookmaker_groups, estimate_plan, assert_reserve


def test_bookmaker_groups():
    assert bookmaker_groups(["a", "b", "c"]) == 1
    assert bookmaker_groups([str(i) for i in range(11)]) == 2


def test_spec_plan_16_games():
    p = estimate_plan(16, 4, 3, 6, 2, ["draftkings", "fanduel", "betrivers"])
    assert p.opportunity_cost == 64
    assert p.mainline_cost == 3
    assert p.production_cost == 18
    assert p.reprice_cost == 12
    assert p.planned_max == 97


def test_reserve_blocks():
    with pytest.raises(RuntimeError, match="BLOCKED_BY_QUOTA_GOVERNOR"):
        assert_reserve(105, 6, 100)
