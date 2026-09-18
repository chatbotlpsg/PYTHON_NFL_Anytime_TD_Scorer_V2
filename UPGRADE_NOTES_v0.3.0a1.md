# AITA NFL Scorer v0.3.0a1 Upgrade Notes

## Objective

Add independent public fantasy/projection corroboration without weakening the existing current-roster hard gate or allowing external fantasy sites to become the primary probability engine.

## New providers

### FFToday
Public weekly QB/RB/WR/TE projection pages.

Normalized fields include projected fantasy points, rushing opportunity, rushing TD, receptions, receiving yards, receiving TD and a Poisson-style external Anytime-TD comparison signal.

### FantasyPros
Public weekly consensus rankings.

Normalized fields include position rank, best/worst/average expert rank and standard deviation.

### Pro-Football-Reference
Public current-season fantasy/production table.

Normalized fields include current rushing/receiving TDs, targets/receptions, fantasy points, PPR/DK/FD points and positional rank when available.

## New feature layer

`src/nfl_model/features/external_fantasy_consensus.py`

Default normalized weights:

- FFToday 45%
- FantasyPros 35%
- PFR 20%

Weights are renormalized over whichever providers actually returned a matched row.

The consensus multiplier is capped to 0.90–1.10.

## Rejection behavior

With at least two matched external sources, sufficiently weak consensus can produce:

```text
external_consensus_status = EXTERNAL_DISAGREEMENT
external_consensus_rejection_flag = True
sharp_board_eligible = False
```

The EV engine then rejects the player as:

```text
EXTERNAL_CONSENSUS_DISAGREEMENT
```

The player remains available in audit/probability diagnostics when otherwise roster-valid; the model does not delete evidence.

## Data freshness

Public HTML is cache-first and timestamped.

- normal max age: 24 hours
- within 24 hours of kickoff: 12 hours
- default request cache TTL: 6 hours
- stale cache is not silently reused when a refresh fails

## Yahoo

Yahoo is retained as an optional OAuth source for users who already have it configured. It is no longer required for the new external consensus layer.

## New handoff artifacts

- `NFL_SCORER_FFTODAY_WEEKLY_PROJECTIONS_*.csv`
- `NFL_SCORER_FANTASYPROS_WEEKLY_RANKINGS_*.csv`
- `NFL_SCORER_PFR_CURRENT_FANTASY_ACTUALS_*.csv`
- `NFL_SCORER_EXTERNAL_FANTASY_CONSENSUS_BOARD_*.csv`

## Validation

- Python compileall: PASS
- Automated tests: 40/40 PASS
- v0.3 config validation: PASS
- Offline scorer handoff audit: PASS
