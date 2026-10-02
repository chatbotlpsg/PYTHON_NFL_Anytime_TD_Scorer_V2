import pandas as pd
from nfl_model.features.game_day_overrides import apply_game_day_overrides


def _pm():
    return pd.DataFrame([
        {"aita_player_id":"caleb","full_name":"Caleb Williams","normalized_name":"caleb williams","position":"QB","current_team":"CHI","available_for_simulation":True,"primary_scorer_eligible":True,"starter_role_verified":True,"starter_gate_status":"VERIFIED_STARTER","depth_rank":1,"role_certainty_score":90.0,"data_freshness_score":95.0},
        {"aita_player_id":"case","full_name":"Case Keenum","normalized_name":"case keenum","position":"QB","current_team":"CHI","available_for_simulation":True,"primary_scorer_eligible":False,"starter_role_verified":False,"starter_gate_status":"BENCH_OR_BACKUP","depth_rank":3,"role_certainty_score":50.0,"data_freshness_score":95.0},
        {"aita_player_id":"goedert","full_name":"Dallas Goedert","normalized_name":"dallas goedert","position":"TE","current_team":"PHI","available_for_simulation":True,"primary_scorer_eligible":True,"starter_role_verified":True,"starter_gate_status":"VERIFIED_STARTER","depth_rank":1,"role_certainty_score":90.0,"data_freshness_score":95.0},
        {"aita_player_id":"ertz","full_name":"Zach Ertz","normalized_name":"zach ertz","position":"TE","current_team":"PHI","available_for_simulation":True,"primary_scorer_eligible":False,"starter_role_verified":False,"starter_gate_status":"NO_DEPTH_VERIFICATION","depth_rank":None,"role_certainty_score":50.0,"data_freshness_score":95.0},
    ])

def test_manual_qb_and_te_overrides_apply_and_demote_old_starters():
    out,audit=apply_game_day_overrides(_pm(), ["CHI:QB:Case Keenum","PHI:TE:Zach Ertz"], ["CHI:Caleb Williams","PHI:Dallas Goedert"])
    case=out[out.aita_player_id.eq("case")].iloc[0]
    caleb=out[out.aita_player_id.eq("caleb")].iloc[0]
    ertz=out[out.aita_player_id.eq("ertz")].iloc[0]
    goedert=out[out.aita_player_id.eq("goedert")].iloc[0]
    assert bool(case.starter_role_verified) and case.depth_rank == 1 and bool(case.available_for_simulation)
    assert not bool(caleb.available_for_simulation)
    assert bool(ertz.starter_role_verified) and ertz.depth_rank == 1
    assert not bool(goedert.available_for_simulation)
    assert len(audit) == 4
