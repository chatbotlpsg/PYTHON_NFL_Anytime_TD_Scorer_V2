# AITA NFL Scorer — Git Bash Commands

```bash
cd /c/Python
unzip AITA-NFL-SCORER-PIPELINE.zip
cd AITA-NFL-SCORER-PIPELINE
python -m venv virt
source virt/Scripts/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
nfl-scorer --root . validate-config --season 2026 --week 1
```

9/13/2026 production slate:

```bash
nfl-scorer --root . run --season 2026 --week 1 --slate-date 2026-09-13 --slate-label SUN_0913 --draws 500000
HANDOFF=$(ls -t data/outputs/NFL_SCORER_TRADING_AGENT_HANDOFF_2026-W01_*.zip | head -1)
nfl-scorer --root . audit-handoff --zip "$HANDOFF"
echo "$HANDOFF"
```
