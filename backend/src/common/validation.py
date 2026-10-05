"""
The boundary between the untrusted internet and our data.

Every field of every incoming event is checked here, against the contract in
docs/architecture/04-data-model.md. Nothing downstream re-checks anything, so
if a rule is missing here it is missing everywhere.

Design choices worth defending at the oral:

* We validate the SHAPE and the PLAUSIBILITY, not just the shape. A temperature
  of 4000 parses fine as a number and is still nonsense.
* We reject rather than repair. Silently coercing "42" to 42 hides a broken
  sensor; a 400 with a clear message makes someone fix it.
* The client's `severity` is ignored entirely - see rules.py.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from common import campus_config as cfg


class ValidationError(Exception):
    """Carries a message safe to return to the caller: no internals, no stack."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValidationError("timestamp must be a string in ISO-8601 UTC format")
    text = value.strip()
    # Python 3.10's fromisoformat does not accept the trailing 'Z', although
    # 3.11+ does. Normalising here keeps the Lambda runtime version from
    # becoming a silent behaviour change.
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise ValidationError("timestamp must be ISO-8601, e.g. 2026-09-22T14:05:00Z")
    if parsed.tzinfo is None:
        raise ValidationError("timestamp must include a timezone; use UTC and end with Z")
    return parsed.astimezone(timezone.utc)


def _check_window(ts: datetime, now: datetime) -> None:
    """
    Reject events from the distant past or the future.

    Why: a sensor with a wrong clock would scatter events across partitions we
    never query, so they would be stored and never seen - the worst kind of
    bug, because nothing appears to fail.
    """
    if ts > now + timedelta(minutes=cfg.TIMESTAMP_MAX_FUTURE_MINUTES):
        raise ValidationError("timestamp is in the future")
    if ts < now - timedelta(hours=cfg.TIMESTAMP_MAX_AGE_HOURS):
        raise ValidationError(f"timestamp is older than {cfg.TIMESTAMP_MAX_AGE_HOURS} hours")


def parse_body(raw: Any) -> dict:
    """Accepts the API Gateway body (a string) or an already-parsed dict."""
    if isinstance(raw, dict):
        return raw
    if raw is None or raw == "":
        raise ValidationError("request body is empty")
    if not isinstance(raw, str):
        raise ValidationError("request body must be JSON")
    if len(raw.encode("utf-8")) > cfg.MAX_BODY_BYTES:
        raise ValidationError(f"request body exceeds {cfg.MAX_BODY_BYTES} bytes")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise ValidationError("request body is not valid JSON")
    if not isinstance(parsed, dict):
        raise ValidationError("request body must be a JSON object")
    return parsed


def _require_str(data: dict, field: str, max_len: int) -> str:
    value = data.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field} is required")
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    value = value.strip()
    if len(value) > max_len:
        raise ValidationError(f"{field} must be at most {max_len} characters")
    return value


def validate_event(raw_body: Any, now: datetime = None) -> dict:
    """
    Returns a clean event dict, or raises ValidationError with a message that
    is safe to send back to the caller.

    Note what is NOT returned: severity. That is the server's decision.
    """
    now = now or datetime.now(timezone.utc)
    data = parse_body(raw_body)

    event_id = _require_str(data, "event_id", cfg.MAX_ID_CHARS)
    building = _require_str(data, "building", 40)
    room = _require_str(data, "room", 20)
    event_type = _require_str(data, "event_type", 40)

    if event_type not in cfg.EVENT_TYPES:
        known = ", ".join(sorted(cfg.EVENT_TYPES))
        raise ValidationError(f"event_type must be one of: {known}")

    if not cfg.is_known_building(building):
        raise ValidationError(f"unknown building: {building}")
    if not cfg.is_known_room(building, room):
        raise ValidationError(f"unknown room {room} in {building}")

    unit = _require_str(data, "unit", 20)
    expected = cfg.expected_unit(event_type)
    if unit != expected:
        # Catches the classic sensor-configuration error: Fahrenheit sent where
        # Celsius is expected would otherwise look like a genuine heat alarm.
        raise ValidationError(f"unit for {event_type} must be '{expected}', got '{unit}'")

    value = data.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        # bool is a subclass of int in Python; True would otherwise pass as 1.
        raise ValidationError("value must be a number")
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValidationError("value must be a finite number")

    spec = cfg.EVENT_TYPES[event_type]
    if "plausible" in spec:
        low, high = spec["plausible"]
        if not (low <= value <= high):
            raise ValidationError(f"{event_type} value {value} is outside the plausible range {low} to {high}")
    if spec["rule"] == "level" and int(value) not in spec["levels"]:
        allowed = ", ".join(str(k) for k in sorted(spec["levels"]))
        raise ValidationError(f"{event_type} value must be one of: {allowed}")
    if spec["rule"] == "ratio" and value < 0:
        raise ValidationError(f"{event_type} value cannot be negative")

    ts = _parse_timestamp(data.get("timestamp"))
    _check_window(ts, now)

    event = {
        "event_id": event_id,
        "building": building,
        "room": room,
        "event_type": event_type,
        "value": value,
        "unit": unit,
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "simulator",
    }

    message = data.get("message")
    if message is not None:
        if not isinstance(message, str):
            raise ValidationError("message must be a string")
        message = message.strip()
        if len(message) > cfg.MAX_MESSAGE_CHARS:
            raise ValidationError(f"message must be at most {cfg.MAX_MESSAGE_CHARS} characters")
        event["message"] = message

    return event


def validate_service_request(raw_body: Any, username: str, now: datetime = None) -> dict:
    """
    POST /requests - the staff-facing endpoint.

    A service request becomes an ordinary event with event_type
    'service_request', so it flows through exactly the same pipeline as a
    sensor reading: same validation, same severity rules, same storage, same
    alerts list. One path, two stories.
    """
    now = now or datetime.now(timezone.utc)
    data = parse_body(raw_body)

    priority = data.get("priority", 2)
    if isinstance(priority, bool) or not isinstance(priority, int):
        raise ValidationError("priority must be an integer: 1 low, 2 normal, 3 urgent")

    synthetic = {
        "event_id": f"req-{int(now.timestamp() * 1000)}",
        "building": data.get("building"),
        "room": data.get("room"),
        "event_type": "service_request",
        "value": priority,
        "unit": "priority",
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "message": data.get("message"),
    }
    if synthetic["message"] is None:
        raise ValidationError("message is required for a service request")

    event = validate_event(synthetic, now=now)
    event["source"] = "staff-portal"
    event["requested_by"] = username
    return event
