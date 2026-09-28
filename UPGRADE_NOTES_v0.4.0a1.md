# AITA NFL Scorer v0.4.0a1 — Week 3 Upgrade Notes

## Purpose

This release addresses two false-positive patterns in scorer recommendations:

1. backups/no-name players reaching recommendation boards because historical opportunity or fantasy projections looked attractive;
2. star players on very weak/low-scoring offenses being ranked too aggressively without enough current-season scoring evidence.

## Changes

### Verified-starter-only primary/EV gate

- QB1, RB1, WR starter slot(s), and TE1 require ESPN offensive depth rank `1`.
- The player must also pass the current ESPN roster and availability gates.
- Fantasy projections cannot create a primary-role override.
- A depth-rank 2+ player may remain in Monte Carlo touchdown allocation but cannot be promoted to the primary/actionable EV board.
- Multiple ESPN starting WR slots may each have rank `1`; this avoids incorrectly treating a real starting WR2 in three-WR personnel as a bench player merely because the team has several starters.

### 2026 pregame scoring-form ingestion

- Current season is now loaded alongside 2023–2025 history.
- An anti-leakage filter removes the requested week and all future weeks before feature construction.
- Week 3 therefore uses only completed Week 1–2 2026 information.

### Team offense strength

Pregame team context now includes:

- current-season team points;
- points/game;
- offensive rushing + receiving TDs;
- offensive TD/game;
- summed skill-player PPR/game when available;
- league-relative offense score;
- bounded offense multiplier (default 0.88–1.10);
- offense tier.

The team multiplier enters the pre-market score prior. Market totals/spreads may still move the final game environment because current market information should not be ignored.

### Player TD production

The model records each player's current-season:

- games;
- rushing TDs;
- receiving TDs;
- anytime-scorer TD total;
- scorer TD/game;
- Bayesian-shrunk TD multiplier;
- TD form status.

For QBs, only rushing TDs count toward anytime-TD scorer production.

### Weak-offense rejection rule

After at least two current-season games, a verified starter is blocked from the sharp/EV board when:

- team offense tier = `VERY_WEAK`; and
- player current-season scorer TDs = 0.

This is a rejection/suppression rule, not deletion from the simulation universe.

### Handoff transparency

New files:

- `NFL_SCORER_CURRENT_SEASON_TEAM_OFFENSE_<tag>.csv`
- `NFL_SCORER_CURRENT_SEASON_PLAYER_TD_FORM_<tag>.csv`

The scorer/EV boards also expose starter status, depth rank, current-season TD form, team PPG, team offense tier and suppression flags.

## Validation

- Unit/regression tests: `45 passed`
- Week 3 config validation: `OK`
- Offline 50K demo handoff: audit `OK`
- Demo handoff: `49` files; no missing or forbidden artifacts.

## Operational limitation

A successful run cannot create information that a live provider has not published. Game-day inactive/starter certainty still depends on the live ESPN roster/depth/injury feeds available at run time. The model fails closed for primary starter promotion when depth verification is missing and surfaces provider health for audit.
