# AITA NFL Anytime TD Scorer v0.4.1a1

Adds explicit game-day lineup overrides for late injury/inactive situations.

## New CLI flags

- `--starter-override TEAM:POS:PLAYER` (repeatable)
- `--inactive-player TEAM:PLAYER` (repeatable)

Overrides are applied before current-season scoring/fantasy/external consensus and before Monte Carlo simulation.
For QB, the opportunity simulator now prefers the verified/overridden starter rather than simply the quarterback with the largest historical attempts prior.
Out players are removed from simulation. Single-starter positions QB/RB/TE are demoted behind a manual starter override while remaining available as backups unless separately marked inactive.

## New audit artifact

`NFL_SCORER_GAMEDAY_OVERRIDE_AUDIT_<season-week>.csv`

The run manifest also records the exact starter and inactive override strings.

## Important

Manual overrides are intentionally explicit and auditable. They should only be used from trustworthy game-day information. An expected starter should not be mislabeled as officially confirmed.
