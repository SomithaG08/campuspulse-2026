"""
The business logic: deciding what is abnormal.

This is the smallest file in the project and the one to understand first. It
is also the answer to "where is your data processing?" - every event that
enters the system passes through classify().

WHY THRESHOLDS AND NOT MACHINE LEARNING
---------------------------------------
Because every one of these decisions can be explained in a sentence, audited
by a human, and defended at an oral exam. A model that flags a room as
anomalous cannot tell the operations team WHY, and "the model said so" is not
something a campus engineer can act on. The reason string below is as much a
part of the product as the severity.

All thresholds live in campus_config.py, never here - one place to change.
"""

from typing import Tuple

from common import campus_config as cfg

NORMAL = "normal"
WARNING = "warning"
CRITICAL = "critical"


def classify(event: dict) -> Tuple[str, str]:
    """
    Returns (severity, reason).

    The reason is written for a human reading an alert at 2pm on a Tuesday:
    "occupancy 58 exceeds 120% of capacity 45", not "threshold_2_exceeded".
    """
    event_type = event["event_type"]
    value = event["value"]
    spec = cfg.EVENT_TYPES[event_type]
    rule = spec["rule"]

    if rule == "ratio":
        return _classify_ratio(event, spec, value)
    if rule == "band":
        return _classify_band(event_type, spec, value)
    if rule == "level":
        return _classify_level(event_type, spec, value)

    # Unreachable while validation restricts event_type, but an unknown type
    # must never be silently treated as normal.
    return WARNING, f"no rule defined for event type {event_type}"


def _classify_ratio(event: dict, spec: dict, value: float) -> Tuple[str, str]:
    """Occupancy against room capacity, energy against a building baseline."""
    if spec["reference"] == "capacity":
        reference = cfg.get_capacity(event["building"], event["room"])
        label, noun = "capacity", "occupancy"
    else:
        reference = cfg.get_energy_baseline(event["building"])
        label, noun = "baseline", "energy use"

    if not reference:
        # A building-level occupancy reading has no capacity to compare against.
        return NORMAL, f"{noun} {value:g} recorded (no {label} defined for comparison)"

    ratio = value / reference
    if ratio > spec["critical_above"]:
        pct = int(spec["critical_above"] * 100)
        return CRITICAL, f"{noun} {value:g} exceeds {pct}% of {label} {reference:g}"
    if ratio > spec["warning_above"]:
        pct = int(spec["warning_above"] * 100)
        return WARNING, f"{noun} {value:g} exceeds {pct}% of {label} {reference:g}"
    return NORMAL, f"{noun} {value:g} is within {label} {reference:g}"


def _classify_band(event_type: str, spec: dict, value: float) -> Tuple[str, str]:
    """Temperature and humidity: comfortable range, then an outer safety range."""
    n_low, n_high = spec["normal"]
    c_low, c_high = spec["critical_outside"]
    unit = spec["unit"]

    if value < c_low or value > c_high:
        return CRITICAL, f"{event_type} {value:g} {unit} is outside the safe range {c_low:g} to {c_high:g}"
    if value < n_low or value > n_high:
        return WARNING, f"{event_type} {value:g} {unit} is outside the normal range {n_low:g} to {n_high:g}"
    return NORMAL, f"{event_type} {value:g} {unit} is normal"


def _classify_level(event_type: str, spec: dict, value: float) -> Tuple[str, str]:
    """Equipment status and request priority: a code that maps straight to a severity."""
    level = int(value)
    severity = spec["levels"].get(level, WARNING)
    label = spec["labels"].get(level, f"level {level}")
    noun = "equipment" if event_type == "equipment" else "service request"
    return severity, f"{noun} reported as {label}"


def is_alert(severity: str) -> bool:
    """The single definition of 'alert' used everywhere in the system."""
    return severity != NORMAL
