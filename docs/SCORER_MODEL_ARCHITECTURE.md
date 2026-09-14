# AITA NFL Touchdown Scorer Model Architecture

## Purpose
This model extends the NFL player-prop pipeline with a specialized market-blind touchdown-scorer layer and a price-sensitive EV layer for `player_anytime_td`.

## Data inputs
It deliberately reuses the same football inputs as the source NFL player-prop model:
- ESPN weekly schedule, rosters, depth charts, injuries, transactions
- nflverse play-by-play, weekly player stats, snap counts and supporting historical tables
- NWS weather for outdoor games
- The Odds API mainlines for market context and `player_anytime_td` for pricing only

## Probability engine
1. The existing possession/game-state engine simulates game score paths and offensive TD counts.
2. Historical nflverse player stats create scorer state: rushing/receiving TD rates, carries/targets, recent TD rate, and Bayesian-smoothed type-specific TD propensity.
3. Historical team scoring creates a rushing-vs-passing TD mix.
4. Every simulated team offensive TD is split into rushing or receiving paths.
5. Rushing TDs are allocated only through rushing scorer paths; receiving TDs only through receiving scorer paths.
6. Passing TDs do not count as a TD score for the passer. A QB only receives anytime-TD credit through a rushing TD path. V0.1 allocates named-player scorer probability through offensive rushing/receiving paths; rare return/fumble-recovery scorer paths remain in the residual OTHER bucket rather than being fabricated at player level.
7. An explicit OTHER bucket preserves roster/model coverage uncertainty.
8. Per-team scorer allocations reconcile exactly to simulated offensive TD totals.

## Boards
- Matchup probability board: most probable scorers in each game.
- Slate probability board: most probable scorers across the entire selected slate.
- Matchup EV board: price-sensitive +EV straight scorer plays by game.
- Slate EV board: all actionable straight scorer plays across the slate.
- Pair/triple joint boards: empirical shared-Monte-Carlo scorer joint probabilities for parlay construction.
- Parlay candidate board: model joint probability + fair price only; live parlay EV belongs to the Trading Agent because the executable SGP/parlay payout must be observed at decision time.

## Calibration boundary
The scorer model starts with identity probability calibration rather than shrinking low touchdown probabilities toward 50%. Live Dataset-B outcomes/price movement should later be used for walk-forward calibration by probability bucket, position, TD type, market-price range, week/regime and model version.
