import pandas as pd

from nfl_model.providers.fftoday.normalize import normalize_fftoday_weekly
from nfl_model.providers.fantasypros.normalize import normalize_fantasypros_weekly
from nfl_model.providers.pfr.normalize import normalize_pfr_fantasy
from nfl_model.features.external_fantasy_consensus import build_external_fantasy_consensus


def test_fftoday_weekly_parser_and_poisson_signal():
    html = """
    <table>
      <tr><th>Chg</th><th>Player</th><th>Team</th><th>Opp</th><th>Att</th><th>Yard</th><th>TD</th><th>Rec</th><th>Yard</th><th>TD</th><th>FPts</th></tr>
      <tr><td></td><td>Amon-Ra St. Brown</td><td>DET</td><td>@BUF</td><td>0.0</td><td>0.0</td><td>0.0</td><td>7.0</td><td>88.0</td><td>0.6</td><td>22.9</td></tr>
    </table>
    """
    df = normalize_fftoday_weekly(html, "WR", "2026-09-16T12:00:00Z", "https://example.test")
    assert len(df) == 1
    r = df.iloc[0]
    assert r["team"] == "DET"
    assert r["opponent"] == "BUF"
    assert r["fftoday_proj_rec_td"] == 0.6
    assert 0.45 < r["fftoday_anytime_td_signal"] < 0.46


def test_fantasypros_weekly_parser_keeps_requested_position():
    html = """
    <table>
      <tr><th>Rank</th><th>Player (Team)</th><th>Best</th><th>Worst</th><th>AVG</th><th>STD DEV</th></tr>
      <tr><td>1</td><td>Amon-Ra St. Brown (WR - DET)</td><td>1</td><td>5</td><td>2.8</td><td>1.1</td></tr>
      <tr><td>2</td><td>Sam LaPorta (TE - DET)</td><td>2</td><td>8</td><td>5.2</td><td>1.8</td></tr>
    </table>
    """
    df = normalize_fantasypros_weekly(html, "WR", 2, "2026-09-16T12:00:00Z", "https://example.test")
    assert len(df) == 1
    assert df.iloc[0]["player_name"] == "Amon-Ra St. Brown"
    assert df.iloc[0]["fantasypros_rank_stddev"] == 1.1


def test_pfr_parser_handles_data_stat_rows():
    html = """
    <table id="fantasy"><tbody><tr>
      <th data-stat="ranker">1</th><td data-stat="player">Jahmyr Gibbs</td><td data-stat="team">DET</td>
      <td data-stat="fantasy_pos">RB</td><td data-stat="games">1</td><td data-stat="rush_att">29</td>
      <td data-stat="rush_yds">156</td><td data-stat="rush_td">2</td><td data-stat="targets">5</td>
      <td data-stat="rec">5</td><td data-stat="rec_yds">30</td><td data-stat="rec_td">0</td>
      <td data-stat="all_td">2</td><td data-stat="fantasy_points">29</td><td data-stat="fantasy_points_ppr">33.6</td>
      <td data-stat="draftkings_points">37.6</td><td data-stat="fanduel_points">31.1</td><td data-stat="fantasy_rank_pos">3</td>
    </tr></tbody></table>
    """
    df = normalize_pfr_fantasy(html, 2026, "2026-09-16T12:00:00Z", "https://example.test")
    assert len(df) == 1
    r = df.iloc[0]
    assert r["player_name"] == "Jahmyr Gibbs"
    assert r["pfr_rush_td"] == 2
    assert r["pfr_ppr_points"] == 33.6


def test_external_consensus_is_bounded_and_can_reject_multisource_tail():
    pm = pd.DataFrame([
        {"aita_player_id":"P1","full_name":"Star Player","current_team":"DET","position":"WR","primary_scorer_eligible":True,"roster_verified_current":True,"depth_rank":1},
        {"aita_player_id":"P2","full_name":"Tail Player","current_team":"DET","position":"WR","primary_scorer_eligible":True,"roster_verified_current":True,"depth_rank":3},
    ])
    names = ["Star Player", "Mid A", "Mid B", "Mid C", "Tail Player"]
    ff = pd.DataFrame([
        {"player_name":n,"team":"DET","position":"WR","fftoday_anytime_td_signal":v,"fftoday_proj_fpts":f}
        for n,v,f in zip(names,[.55,.35,.25,.15,.02],[22,17,14,10,2])
    ])
    fp = pd.DataFrame([
        {"player_name":n,"team":"DET","position":"WR","fantasypros_pos_rank":r,"fantasypros_rank_stddev":1.0}
        for n,r in zip(names,[1,12,25,45,80])
    ])
    pfr = pd.DataFrame([
        {"player_name":n,"team":"DET","position":"WR","pfr_fantasy_points":f,"pfr_ppr_points":f,"pfr_pos_rank":r}
        for n,f,r in zip(names,[30,20,14,8,1],[1,15,30,50,90])
    ])
    out, board = build_external_fantasy_consensus(pm, ff, fp, pfr)
    star = out[out.aita_player_id.eq("P1")].iloc[0]
    tail = out[out.aita_player_id.eq("P2")].iloc[0]
    assert 0.90 <= star.external_consensus_multiplier <= 1.10
    assert 0.90 <= tail.external_consensus_multiplier <= 1.10
    assert star.external_consensus_status == "STRONG_AGREEMENT"
    assert tail.external_consensus_status == "EXTERNAL_DISAGREEMENT"
    assert bool(tail.external_consensus_rejection_flag)
    assert not bool(tail.sharp_board_eligible)


def test_external_disagreement_blocks_ev_promotion():
    import numpy as np
    from nfl_model.pricing.scorer import price_anytime_td_rows

    odds = pd.DataFrame([{
        "aita_event_id":"E1","aita_player_id":"P2","entity_status":"RESOLVED","american_odds":1800,
        "market_raw_implied_prob":1/19,"bookmaker":"demo","market_key":"player_anytime_td","side":"YES",
    }])
    pm = pd.DataFrame([{
        "aita_player_id":"P2","critical_current_state_ok":True,"roster_verified_current":True,
        "available_for_simulation":True,"primary_scorer_eligible":True,"sharp_board_eligible":False,
        "external_consensus_status":"EXTERNAL_DISAGREEMENT","external_consensus_score":0.12,"external_source_count":3,
    }])
    draws = {"SCORER|P2|anytime": np.ones(1000, dtype=np.int8)}
    priced = price_anytime_td_rows(odds, draws, pm, max_market_age_minutes=999999)
    assert priced.iloc[0]["model_status"] == "REJECTED"
    assert priced.iloc[0]["rejection_reason"] == "EXTERNAL_CONSENSUS_DISAGREEMENT"
