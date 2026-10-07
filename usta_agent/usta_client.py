"""Client for USTA's public tournament search (the API behind playtennis.usta.com/tournaments).

NOTE: USTA does not publish an official public API. This module calls the same JSON
endpoint the PlayTennis website uses. If USTA changes it, open
https://playtennis.usta.com/tournaments in Chrome, open DevTools > Network, run a search,
and update SEARCH_URL / build_payload() to match the "Query" request you see.
Parsing is intentionally defensive so small schema changes don't break the agent.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from usta_agent.models import Event, Tournament

SEARCH_URL = (
    "https://prd-usta-kube.clubspark.pro/unified-search-api/api/Search/tournaments/Query"
    "?indexSchema=tournament"
)
TOURNAMENT_URL = "https://playtennis.usta.com/Competitions/{org}/Tournaments/overview/{id}"
SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_response.json"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://playtennis.usta.com",
    "Referer": "https://playtennis.usta.com/",
    "User-Agent": "Mozilla/5.0 (usta-tournament-agent; educational project)",
}


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #
def build_payload(
    lat: float,
    lon: float,
    radius_miles: int,
    start: date,
    end: date,
    offset: int = 0,
    page_size: int = 100,
) -> dict:
    """Build the JSON body for the USTA search endpoint (junior tournaments only)."""
    return {
        "options": {
            "size": page_size,
            "from": offset,
            "sortKey": "date",
            "latitude": lat,
            "longitude": lon,
        },
        "filters": [
            {
                "key": "date-range",
                "items": [
                    {
                        "minDate": f"{start.isoformat()}T00:00:00.000Z",
                        "maxDate": f"{end.isoformat()}T23:59:59.999Z",
                    }
                ],
            },
            {"key": "distance", "items": [{"value": radius_miles}]},
            {"key": "level-category", "items": [{"value": "junior"}]},
        ],
    }


def fetch_raw_results(
    lat: float,
    lon: float,
    radius_miles: int,
    start: date,
    end: date,
    page_size: int = 100,
    max_pages: int = 10,
    session: requests.Session | None = None,
) -> list[dict]:
    """Fetch all pages of raw search results from USTA."""
    session = session or requests.Session()
    results: list[dict] = []
    for page in range(max_pages):
        payload = build_payload(lat, lon, radius_miles, start, end, page * page_size, page_size)
        resp = session.post(SEARCH_URL, json=payload, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("searchResults") or data.get("results") or []
        results.extend(batch)
        total = data.get("total", len(results))
        if not batch or len(results) >= total:
            break
    return results


def load_sample_results(path: Path = SAMPLE_PATH, shift_to_today: bool = True) -> list[dict]:
    """Load offline sample data (same shape as the live API response).

    If shift_to_today is True, all dates are moved so the earliest tournament starts
    10 days from today. This keeps the demo working no matter when it is run.
    """
    with open(path, encoding="utf-8") as f:
        results = json.load(f)["searchResults"]
    if not shift_to_today:
        return results

    starts = [_to_date(r["item"].get("startDateTime")) for r in results]
    earliest = min(d for d in starts if d)
    offset = (date.today() + timedelta(days=10)) - earliest
    for r in results:
        item = r["item"]
        for key in ("startDateTime", "endDateTime"):
            d = _to_date(item.get(key))
            if d:
                item[key] = f"{(d + offset).isoformat()}T09:00:00Z"
    return results


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def _first(data: Any, *paths: str) -> Any:
    """Return the first non-empty value found at any dotted path, e.g. 'location.geo.latitude'."""
    for path in paths:
        cur = data
        for key in path.split("."):
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                cur = None
                break
        if cur not in (None, "", [], {}):
            return cur
    return None


def _to_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_event(raw: dict) -> Event:
    division = raw.get("division") or {}
    return Event(
        name=str(_first(raw, "name", "division.name", "title") or ""),
        gender=str(_first(division, "gender") or _first(raw, "gender") or "").lower(),
        event_type=str(_first(division, "eventType") or _first(raw, "eventType", "type") or "").lower(),
        max_age=_to_int(_first(division, "ageCategory.maximumAge", "ageCategory.maxAge", "maxAge")),
    )


def parse_tournament(raw: dict) -> Tournament:
    """Convert one raw search result into a Tournament."""
    # Imported here to avoid a circular import (filters imports models only).
    from usta_agent.filters import parse_level

    item = raw.get("item", raw)
    tid = str(_first(item, "id", "tournamentId") or "")
    org = _first(item, "organization.urlSegment", "organization.id") or ""
    url = _first(item, "url", "link") or (TOURNAMENT_URL.format(org=org, id=tid) if tid else "")

    return Tournament(
        id=tid,
        name=str(_first(item, "name", "title") or "Unnamed tournament"),
        start_date=_to_date(_first(item, "startDateTime", "startDate", "dates.start")),
        end_date=_to_date(_first(item, "endDateTime", "endDate", "dates.end")),
        level=parse_level(str(_first(item, "level.name", "level.shortName", "levelName", "level") or "")),
        venue=str(_first(item, "location.name", "venue.name") or ""),
        city=str(_first(item, "location.address.city", "location.city", "location.town") or ""),
        state=str(_first(item, "location.address.state", "location.state", "location.county") or ""),
        latitude=_to_float(
            _first(item, "location.geo.latitude", "location.latitude", "location.address.latitude", "geo.latitude")
        ),
        longitude=_to_float(
            _first(item, "location.geo.longitude", "location.longitude", "location.address.longitude", "geo.longitude")
        ),
        url=str(url),
        events=[parse_event(e) for e in (item.get("events") or []) if isinstance(e, dict)],
    )
