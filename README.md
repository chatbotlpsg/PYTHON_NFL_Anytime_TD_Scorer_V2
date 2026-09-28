# AITA NFL Touchdown Scorer Probability + EV Pipeline v0.4.0a1

Specialized NFL anytime-touchdown scorer pipeline built for the AITA Sports Model workflow.

Version **0.4.0a1** adds two production safeguards for Week 3 and beyond:

1. **Verified-starter-only recommendation gating** — the primary/EV boards require the player to be on the current ESPN roster, available, present on the offensive depth chart, and depth rank 1 at QB/RB/WR/TE. Fantasy projections cannot promote a backup. Multiple starting WR slots may each be rank 1.
2. **Current-season scoring-strength context** — the model ingests only completed prior weeks from the current season, measures team points per game, offensive TDs per game, skill-position PPR production when available, and each player's current-season anytime-TD production. Weak offenses and zero-TD players receive bounded penalties/suppression rather than being blindly promoted because of name recognition or long odds.

## Production order

1. ESPN current roster — hard identity/eligibility gate.
2. ESPN current injuries/availability and offensive depth chart.
3. Verified starter gate (depth rank 1 at QB/RB/WR/TE).
4. nflverse historical + current-season pregame-only PBP/player/snap/schedule data.
5. Current-season team offense: PPG, offensive TD/game, skill-position PPR/game.
6. Current-season player TD form: rushing/receiving scorer TDs and TD/game, Bayesian-shrunk.
7. ESPN team leaders and fantasy context.
8. FFToday/FantasyPros/PFR bounded external consensus; Yahoo remains optional.
9. Defensive TD vulnerability, TD style, QB goal-line cannibalization.
10. 500,000-draw market-blind Monte Carlo scorer simulation.
11. Starter-only probability/primary boards and weak-offense suppression flags.
12. Odds API anytime-TD prices and EV gating.
13. Empirical pair/triple joint probabilities.
14. Frozen Trading-Agent handoff ZIP.

## Starter doctrine

Backups are not deleted from the football simulation. They may still absorb realistic touchdown probability in the Monte Carlo so team scoring is not artificially forced onto starters. However, a backup/deep player cannot be promoted to the primary scorer or actionable EV board.

Primary recommendation eligibility requires:

- current ESPN roster verification;
- roster active flag;
- injury/availability gate pass;
- offensive depth-chart verification;
- depth rank `1` at QB/RB/WR/TE.

Fantasy data and third-party projections are corroboration only and cannot override this gate.

## Current-season scoring form

For a requested Week `W`, only current-season rows with `week < W` are used. This prevents same-week/future result leakage.

Team scoring strength uses available pregame fields:

- actual team points/game — 55%;
- offensive rushing + receiving TD/game — 35%;
- summed skill-player PPR/game — 10% when available.

The league-relative result is converted into a bounded team offense multiplier of **0.88–1.10** and offense tiers `VERY_WEAK`, `WEAK`, `AVERAGE`, `STRONG`, `ELITE`.

Player current-season anytime-TD production is Bayesian-shrunk toward the position prior and capped to **0.88–1.10**. For QBs, scorer TDs mean rushing TDs only; passing TDs are not anytime-touchdown scorer events.

A verified starter on a `VERY_WEAK` offense with zero current-season scorer TDs after the configured minimum sample (default two games) remains in audit/simulation data but is blocked from the sharp/EV board.

## External consensus

FFToday, FantasyPros and PFR remain challenger/corroboration inputs. Their combined influence remains capped and cannot bypass the starter gate or directly replace Monte Carlo probability.

## Key v0.4 handoff artifacts

In addition to the existing probability/EV/context files, the handoff contains:

- `NFL_SCORER_CURRENT_SEASON_TEAM_OFFENSE_<tag>.csv`
- `NFL_SCORER_CURRENT_SEASON_PLAYER_TD_FORM_<tag>.csv`

These expose the current-season evidence used to boost, penalize or suppress players.

## Validation

Release regression target: **45 tests passed**.

Run:

```bash
pytest -q
nfl-scorer --root . validate-config --season 2026 --week 3
```

Expected model version: `0.4.0a1`.
