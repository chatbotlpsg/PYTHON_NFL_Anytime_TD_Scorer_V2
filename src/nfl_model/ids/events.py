from __future__ import annotations
import hashlib


def make_event_id(season: int, week: int, kickoff_utc: str, away: str, home: str) -> str:
    raw = f"{season}|{week}|{kickoff_utc}|{away}|{home}".encode()
    return "NFL-EVT-" + hashlib.sha1(raw).hexdigest()[:16].upper()
