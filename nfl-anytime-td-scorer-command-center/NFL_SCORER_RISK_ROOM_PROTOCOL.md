# NFL Anytime TD Scorer Risk Room Protocol

## Sharp Scorer Criteria

A scorer can rank highly in the sharp board only when multiple pillars agree:

```text
strong model probability
positive conservative EV
confidence support
role certainty
availability clean
market price valid
convergence clean
reconciliation clean
no stale-data block
```

## Downgrade Conditions

Downgrade or block when any of these are present:

```text
price missing
price stale
hard-stop failed
low role certainty
availability concern
entity unresolved
market mismatch
non-converged simulation
large unexplained market disagreement
insufficient EV
```

## Exposure

Do not treat correlated scorer positions as independent. Use joint/correlation boards for pair/triple exposures.
