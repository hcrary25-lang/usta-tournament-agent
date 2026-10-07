"""Geographic helpers: ZIP code lookup and distance calculation."""

from __future__ import annotations

import math

import requests

EARTH_RADIUS_MILES = 3958.8

# Known ZIPs are resolved locally (fast, deterministic, works offline).
KNOWN_ZIPS: dict[str, tuple[float, float]] = {
    "30022": (34.0287, -84.2425),  # Alpharetta / Johns Creek, GA
}


def zip_to_latlon(zip_code: str, timeout: float = 10.0) -> tuple[float, float]:
    """Return (latitude, longitude) for a US ZIP code.

    Uses a local table first, then the free Zippopotam.us API.
    """
    zip_code = zip_code.strip()[:5]
    if zip_code in KNOWN_ZIPS:
        return KNOWN_ZIPS[zip_code]
    try:
        resp = requests.get(f"https://api.zippopotam.us/us/{zip_code}", timeout=timeout)
        resp.raise_for_status()
        place = resp.json()["places"][0]
        return float(place["latitude"]), float(place["longitude"])
    except (requests.RequestException, KeyError, IndexError, ValueError) as err:
        raise ValueError(f"Could not geocode ZIP code {zip_code!r}: {err}") from err


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points, in miles."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))
