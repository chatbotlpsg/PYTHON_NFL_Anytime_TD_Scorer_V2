import pandas as pd

from nfl_model.providers.espn.client import ESPNClient
from nfl_model.providers.espn.normalize import normalize_roster
from nfl_model.features.current_role import enrich_player_map_with_current_context


def test_roster_detailed_team_schema():
    payload = {
        "team": {
            "athletes": [
                {
                    "id": "100",
                    "fullName": "Example QB",
                    "position": {
                        "abbreviation": "QB"
                    },
                    "jersey": "1",
                },
                {
                    "id": "101",
                    "fullName": "Example WR",
                    "position": {
                        "abbreviation": "WR"
                    },
                    "jersey": "10",
                },
            ]
        }
    }

    df = normalize_roster(
        payload,
        "ARI",
    )

    assert len(df) == 2
    assert set(df["espn_athlete_id"]) == {"100", "101"}
    assert set(df["current_team"]) == {"ARI"}


def test_client_roster_falls_back_to_detailed_team():
    client = ESPNClient(
        "https://example.invalid",
        timeout=1,
        max_retries=1,
    )

    calls = []

    def fake_get(resource, params=None):
        calls.append((resource, params))

        if resource.endswith("/roster"):
            raise RuntimeError("primary failed")

        return {
            "team": {
                "athletes": []
            }
        }

    client._get = fake_get

    payload = client.get_roster("22")

    assert payload == {
        "team": {
            "athletes": []
        }
    }

    assert calls == [
        ("teams/22/roster", None),
        ("teams/22", {"enable": "roster"}),
    ]


def test_blank_injury_id_does_not_attach_to_blank_player_id():
    players = pd.DataFrame(
        [
            {
                "aita_player_id": "TEST",
                "full_name": "Example Player",
                "normalized_name": "example player",
                "position": "WR",
                "current_team": "ARI",
                "espn_athlete_id": "",
                "role_certainty_score": 50.0,
            }
        ]
    )

    injuries = pd.DataFrame(
        [
            {
                "espn_athlete_id": "",
                "status": "Out",
            }
        ]
    )

    out = enrich_player_map_with_current_context(
        players,
        pd.DataFrame(),
        pd.DataFrame(),
        injuries,
    )

    assert out.iloc[0]["availability_status"] == "ACTIVE_OR_UNLISTED"
    assert bool(out.iloc[0]["available_for_simulation"]) is True
