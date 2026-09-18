from __future__ import annotations

from typing import Any
import pandas as pd


def _walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _scalar(v: Any) -> Any:
    if isinstance(v, dict):
        for k in ["value", "total", "display_value", "name", "full"]:
            if k in v:
                return _scalar(v[k])
    if isinstance(v, list) and len(v) == 1:
        return _scalar(v[0])
    return v


def normalize_yahoo_players(payloads: list[dict[str, Any]]) -> pd.DataFrame:
    """Best-effort normalizer for official Yahoo JSON responses.

    The handoff treats Yahoo as a corroborating fantasy layer only; identity and roster
    eligibility remain ESPN-current-roster controlled.
    """
    rows: dict[str, dict[str, Any]] = {}
    for payload in payloads or []:
        for node in _walk(payload):
            if "player_key" not in node:
                continue
            key = str(_scalar(node.get("player_key")) or "")
            if not key:
                continue
            rec = rows.setdefault(key, {"yahoo_player_key": key})
            name = node.get("name")
            if isinstance(name, dict):
                rec["player_name"] = _scalar(name.get("full"))
            rec["team"] = _scalar(node.get("editorial_team_abbr")) or rec.get("team")
            rec["position"] = _scalar(node.get("display_position")) or rec.get("position")
            if "player_points" in node:
                pp = node.get("player_points")
                if isinstance(pp, dict):
                    rec["yahoo_fantasy_points"] = _scalar(pp.get("total"))
            if "percent_owned" in node:
                po = node.get("percent_owned")
                if isinstance(po, dict):
                    rec["yahoo_percent_owned"] = _scalar(po.get("value"))
    out = pd.DataFrame(list(rows.values()))
    if out.empty:
        return out
    for col in ["yahoo_fantasy_points", "yahoo_percent_owned"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out
