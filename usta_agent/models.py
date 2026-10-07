"""Data models used throughout the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Event:
    """A single event (draw) inside a tournament, e.g. 'Boys 12U Singles'."""

    name: str = ""
    gender: str = ""  # e.g. "boys", "girls", "mixed"
    event_type: str = ""  # e.g. "singles", "doubles"
    max_age: int | None = None  # e.g. 12 for 12-and-under


@dataclass
class Tournament:
    """A normalized USTA tournament record."""

    id: str
    name: str
    start_date: date | None
    end_date: date | None
    level: int | None  # 1-7 (USTA junior levels)
    venue: str = ""
    city: str = ""
    state: str = ""
    latitude: float | None = None
    longitude: float | None = None
    url: str = ""
    events: list[Event] = field(default_factory=list)
    distance_miles: float | None = None

    def to_summary(self) -> dict:
        """Compact, JSON-serializable view (used for CSV rows and LLM tool output)."""
        return {
            "name": self.name,
            "start_date": self.start_date.isoformat() if self.start_date else "",
            "end_date": self.end_date.isoformat() if self.end_date else "",
            "level": f"L{self.level}" if self.level else "",
            "distance_miles": round(self.distance_miles, 1) if self.distance_miles is not None else "",
            "venue": self.venue,
            "city": self.city,
            "state": self.state,
            "url": self.url,
        }
