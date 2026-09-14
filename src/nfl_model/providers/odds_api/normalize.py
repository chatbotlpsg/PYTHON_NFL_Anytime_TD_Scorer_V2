from __future__ import annotations

from typing import Any
import hashlib
import pandas as pd

from nfl_model.pricing.odds import american_to_decimal, american_to_implied
from nfl_model.utils import stable_json_dumps


def normalize_event_odds(payload: dict | list[dict], snapshot_time_utc: str) -> pd.DataFrame:
    events = payload if isinstance(payload, list) else [payload]
    response_hash = hashlib.sha256(stable_json_dumps(payload).encode()).hexdigest()
    rows: list[dict[str, Any]] = []
    for event in events:
        for book in event.get("bookmakers", []):
            for market in book.get("markets", []):
                for outcome in market.get("outcomes", []):
                    price = outcome.get("price")
                    try:
                        decimal = american_to_decimal(float(price)) if price is not None else None
                        raw_implied = american_to_implied(float(price)) if price is not None else None
                    except (TypeError, ValueError):
                        decimal = None
                        raw_implied = None
                    rows.append({
                        "odds_api_event_id": event.get("id"),
                        "commence_time": event.get("commence_time"),
                        "home_team_raw": event.get("home_team"),
                        "away_team_raw": event.get("away_team"),
                        "bookmaker": book.get("key"),
                        "bookmaker_title": book.get("title"),
                        "book_last_update": book.get("last_update"),
                        "market_key": market.get("key"),
                        "market_last_update": market.get("last_update"),
                        "player_name_raw": outcome.get("description"),
                        "side": str(outcome.get("name", "")).upper(),
                        "line": outcome.get("point"),
                        "american_odds": price,
                        "decimal_odds": decimal,
                        "market_raw_implied_prob": raw_implied,
                        "snapshot_time_utc": snapshot_time_utc,
                        "market_snapshot_timestamp": snapshot_time_utc,
                        "source": "THE_ODDS_API",
                        "source_response_hash": response_hash,
                    })
    return pd.DataFrame(rows)
