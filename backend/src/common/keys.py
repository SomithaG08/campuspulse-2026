"""
Turning a validated, classified event into the DynamoDB item that gets stored.

The key design and its reasoning are in docs/architecture/04-data-model.md.
This module is the executable version of that document, and the two must stay
in step - if you change a key shape here, change it there in the same commit.

The one subtlety: gsi2pk is written ONLY for abnormal events. That is what
makes the alerts index sparse - a normal event has no key for that index and
so does not physically exist in it. GET /alerts therefore reads an index
containing alerts and nothing else, instead of filtering the whole table.
"""

from datetime import datetime, timedelta, timezone

from common import campus_config as cfg
from common import rules


def day_partition(timestamp: str) -> str:
    """'2026-09-22T14:05:00Z' -> 'DAY#2026-09-22'"""
    return f"DAY#{timestamp[:10]}"


def building_partition(building: str, timestamp: str) -> str:
    return f"BLD#{building}#{timestamp[:10]}"


def alert_partition(timestamp: str) -> str:
    return f"ALERT#{timestamp[:10]}"


def requester_partition(requester_id: str) -> str:
    """GSI3 key: every service request raised by one user, across days."""
    return f"USER#{requester_id}"


def sort_key(timestamp: str, event_id: str) -> str:
    """
    Sort keys are stored in order, so a key beginning with the timestamp means
    'newest first' is a query with ScanIndexForward=false - no sorting, no
    scanning. The event_id suffix keeps two events in the same second distinct.
    """
    return f"{timestamp}#{event_id}"


def build_item(event: dict, severity: str, reason: str, now: datetime = None) -> dict:
    """The complete item written by PutItem."""
    now = now or datetime.now(timezone.utc)
    ts = event["timestamp"]
    sk = sort_key(ts, event["event_id"])

    item = {
        "pk": day_partition(ts),
        "sk": sk,
        "gsi1pk": building_partition(event["building"], ts),
        "gsi1sk": sk,
        **event,
        "severity": severity,
        "reason": reason,
        "received_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        # TTL: DynamoDB deletes the item after this epoch second, at no charge.
        "expires_at": int((now + timedelta(days=cfg.TTL_DAYS)).timestamp()),
    }

    if rules.is_alert(severity):
        item["gsi2pk"] = alert_partition(ts)
        item["gsi2sk"] = sk

    # Sparse like GSI2: only service requests carry a requester, so GSI3 holds
    # requests and nothing else. It is what lets a student list THEIR OWN
    # requests with one Query, and never anybody else's.
    requester_id = event.get("requester_id")
    if requester_id:
        item["gsi3pk"] = requester_partition(requester_id)
        item["gsi3sk"] = sk

    return item
