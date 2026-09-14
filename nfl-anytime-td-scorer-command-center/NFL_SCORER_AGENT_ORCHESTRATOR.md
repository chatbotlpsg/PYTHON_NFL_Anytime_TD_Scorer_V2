# NFL Anytime TD Scorer Agent Orchestrator

## Purpose

Coordinate the downstream Trading Agent workflow for AITA NFL Anytime TD Scorer handoff ZIPs.

## Agent Call Order

```text
1. nfl-scorer-handoff-intake-agent
2. nfl-scorer-data-qc-agent
3. nfl-matchup-scorer-board-agent
4. nfl-slate-probability-board-agent
5. nfl-scorer-ev-board-agent
6. nfl-sharp-scorer-rank-agent
7. nfl-scorer-parlay-math-agent
8. nfl-scorer-sgp-price-agent
9. nfl-scorer-risk-room-agent
10. nfl-scorer-market-quality-agent
11. nfl-scorer-close-clv-agent when close/CLV requested
12. nfl-scorer-result-grade-agent when grading requested
13. nfl-scorer-datasetb-recap-agent when recap requested
```

## Required Final Output

Always preserve separation between:

```text
most probable scorer
best EV scorer
sharpest risk-adjusted scorer
parlay math candidate
executable parlay price
final trading decision
```
