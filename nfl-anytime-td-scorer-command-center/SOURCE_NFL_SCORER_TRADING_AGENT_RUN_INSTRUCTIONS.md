RUN THE ATTACHED NFL SCORER TRADING-AGENT HANDOFF ZIP FOR THE 2026-09-13 SLATE.

Treat the Python handoff as the frozen Dataset-A modeling source. Do not alter, rerun, replace, or override the Python model probabilities.

First validate the handoff package, manifest, model version, slate identity, market identity, and all required scorer/joint-probability artifacts.

Then produce:

1. MATCHUP MOST-PROBABLE SCORER BOARDS
For every game on the slate, print the Anytime Touchdown Scorer board ranked from highest model scoring probability to lowest.

Show at minimum:
- Rank
- Game
- Player
- Team
- Position
- Model Anytime-TD Probability
- Model Fair Odds
- Available Sportsbook Odds where present
- Break-Even Probability
- EV%
- Conservative EV%
- Status / pricing gate

2. FULL-SLATE MOST-PROBABLE SCORER BOARD
Combine every modeled player from every matchup and rank the entire slate strictly by model Anytime-TD probability.

Clearly identify:
- Highest-probability scorer on the slate
- Top 5
- Top 10
- Top 20 where available

Probability ranking and EV ranking must remain separate. A highly probable scorer is not automatically a value bet.

3. MATCHUP EV+ BOARDS
For every matchup, print only the positive-EV Anytime-TD opportunities that survive the model's pricing and quality gates.

Rank them by conservative EV%.

4. FULL-SLATE EV+ BOARD
Combine all qualified straight Anytime-TD positions across the slate.

Rank by:
1. Conservative EV%
2. Model confidence
3. Model probability

Show:
- Player
- Matchup
- Model probability
- Fair odds
- Sportsbook price
- Break-even probability
- Raw EV%
- Conservative EV%
- Buy-to price / hard-stop price if available
- Final status

Separate:
- ELITE / SHARP VALUE
- PLAYABLE VALUE
- MARGINAL / WATCH
- PASS / NEGATIVE EV

Do not manufacture labels that contradict the handoff's existing thresholds.

5. SHARP SCORER BOARD
Identify the strongest scorer positions using the combination of:
- Model probability
- Conservative EV
- Model confidence
- Pricing quality
- Simulation convergence
- Market disagreement diagnostics
- Data-quality/reconciliation status

Do not rank solely by headline EV%.

6. PARLAY ANALYSIS
Use the handoff's empirical joint pair and triple probability boards.

DO NOT multiply same-game scorer probabilities as though the legs are independent whenever an empirical joint probability exists.

For each mathematically valid 2-leg or covered 3-leg candidate, show:
- Legs
- Individual probabilities
- Empirical joint probability
- Model fair parlay odds
- Correlation / dependence information
- Actual sportsbook parlay or SGP payout
- Sportsbook break-even probability
- Parlay EV%
- Conservative assessment
- Final decision

You MUST obtain or verify the actual executable sportsbook parlay/SGP payout before declaring a parlay +EV.

If an actual parlay quote is unavailable, label it:
PRICE REQUIRED / NOT YET TRADEABLE

Do not fabricate a sportsbook parlay price.

7. FINAL TRADING BOARD
Finish with separate professional tables for:

A. MOST PROBABLE SCORERS
B. BEST STRAIGHT +EV SCORER PLAYS
C. SHARPEST RISK-ADJUSTED SCORER PLAYS
D. BEST 2-LEG PARLAY CANDIDATES
E. BEST 3-LEG PARLAY CANDIDATES
F. PASSES / REJECTED POSITIONS

For each recommended wager, explain briefly why the mathematics supports the position.

Preserve the boundary between:
- model probability,
- market price,
- expected value,
- and execution.

Never convert "most probable" into "best bet" unless the sportsbook price also creates positive EV.
