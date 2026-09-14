# NFL Anytime TD Scorer Commands Playbook

## /print-nfl-scorer-boards

Read the attached `NFL_SCORER_TRADING_AGENT_HANDOFF_*.zip` and print the full board sequence:

```text
handoff check
matchup scorer boards
full-slate probability board
matchup EV+ boards
full-slate EV+ board
sharp scorer board
parlay analysis
final trading board
```

## /qc-nfl-scorer-handoff

Validate manifest, metadata, slate identity, market identity, probability boards, EV boards, joint pair/triple boards, parlay board, market snapshot, provider health, data lineage, and required columns.

## /write-nfl-scorer-matchups

Print only the matchup-level most probable scorer boards, one game at a time.

## /rank-nfl-scorer-ev

Print only the positive-EV straight anytime-TD scorer board ranked by conservative EV%, then confidence, then model probability.

## /review-nfl-scorer-sharp-board

Print the sharp scorer board using probability, conservative EV, confidence, price quality, role certainty, convergence, market disagreement, and data health.

## /price-nfl-scorer-parlays

Use empirical joint pair/triple probabilities and require an executable sportsbook parlay/SGP payout before declaring parlay EV.

## /capture-nfl-scorer-close

Record close-proxy prices for selected straight scorer plays and any quoted parlay/SGP positions. Never overwrite entry prices.

## /grade-nfl-scorer-week

Grade final scorer outcomes, EV quality, parlay quotes, close movement, CLV, and result/P&L using Dataset B.

## /build-nfl-scorer-recap

Create the permanent weekly scorer audit recap for future calibration research.
