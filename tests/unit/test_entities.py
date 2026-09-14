import pandas as pd
from nfl_model.ids.resolver import build_player_map, resolve_player


def test_never_name_only_ambiguous():
    pm = build_player_map([
        {"full_name": "John Smith", "team": "KC", "position": "WR", "gsis_id": "1"},
        {"full_name": "John Smith", "team": "BUF", "position": "WR", "gsis_id": "2"},
    ])
    assert resolve_player("John Smith", None, "WR", pm).status == "ENTITY_QUARANTINE"
    assert resolve_player("John Smith", "KC", "WR", pm).status == "RESOLVED"
