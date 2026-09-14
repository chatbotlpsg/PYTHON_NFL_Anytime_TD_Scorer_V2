# NFL Anytime TD Scorer Pipeline Inspection Summary

Inspected package:

```text
PYTHON_NFL_Anytime_TD_Scorer_V2.zip
```

Relevant pipeline identity:

```text
AITA NFL Touchdown Scorer Probability + EV Pipeline
market = player_anytime_td
model family = AITA_NFL_TOUCHDOWN_SCORER
```

Observed handoff output pattern:

```text
NFL_SCORER_TRADING_AGENT_HANDOFF_*.zip
MATCHUPS/SCORERS_*.csv
MATCHUPS/EV_*.csv
NFL_SCORER_SLATE_PROBABILITY_BOARD_*.csv
NFL_SCORER_SLATE_EV_PLAY_BOARD_*.csv
NFL_SCORER_JOINT_PAIR_BOARD_*.csv
NFL_SCORER_JOINT_TRIPLE_BOARD_*.csv
NFL_SCORER_PARLAY_MATH_CANDIDATE_BOARD_*.csv
NFL_SCORER_REJECTION_BOARD_*.csv
NFL_SCORER_RUN_MANIFEST_*.json
NFL_SCORER_MODEL_METADATA.json
```

Observed sample run:

```text
run_id = NFL-SCORER-2026-W01-20260913T153445Z-SUN_0913
slate_date = 2026-09-13
season = 2026
week = 1
simulation_count = 500000
slate probability rows = 416
straight EV rows = 82
parlay math candidate rows = 890
```

Core boundary:

```text
Python prices scorer claims.
Trading Agent trades, price-checks, captures close, grades, and audits.
```
