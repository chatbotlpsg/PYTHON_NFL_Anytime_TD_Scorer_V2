# NFL Player Props EV+ Board Protocol

EV+ boards are price-sensitive and must remain separate from forecast boards.

Input priority:

1. NFL_EV_PLAY_BOARD_*.csv
2. NFL_EDGE_LEADERBOARD_*.csv
3. NFL_OPPORTUNITY_PROP_BOARD_*.csv
4. NFL_PRODUCTION_PROP_BOARD_*.csv

Filter:

```text
ev_conservative_pct > 0
valid line
valid American odds
valid p_conservative
model_status not hard rejected
entity_status valid
convergence_status not failed
```

Columns:

```text
Rank | Date | Time | Game | Player | Team | Opp | Market | Side | Line | Book | Odds | P Cons | Fair Cons | EV Raw | EV Blend | EV Cons | Prob Edge | Buy-To | Hard Stop | Confidence | Thesis | Gate
```

Sort:

```text
EV Conservative desc → Confidence desc → Probability Edge desc → Market Trust desc → Risk Flags asc
```

Rules:

- No sportsbook price = no EV.
- No book/timestamp = non-promotable.
- Line change after handoff = different proposition.
- Do not duplicate same player/stat/side/line across books unless showing best price only.
- Do not stack highly correlated same-thesis props as independent plays.
