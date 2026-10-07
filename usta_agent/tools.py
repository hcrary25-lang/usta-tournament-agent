"""Tools the LLM agent can call. Each is a plain Python function with type hints and a
docstring, which the Gemini SDK turns into a function declaration automatically."""

from __future__ import annotations

import os
from datetime import date, timedelta

from usta_agent import filters, geo, output, usta_client

# Runtime settings (set by main.py from CLI flags).
SETTINGS = {
    "use_sample": False,
    "csv_path": "results/tournaments_12u_boys.csv",
}


def run_search(
    zip_code: str = "30022",
    radius_miles: int = 200,
    months_ahead: int = 6,
    levels: list[int] | None = None,
    sort_by: str = "date",
):
    """Deterministic pipeline: geocode -> fetch -> parse -> filter -> rank -> print table -> CSV."""
    levels = levels or [4, 5]
    origin = geo.zip_to_latlon(zip_code)
    start = date.today()
    end = start + timedelta(days=int(months_ahead * 30.5))

    if SETTINGS["use_sample"] or os.getenv("USTA_USE_SAMPLE") == "1":
        raw = usta_client.load_sample_results()
    else:
        raw = usta_client.fetch_raw_results(origin[0], origin[1], radius_miles, start, end)

    parsed = [usta_client.parse_tournament(r) for r in raw]
    matches = filters.filter_and_rank(parsed, origin, radius_miles, start, end, levels, sort_by)

    output.print_table(matches)
    csv_path = output.write_csv(matches, SETTINGS["csv_path"])
    print(f"Saved {len(matches)} result(s) to {csv_path}\n")
    return matches, csv_path


# ----------------------------- LLM-callable tools ----------------------------- #
def search_tournaments(
    zip_code: str = "30022",
    radius_miles: int = 200,
    months_ahead: int = 6,
    levels: str = "4,5",
    sort_by: str = "date",
) -> dict:
    """Search USTA junior tournaments that offer a Boys 12U Singles draw.

    Prints a results table for the user and saves a CSV file.

    Args:
        zip_code: US ZIP code to measure distance from. Default "30022".
        radius_miles: Maximum distance from the ZIP code, in miles. Default 200.
        months_ahead: How many months ahead of today to search. Default 6.
        levels: Comma-separated USTA junior levels to include, e.g. "4,5".
        sort_by: "date" (soonest first, then closest) or "distance" (closest first).

    Returns:
        A dict with the result count, CSV path, and a list of matching tournaments.
    """
    level_list = [int(x) for x in str(levels).replace("L", "").replace("l", "").split(",") if x.strip()]
    try:
        matches, csv_path = run_search(zip_code, radius_miles, months_ahead, level_list, sort_by)
    except Exception as err:  # Surface errors to the LLM so it can explain them.
        return {"error": f"{type(err).__name__}: {err}"}
    return {
        "count": len(matches),
        "csv_path": str(csv_path),
        "tournaments": [t.to_summary() for t in matches],
    }


def get_distance_between_zips(zip_a: str, zip_b: str) -> dict:
    """Return the straight-line distance in miles between two US ZIP codes.

    Args:
        zip_a: First ZIP code.
        zip_b: Second ZIP code.
    """
    try:
        a, b = geo.zip_to_latlon(zip_a), geo.zip_to_latlon(zip_b)
    except ValueError as err:
        return {"error": str(err)}
    return {"miles": round(geo.haversine_miles(*a, *b), 1)}


AGENT_TOOLS = [search_tournaments, get_distance_between_zips]
