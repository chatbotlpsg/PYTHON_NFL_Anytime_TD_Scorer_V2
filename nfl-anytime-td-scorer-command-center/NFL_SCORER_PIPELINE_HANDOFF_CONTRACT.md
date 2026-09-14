# NFL Anytime TD Scorer Handoff Contract

## Required ZIP

```text
NFL_SCORER_TRADING_AGENT_HANDOFF_*.zip
```

## Required Metadata

```text
NFL_SCORER_RUN_MANIFEST_*.json
NFL_SCORER_MODEL_METADATA.json
NFL_SCORER_PROVIDER_HEALTH_*.json
NFL_SCORER_DATA_LINEAGE.json
README.md
```

## Required Boards

```text
MATCHUPS/SCORERS_*.csv
MATCHUPS/EV_*.csv
NFL_SCORER_MATCHUP_PROBABILITY_BOARD_*.csv
NFL_SCORER_SLATE_PROBABILITY_BOARD_*.csv
NFL_SCORER_MATCHUP_EV_PLAY_BOARD_*.csv
NFL_SCORER_SLATE_EV_PLAY_BOARD_*.csv
NFL_SCORER_EDGE_LEADERBOARD_*.csv
NFL_SCORER_MARKET_SNAPSHOT_*.csv
NFL_SCORER_JOINT_PAIR_BOARD_*.csv
NFL_SCORER_JOINT_TRIPLE_BOARD_*.csv
NFL_SCORER_PARLAY_MATH_CANDIDATE_BOARD_*.csv
NFL_SCORER_REJECTION_BOARD_*.csv
NFL_SCORER_FINAL_BOARDS_*.md
```

## Required Validation

The Trading Agent must validate:

```text
ZIP opens
manifest exists
run_id present
season/week/slate date present
simulation count present
model version present
market = player_anytime_td
probability columns valid
EV columns valid
fair odds valid
market odds valid where present
joint probabilities valid where present
no duplicate economic recommendations
no fabricated prices
```

## Critical Boundary

The ZIP is Dataset A. It is immutable. Do not modify Python probabilities, scorer ranks, frozen reference prices, or empirical joint probabilities.
