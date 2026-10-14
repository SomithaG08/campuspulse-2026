"""
Key-building tests.

The sparse-index behaviour is the one to get right: if a normal event ever
gained an alert key, GET /alerts would start returning normal events and the
dashboard would cry wolf.
"""
from datetime import datetime, timezone

from common.keys import build_item
from common.rules import CRITICAL, NORMAL, WARNING

NOW = datetime(2026, 9, 22, 14, 5, 1, tzinfo=timezone.utc)

EVENT = {
    "event_id": "evt-2026-0042", "building": "Library-A", "room": "A203",
    "event_type": "occupancy", "value": 58.0, "unit": "people",
    "timestamp": "2026-09-22T14:05:00Z", "source": "simulator",
}


def test_primary_keys_match_the_data_model():
    item = build_item(EVENT, CRITICAL, "reason", now=NOW)
    assert item["pk"] == "DAY#2026-09-22"
    assert item["sk"] == "2026-09-22T14:05:00Z#evt-2026-0042"


def test_building_index_keys():
    item = build_item(EVENT, NORMAL, "reason", now=NOW)
    assert item["gsi1pk"] == "BLD#Library-A#2026-09-22"
    assert item["gsi1sk"] == item["sk"]


def test_alert_keys_written_only_for_abnormal_events():
    for severity in (WARNING, CRITICAL):
        item = build_item(EVENT, severity, "reason", now=NOW)
        assert item["gsi2pk"] == "ALERT#2026-09-22"
        assert item["gsi2sk"] == item["sk"]


def test_normal_event_is_absent_from_the_sparse_alert_index():
    item = build_item(EVENT, NORMAL, "reason", now=NOW)
    assert "gsi2pk" not in item
    assert "gsi2sk" not in item


def test_sort_key_orders_chronologically():
    """Newest-first is free only if string order equals time order."""
    early = build_item({**EVENT, "timestamp": "2026-09-22T09:00:00Z"}, NORMAL, "r", now=NOW)
    late = build_item({**EVENT, "timestamp": "2026-09-22T17:00:00Z"}, NORMAL, "r", now=NOW)
    assert early["sk"] < late["sk"]


def test_ttl_is_thirty_days_ahead():
    item = build_item(EVENT, NORMAL, "reason", now=NOW)
    assert item["expires_at"] == int(NOW.timestamp()) + 30 * 86400


def test_event_fields_are_preserved():
    item = build_item(EVENT, CRITICAL, "occupancy 58 exceeds 120% of capacity 45", now=NOW)
    assert item["building"] == "Library-A"
    assert item["severity"] == CRITICAL
    assert item["reason"] == "occupancy 58 exceeds 120% of capacity 45"
    assert item["received_at"] == "2026-09-22T14:05:01Z"
