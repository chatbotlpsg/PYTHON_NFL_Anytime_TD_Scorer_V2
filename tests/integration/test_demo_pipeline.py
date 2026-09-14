from pathlib import Path
from nfl_model.config import load_config
from nfl_model.pipeline import run_demo


def test_demo_builds_handoff(tmp_path):
    source = Path(__file__).resolve().parents[2]
    # Copy only configs into temp root; output is isolated.
    import shutil
    shutil.copytree(source / "configs", tmp_path / "configs")
    for d in ["data/raw", "data/normalized", "data/features", "data/cache", "data/outputs"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    cfg = load_config(tmp_path)
    art = run_demo(cfg, 2026, 1, draws_n=4000)
    assert art.handoff_zip.exists()
    assert (art.run_dir / "README.md").exists()
    assert (art.run_dir / "NFL_MARKET_SNAPSHOT_2026-W01.csv").exists()
    assert (art.run_dir / "NFL_RECEIVING_FORECAST_BOARD_2026-W01.csv").exists()
    assert (art.run_dir / "NFL_RUSHING_FORECAST_BOARD_2026-W01.csv").exists()
    assert (art.run_dir / "NFL_PASSING_FORECAST_BOARD_2026-W01.csv").exists()
    assert (art.run_dir / "NFL_ALL_PLAYER_FORECAST_BOARD_2026-W01.csv").exists()
    assert (art.run_dir / "NFL_MARKET_LINED_PICK_BOARD_2026-W01.csv").exists()
    assert not any(p.name.lower().startswith("clv") for p in art.run_dir.iterdir())
