# AITA NFL Model V1 — Build Validation Report

Build version: `0.3.0a3`  
Target: NFL 2026 opportunity-first player alpha pipeline

## Locked scope implemented

- nflverse/nflreadpy historical adapter and local Parquet cache.
- ESPN current slate/roster/depth/injury/transaction adapters with immutable raw snapshots and provider isolation.
- NWS outdoor-weather adapter and dome/covered zero-impact policy.
- The Odds API reference-pricing adapter with request fingerprints, TTL cache, quota reserve gate, response-header ledger, and append-only archive.
- Canonical team/event/player identity and explicit `ENTITY_QUARANTINE` handling.
- Current-state degradation gate for failed critical roster/depth/injury state.
- Time-decayed team state plus QB/RB/receiver/coaching/matchup state tables.
- Joint possession game simulation feeding the same per-draw play counts and script state into player opportunity.
- Opportunity-first chain: pass/run → QB attempts → RB carries / routes → targets → catches/completions → yards.
- Route/target, target/attempt, reception/completion, RB-carry/team-rush, and pass+run/team-play reconciliation gates.
- Role/input uncertainty, Week-1-only uncertainty amplification, and bounded weather effects.
- Four probability layers: raw, calibrated, blended, conservative.
- Raw implied + no-vig market probabilities, four fair-price/EV layers, BUY-TO, hard stop, uncertainty haircut, model disagreement and confidence diagnostics.
- Monte Carlo convergence annotations and candidate quarantine when production checkpoints fail tolerance.
- Joint-draw correlation matrix, edge labels, thesis grouping, best-expression / redundant-exposure logic.
- Required opportunity/production/EV/leaderboard/rejection/thesis boards plus convergence report.
- Immutable deterministic Trading-Agent handoff ZIP with Dataset A and explicit boundary manifest.
- Research-only Dataset-B importer; Python production never creates actual-entry, close, CLV, grading, or trading-history records.

## Acceptance checks executed

```text
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src python -m pytest -q
................... [100%]
19 passed
```

Configuration validation:

```text
STATUS: OK
MODEL_VERSION: 0.3.0a3
```

Quota dry-run, 16 events / 6 shortlisted games / three books:

```text
Mainline cost:                       3
Opportunity full-slate max:        64
Targeted production allowance:     18
Final candidate reprice allowance: 12
Planned max:                        97
Safety reserve:                    100
```

Zero-credit 25,000-draw demo validation:

```text
BOUNDARY_AUDIT: OK
FORBIDDEN_POST_HANDOFF_ARTIFACTS: []
DATASET_A_HAS_CANDIDATE_ID: TRUE
DATASET_A_HAS_RAW_IMPLIED_PROB: TRUE
DATASET_A_HAS_NO_VIG_PROB: TRUE
DATASET_A_HAS_4_PROBABILITY_LAYERS: TRUE
DATASET_A_HAS_BUY_TO_AND_HARD_STOP: TRUE
```

## Validation boundary

A synthetic demo proves code paths, accounting, schemas, deterministic packaging, EV math, and the Python/Trading-Agent boundary. It does not prove betting alpha. Live 2026 calibration and market-trust promotion must be earned through time-safe validation, CLV, realized ROI, and completed Dataset-B audit history.
