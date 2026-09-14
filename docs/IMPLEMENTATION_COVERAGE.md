# AITA NFL 2026 Build-Spec Implementation Coverage

This file maps the architecture specification into code so future coding agents can see what owns each requirement.

## Opportunity-first build specification

| Spec area | Implementation |
|---|---|
| 0 V1 alpha hierarchy | `configs/markets.yaml`, scope regression test |
| 1–4 Source separation / nflverse backbone | `providers/nflverse/client.py`, `providers/espn/*` |
| 5 Source-of-truth matrix | provider adapters + `pipeline.ingest_football` |
| 6 Entity resolution | `ids/resolver.py`, `normalize/market.py`; ambiguous entities quarantine |
| 7 Weather | `providers/nws/client.py`, `configs/stadiums.yaml` |
| 8–16 Odds API / quota discipline | `providers/odds_api/client.py`, `quota.py`, TTL cache + ledger |
| 17 Refresh cadence | orchestration stages in `pipeline.py`; snapshots are append-only |
| 18 Week 1 uncertainty | role certainty + Week 1 simulation multiplier |
| 19 Canonical tables | normalized CSVs, feature state outputs, required handoff boards |
| 20 Team state | `features/team.py` time-decayed offense + defense state |
| 21 QB state | `features/qb.py` |
| 22 Coaching state | `features/coaching.py` foundation |
| 23 Game state | `simulation/game_state.py` possession/drive score evolution + per-draw plays/script |
| 24 Team plays | `models/plays.py` |
| 25 Pass/run | `models/pass_run.py` |
| 26 QB attempts | joint simulator, finite pass-play accounting |
| 27 RB carries | `models/rb_opportunity.py`, finite team-rush allocation |
| 28–30 Routes / targets / catches | route-first joint finite route/target pool in `simulation/monte_carlo.py` |
| 31 Receptions | direct draw distribution from joint target/catch process |
| 32 Production after opportunity | receiving/rushing/passing yards derived after volume |
| 33 Joint simulation | one team simulation state drives all player metrics |
| 34 Monte Carlo | configurable 25k–500k, candidate-line convergence gate/report |
| 35 Parameter uncertainty | team play, pass rate, role shares, route share, catch/efficiency draws |
| 36 Four probability layers | raw, calibrated, blended, conservative in pricing engine |
| 37–38 Market anchoring / trust | mainline total/spread anchor in `simulation/game_state.py`; prop blend in `models/calibration.py`; config trust weights |
| 39 EV | `pricing/ev.py`, four EV layers |
| 40 No-vig | `pricing/novig.py`, same-book/line two-way normalization |
| 41 Extreme disagreement | `pricing/engine.py` quarantine |
| 42–45 Edge type / opportunity vs production | boards + thesis inference; role/volume/game-script/efficiency labels |
| 46 Thesis optimizer | `portfolio/thesis_optimizer.py` |
| 47 Cross-market consistency | simulation reconciliation tests and audit gate |
| 48 Directional diagnostics | side preserved on every board / future Dataset B calibration join |
| 49 Role certainty | player-map role certainty score + current-state degradation gate + current-state degradation gate |
| 50 Data gates | `audit/validation.py`, entity quarantine, pricing missing-data statuses |
| 51 Provider health | handoff `NFL_PROVIDER_HEALTH_*.json` |
| 52 Weekly orchestration | `pipeline.run_live` |
| 53 CLI | `cli.py` |
| 54 Config not hardcoding | YAML configs + `ODDS_API_KEY` env |
| 55 Reproducibility | run ID, version, config hash, seed, simulation count, git commit |
| 56 Immutable raw | snapshot helper + append-only naming |
| 57 Tests | unit/integration/regression suites; no standard test calls live APIs |
| 58 Boards | required game/opportunity/production/EV/leaderboard/rejection/correlation/thesis outputs |
| 59 Initial EV floors | config |
| 60 Confidence | role/model/freshness fields |
| 61 Conservative EV | `pricing/conservative.py` |
| 62 Handoff ZIP | `package/handoff.py`, `pipeline.build_handoff` |
| 63–64 Python/Claude boundary | hardcoded manifest + tests |
| 65–71 Postgame/calibration | intentionally not production-owned; research-only import namespace |
| 72 Failure behavior | provider exceptions and degraded health flags |
| 73 Security | env key only, `.env` ignored, keys never placed in output |
| 74 Performance | numpy vectorized Monte Carlo, Polars/nflreadpy historical cache |
| 75 Repository layout | implemented |
| 76 Development layers | repository modules follow the prescribed layers |
| 77 Scope control | approved-market regression test |
| 78 Acceptance criteria | tests + validation command + demo handoff |
| 79 Architecture lock | README + boundary manifest |
| 80 Provider verification | adapters follow current provider documentation patterns |
| 81 Build in layers | package structure enforces separation |

## Python vs Trading-Agent boundary specification

| Boundary requirement | Implementation |
|---|---|
| Python stops at ZIP | `build_handoff()` returns artifact; no post-handoff callback |
| Dataset A | `NFL_MARKET_SNAPSHOT_*.csv` |
| Dataset B | not created; only research importer exists |
| BUY-TO / hard stop | `pricing/buy_to.py` |
| Claude cannot rewrite probabilities | handoff README / immutable run manifest |
| Football-state change requires rerun | README operating rule |
| Market-only move does not require rerun | BUY-TO/hard-stop execution contract |
| No continuous polling | no watcher/loop module; Odds calls only explicit production stages |
| No Python close/CLV/grading | boundary manifest + regression test |
| Immutable candidate IDs | board candidate hash includes run/event/player/market/side/line/book |
| Immutable handoffs | run directory creation refuses overwrite; deterministic ZIP timestamps |
| Dataset B future calibration | `calibration/import_trading_audit.py` reads completed audits by immutable join keys |
