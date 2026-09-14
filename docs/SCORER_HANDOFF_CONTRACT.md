# NFL Scorer Trading-Agent Handoff Contract

The ZIP is Dataset A and is immutable.

Python owns:
- scorer probability distributions
- matchup and slate probability ranks
- frozen straight `player_anytime_td` reference prices
- conservative straight EV and executable buy-to/hard-stop prices
- scorer pair/triple joint probabilities and fair joint prices
- provider health, data lineage, reconciliation and manifest

The downstream Trading Agent owns:
- verification of current straight scorer prices
- capture of current sportsbook parlay/SGP payout
- final parlay EV calculation
- execution decision and actual entry
- results, closing price/line capture, CLV/price movement, P&L and grading

No downstream process may silently rewrite Dataset-A probabilities to make a price look actionable.
