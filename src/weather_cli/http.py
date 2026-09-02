"""Tiny JSON HTTP helper with the User-Agent NWS and Nominatim require."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable

from weather_cli import USER_AGENT

JsonFetcher = Callable[[str], Any]


def fetch_json(url: str, timeout: float = 20.0) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/geo+json, application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:200].strip()
        raise RuntimeError(
            f"HTTP {exc.code} from {exc.url or url}"
            + (f": {detail}" if detail else "")
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error talking to {url}: {exc.reason}") from exc
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from {url}") from exc
