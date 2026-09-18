from pathlib import Path
import shutil
from zipfile import ZipFile

from nfl_model.config import load_config
from nfl_model.scorer_pipeline import run_scorer_demo


def test_scorer_demo_handoff_contains_role_first_boards(tmp_path):
    source=Path(__file__).resolve().parents[2]
    shutil.copytree(source/"configs",tmp_path/"configs")
    agent=tmp_path/"NFL Scorer Agent"; agent.mkdir()
    src_prompt=source/"NFL Scorer Agent"/"NFL_SCORER_TRADING_AGENT_USER_INPUT_PROMPT_V1.md"
    if src_prompt.exists(): shutil.copy2(src_prompt,agent/src_prompt.name)
    for d in ["data/raw","data/normalized","data/features","data/cache","data/outputs"]:
        (tmp_path/d).mkdir(parents=True,exist_ok=True)
    cfg=load_config(tmp_path)
    art=run_scorer_demo(cfg,2026,1,draws_n=3000)
    with ZipFile(art.handoff_zip) as zf:
        names=set(zf.namelist())
    for frag in [
        "NFL_SCORER_QB_SLATE_PROBABILITY_BOARD_2026-W01.csv",
        "NFL_SCORER_RB_SLATE_PROBABILITY_BOARD_2026-W01.csv",
        "NFL_SCORER_WR_SLATE_PROBABILITY_BOARD_2026-W01.csv",
        "NFL_SCORER_CURRENT_ROSTER_VALIDATION_BOARD_2026-W01.csv",
        "NFL_SCORER_DEFENSIVE_TD_VULNERABILITY_BOARD_2026-W01.csv",
    ]:
        assert frag in names
