"""Filtering and ranking logic: 12U Boys Singles, level, radius, date window."""

from __future__ import annotations

import re
from datetime import date

from usta_agent.geo import haversine_miles
from usta_agent.models import Event, Tournament

_LEVEL_RE = re.compile(r"(?:level|lvl|\bl)\s*-?\s*([1-7])\b", re.IGNORECASE)
_AGE_12_RE = re.compile(r"(?<!\d)12(?!\d)")


def parse_level(text: str) -> int | None:
    """'Level 4' -> 4, 'L5' -> 5, 'Southern L4 Open' -> 4. Returns None if unknown."""
    if not text:
        return None
    match = _LEVEL_RE.search(text)
    return int(match.group(1)) if match else None


def is_boys_12u_singles(event: Event) -> bool:
    """True if the event is a Boys 12-and-under singles draw."""
    text = f"{event.name} {event.gender} {event.event_type}".lower()

    # Gender: must be boys.
    if event.gender in ("girls", "female", "girl", "women", "mixed"):
        return False
    if re.search(r"\bgirls?\b|\bmixed\b", text):
        return False
    is_boys = event.gender in ("boys", "boy", "male", "men") or bool(re.search(r"\bboys?\b|\bb\s?12\b", text))

    # Age: 12 & under.
    is_12u = event.max_age == 12 if event.max_age is not None else bool(_AGE_12_RE.search(event.name))

    # Format: singles, not doubles.
    is_singles = ("singles" in text or event.event_type == "singles") and "doubles" not in text

    return is_boys and is_12u and is_singles


def filter_and_rank(
    tournaments: list[Tournament],
    origin: tuple[float, float],
    radius_miles: float,
    start: date,
    end: date,
    levels: list[int],
    sort_by: str = "date",
) -> list[Tournament]:
    """Keep matching tournaments and sort by date (then distance) or by distance (then date)."""
    kept: list[Tournament] = []
    for t in tournaments:
        if t.level not in levels:
            continue
        if not any(is_boys_12u_singles(e) for e in t.events):
            continue
        if t.start_date and not (start <= t.start_date <= end):
            continue
        if t.latitude is not None and t.longitude is not None:
            t.distance_miles = haversine_miles(origin[0], origin[1], t.latitude, t.longitude)
            if t.distance_miles > radius_miles:
                continue
        kept.append(t)

    far = float("inf")
    if sort_by == "distance":
        kept.sort(key=lambda t: (t.distance_miles if t.distance_miles is not None else far, t.start_date or date.max))
    else:
        kept.sort(key=lambda t: (t.start_date or date.max, t.distance_miles if t.distance_miles is not None else far))
    return kept
