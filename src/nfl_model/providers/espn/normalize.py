from __future__ import annotations

from typing import Any
import pandas as pd

from nfl_model.ids.events import make_event_id
from nfl_model.ids.teams import canonical_team


def normalize_scoreboard(payload: dict, season: int, week: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for event in payload.get("events", []):
        competitions = event.get("competitions") or []
        if not competitions:
            continue
        comp = competitions[0]
        teams: dict[str, dict] = {}
        for c in comp.get("competitors", []):
            t = c.get("team", {})
            teams[c.get("homeAway", "")] = {
                "id": str(t.get("id", "")),
                "abbr": canonical_team(t.get("abbreviation", "")),
                "name": t.get("displayName") or t.get("name"),
            }
        if "home" not in teams or "away" not in teams:
            continue
        kickoff = event.get("date")
        home, away = teams["home"], teams["away"]
        rows.append({
            "aita_event_id": make_event_id(season, week, kickoff, away["abbr"], home["abbr"]),
            "season": season,
            "week": week,
            "kickoff_utc": kickoff,
            "home_team": home["abbr"],
            "away_team": away["abbr"],
            "home_espn_team_id": home["id"],
            "away_espn_team_id": away["id"],
            "espn_event_id": str(event.get("id", "")),
            "status": ((event.get("status") or {}).get("type") or {}).get("name"),
            "venue": ((comp.get("venue") or {}).get("fullName")),
        })
    return pd.DataFrame(rows)


def normalize_roster(payload: dict, team: str) -> pd.DataFrame:
    rows = []
    groups = (
        payload.get("athletes")
        or ((payload.get("team") or {}).get("athletes"))
        or []
    )
    for group in groups:
        items = group.get("items") or []
        if not items and isinstance(group, dict) and group.get("id"):
            items = [group]
        for athlete in items:
            pos = athlete.get("position") or {}
            rows.append({
                "espn_athlete_id": str(athlete.get("id", "")),
                "full_name": athlete.get("fullName") or athlete.get("displayName"),
                "position": pos.get("abbreviation") if isinstance(pos, dict) else None,
                "current_team": canonical_team(team),
                "jersey": athlete.get("jersey"),
                "active_flag": athlete.get("status", {}).get("type") != "inactive" if isinstance(athlete.get("status"), dict) else True,
            })
    return pd.DataFrame(rows)


def normalize_depth_chart(payload: dict, team: str) -> pd.DataFrame:
    columns = [
        "team",
        "unit",
        "position",
        "rank",
        "espn_athlete_id",
        "player_name",
    ]

    rows = []

    # ESPN currently returns lowercase singular "depthchart".
    # Retain legacy support for "depthCharts" in case the provider changes again.
    charts = (
        payload.get("depthchart")
        or payload.get("depthCharts")
        or []
    )

    if isinstance(charts, dict):
        charts = [charts]

    for chart in charts:
        if not isinstance(chart, dict):
            continue

        unit = chart.get("name")

        positions = chart.get("positions") or {}

        if isinstance(positions, list):
            positions = {
                str(i): value
                for i, value in enumerate(positions)
            }

        for _, position in positions.items():
            if not isinstance(position, dict):
                continue

            p = position.get("position") or {}

            pos = (
                p.get("abbreviation")
                or p.get("name")
            )

            athletes = position.get("athletes") or []

            for ordinal, item in enumerate(athletes, start=1):
                if not isinstance(item, dict):
                    continue

                # ESPN currently places athlete fields directly in the list item.
                # Older/alternate schemas may wrap them under "athlete".
                athlete = item.get("athlete") or item

                raw_rank = (
                    item.get("rank")
                    or item.get("depth")
                    or item.get("order")
                    or ordinal
                )

                try:
                    rank = int(raw_rank)
                except (TypeError, ValueError):
                    rank = ordinal

                rows.append(
                    {
                        "team": canonical_team(team),
                        "unit": unit,
                        "position": pos,
                        "rank": rank,
                        "espn_athlete_id": str(
                            athlete.get("id", "")
                        ),
                        "player_name": (
                            athlete.get("displayName")
                            or athlete.get("fullName")
                        ),
                    }
                )

    return pd.DataFrame(rows, columns=columns)


def normalize_injuries(
    payload: dict,
    team: str | None = None,
    team_id_to_abbr: dict[str, str] | None = None,
) -> pd.DataFrame:

    columns = [
        "team",
        "espn_team_id",
        "injury_id",
        "espn_athlete_id",
        "player_name",
        "status",
        "date",
        "details",
    ]

    rows: list[dict[str, Any]] = []

    id_map = {
        str(k): canonical_team(v)
        for k, v in (team_id_to_abbr or {}).items()
    }

    def add_row(
        item: dict,
        resolved_team: str | None,
        espn_team_id: str | None = None,
    ) -> None:

        athlete = item.get("athlete") or {}
        status = item.get("status")

        rows.append(
            {
                "team": canonical_team(
                    resolved_team or ""
                ),
                "espn_team_id": str(
                    espn_team_id or ""
                ),
                "injury_id": str(
                    item.get("id", "")
                ),
                "espn_athlete_id": str(
                    athlete.get("id", "")
                ),
                "player_name": (
                    athlete.get("displayName")
                    or athlete.get("fullName")
                ),
                "status": (
                    status.get("name")
                    if isinstance(status, dict)
                    else status
                ),
                "date": item.get("date"),
                "details": (
                    item.get("details")
                    or item.get("shortComment")
                    or item.get("longComment")
                ),
            }
        )

    groups = (
        payload.get("injuries")
        or payload.get("items")
        or []
    )

    if isinstance(groups, dict):
        groups = [groups]

    for group in groups:
        if not isinstance(group, dict):
            continue

        # League-wide ESPN injury schema:
        #
        # injuries:
        #   - id: team_id
        #     displayName: team
        #     injuries:
        #       - athlete: ...
        #         status: ...
        nested = group.get("injuries")

        if isinstance(nested, list):
            espn_team_id = str(
                group.get("id")
                or ((group.get("team") or {}).get("id"))
                or ""
            )

            resolved_team = (
                team
                or id_map.get(espn_team_id)
            )

            if not resolved_team:
                team_obj = group.get("team") or {}

                resolved_team = (
                    group.get("abbreviation")
                    or team_obj.get("abbreviation")
                )

            for item in nested:
                if isinstance(item, dict):
                    add_row(
                        item,
                        resolved_team,
                        espn_team_id,
                    )

            continue

        # Retain support for a flat injury schema.
        team_obj = group.get("team") or {}

        espn_team_id = str(
            team_obj.get("id")
            or ""
        )

        resolved_team = (
            team
            or id_map.get(espn_team_id)
            or team_obj.get("abbreviation")
        )

        add_row(
            group,
            resolved_team,
            espn_team_id,
        )

    return pd.DataFrame(
        rows,
        columns=columns,
    )
