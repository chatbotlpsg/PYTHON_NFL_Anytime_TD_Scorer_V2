# AITA NFL Touchdown Scorer Probability + EV Pipeline v0.1.0a1

Specialized NFL anytime-touchdown scorer pipeline built on the attached `nfl-player-prop-model` foundation.

It reuses the same football data inputs, generates market-blind scorer probabilities, ranks the most probable scorers by matchup and across the entire selected slate, prices `player_anytime_td`, produces conservative EV+ boards, and exports empirical 2-leg/3-leg joint scorer probabilities for a separate Trading Agent to construct and price parlays mathematically.

## Core boundary

**Python prices the scorer claims. The Trading Agent trades them.**

The Python handoff contains reference sportsbook prices and mathematical parlay fair probabilities. The Trading Agent must verify live prices and obtain the live SGP/parlay payout before claiming a parlay is +EV.

## Install — Git Bash / Windows

```bash
cd /c/Python
unzip AITA-NFL-SCORER-PIPELINE.zip
cd AITA-NFL-SCORER-PIPELINE

python -m venv virt
source virt/Scripts/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"

cp .env.example .env
# Edit .env and set ODDS_API_KEY=...
```

## Validate

```bash
nfl-scorer --root . validate-config --season 2026 --week 1
pytest -q
```

## Offline proof

```bash
nfl-scorer --root . demo --season 2026 --week 1 --draws 50000
```

## Production — Sunday 2026-09-13 slate

```bash
nfl-scorer --root . run \
  --season 2026 \
  --week 1 \
  --slate-date 2026-09-13 \
  --slate-label SUN_0913 \
  --draws 500000
```

The date filter keeps all NFL games whose kickoff date is September 13 in NFL Eastern time and excludes the September 9/10 games and Monday September 14 game.

Audit the newest handoff:

```bash
HANDOFF=$(ls -t data/outputs/NFL_SCORER_TRADING_AGENT_HANDOFF_2026-W01_*.zip | head -1)
nfl-scorer --root . audit-handoff --zip "$HANDOFF"
echo "$HANDOFF"
```

If the console-script entry point is unavailable, replace `nfl-scorer` with:

```bash
python -m nfl_model.scorer_cli
```

## Principal handoff files

- `MATCHUPS/SCORERS_<AWAY>_AT_<HOME>.csv`
- `MATCHUPS/EV_<AWAY>_AT_<HOME>.csv`
- `NFL_SCORER_MATCHUP_PROBABILITY_BOARD_*.csv`
- `NFL_SCORER_SLATE_PROBABILITY_BOARD_*.csv`
- `NFL_SCORER_MATCHUP_EV_PLAY_BOARD_*.csv`
- `NFL_SCORER_SLATE_EV_PLAY_BOARD_*.csv`
- `NFL_SCORER_MARKET_SNAPSHOT_*.csv`
- `NFL_SCORER_JOINT_PAIR_BOARD_*.csv`
- `NFL_SCORER_JOINT_TRIPLE_BOARD_*.csv`
- `NFL_SCORER_PARLAY_MATH_CANDIDATE_BOARD_*.csv`
- `TRADING_AGENT_PARLAY_PROTOCOL.md`

## EV rules

Straight anytime-TD EV uses conservative probability and the exact frozen book quote. The default straight scorer floor is +6% EV.

Parlay candidates are probability/fair-price outputs only until the Trading Agent sees an executable parlay quote. The default downstream parlay EV floor is +8%.
