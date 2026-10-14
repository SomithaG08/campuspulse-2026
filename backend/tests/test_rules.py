"""
Severity rule tests.

Every threshold in docs/architecture/04-data-model.md gets a test on each side
of its boundary. Thresholds without boundary tests are where off-by-one bugs
live - and a wrong threshold here means a wrong alert in the demo.
"""
import pytest

from common.rules import CRITICAL, NORMAL, WARNING, classify, is_alert


def event(**kw):
    base = {"building": "Library-A", "room": "A203", "event_type": "occupancy",
            "value": 30, "unit": "people"}
    base.update(kw)
    return base


# --- occupancy: A203 capacity is 45 ---------------------------------------

@pytest.mark.parametrize("value,expected", [
    (30, NORMAL),     # well under
    (45, NORMAL),     # exactly at capacity is not yet over
    (46, WARNING),    # just over 100%
    (54, WARNING),    # 120% exactly - not yet critical
    (55, CRITICAL),   # just over 120%
    (58, CRITICAL),   # the worked example from the data model
])
def test_occupancy_thresholds(value, expected):
    severity, _ = classify(event(value=value))
    assert severity == expected


def test_worked_example_matches_the_documentation():
    """This exact sentence appears in 04-data-model.md and 06-data-flow.md."""
    severity, reason = classify(event(value=58))
    assert severity == CRITICAL
    assert reason == "occupancy 58 exceeds 120% of capacity 45"


def test_building_level_occupancy_has_no_capacity_to_compare():
    severity, reason = classify(event(room="-", value=500))
    assert severity == NORMAL
    assert "no capacity defined" in reason


# --- temperature: normal 18-26, critical outside 15-30 --------------------

@pytest.mark.parametrize("value,expected", [
    (22, NORMAL), (18, NORMAL), (26, NORMAL),
    (17.9, WARNING), (26.1, WARNING), (15, WARNING), (30, WARNING),
    (14.9, CRITICAL), (30.1, CRITICAL), (-5, CRITICAL),
])
def test_temperature_bands(value, expected):
    severity, _ = classify(event(event_type="temperature", unit="celsius", value=value))
    assert severity == expected


# --- humidity: normal 30-60, critical outside 20-70 -----------------------

@pytest.mark.parametrize("value,expected", [
    (45, NORMAL), (29, WARNING), (61, WARNING), (19, CRITICAL), (71, CRITICAL),
])
def test_humidity_bands(value, expected):
    severity, _ = classify(event(event_type="humidity", unit="percent", value=value))
    assert severity == expected


# --- energy: Library-A baseline is 210 kWh --------------------------------

@pytest.mark.parametrize("value,expected", [
    (200, NORMAL), (210, NORMAL), (316, WARNING), (421, CRITICAL),
])
def test_energy_against_building_baseline(value, expected):
    severity, _ = classify(event(event_type="energy", unit="kwh", room="-", value=value))
    assert severity == expected


def test_energy_uses_the_right_building_baseline():
    """
    The same reading means different things in different buildings.
    Science-B's baseline is 480 kWh (labs), Library-A's is 210.
    450 kWh is therefore normal in Science-B and critical in Library-A.
    """
    sci, _ = classify(event(building="Science-B", room="-", event_type="energy", unit="kwh", value=450))
    lib, _ = classify(event(building="Library-A", room="-", event_type="energy", unit="kwh", value=450))
    assert sci == NORMAL      # 450 / 480 = 0.94
    assert lib == CRITICAL    # 450 / 210 = 2.14, above the 2.0 critical ratio


# --- discrete levels -------------------------------------------------------

@pytest.mark.parametrize("value,expected", [(0, NORMAL), (1, WARNING), (2, CRITICAL)])
def test_equipment_levels(value, expected):
    severity, _ = classify(event(event_type="equipment", unit="status", value=value))
    assert severity == expected


@pytest.mark.parametrize("value,expected", [(1, NORMAL), (2, WARNING), (3, CRITICAL)])
def test_service_request_priority(value, expected):
    severity, _ = classify(event(event_type="service_request", unit="priority", value=value))
    assert severity == expected


# --- the reason string is part of the product ------------------------------

def test_reason_is_written_for_a_human():
    _, reason = classify(event(event_type="temperature", unit="celsius", value=31))
    assert "31" in reason and "safe range" in reason


def test_is_alert_definition():
    assert is_alert(WARNING) and is_alert(CRITICAL)
    assert not is_alert(NORMAL)
