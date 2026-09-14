from nfl_model.providers.espn.normalize import (
    normalize_depth_chart,
    normalize_injuries,
)


def test_depthchart_lowercase_singular_schema():
    payload = {
        "depthchart": [
            {
                "id": "1",
                "name": "Offense",
                "positions": {
                    "qb": {
                        "position": {
                            "abbreviation": "QB",
                        },
                        "athletes": [
                            {
                                "id": "100",
                                "displayName": "QB One",
                            },
                            {
                                "id": "101",
                                "displayName": "QB Two",
                            },
                        ],
                    }
                },
            }
        ]
    }

    df = normalize_depth_chart(
        payload,
        "SEA",
    )

    assert len(df) == 2

    assert list(
        df["rank"]
    ) == [1, 2]

    assert list(
        df["espn_athlete_id"]
    ) == ["100", "101"]

    assert set(
        df["team"]
    ) == {"SEA"}


def test_league_wide_nested_injury_schema():
    payload = {
        "injuries": [
            {
                "id": "26",
                "displayName": "Seattle Seahawks",
                "injuries": [
                    {
                        "id": "999",
                        "status": "Questionable",
                        "date": "2026-09-02T12:00Z",
                        "athlete": {
                            "id": "123",
                            "displayName": "Example Player",
                        },
                        "shortComment": "Example injury.",
                    }
                ],
            }
        ]
    }

    df = normalize_injuries(
        payload,
        team_id_to_abbr={
            "26": "SEA",
        },
    )

    assert len(df) == 1

    row = df.iloc[0]

    assert row["team"] == "SEA"
    assert row["espn_team_id"] == "26"
    assert row["espn_athlete_id"] == "123"
    assert row["status"] == "Questionable"


def test_empty_current_state_frames_keep_schema():
    depth = normalize_depth_chart(
        {},
        "SEA",
    )

    injuries = normalize_injuries(
        {},
    )

    assert list(depth.columns) == [
        "team",
        "unit",
        "position",
        "rank",
        "espn_athlete_id",
        "player_name",
    ]

    assert list(injuries.columns) == [
        "team",
        "espn_team_id",
        "injury_id",
        "espn_athlete_id",
        "player_name",
        "status",
        "date",
        "details",
    ]
