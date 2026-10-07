"""Unit tests for filtering, geo, and parsing. Run with: pytest"""

from datetime import date, timedelta

import pytest

from usta_agent import filters, geo, usta_client
from usta_agent.models import Event

ORIGIN = geo.KNOWN_ZIPS["30022"]


# ----------------------------- geo ----------------------------- #
def test_haversine_zero_distance():
    assert geo.haversine_miles(*ORIGIN, *ORIGIN) == pytest.approx(0.0)


def test_haversine_atlanta_to_chattanooga_is_about_100_miles():
    miles = geo.haversine_miles(*ORIGIN, 35.0456, -85.3097)
    assert 90 < miles < 115


def test_known_zip_resolves_offline():
    assert geo.zip_to_latlon("30022") == ORIGIN


# --------------------------- levels ---------------------------- #
@pytest.mark.parametrize(
    "text, expected",
    [("Level 4", 4), ("L5", 5), ("Southern L4 Open", 4), ("level-5", 5), ("Open", None), ("", None)],
)
def test_parse_level(text, expected):
    assert filters.parse_level(text) == expected


# --------------------------- events ---------------------------- #
@pytest.mark.parametrize(
    "event, expected",
    [
        (Event(name="Boys' 12 & Under Singles", gender="boys", event_type="singles", max_age=12), True),
        (Event(name="Boys 12U Singles"), True),
        (Event(name="Girls' 12 & Under Singles", gender="girls", event_type="singles", max_age=12), False),
        (Event(name="Boys' 12 & Under Doubles", gender="boys", event_type="doubles", max_age=12), False),
        (Event(name="Boys' 14 & Under Singles", gender="boys", event_type="singles", max_age=14), False),
        (Event(name="Mixed 12 Singles"), False),
    ],
)
def test_is_boys_12u_singles(event, expected):
    assert filters.is_boys_12u_singles(event) is expected


# ------------------------ end-to-end (sample) ------------------------ #
def _sample_tournaments():
    raw = usta_client.load_sample_results()  # dates shifted to start ~10 days from today
    return [usta_client.parse_tournament(r) for r in raw]


def test_parse_sample_fields():
    t = _sample_tournaments()[0]
    assert t.name == "Johns Creek Fall L5 Junior Open"
    assert t.level == 5
    assert t.city == "Johns Creek" and t.state == "GA"
    assert t.latitude is not None and t.start_date is not None
    assert len(t.events) == 2


def test_filter_and_rank_sample_by_date():
    today = date.today()
    results = filters.filter_and_rank(
        _sample_tournaments(), ORIGIN, 200, today, today + timedelta(days=183), [4, 5], "date"
    )
    names = [t.name for t in results]

    assert len(results) == 4
    assert all("EXCLUDED" not in n for n in names)
    # Sorted by date ascending...
    assert [t.start_date for t in results] == sorted(t.start_date for t in results)
    # ...with same-day ties broken by distance (Atlanta is closer than Chattanooga).
    assert names.index("Atlanta Winter Classic L4") < names.index("Chattanooga Riverfront L4 Junior")


def test_filter_and_rank_sample_by_distance():
    today = date.today()
    results = filters.filter_and_rank(
        _sample_tournaments(), ORIGIN, 200, today, today + timedelta(days=183), [4, 5], "distance"
    )
    distances = [t.distance_miles for t in results]
    assert distances == sorted(distances)
    assert results[0].name == "Johns Creek Fall L5 Junior Open"


def test_level_filter_only_l4():
    today = date.today()
    results = filters.filter_and_rank(
        _sample_tournaments(), ORIGIN, 200, today, today + timedelta(days=183), [4], "date"
    )
    assert results and all(t.level == 4 for t in results)


def test_build_payload_shape():
    payload = usta_client.build_payload(*ORIGIN, 200, date(2026, 1, 1), date(2026, 6, 30))
    keys = {f["key"] for f in payload["filters"]}
    assert {"date-range", "distance", "level-category"} <= keys
    assert payload["options"]["latitude"] == ORIGIN[0]
