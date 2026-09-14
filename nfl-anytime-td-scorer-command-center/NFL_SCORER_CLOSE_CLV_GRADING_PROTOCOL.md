# NFL Anytime TD Scorer Close / CLV / Grading Protocol

## Dataset B Ownership

The Trading Agent owns:

```text
entry price
close-proxy price
result
settlement
P&L
CLV / price movement
recap
```

## Close Capture

Capture only timestamped evidence. Do not overwrite frozen reference prices.

Suggested fields:

```text
run_id
season
week
slate_date
player
team
matchup
market
book
entry_price
entry_timestamp
closing_price
closing_timestamp
close_quality
source
```

## Grading

Grade separately:

```text
probability board
EV board
sharp board
parlay math board
execution price
closing-price movement
result
```

A winning bet is not automatically a good model read. A losing bet is not automatically a bad model read.
