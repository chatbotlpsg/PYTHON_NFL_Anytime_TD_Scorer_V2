import pandas as pd

from nfl_model.providers.espn_fantasy.normalize import normalize_fantasy_players
from nfl_model.features.fantasy_context import build_fantasy_context


def test_espn_fantasy_projection_and_actual_points_normalize():
    payload={"players":[{"player":{
        "id":100,"fullName":"Example RB","proTeamId":12,"defaultPositionId":2,"active":True,
        "stats":[
            {"statSourceId":1,"scoringPeriodId":2,"appliedTotal":17.4},
            {"statSourceId":0,"scoringPeriodId":2,"appliedTotal":12.1},
        ]
    }}]}
    out=normalize_fantasy_players(payload,{"12":"KC"},2)
    assert len(out)==1
    assert out.iloc[0]["team"]=="KC"
    assert out.iloc[0]["position"]=="RB"
    assert out.iloc[0]["espn_fantasy_projected_points"]==17.4
    assert out.iloc[0]["espn_fantasy_actual_points"]==12.1


def test_fantasy_projection_can_promote_verified_missing_depth_player_only():
    pm=pd.DataFrame([
        {"aita_player_id":"A","full_name":"A","current_team":"KC","position":"WR","espn_athlete_id":"1","available_for_simulation":True,"primary_depth_eligible":False},
        {"aita_player_id":"B","full_name":"B","current_team":"KC","position":"WR","espn_athlete_id":"2","available_for_simulation":False,"primary_depth_eligible":False},
    ])
    ef=pd.DataFrame([
        {"espn_athlete_id":"1","player_name":"A","team":"KC","position":"WR","espn_fantasy_projected_points":20.0,"espn_fantasy_actual_points":10.0,"espn_fantasy_positional_rank":2},
        {"espn_athlete_id":"2","player_name":"B","team":"KC","position":"WR","espn_fantasy_projected_points":30.0,"espn_fantasy_actual_points":15.0,"espn_fantasy_positional_rank":1},
    ])
    out,_=build_fantasy_context(pm,ef,pd.DataFrame())
    assert bool(out[out["aita_player_id"].eq("A")].iloc[0]["primary_scorer_eligible"]) is True
    assert bool(out[out["aita_player_id"].eq("B")].iloc[0]["primary_scorer_eligible"]) is False
