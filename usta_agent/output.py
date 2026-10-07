"""Output helpers: terminal table and CSV export."""

from __future__ import annotations

import csv
from pathlib import Path

from tabulate import tabulate

from usta_agent.models import Tournament

COLUMNS = ["start_date", "end_date", "level", "distance_miles", "name", "city", "state", "url"]


def print_table(tournaments: list[Tournament]) -> None:
    if not tournaments:
        print("\nNo matching tournaments found.\n")
        return
    rows = []
    for i, t in enumerate(tournaments, 1):
        s = t.to_summary()
        rows.append([i, s["start_date"], s["level"], s["distance_miles"], s["name"][:45], f"{s['city']}, {s['state']}"])
    print()
    print(tabulate(rows, headers=["#", "Start", "Level", "Miles", "Tournament", "Location"], tablefmt="github"))
    print()


def write_csv(tournaments: list[Tournament], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for t in tournaments:
            writer.writerow(t.to_summary())
    return path
