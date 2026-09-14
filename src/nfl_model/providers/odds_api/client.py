from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import os
import time
import requests

from nfl_model.storage.snapshots import append_jsonl
from nfl_model.utils import stable_json_dumps, utc_now_iso
from .quota import assert_reserve


class OddsAPIClient:
    def __init__(self, base_url: str, cache_dir: str | Path, ledger_path: str | Path,
                 bookmakers: list[str], reserve: int = 100, ttl_minutes: int = 30,
                 timeout: int = 20, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = Path(ledger_path)
        self.archive_dir = self.ledger_path.parent / "archive"
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self.bookmakers = bookmakers
        self.reserve = reserve
        self.ttl_seconds = ttl_minutes * 60
        self.timeout = timeout
        self.max_retries = max_retries
        self.api_key = os.getenv("ODDS_API_KEY", "").strip()
        self.session = requests.Session()
        self.last_remaining: int | None = None

    def _key(self, endpoint: str, markets: list[str], event_id: str | None = None) -> str:
        obj = {
            "endpoint": endpoint,
            "event_id": event_id,
            "markets": sorted(markets),
            "bookmakers": sorted(self.bookmakers),
            "oddsFormat": "american",
        }
        return hashlib.sha256(stable_json_dumps(obj).encode()).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _read_cache(self, key: str) -> Any | None:
        path = self._cache_path(key)
        if not path.exists() or time.time() - path.stat().st_mtime > self.ttl_seconds:
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _request(self, url: str, endpoint: str, markets: list[str], event_id: str | None,
                 force_refresh: bool = False, estimated_cost: int = 0) -> Any:
        key = self._key(endpoint, markets, event_id)
        if not force_refresh:
            cached = self._read_cache(key)
            if cached is not None:
                return cached
        if not self.api_key:
            raise RuntimeError("ODDS_API_KEY is not set")
        assert_reserve(self.last_remaining, estimated_cost, self.reserve)
        params = {
            "apiKey": self.api_key,
            "bookmakers": ",".join(self.bookmakers),
            "markets": ",".join(markets),
            "oddsFormat": "american",
            "dateFormat": "iso",
        }
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                r = self.session.get(url, params=params, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()
                self.last_remaining = _as_int(r.headers.get("x-requests-remaining"))
                row = {
                    "timestamp": utc_now_iso(), "endpoint": endpoint, "event_id": event_id,
                    "markets_requested": markets, "bookmakers": self.bookmakers,
                    "estimated_cost": estimated_cost,
                    "actual_last_request_cost": _as_int(r.headers.get("x-requests-last")),
                    "requests_used": _as_int(r.headers.get("x-requests-used")),
                    "requests_remaining": self.last_remaining,
                    "request_hash": key,
                    "response_hash": hashlib.sha256(stable_json_dumps(data).encode()).hexdigest(),
                }
                append_jsonl(self.ledger_path, row)
                payload_text = stable_json_dumps(data)
                self._cache_path(key).write_text(payload_text, encoding="utf-8")
                # Append-only raw archive: every paid response becomes permanent research data.
                stamp = row["timestamp"].replace(":", "").replace("-", "").replace("+00:00", "Z")
                event_tag = str(event_id or "SLATE").replace("/", "_")
                archive = self.archive_dir / f"{stamp}_{endpoint}_{event_tag}_{key[:12]}.json"
                archive.write_text(payload_text, encoding="utf-8")
                return data
            except Exception as exc:
                last_exc = exc
                if attempt + 1 < self.max_retries:
                    time.sleep(0.6 * (2**attempt))
        raise RuntimeError(f"Odds API request failed: {endpoint}") from last_exc

    def events(self, sport_key: str) -> list[dict]:
        if not self.api_key:
            raise RuntimeError("ODDS_API_KEY is not set")
        url = f"{self.base_url}/sports/{sport_key}/events"
        r = self.session.get(url, params={"apiKey": self.api_key, "dateFormat": "iso"}, timeout=self.timeout)
        r.raise_for_status()
        self.last_remaining = _as_int(r.headers.get("x-requests-remaining"))
        data = r.json()
        now = utc_now_iso()
        payload_text = stable_json_dumps(data)
        response_hash = hashlib.sha256(payload_text.encode()).hexdigest()
        append_jsonl(self.ledger_path, {
            "timestamp": now, "endpoint": "events", "event_id": None, "markets_requested": [],
            "bookmakers": [], "estimated_cost": 0, "actual_last_request_cost": _as_int(r.headers.get("x-requests-last")),
            "requests_used": _as_int(r.headers.get("x-requests-used")), "requests_remaining": self.last_remaining,
            "request_hash": hashlib.sha256(f"events|{sport_key}".encode()).hexdigest(), "response_hash": response_hash,
        })
        stamp = now.replace(":", "").replace("-", "").replace("+00:00", "Z")
        (self.archive_dir / f"{stamp}_events_SLATE_{response_hash[:12]}.json").write_text(payload_text, encoding="utf-8")
        return data

    def mainlines(self, sport_key: str, markets: list[str], force_refresh: bool = False) -> list[dict]:
        url = f"{self.base_url}/sports/{sport_key}/odds"
        return self._request(url, "mainlines", markets, None, force_refresh, estimated_cost=len(markets))

    def event_odds(self, sport_key: str, event_id: str, markets: list[str], force_refresh: bool = False) -> dict:
        url = f"{self.base_url}/sports/{sport_key}/events/{event_id}/odds"
        return self._request(url, "event_odds", markets, event_id, force_refresh, estimated_cost=len(markets))


def _as_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
