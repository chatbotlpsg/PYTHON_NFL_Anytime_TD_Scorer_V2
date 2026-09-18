from __future__ import annotations

import math
import re

import pandas as pd
from bs4 import BeautifulSoup

from nfl_model.ids.teams import TEAM_FULL_NAMES, canonical_team

TEAM_CODES = set(TEAM_FULL_NAMES)


def _num(value: object) -> float | None:
    s = str(value or "").strip().replace(",", "")
    try:
        return float(s)
    except Exception:
        return None


def _clean_player(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = re.sub(r"\s+(?:Risk|Upside)\s*:\s*.*$", "", text, flags=re.I)
    text = re.sub(r"^Image:\s*", "", text, flags=re.I)
    return text.strip()


def _canonical_opp(value: str) -> str:
    return canonical_team(str(value or "").replace("@", "").strip())


def normalize_fftoday_weekly(html: str, position: str, scraped_at_utc: str, source_url: str) -> pd.DataFrame:
    """Normalize FFToday's public weekly projection table.

    The parser intentionally consumes ordinary rendered table rows only. It does not attempt
    to bypass login-only custom scoring or any access controls.
    """
    pos = str(position).upper()
    soup = BeautifulSoup(html or "", "html.parser")
    rows: list[dict] = []
    for tr in soup.find_all("tr"):
        cells = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)).strip() for td in tr.find_all(["td", "th"])]
        if len(cells) < 6:
            continue
        team_idx = None
        for i, cell in enumerate(cells):
            team = canonical_team(cell)
            if team in TEAM_CODES and str(cell).strip().upper().replace("@", "") in TEAM_CODES | {"JAC", "WSH", "LAR"}:
                team_idx = i
                break
        if team_idx is None or team_idx < 1 or team_idx + 1 >= len(cells):
            continue
        player = _clean_player(cells[team_idx - 1])
        team = canonical_team(cells[team_idx])
        opp = _canonical_opp(cells[team_idx + 1])
        if not player or team not in TEAM_CODES:
            continue
        vals = [_num(x) for x in cells[team_idx + 2:]]
        vals = [x for x in vals if x is not None]
        rec: dict = {
            "player_name": player,
            "team": team,
            "opponent": opp,
            "position": pos,
            "scraped_at_utc": scraped_at_utc,
            "source_url": source_url,
        }
        if pos == "QB" and len(vals) >= 9:
            rec.update({
                "fftoday_proj_pass_completions": vals[0],
                "fftoday_proj_pass_attempts": vals[1],
                "fftoday_proj_pass_yards": vals[2],
                "fftoday_proj_pass_td": vals[3],
                "fftoday_proj_interceptions": vals[4],
                "fftoday_proj_rush_attempts": vals[5],
                "fftoday_proj_rush_yards": vals[6],
                "fftoday_proj_rush_td": vals[7],
                "fftoday_proj_fpts": vals[8],
                "fftoday_proj_receptions": 0.0,
                "fftoday_proj_rec_yards": 0.0,
                "fftoday_proj_rec_td": 0.0,
            })
        elif pos in {"RB", "WR", "TE"} and len(vals) >= 7:
            rec.update({
                "fftoday_proj_rush_attempts": vals[0],
                "fftoday_proj_rush_yards": vals[1],
                "fftoday_proj_rush_td": vals[2],
                "fftoday_proj_receptions": vals[3],
                "fftoday_proj_rec_yards": vals[4],
                "fftoday_proj_rec_td": vals[5],
                "fftoday_proj_fpts": vals[6],
                "fftoday_proj_pass_td": 0.0,
            })
        else:
            continue
        # Anytime scorer excludes passing TD credit for quarterbacks.
        lam = float(rec.get("fftoday_proj_rush_td", 0.0) or 0.0)
        if pos != "QB":
            lam += float(rec.get("fftoday_proj_rec_td", 0.0) or 0.0)
        rec["fftoday_proj_scorer_td_lambda"] = max(0.0, lam)
        rec["fftoday_anytime_td_signal"] = 1.0 - math.exp(-max(0.0, lam))
        rows.append(rec)
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows).drop_duplicates(["player_name", "team", "position"], keep="last")
    return out.reset_index(drop=True)
