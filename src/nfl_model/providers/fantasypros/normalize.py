from __future__ import annotations

import re

import pandas as pd
from bs4 import BeautifulSoup

from nfl_model.ids.teams import TEAM_FULL_NAMES, canonical_team

TEAM_CODES = set(TEAM_FULL_NAMES)


def _float(value: object) -> float | None:
    try:
        return float(str(value).strip().replace(",", ""))
    except Exception:
        return None


def _int(value: object) -> int | None:
    x = _float(value)
    return int(x) if x is not None else None


def normalize_fantasypros_weekly(html: str, requested_position: str, week: int,
                                 scraped_at_utc: str, source_url: str) -> pd.DataFrame:
    soup = BeautifulSoup(html or "", "html.parser")
    rows: list[dict] = []
    req = str(requested_position).upper()
    pattern = re.compile(r"^(.*?)\s*\((QB|RB|WR|TE)\s*-\s*([A-Z]{2,3})\)\s*$", re.I)
    for tr in soup.find_all("tr"):
        cells = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)).strip() for td in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        rank = _int(cells[0])
        if rank is None:
            continue
        player = ""
        team = ""
        pos = req
        m = pattern.match(cells[1])
        if m:
            player, pos, team = m.group(1).strip(), m.group(2).upper(), canonical_team(m.group(3))
        else:
            # Fallback for position pages that render Player / Team / Opp in separate cells.
            player = cells[1].strip()
            for cell in cells[2:5]:
                t = canonical_team(str(cell).replace("@", "").replace("vs.", "").strip().split()[-1] if str(cell).strip() else "")
                if t in TEAM_CODES:
                    team = t
                    break
        if not player or team not in TEAM_CODES or pos not in {"QB", "RB", "WR", "TE"}:
            continue
        nums = [_float(x) for x in cells[2:]]
        nums = [x for x in nums if x is not None]
        best = nums[0] if len(nums) >= 1 else None
        worst = nums[1] if len(nums) >= 2 else None
        avg = nums[2] if len(nums) >= 3 else None
        std = nums[3] if len(nums) >= 4 else None
        rows.append({
            "player_name": player,
            "team": team,
            "position": pos,
            "fantasypros_pos_rank": rank,
            "fantasypros_best_rank": best,
            "fantasypros_worst_rank": worst,
            "fantasypros_avg_rank": avg,
            "fantasypros_rank_stddev": std,
            "fantasypros_week": int(week),
            "scraped_at_utc": scraped_at_utc,
            "source_url": source_url,
        })
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    # Some FantasyPros endpoints can expose Flex rows even when a position query is supplied.
    # Keep only the explicitly requested position so cross-position ranks cannot leak into the model.
    out = out[out["position"].eq(req)].copy()
    return out.drop_duplicates(["player_name", "team", "position"], keep="last").reset_index(drop=True)
