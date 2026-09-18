# AITA NFL Touchdown Scorer Probability + EV Pipeline v0.3.0a1

Specialized NFL anytime-touchdown scorer pipeline built on the AITA `nfl-player-prop-model` foundation.

Version **0.3.0a1** adds a public external-consensus layer while preserving the hard separation between football probability and sportsbook price.

## Production order

1. ESPN current roster — **hard eligibility gate**.
2. ESPN injury/depth/team-leader context.
3. nflverse current/historical opportunity, red-zone work, TD history, PBP and snap context.
4. ESPN fantasy weekly context.
5. **FFToday public weekly projections** — projected rush/receive TD components, opportunity and fantasy points.
6. **FantasyPros public weekly consensus** — position rank, best/worst/average rank and expert dispersion.
7. **Pro-Football-Reference public season actuals** — current production, fantasy points and position rank.
8. Optional Yahoo Fantasy OAuth context — no longer required.
9. Defensive TD vulnerability + player TD style + QB goal-line cannibalization.
10. 500,000-draw market-blind Monte Carlo scorer simulation.
11. Probability-first QB/RB/WR/TE, matchup and slate boards.
12. Odds API `player_anytime_td` pricing.
13. Conservative straight EV gate.
14. Empirical pair/triple joint scorer probability boards.
15. Immutable Trading-Agent handoff ZIP.

## External consensus doctrine

The public third-party sources are a **challenger / corroboration / rejection layer**, not a replacement probability model.

Default weights:

```yaml
external_fantasy:
  weights:
    fftoday: 0.45
    fantasypros: 0.35
    pfr: 0.20
  multiplier_min: 0.90
  multiplier_max: 1.10
  minimum_sources_for_rejection: 2
```

The external consensus multiplier is bounded to **0.90–1.10**.

It can modestly sharpen or haircut player TD allocation, but it cannot:

- put a non-roster player back into the model;
- bypass injury/availability gates;
- transform a deep lottery player into a primary scorer by itself;
- overwrite the Monte Carlo probability with a fantasy projection;
- use sportsbook odds to change the probability.

If at least two independent public external sources materially disagree with a player's model role, the player can be marked:

```text
EXTERNAL_DISAGREEMENT
```

and becomes:

```text
sharp_board_eligible = False
```

Any otherwise attractive straight EV row is then rejected as:

```text
EXTERNAL_CONSENSUS_DISAGREEMENT
```

This is specifically designed to stop long-price tail players from appearing as sharp plays simply because +1000/+1500 creates a flashy nominal EV number.

## FFToday treatment

FFToday projected TD values are treated as expected TD counts, not direct scoring probabilities.

For comparison only, the pipeline derives:

```text
P(at least one TD) = 1 - exp(-lambda)
```

For quarterbacks, only projected **rushing TD** contributes to Anytime-TD scorer signal. Passing TDs do not credit the passer.

## FantasyPros treatment

The model stores:

- position rank;
- best rank;
- worst rank;
- average rank;
- expert rank standard deviation.

Expert dispersion reduces confidence in the FantasyPros component instead of being ignored.

## PFR treatment

The model stores realized current-season production including available:

- rushing/receiving TDs;
- targets/receptions;
- fantasy points;
- PPR/DraftKings/FanDuel fantasy points;
- position rank.

PFR is an actual-form corroboration layer, not a projection source.

## Public scraping rules

The pipeline only requests ordinary public pages. It intentionally does **not** implement:

- login bypass;
- paywall bypass;
- CAPTCHA bypass;
- anti-bot circumvention;
- hidden/private API access.

If a site blocks normal public HTTP access, the provider becomes `DEGRADED` and the model continues without that source.

Every provider is cached and timestamped. Stale cache is not silently reused after its allowed age if refresh fails.

Defaults:

```yaml
external_fantasy:
  cache_ttl_hours: 6
  projection_max_age_hours: 24
  near_kickoff_window_hours: 24
  near_kickoff_max_age_hours: 12
```

## New handoff boards

v0.3 adds:

- `NFL_SCORER_FFTODAY_WEEKLY_PROJECTIONS_*.csv`
- `NFL_SCORER_FANTASYPROS_WEEKLY_RANKINGS_*.csv`
- `NFL_SCORER_PFR_CURRENT_FANTASY_ACTUALS_*.csv`
- `NFL_SCORER_EXTERNAL_FANTASY_CONSENSUS_BOARD_*.csv`

The existing current-roster, probability, matchup, EV, TD-vulnerability, TD-style, QB goal-line and joint-probability boards remain.

## `.env`

Required:

```env
ODDS_API_KEY=YOUR_KEY
```

Recommended identification headers:

```env
NWS_USER_AGENT=AITA-NFL-SCORER/0.3.0a1 (contact: you@example.com)
PUBLIC_FANTASY_USER_AGENT=AITA-NFL-SCORER/0.3.0a1 (contact: you@example.com)
```

Yahoo remains optional:

```env
YAHOO_FANTASY_ACCESS_TOKEN=
YAHOO_FANTASY_LEAGUE_KEY=
```

## 9/17/2026 production run

```bash
nfl-scorer --root . validate-config \
  --season 2026 \
  --week 2

nfl-scorer --root . run \
  --season 2026 \
  --week 2 \
  --slate-date 2026-09-17 \
  --slate-label TNF_0917 \
  --draws 500000
```

Then:

```bash
HANDOFF=$(ls -t data/outputs/NFL_SCORER_TRADING_AGENT_HANDOFF_2026-W02_*TNF_0917.zip | head -1)

nfl-scorer --root . audit-handoff \
  --zip "$HANDOFF"

echo "$HANDOFF"
cygpath -aw "$HANDOFF"
```

The resulting `NFL_SCORER_TRADING_AGENT_HANDOFF...zip` is the file for the separate Claude Trading Agent.
