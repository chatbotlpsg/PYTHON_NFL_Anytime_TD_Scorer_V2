# Layer-1 → Opportunity-First V1 Full-Build Hardening

Build version: `0.3.0a3`

This package retains the Layer-1 repository structure but hardens it against the controlling 2026 NFL opportunity-first and Python/Trading-Agent boundary specifications.

## Material implementation upgrades

- Replaced final-score-only behavior with a joint possession/drive-state game simulator that evolves scores, possessions, play counts, and lead/trail pass pressure together.
- Player simulation consumes the game engine's per-draw offensive play counts rather than generating an unrelated second team-volume surface.
- Enforced the opportunity causal order: routes are drawn before receiver targets; targets cannot exceed routes; receptions cannot exceed targets; modeled receptions cannot exceed QB completions.
- QB attempts reconcile to pass plays after sacks/scrambles; RB carries reconcile to the finite team-rush pool.
- Receiving production is generated after opportunity using caught-air-yard + YAC components with heavy-tail explosive outcomes instead of a single yards-per-reception multiplier.
- Weather is converted into bounded football effects, with wind receiving the strongest weight; dome/covered games are zero-impact.
- Week-1 uncertainty is applied only to Week 1 instead of globally.
- Current ESPN roster/depth/injury bundle failures mark affected teams as degraded and block prop rows rather than silently pricing from stale current state.
- V1 `player_rush_yds` scope is RB-only, matching the controlling market hierarchy.
- Odds rows preserve raw implied probability as well as same-book/line no-vig probability.
- Stale market timestamps and entity-quarantined rows are blocked before EV ranking.
- BUY-TO and HARD-STOP EV margins come from configuration rather than hidden literals.
- Dataset A carries immutable `candidate_id` values for exact later Dataset-B joins.
- Candidate-line Monte Carlo convergence is written to `NFL_CONVERGENCE_REPORT_*`; unstable production candidates are quarantined rather than promoted.
- Probability transformation attribution separates raw-vs-market, calibration, market blend, and uncertainty haircut. It does not fake independent causal football contributions.
- Calibration and market-trust fields explicitly identify initial priors until walk-forward / Dataset-B evidence exists; the package does not fabricate historical calibration evidence.
- The production boundary remains locked: no close watcher, entry tracker, grading engine, CLV producer, or Dataset-B writer exists inside Python production.

## What live data must still prove

The software implements the architecture, but a 2026 live edge cannot be manufactured in source code. Market trust, calibration transforms, EV floors, coordinator-change priors, and confidence policy must be updated from time-safe historical validation and completed Trading-Agent audit history as sample size becomes sufficient.
