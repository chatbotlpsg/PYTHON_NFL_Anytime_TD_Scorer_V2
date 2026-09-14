from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
import json
import yaml


@dataclass(frozen=True)
class AppConfig:
    root: Path
    data: dict[str, Any]
    markets: dict[str, Any]
    stadiums: dict[str, Any]

    def get(self, *keys: str, default: Any = None) -> Any:
        cur: Any = self.data
        for key in keys:
            if not isinstance(cur, dict) or key not in cur:
                return default
            cur = cur[key]
        return cur

    @property
    def config_hash(self) -> str:
        payload = json.dumps(
            {"data": self.data, "markets": self.markets, "stadiums": self.stadiums},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(payload).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(root: str | Path | None = None) -> AppConfig:
    root_path = Path(root or Path.cwd()).resolve()
    return AppConfig(
        root=root_path,
        data=_load_yaml(root_path / "configs" / "nfl_2026.yaml"),
        markets=_load_yaml(root_path / "configs" / "markets.yaml"),
        stadiums=_load_yaml(root_path / "configs" / "stadiums.yaml"),
    )
