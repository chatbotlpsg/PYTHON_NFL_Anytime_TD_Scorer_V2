# NFL Anytime TD Scorer Parlay Joint Probability Protocol

## Core Rule

Do not multiply scorer legs as independent whenever an empirical joint row exists.

## Required Boards

```text
NFL_SCORER_JOINT_PAIR_BOARD_*.csv
NFL_SCORER_JOINT_TRIPLE_BOARD_*.csv
NFL_SCORER_PARLAY_MATH_CANDIDATE_BOARD_*.csv
```

## 2-Leg Parlays

Use pair-board `p_joint_model_raw`.

## 3-Leg Parlays

Use triple-board `p_joint_model_raw` when supplied.

## Missing Joint Row

If a requested combination is not in the joint board, mark:

```text
NO_JOINT_PROBABILITY_AVAILABLE
```

## Fair Odds Are Not Market Offers

`fair_joint_american_raw` is the model fair parlay price. It is not a sportsbook quote.

## Live Quote Required

A parlay is not tradeable until the agent receives or verifies an executable sportsbook parlay/SGP payout.

Use:

```text
PRICE REQUIRED / NOT YET TRADEABLE
```

when no executable quote exists.
