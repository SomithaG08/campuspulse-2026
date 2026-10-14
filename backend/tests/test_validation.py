"""
Validation tests.

These test the boundary between the internet and our data, so most of them are
about REJECTION. A validator that only gets tested with good input is not
tested at all.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from common.validation import ValidationError, validate_event, validate_service_request

NOW = datetime(2026, 9, 22, 14, 5, 0, tzinfo=timezone.utc)


def good(**overrides):
    event = {
        "event_id": "evt-2026-0042",
        "building": "Library-A",
        "room": "A203",
        "event_type": "occupancy",
        "value": 30,
        "unit": "people",
        "severity": "normal",
        "timestamp": "2026-09-22T14:05:00Z",
    }
    event.update(overrides)
    return json.dumps(event)


# --- the happy path --------------------------------------------------------

def test_valid_event_is_accepted():
    result = validate_event(good(), now=NOW)
    assert result["event_id"] == "evt-2026-0042"
    assert result["value"] == 30.0


def test_client_severity_is_stripped():
    """The server decides severity. A sensor must not be able to declare itself normal."""
    result = validate_event(good(severity="critical"), now=NOW)
    assert "severity" not in result


def test_whitespace_is_trimmed():
    assert validate_event(good(room="  A203  "), now=NOW)["room"] == "A203"


# --- malformed input -------------------------------------------------------

@pytest.mark.parametrize("body", ["", "not json", "[1,2,3]", '"a string"'])
def test_non_object_bodies_rejected(body):
    with pytest.raises(ValidationError):
        validate_event(body, now=NOW)


@pytest.mark.parametrize("field", ["event_id", "building", "room", "event_type", "unit"])
def test_missing_required_field_rejected(field):
    payload = json.loads(good())
    del payload[field]
    with pytest.raises(ValidationError) as exc:
        validate_event(json.dumps(payload), now=NOW)
    assert field in exc.value.message


def test_oversized_body_rejected():
    with pytest.raises(ValidationError) as exc:
        validate_event(good(event_id="x" * 5000), now=NOW)
    assert "bytes" in exc.value.message or "characters" in exc.value.message


# --- values ----------------------------------------------------------------

@pytest.mark.parametrize("value", ["42", None, True, [1], {"a": 1}])
def test_non_numeric_value_rejected(value):
    """True is included deliberately: bool subclasses int in Python."""
    with pytest.raises(ValidationError):
        validate_event(good(value=value), now=NOW)


def test_implausible_temperature_rejected():
    with pytest.raises(ValidationError) as exc:
        validate_event(good(event_type="temperature", unit="celsius", value=4000), now=NOW)
    assert "plausible" in exc.value.message


def test_negative_occupancy_rejected():
    with pytest.raises(ValidationError):
        validate_event(good(value=-5), now=NOW)


def test_invalid_equipment_level_rejected():
    with pytest.raises(ValidationError):
        validate_event(good(event_type="equipment", unit="status", value=7), now=NOW)


# --- units: the sensor-misconfiguration guard ------------------------------

def test_wrong_unit_rejected():
    with pytest.raises(ValidationError) as exc:
        validate_event(good(event_type="temperature", unit="fahrenheit", value=71), now=NOW)
    assert "celsius" in exc.value.message


# --- campus membership -----------------------------------------------------

def test_unknown_building_rejected():
    with pytest.raises(ValidationError):
        validate_event(good(building="Hogwarts"), now=NOW)


def test_unknown_room_rejected():
    with pytest.raises(ValidationError):
        validate_event(good(room="Z999"), now=NOW)


def test_building_level_room_accepted():
    """'-' means a building-wide reading, such as an energy meter."""
    result = validate_event(
        good(room="-", event_type="energy", unit="kwh", value=100), now=NOW
    )
    assert result["room"] == "-"


# --- timestamps ------------------------------------------------------------

def test_future_timestamp_rejected():
    future = (NOW + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with pytest.raises(ValidationError) as exc:
        validate_event(good(timestamp=future), now=NOW)
    assert "future" in exc.value.message


def test_ancient_timestamp_rejected():
    old = (NOW - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with pytest.raises(ValidationError):
        validate_event(good(timestamp=old), now=NOW)


def test_timestamp_without_timezone_rejected():
    with pytest.raises(ValidationError) as exc:
        validate_event(good(timestamp="2026-09-22T14:05:00"), now=NOW)
    assert "timezone" in exc.value.message


def test_offset_timestamp_normalised_to_utc():
    """16:05 in +02:00 is 14:05 UTC. Everything we store is UTC."""
    result = validate_event(good(timestamp="2026-09-22T16:05:00+02:00"), now=NOW)
    assert result["timestamp"] == "2026-09-22T14:05:00Z"


# --- service requests ------------------------------------------------------

def test_service_request_requires_message():
    body = json.dumps({"building": "Library-A", "room": "A203", "priority": 3})
    with pytest.raises(ValidationError) as exc:
        validate_service_request(body, "student@northbridge.edu", now=NOW)
    assert "message" in exc.value.message


def test_service_request_records_requester():
    body = json.dumps({"building": "Library-A", "room": "A203",
                       "message": "Projector not working", "priority": 3})
    result = validate_service_request(body, "student@northbridge.edu", now=NOW)
    assert result["requested_by"] == "student@northbridge.edu"
    assert result["source"] == "student-portal"
    assert result["event_type"] == "service_request"
