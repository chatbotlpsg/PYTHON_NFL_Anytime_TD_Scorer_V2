from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import time
from urllib.parse import urlencode

import requests


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


@dataclass
class PublicHTMLResponse:
    text: str
    url: str
    fetched_at_utc: str
    cache_status: str
    age_hours: float


class PublicHTMLClient:
    """Polite, cache-first reader for public fantasy pages.

    This client intentionally does not implement login, paywall, CAPTCHA, cookie-wall,
    or anti-bot bypasses. If a provider blocks ordinary public HTTP access, the caller
    should mark that provider degraded and continue without it.
    """

    def __init__(
        self,
        cache_dir: Path,
        user_agent: str,
        timeout: int = 20,
        cache_ttl_hours: float = 6.0,
        min_request_interval_seconds: float = 0.75,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_agent = user_agent
        self.timeout = int(timeout)
        self.cache_ttl_hours = float(cache_ttl_hours)
        self.min_request_interval_seconds = float(min_request_interval_seconds)
        self._last_request_monotonic = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _cache_paths(self, url: str, params: dict | None) -> tuple[Path, Path]:
        query = urlencode(sorted((params or {}).items()))
        raw = f"{url}?{query}" if query else url
        key = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.html", self.cache_dir / f"{key}.json"

    def _read_cache(self, html_path: Path, meta_path: Path) -> PublicHTMLResponse | None:
        if not html_path.exists() or not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            fetched = _parse_iso(meta.get("fetched_at_utc"))
            if fetched is None:
                return None
            age = max(0.0, (_utc_now() - fetched).total_seconds() / 3600.0)
            return PublicHTMLResponse(
                text=html_path.read_text(encoding="utf-8", errors="replace"),
                url=str(meta.get("url") or ""),
                fetched_at_utc=fetched.isoformat().replace("+00:00", "Z"),
                cache_status="HIT",
                age_hours=age,
            )
        except Exception:
            return None

    def get(self, url: str, params: dict | None = None, max_age_hours: float | None = None) -> PublicHTMLResponse:
        html_path, meta_path = self._cache_paths(url, params)
        cached = self._read_cache(html_path, meta_path)
        usable_age = min(self.cache_ttl_hours, float(max_age_hours)) if max_age_hours is not None else self.cache_ttl_hours
        if cached is not None and cached.age_hours <= usable_age:
            return cached

        elapsed = time.monotonic() - self._last_request_monotonic
        if elapsed < self.min_request_interval_seconds:
            time.sleep(self.min_request_interval_seconds - elapsed)

        resp = self.session.get(url, params=params, timeout=self.timeout, allow_redirects=True)
        self._last_request_monotonic = time.monotonic()
        resp.raise_for_status()
        text = resp.text
        fetched = _utc_now()
        final_url = str(resp.url)
        html_path.write_text(text, encoding="utf-8")
        meta_path.write_text(json.dumps({
            "url": final_url,
            "fetched_at_utc": fetched.isoformat().replace("+00:00", "Z"),
            "status_code": int(resp.status_code),
        }, indent=2, sort_keys=True), encoding="utf-8")
        return PublicHTMLResponse(
            text=text,
            url=final_url,
            fetched_at_utc=fetched.isoformat().replace("+00:00", "Z"),
            cache_status="MISS_REFRESHED",
            age_hours=0.0,
        )
