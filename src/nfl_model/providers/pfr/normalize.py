from __future__ import annotations

from bs4 import BeautifulSoup, Comment
import pandas as pd

from nfl_model.ids.teams import canonical_team

PFR_TEAM_ALIASES = {
    "GNB": "GB", "KAN": "KC", "LAR": "LA", "LVR": "LV", "NWE": "NE",
    "NOR": "NO", "SFO": "SF", "TAM": "TB", "JAX": "JAX", "WSH": "WAS",
}


def _team(value: str) -> str:
    v = str(value or "").strip().upper()
    return canonical_team(PFR_TEAM_ALIASES.get(v, v))


def _num(value: object) -> float | None:
    s = str(value or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _collect_soups(html: str) -> list[BeautifulSoup]:
    root = BeautifulSoup(html or "", "html.parser")
    soups = [root]
    for c in root.find_all(string=lambda text: isinstance(text, Comment)):
        text = str(c)
        if "<table" in text and "data-stat" in text:
            soups.append(BeautifulSoup(text, "html.parser"))
    return soups


def normalize_pfr_fantasy(html: str, season: int, scraped_at_utc: str, source_url: str) -> pd.DataFrame:
    rows: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for soup in _collect_soups(html):
        for tr in soup.find_all("tr"):
            cells = {}
            for cell in tr.find_all(["th", "td"]):
                stat = cell.get("data-stat")
                if stat:
                    cells[stat] = cell.get_text(" ", strip=True)
            player = str(cells.get("player") or "").strip()
            pos = str(cells.get("fantasy_pos") or "").strip().upper()
            team = _team(str(cells.get("team") or ""))
            if not player or pos not in {"QB", "RB", "WR", "TE"} or not team:
                continue
            key = (player, team, pos)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "player_name": player,
                "team": team,
                "position": pos,
                "pfr_games": _num(cells.get("games")),
                "pfr_games_started": _num(cells.get("games_started")),
                "pfr_pass_td": _num(cells.get("pass_td")),
                "pfr_rush_attempts": _num(cells.get("rush_att")),
                "pfr_rush_yards": _num(cells.get("rush_yds")),
                "pfr_rush_td": _num(cells.get("rush_td")),
                "pfr_targets": _num(cells.get("targets")),
                "pfr_receptions": _num(cells.get("rec")),
                "pfr_rec_yards": _num(cells.get("rec_yds")),
                "pfr_rec_td": _num(cells.get("rec_td")),
                "pfr_total_td": _num(cells.get("all_td")),
                "pfr_fantasy_points": _num(cells.get("fantasy_points")),
                "pfr_ppr_points": _num(cells.get("fantasy_points_ppr")),
                "pfr_dk_points": _num(cells.get("draftkings_points")),
                "pfr_fd_points": _num(cells.get("fanduel_points")),
                "pfr_pos_rank": _num(cells.get("fantasy_rank_pos")),
                "pfr_overall_rank": _num(cells.get("fantasy_rank_overall")),
                "pfr_season": int(season),
                "scraped_at_utc": scraped_at_utc,
                "source_url": source_url,
            })
    return pd.DataFrame(rows)
