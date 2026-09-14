from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from nfl_model.utils import ensure_parent, sha256_bytes, stable_json_dumps, utc_now_iso


def save_json_snapshot(base_dir: str | Path, provider: str, season: int, week: int, label: str, payload: Any) -> dict:
    stamp = utc_now_iso().replace(":", "").replace("-", "")
    raw = stable_json_dumps(payload).encode("utf-8")
    digest = sha256_bytes(raw)
    path = Path(base_dir) / provider / str(season) / f"week_{week:02d}" / f"{label}_{stamp}_{digest[:12]}.json"
    ensure_parent(path)
    path.write_bytes(raw)
    return {"path": str(path), "sha256": digest, "captured_at": utc_now_iso()}


def append_jsonl(path: str | Path, row: dict) -> None:
    p = ensure_parent(path)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
