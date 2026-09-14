# Run AITA NFL Scorer Model — 2026-09-13 Sunday Slate

From Git Bash:

```bash
cd /c/Python/AITA-NFL-SCORER-PIPELINE
source virt/Scripts/activate

nfl-scorer --root . validate-config --season 2026 --week 1

nfl-scorer --root . run \
  --season 2026 \
  --week 1 \
  --slate-date 2026-09-13 \
  --slate-label SUN_0913 \
  --draws 500000

HANDOFF=$(ls -t data/outputs/NFL_SCORER_TRADING_AGENT_HANDOFF_2026-W01_*.zip | head -1)

nfl-scorer --root . audit-handoff --zip "$HANDOFF"

echo "$HANDOFF"
```

Expected audit result:

```text
"status": "OK"
```

Then upload the printed handoff ZIP to the separate Claude Trading Agent together with `NFL_SCORER_TRADING_AGENT_USER_INPUT_PROMPT_V1.md` (the prompt is also embedded inside the handoff ZIP).

Trading Agent instruction:

```text
RUN THE NFL SCORER HANDOFF. Validate Dataset A first. Print the most-probable scorer boards by matchup, the slate-wide scorer board, the straight EV+ boards by matchup and across the slate, then build 2-leg and covered 3-leg scorer parlays only from the empirical joint-probability boards. Verify current straight prices and actual sportsbook parlay/SGP payouts before calculating current EV. Do not multiply same-game legs when an empirical joint probability exists. Do not fabricate a parlay quote.
```
