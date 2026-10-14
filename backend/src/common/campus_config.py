"""
NorthBridge University — the single source of truth for the campus.

WHY THIS FILE EXISTS
--------------------
The simulator and the backend must agree on what the campus looks like and on
what counts as abnormal. If the simulator thought room A203 held 60 people and
the backend thought it held 45, every alert would be wrong and nobody would
know which side was lying. Both sides import THIS file, so disagreement is
impossible by construction.

It contains data and lookups only — no AWS, no network, no business logic.
That makes it trivially unit-testable and safe to import anywhere.

Scale note: five buildings and eleven rooms, on purpose. This is a course
prototype; see the scale guardrails in the README before adding more.
"""

import os
from typing import Optional

# --------------------------------------------------------------------------
# The campus.
# capacity = how many people the room is designed to hold.
# Rooms named "-" are building-level readings (an energy meter, for example)
# rather than a physical room.
# --------------------------------------------------------------------------
BUILDINGS: dict[str, dict] = {
    "Library-A": {
        "rooms": {"A203": {"capacity": 45}, "A204": {"capacity": 30}, "A101": {"capacity": 120}},
        "energy_baseline_kwh": 210.0,
    },
    "Science-B": {
        "rooms": {"B012": {"capacity": 24}, "B110": {"capacity": 60}},
        "energy_baseline_kwh": 480.0,  # labs draw the most on campus
    },
    "Arts-C": {
        "rooms": {"C005": {"capacity": 80}, "C201": {"capacity": 35}},
        "energy_baseline_kwh": 150.0,
    },
    "Sports-D": {
        "rooms": {"D001": {"capacity": 200}, "D002": {"capacity": 40}},
        "energy_baseline_kwh": 320.0,
    },
    "Admin-E": {
        "rooms": {"E100": {"capacity": 20}, "E101": {"capacity": 12}},
        "energy_baseline_kwh": 95.0,
    },
}

# --------------------------------------------------------------------------
# Event types: the unit each one must carry, and the thresholds that decide
# severity. These MUST match docs/architecture/04-data-model.md section 2.
#
# How to read the threshold shapes:
#   "ratio"  -> value is compared to a reference (capacity or baseline)
#   "band"   -> value must sit inside a numeric range
#   "level"  -> value is a discrete code mapped straight to a severity
# --------------------------------------------------------------------------
EVENT_TYPES: dict[str, dict] = {
    "occupancy": {
        "unit": "people",
        "rule": "ratio",
        "reference": "capacity",
        "warning_above": 1.0,    # over 100% of capacity
        "critical_above": 1.2,   # over 120% of capacity
    },
    "temperature": {
        "unit": "celsius",
        "rule": "band",
        "normal": (18.0, 26.0),
        "critical_outside": (15.0, 30.0),
        "plausible": (-20.0, 60.0),  # anything outside this is a broken sensor, not a heatwave
    },
    "humidity": {
        "unit": "percent",
        "rule": "band",
        "normal": (30.0, 60.0),
        "critical_outside": (20.0, 70.0),
        "plausible": (0.0, 100.0),
    },
    "energy": {
        "unit": "kwh",
        "rule": "ratio",
        "reference": "energy_baseline_kwh",
        "warning_above": 1.5,
        "critical_above": 2.0,
    },
    "equipment": {
        "unit": "status",
        "rule": "level",
        "levels": {0: "normal", 1: "warning", 2: "critical"},
        "labels": {0: "operational", 1: "degraded", 2: "failed"},
    },
    "service_request": {
        "unit": "priority",
        "rule": "level",
        "levels": {1: "normal", 2: "warning", 3: "critical"},
        "labels": {1: "low", 2: "normal", 3: "urgent"},
    },
}

SEVERITIES = ("normal", "warning", "critical")

# Limits enforced at ingestion. Small on purpose: a validator with generous
# limits is barely a validator.
MAX_BODY_BYTES = 4096
MAX_MESSAGE_CHARS = 280
MAX_ID_CHARS = 64
TIMESTAMP_MAX_AGE_HOURS = 24
TIMESTAMP_MAX_FUTURE_MINUTES = 5

# How long an event lives before DynamoDB deletes it automatically.
# Terraform passes var.ttl_days to cp-ingest as TTL_DAYS; 30 when unset
# (unit tests, simulator).
TTL_DAYS = int(os.environ.get("TTL_DAYS", "30"))

BUILDING_LEVEL_ROOM = "-"


# --------------------------------------------------------------------------
# Lookups. Each returns None rather than raising, so callers decide whether a
# miss is a validation error (the API) or a programming error (the simulator).
# --------------------------------------------------------------------------
def is_known_building(building: str) -> bool:
    return building in BUILDINGS


def is_known_room(building: str, room: str) -> bool:
    if building not in BUILDINGS:
        return False
    return room == BUILDING_LEVEL_ROOM or room in BUILDINGS[building]["rooms"]


def get_capacity(building: str, room: str) -> Optional[int]:
    """People the room holds, or None for an unknown or building-level room."""
    b = BUILDINGS.get(building)
    if not b:
        return None
    r = b["rooms"].get(room)
    return r["capacity"] if r else None


def get_energy_baseline(building: str) -> Optional[float]:
    b = BUILDINGS.get(building)
    return b["energy_baseline_kwh"] if b else None


def expected_unit(event_type: str) -> Optional[str]:
    t = EVENT_TYPES.get(event_type)
    return t["unit"] if t else None


def all_rooms() -> list[tuple[str, str]]:
    """Every (building, room) pair — used by the simulator to pick a target."""
    return [(b, r) for b, cfg in BUILDINGS.items() for r in cfg["rooms"]]


def campus_layout() -> dict:
    """{building: [rooms]} - lets the student page build its room picker from
    the same source of truth the validator uses, so it can never offer a room
    the API would reject."""
    return {b: sorted(c["rooms"]) for b, c in BUILDINGS.items()}


def campus_totals() -> dict:
    """Small summary, handy in tests and in the dashboard's header."""
    return {
        "buildings": len(BUILDINGS),
        "rooms": sum(len(c["rooms"]) for c in BUILDINGS.values()),
        "total_capacity": sum(
            r["capacity"] for c in BUILDINGS.values() for r in c["rooms"].values()
        ),
    }


if __name__ == "__main__":
    # `python campus_config.py` prints the campus. Useful sanity check.
    t = campus_totals()
    print(f"NorthBridge University — {t['buildings']} buildings, "
          f"{t['rooms']} rooms, capacity {t['total_capacity']} people")
    for b, cfg in BUILDINGS.items():
        rooms = ", ".join(f"{r} ({d['capacity']})" for r, d in cfg["rooms"].items())
        print(f"  {b:<12} baseline {cfg['energy_baseline_kwh']:>6.1f} kWh | {rooms}")
