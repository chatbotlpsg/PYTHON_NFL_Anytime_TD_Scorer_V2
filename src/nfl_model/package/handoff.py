from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
import json

BOUNDARY_WARNING = (
    "This ZIP is a quantitative pricing handoff, not an execution record. The contained sportsbook prices are the "
    "reference market snapshots used by the Python model to calculate EV at run time. The separate Claude NFL Trading "
    "Agent is responsible for verifying current prices, deciding whether the edge remains actionable, recording actual "
    "entry, capturing the close, grading the wager, calculating CLV, and producing the trading audit."
)


def write_handoff_readme(path: Path, run_id: str) -> None:
    path.write_text(f"# AITA NFL Trading-Agent Handoff\n\n**Run:** `{run_id}`\n\n> {BOUNDARY_WARNING}\n\n"
                    "## Boundary\n\n- Python prices the claim.\n- Claude trades the claim.\n- Dataset A is included.\n- Dataset B is not produced here.\n",
                    encoding="utf-8")


def deterministic_zip(source_dir: Path, zip_path: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zf:
        for path in sorted(p for p in source_dir.rglob("*") if p.is_file()):
            rel = path.relative_to(source_dir).as_posix()
            info = ZipInfo(rel)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
    return zip_path


def boundary_manifest() -> dict:
    return {
        "PIPELINE_BOUNDARY": {"PYTHON_COMPLETE_AT_ZIP": True},
        "POST_HANDOFF_OWNER": "CLAUDE_NFL_TRADING_AGENT",
        "PYTHON_MODEL_REFERENCE_SNAPSHOT": "INCLUDED",
        "ACTUAL_ENTRY": "NOT_PYTHON_RESPONSIBILITY",
        "CLOSING_LINE_CAPTURE": "NOT_PYTHON_RESPONSIBILITY",
        "CLV": "NOT_PYTHON_RESPONSIBILITY",
        "PLAY_GRADING": "NOT_PYTHON_RESPONSIBILITY",
        "TRADING_AUDIT": "NOT_PYTHON_RESPONSIBILITY",
    }
