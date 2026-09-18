# AITA NFL Scorer v0.2.0a1 — 2026-09-14 Git Bash Runbook

```bash
cd /c/Python/PYTHON_NFL_Anytime_TD_Scorer_V2
source virt/Scripts/activate

python -m pip install -e ".[dev]"
pytest -q

nfl-scorer --root . validate-config \
  --season 2026 \
  --week 1

nfl-scorer --root . run \
  --season 2026 \
  --week 1 \
  --slate-date 2026-09-14 \
  --slate-label MNF_0914 \
  --draws 500000

HANDOFF=$(ls -t data/outputs/NFL_SCORER_TRADING_AGENT_HANDOFF_2026-W01_*.zip | head -1)

echo "$HANDOFF"

nfl-scorer --root . audit-handoff \
  --zip "$HANDOFF"

cygpath -w "$HANDOFF"
```

The `NFL_SCORER_TRADING_AGENT_HANDOFF_...zip` produced by the final commands is the artifact for the separate Trading Agent. The source-code release ZIP is not the Trading-Agent handoff.
