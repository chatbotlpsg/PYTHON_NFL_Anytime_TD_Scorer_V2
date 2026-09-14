# NFL Anytime TD Scorer SGP Price Verification Protocol

## Required Before Declaring Parlay +EV

For every 2-leg or 3-leg parlay candidate, obtain:

```text
sportsbook
parlay_or_sgp_price
quote_timestamp
legs exactly as quoted
whether same-game or cross-game
stake constraints if supplied
```

## EV Formula

```text
EV per $1 = p_joint × profit_per_dollar(live_parlay_odds) - (1 - p_joint)
EV% = 100 × EV per $1
```

## Final Decision

```text
PLAY — executable quote clears EV threshold and all gates
WATCH / NEEDS PRICE — model math attractive but no quote yet
PASS — quote fails EV or hard gate
QUARANTINE — identity, data, or market mismatch
```

Do not fabricate quotes.
