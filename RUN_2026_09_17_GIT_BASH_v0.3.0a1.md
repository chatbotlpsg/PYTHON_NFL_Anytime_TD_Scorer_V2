# AITA NFL Scorer v0.3.0a1 — 9/17/2026 TNF Runbook

Run from Git Bash.

## 1. Go to the existing model

```bash
cd /c/Python/PYTHON_NFL_Anytime_TD_Scorer_V2
source virt/Scripts/activate
```

## 2. Back up `.env`

```bash
cp .env .env.pre_v0.3_backup
```

## 3. Confirm the new release ZIP exists in `C:\Python`

```bash
ls -lh ../PYTHON_NFL_Anytime_TD_Scorer_V2_v0.3.0a1.zip
```

## 4. Unzip directly into the current project

The release ZIP contains a top-level `PYTHON_NFL_Anytime_TD_Scorer_V2_v0.3.0a1/` directory.

```bash
unzip -o ../PYTHON_NFL_Anytime_TD_Scorer_V2_v0.3.0a1.zip -d .

cp -a PYTHON_NFL_Anytime_TD_Scorer_V2_v0.3.0a1/. .

rm -rf PYTHON_NFL_Anytime_TD_Scorer_V2_v0.3.0a1

cp .env.pre_v0.3_backup .env
```

## 5. Add/update the public-fantasy User-Agent

Open `.env`:

```bash
nano .env
```

Recommended:

```env
PUBLIC_FANTASY_USER_AGENT=AITA-NFL-SCORER/0.3.0a1 (contact: YOUR_REAL_EMAIL)
```

Yahoo fields may remain blank.

## 6. Install upgraded package

```bash
python -m pip install -e ".[dev]"
```

## 7. Run tests

```bash
pytest -q
```

Expected release result:

```text
40 passed
```

## 8. Validate configuration

```bash
nfl-scorer --root . validate-config \
  --season 2026 \
  --week 2
```

Expected:

```text
"status": "OK"
"model_version": "0.3.0a1"
```

## 9. Run the 9/17 TNF scorer model — 500,000 draws

```bash
nfl-scorer --root . run \
  --season 2026 \
  --week 2 \
  --slate-date 2026-09-17 \
  --slate-label TNF_0917 \
  --draws 500000
```

## 10. Capture only the new v0.3 TNF handoff

```bash
HANDOFF=$(ls -t data/outputs/NFL_SCORER_TRADING_AGENT_HANDOFF_2026-W02_*TNF_0917.zip | head -1)

echo "$HANDOFF"
```

## 11. Audit it

```bash
nfl-scorer --root . audit-handoff \
  --zip "$HANDOFF"
```

Expected:

```text
"status": "OK"
"missing": []
"forbidden": []
```

## 12. Print the Windows path

```bash
cygpath -aw "$HANDOFF"
```

That ZIP is what you give the separate Claude Trading Agent.

## 13. Confirm the new public providers actually participated

```bash
RUN_DIR=$(ls -td data/outputs/NFL-SCORER-2026-W02-*TNF_0917 | head -1)

cat "$RUN_DIR/NFL_SCORER_PROVIDER_HEALTH_2026-W02.json"
```

Look for provider statuses for:

```text
fftoday
fantasypros
pfr_fantasy
```

Then inspect the new normalized handoff boards:

```bash
head -20 "$RUN_DIR/NFL_SCORER_FFTODAY_WEEKLY_PROJECTIONS_2026-W02.csv"
head -20 "$RUN_DIR/NFL_SCORER_FANTASYPROS_WEEKLY_RANKINGS_2026-W02.csv"
head -20 "$RUN_DIR/NFL_SCORER_PFR_CURRENT_FANTASY_ACTUALS_2026-W02.csv"
head -20 "$RUN_DIR/NFL_SCORER_EXTERNAL_FANTASY_CONSENSUS_BOARD_2026-W02.csv"
```

If a public provider is blocked or unavailable, it should show `DEGRADED` and the model should continue without fabricating data.
