"""
Aggregation tests - every field of the GET /stats response.

Items are passed newest-first, as every query returns them, because that
ordering is what makes "current occupancy" correct.
"""
from decimal import Decimal

from common.aggregate import summarise

DATE = "2026-10-04"


def ev(**kw):
    base = {"building": "Library-A", "room": "A203", "event_type": "occupancy",
            "value": 20, "unit": "people", "severity": "normal",
            "timestamp": "2026-10-04T10:00:00Z"}
    base.update(kw)
    return base


def test_empty_day_is_not_an_error():
    out = summarise([], DATE)
    assert out["total_events"] == 0
    assert out["alert_count"] == 0
    assert out["current_occupancy"] == []
    assert out["top_energy_building"] is None


def test_counts_by_type_and_severity():
    items = [
        ev(), ev(severity="warning"),
        ev(event_type="temperature", unit="celsius", value=22),
        ev(event_type="energy", room="-", unit="kwh", value=100, severity="critical"),
    ]
    out = summarise(items, DATE)
    assert out["total_events"] == 4
    assert out["events_by_type"] == {"energy": 1, "occupancy": 2, "temperature": 1}
    assert out["events_by_severity"] == {"critical": 1, "normal": 2, "warning": 1}
    assert out["alert_count"] == 2


def test_decimal_values_survive():
    """DynamoDB returns Decimal; JSON cannot serialise it."""
    out = summarise([ev(value=Decimal("31"))], DATE)
    assert out["current_occupancy"][0]["value"] == 31.0
    assert isinstance(out["current_occupancy"][0]["value"], float)


# --- current occupancy -----------------------------------------------------

def test_current_occupancy_takes_the_most_recent_reading_per_room():
    items = [  # newest first
        ev(value=40, timestamp="2026-10-04T17:00:00Z"),
        ev(value=10, timestamp="2026-10-04T09:00:00Z"),
    ]
    out = summarise(items, DATE)
    assert len(out["current_occupancy"]) == 1
    assert out["current_occupancy"][0]["value"] == 40.0


def test_occupancy_reports_capacity_and_load():
    out = summarise([ev(value=58)], DATE)  # A203 capacity 45
    row = out["current_occupancy"][0]
    assert row["capacity"] == 45
    assert row["load_pct"] == 129


def test_most_overloaded_room_is_listed_first():
    items = [
        ev(room="A204", value=15),   # capacity 30 -> 50%
        ev(room="A203", value=58),   # capacity 45 -> 129%
        ev(room="A101", value=60),   # capacity 120 -> 50%
    ]
    out = summarise(items, DATE)
    assert out["current_occupancy"][0]["room"] == "A203"


def test_building_level_occupancy_excluded_from_room_view():
    out = summarise([ev(room="-", value=500)], DATE)
    assert out["current_occupancy"] == []


# --- temperature and energy ------------------------------------------------

def test_average_temperature_per_building():
    items = [
        ev(building="Library-A", event_type="temperature", unit="celsius", value=20),
        ev(building="Library-A", event_type="temperature", unit="celsius", value=24),
        ev(building="Science-B", room="B012", event_type="temperature", unit="celsius", value=30),
    ]
    out = summarise(items, DATE)
    assert out["avg_temperature_c"] == {"Library-A": 22.0, "Science-B": 30.0}


def test_energy_is_summed_per_building_and_the_top_one_named():
    items = [
        ev(building="Library-A", room="-", event_type="energy", unit="kwh", value=100),
        ev(building="Library-A", room="-", event_type="energy", unit="kwh", value=50),
        ev(building="Science-B", room="-", event_type="energy", unit="kwh", value=400),
    ]
    out = summarise(items, DATE)
    assert out["energy_kwh_by_building"] == {"Library-A": 150.0, "Science-B": 400.0}
    assert out["top_energy_building"] == "Science-B"


# --- service requests ------------------------------------------------------

def test_only_priority_three_counts_as_urgent():
    items = [
        ev(event_type="service_request", unit="priority", value=3, severity="critical"),
        ev(event_type="service_request", unit="priority", value=3, severity="critical"),
        ev(event_type="service_request", unit="priority", value=1, severity="normal"),
    ]
    assert summarise(items, DATE)["urgent_requests"] == 2


# --- the brief's questions -------------------------------------------------

def test_every_operational_question_is_answerable_from_one_response():
    """
    The project brief asks five questions. This asserts the response has a
    field for each, so /stats alone can answer all of them.
    """
    out = summarise([ev()], DATE)
    for field in ("current_occupancy",          # which rooms are occupied/overloaded
                  "energy_kwh_by_building",     # which buildings consume most
                  "top_energy_building",
                  "alert_count",                # anything unusual
                  "events_by_severity",
                  "urgent_requests",            # which requests are urgent
                  "total_events"):              # overall state
        assert field in out


def test_unknown_fields_do_not_crash_the_summary():
    """Robustness: a malformed stored item must not break the dashboard."""
    out = summarise([{"event_type": "mystery"}, {}], DATE)
    assert out["total_events"] == 2
