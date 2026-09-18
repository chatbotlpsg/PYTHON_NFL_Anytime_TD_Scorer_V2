import numpy as np
import pandas as pd

from nfl_model.simulation.scoring import simulate_scorers
from nfl_model.pricing.scorer import price_anytime_td_rows


def _fixture(n=20000):
    rng=np.random.default_rng(7)
    eid='E1'; team='KC'
    team_tds=rng.poisson(2.7,n).clip(0,6).astype(np.int16)
    draws={
        f'GAME|{eid}|home_touchdowns':team_tds,
        f'TEAM|{team}|rush_plays':rng.normal(27,4,n).clip(15,40).astype(np.int16),
        f'TEAM|{team}|offensive_plays':rng.normal(64,5,n).clip(48,78).astype(np.int16),
        'PLAYER|RB1|rushing_attempts':rng.normal(16,4,n).clip(2,28).astype(np.int16),
        'PLAYER|RB1|targets':rng.normal(4,2,n).clip(0,10).astype(np.int16),
        'PLAYER|WR1|targets':rng.normal(9,3,n).clip(1,16).astype(np.int16),
        'PLAYER|TE1|targets':rng.normal(6,2,n).clip(0,12).astype(np.int16),
    }
    scorer=pd.DataFrame([
        {'aita_player_id':'QB1','player_name':'QB','team':team,'position':'QB','rush_opportunities_ewm':5.5,'receiving_opportunities_ewm':0,'rush_td_propensity_multiplier':1.35,'rec_td_propensity_multiplier':1.0,'historical_td_per_game':.34,'scorer_games_observed':20,'scorer_prior_source':'T'},
        {'aita_player_id':'RB1','player_name':'RB','team':team,'position':'RB','rush_opportunities_ewm':16,'receiving_opportunities_ewm':4,'rush_td_propensity_multiplier':1.15,'rec_td_propensity_multiplier':.95,'historical_td_per_game':.68,'scorer_games_observed':20,'scorer_prior_source':'T'},
        {'aita_player_id':'WR1','player_name':'WR','team':team,'position':'WR','rush_opportunities_ewm':.2,'receiving_opportunities_ewm':9,'rush_td_propensity_multiplier':.7,'rec_td_propensity_multiplier':1.2,'historical_td_per_game':.55,'scorer_games_observed':20,'scorer_prior_source':'T'},
        {'aita_player_id':'TE1','player_name':'TE','team':team,'position':'TE','rush_opportunities_ewm':.1,'receiving_opportunities_ewm':6,'rush_td_propensity_multiplier':.5,'rec_td_propensity_multiplier':1.1,'historical_td_per_game':.38,'scorer_games_observed':20,'scorer_prior_source':'T'},
    ])
    pm=pd.DataFrame([{'aita_player_id':x,'role_certainty_score':90,'available_for_simulation':True,'primary_scorer_eligible':True,'roster_verified_current':True} for x in ['QB1','RB1','WR1','TE1']])
    slate=pd.DataFrame([{'aita_event_id':eid,'home_team':team,'away_team':'BUF'}])
    mix=pd.DataFrame([{'team':team,'historical_rush_td_share':.38}])
    return slate,draws,scorer,pm,mix


def test_scorer_reconciles_and_separates_td_types():
    slate,draws,scorer,pm,mix=_fixture()
    out,summary,recon=simulate_scorers(slate,draws,scorer,pm,123,team_td_state=mix,other_share=.12)
    assert recon and recon[0]['status']=='OK'
    assert recon[0]['max_team_td_allocation_abs_error']==0
    assert (summary['p_anytime_td_raw'].between(0,1)).all()
    qb=summary[summary['aita_player_id'].eq('QB1')].iloc[0]
    assert qb['p_receiving_td_raw']==0.0
    assert qb['p_rushing_td_raw']>0.0
    assert 'SCORER|RB1|anytime' in out


def test_anytime_td_pricing_uses_ev_gate():
    slate,draws,scorer,pm,mix=_fixture()
    out,summary,recon=simulate_scorers(slate,draws,scorer,pm,123,team_td_state=mix,other_share=.12)
    # Match player-map shape required by the pricing layer.
    pm2=pm.copy(); pm2['data_freshness_score']=100.; pm2['critical_current_state_ok']=True; pm2['roster_verified_current']=True; pm2['primary_scorer_eligible']=True
    p=float(np.mean(out['SCORER|RB1|anytime']))
    # Give a deliberately generous price relative to the model probability.
    odds=pd.DataFrame([{'aita_event_id':'E1','aita_player_id':'RB1','bookmaker':'book','market_key':'player_anytime_td','side':'YES','line':.5,'american_odds':250,'market_raw_implied_prob':1/3.5,'entity_status':'RESOLVED'}])
    priced=price_anytime_td_rows(odds,out,pm2,ev_floor=.01,market_trust=0.0,week=2,max_market_age_minutes=999999)
    assert len(priced)==1
    assert priced.iloc[0]['p_model_raw']==p
    assert priced.iloc[0]['ev_raw_pct']>0
    assert priced.iloc[0]['model_status']=='ACTIONABLE_AT_REFERENCE_PRICE'
