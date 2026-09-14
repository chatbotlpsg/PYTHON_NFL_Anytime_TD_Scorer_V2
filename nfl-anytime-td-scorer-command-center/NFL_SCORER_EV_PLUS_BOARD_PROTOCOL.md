# NFL Anytime TD Scorer EV+ Board Protocol

## Straight Anytime TD EV

Use the handoff probabilities and prices as reference values.

Primary fields:

```text
p_model_raw
p_calibrated
p_blend
p_conservative
american_odds
decimal_odds
market_raw_implied_prob
fair_odds_raw
fair_odds_blended
fair_odds_conservative
ev_raw_pct
ev_blended_pct
ev_conservative_pct
minimum_required_ev_pct
buy_to_price
hard_stop_price
confidence_score
model_status
rejection_reason
```

## Ranking

Rank by:

```text
1. ev_conservative_pct
2. confidence_score
3. p_conservative or p_model_raw
```

## Price Verification

If the user supplies a current price, recalculate EV using `p_conservative` and that current price.

If current price is missing, preserve the row as:

```text
REFERENCE_PRICE_ONLY
```

## Buy-To / Hard Stop

If current price is worse than `hard_stop_price`, mark PASS.

If current price is inside `buy_to_price`, keep it eligible if other gates pass.
