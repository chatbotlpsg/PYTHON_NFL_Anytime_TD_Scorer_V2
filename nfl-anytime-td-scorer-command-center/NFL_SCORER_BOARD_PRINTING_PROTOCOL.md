# NFL Anytime TD Scorer Board Printing Protocol

## Board Sequence

```text
1. Handoff check
2. Matchup most-probable scorer boards
3. Full-slate most-probable scorer board
4. Matchup EV+ boards
5. Full-slate EV+ board
6. Sharp scorer board
7. Parlay analysis
8. Final trading board
```

## Probability Board Rule

The most-probable scorer board is sorted by model probability only. It is not a betting recommendation board.

## EV Board Rule

The EV board is sorted by conservative EV%. It requires actual price identity. If no current price is supplied, mark the frozen price as reference-only.

## Sharp Board Rule

The sharp board balances:

```text
model probability
conservative EV
confidence
price quality
role certainty
data freshness
availability
convergence
market disagreement
reconciliation status
```

## Final Board Rule

Separate:

```text
A. Most probable scorers
B. Best straight +EV scorer plays
C. Sharpest risk-adjusted scorer plays
D. Best 2-leg parlay candidates
E. Best 3-leg parlay candidates
F. Passes / rejected positions
```
