"""
Turns a day's raw events into the GET /stats response.

This is the "analytics" half of the project's data processing: classification
happens on write (rules.py), aggregation happens on read (here). The response
shape is fixed by docs/architecture/05-api-contract.md.

WHY AGGREGATE ON READ RATHER THAN MAINTAIN COUNTERS ON WRITE
------------------------------------------------------------
Keeping running totals in the database would make /stats a single tiny read,
and at large scale that is the right answer. At our scale a day is a few
hundred items - one query - and read-time aggregation has two advantages we
care about more: there is no counter to drift out of sync with reality, and
changing a statistic means changing one pure function instead of backfilling
stored totals. The scalability section says what we would do differently with
a thousand times the volume.
"""

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from common import campus_config as cfg


def _num(value) -> float:
    """DynamoDB returns numbers as Decimal; JSON cannot serialise them."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def summarise(items: Iterable[dict], date: str) -> dict:
    """
    One pass over the day's events.

    Items are expected newest-first (that is how every query returns them),
    which is what makes "current occupancy" simply the first reading seen for
    each room.
    """
    by_type = defaultdict(int)
    by_severity = defaultdict(int)
    total = 0
    alert_count = 0
    urgent_requests = 0

    latest_occupancy: dict = {}          # (building, room) -> first seen = most recent
    temp_sum: dict = defaultdict(float)  # building -> running sum
    temp_count: dict = defaultdict(int)
    energy: dict = defaultdict(float)    # building -> kWh total for the day

    for item in items:
        total += 1
        event_type = item.get("event_type", "unknown")
        severity = item.get("severity", "unknown")
        building = item.get("building", "unknown")
        room = item.get("room", "-")
        value = _num(item.get("value"))

        by_type[event_type] += 1
        by_severity[severity] += 1
        if severity != "normal":
            alert_count += 1

        if event_type == "occupancy" and room != cfg.BUILDING_LEVEL_ROOM:
            key = (building, room)
            if key not in latest_occupancy:  # newest-first: first wins
                latest_occupancy[key] = (value, item.get("timestamp"))

        elif event_type == "temperature":
            temp_sum[building] += value
            temp_count[building] += 1

        elif event_type == "energy":
            energy[building] += value

        elif event_type == "service_request" and int(value) == 3:
            urgent_requests += 1

    occupancy = []
    for (building, room), (value, timestamp) in sorted(latest_occupancy.items()):
        capacity = cfg.get_capacity(building, room)
        occupancy.append({
            "building": building,
            "room": room,
            "value": value,
            "capacity": capacity,
            "load_pct": round(value / capacity * 100) if capacity else None,
            "timestamp": timestamp,
        })
    # Most overloaded room first - it is the one an operator needs to see.
    occupancy.sort(key=lambda r: r["load_pct"] if r["load_pct"] is not None else -1, reverse=True)

    avg_temperature = {
        building: round(temp_sum[building] / temp_count[building], 1)
        for building in temp_sum if temp_count[building]
    }

    energy_by_building = {b: round(v, 1) for b, v in energy.items()}
    top_energy = max(energy_by_building, key=energy_by_building.get) if energy_by_building else None

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": date,
        "total_events": total,
        "alert_count": alert_count,
        "events_by_type": dict(sorted(by_type.items())),
        "events_by_severity": dict(sorted(by_severity.items())),
        "current_occupancy": occupancy,
        "avg_temperature_c": dict(sorted(avg_temperature.items())),
        "energy_kwh_by_building": dict(sorted(energy_by_building.items())),
        "top_energy_building": top_energy,
        "urgent_requests": urgent_requests,
        "campus": cfg.campus_totals(),
    }
