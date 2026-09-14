# Provider Verification Snapshot — 2026-09-01

Before this build was packaged, the current public documentation was rechecked for the interfaces used by the model.

- nflreadpy documents loaders for PBP, player/team stats, schedules, rosters, snap counts, participation, injuries, depth charts, Next Gen data and PFR advanced stats.
- ESPN NFL site JSON resources remain available for scoreboard, rosters, depth charts and injuries, but they are treated as unsupported/community-documented interfaces and isolated behind an adapter.
- NWS still uses `/points/{lat},{lon}` to discover `forecastHourly`.
- The Odds API V4 documents `/sports` and `/events` as quota-free, standard odds cost as markets × regions, event odds cost as unique markets returned × region-equivalents, explicit bookmakers in groups of ten, and quota headers `x-requests-remaining`, `x-requests-used`, `x-requests-last`.
- The Odds API current market catalog includes the seven V1 player market keys used in this package.

Re-verify provider contracts if a live fetch begins failing; do not scatter provider schema assumptions outside adapters.
