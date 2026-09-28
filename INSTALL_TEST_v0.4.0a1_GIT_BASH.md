# Install + Test AITA NFL Scorer v0.4.0a1 — Git Bash

Assumption: `PYTHON_NFL_Anytime_TD_Scorer_V2_v0.4.0a1.zip` is saved directly in `C:\Python` and the existing model is `C:\Python\PYTHON_NFL_Anytime_TD_Scorer_V2`.

Run one command at a time:

```bash
cd /c/Python
```

```bash
ls -lh PYTHON_NFL_Anytime_TD_Scorer_V2_v0.4.0a1.zip
```

```bash
cp /c/Python/PYTHON_NFL_Anytime_TD_Scorer_V2/.env /c/Python/PYTHON_NFL_Anytime_TD_Scorer_V2/.env.pre_v0.4_backup
```

```bash
unzip -o PYTHON_NFL_Anytime_TD_Scorer_V2_v0.4.0a1.zip -d /c/Python/PYTHON_NFL_Anytime_TD_Scorer_V2
```

```bash
cp -a /c/Python/PYTHON_NFL_Anytime_TD_Scorer_V2/PYTHON_NFL_Anytime_TD_Scorer_V2_v0.4.0a1/. /c/Python/PYTHON_NFL_Anytime_TD_Scorer_V2/
```

```bash
rm -rf /c/Python/PYTHON_NFL_Anytime_TD_Scorer_V2/PYTHON_NFL_Anytime_TD_Scorer_V2_v0.4.0a1
```

```bash
cp /c/Python/PYTHON_NFL_Anytime_TD_Scorer_V2/.env.pre_v0.4_backup /c/Python/PYTHON_NFL_Anytime_TD_Scorer_V2/.env
```

```bash
cd /c/Python/PYTHON_NFL_Anytime_TD_Scorer_V2
```

```bash
source virt/Scripts/activate
```

```bash
python -m pip install -e ".[dev]"
```

```bash
pytest -q
```

Expected: `45 passed`.

```bash
nfl-scorer --root . validate-config --season 2026 --week 3
```

Expected:

```text
"status": "OK"
"model_version": "0.4.0a1"
"scoring_missing": []
"external_fantasy_missing": []
"current_season_scoring_missing": []
```
