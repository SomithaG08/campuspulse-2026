"""
Query builder tests.

The headline assertion is the last one: no query this system can build ever
performs a Scan. Everything else checks that each access pattern hits the
right index with the right key.
"""
import pytest

from common import queries as q
from common.validation import ValidationError

DATE = "2026-10-04"


# --- parameter parsing -----------------------------------------------------

def test_date_defaults_to_today():
    assert len(q.parse_date(None)) == 10


@pytest.mark.parametrize("bad", ["04-10-2026", "2026/10/04", "yesterday", "2026-13-01", 42])
def test_invalid_date_rejected(bad):
    with pytest.raises(ValidationError):
        q.parse_date(bad)


def test_limit_defaults_and_bounds():
    assert q.parse_limit(None) == q.DEFAULT_LIMIT
    assert q.parse_limit("10") == 10
    assert q.parse_limit(str(q.MAX_LIMIT)) == q.MAX_LIMIT


@pytest.mark.parametrize("bad", ["0", "-5", "201", "abc", "1.5"])
def test_invalid_limit_rejected(bad):
    with pytest.raises(ValidationError):
        q.parse_limit(bad)


# --- pagination tokens -----------------------------------------------------

def test_token_round_trip():
    key = {"pk": "DAY#2026-10-04", "sk": "2026-10-04T09:00:00Z#evt-1"}
    assert q.decode_token(q.encode_token(key)) == key


def test_no_token_when_no_more_pages():
    assert q.encode_token(None) is None
    assert q.decode_token(None) is None


@pytest.mark.parametrize("bad", ["not-base64!!", "eyJhIjog", "W10="])
def test_malformed_token_rejected(bad):
    with pytest.raises(ValidationError):
        q.decode_token(bad)


# --- access pattern 1: recent events across campus -------------------------

def test_recent_events_queries_the_day_partition():
    args = q.recent_events(DATE)
    assert args["KeyConditionExpression"] == "pk = :pk"
    assert args["ExpressionAttributeValues"][":pk"] == "DAY#2026-10-04"
    assert "IndexName" not in args


def test_newest_first():
    assert q.recent_events(DATE)["ScanIndexForward"] is False


# --- access pattern 2: one building ----------------------------------------

def test_building_filter_switches_to_the_building_index():
    """Querying the right index beats reading everything and filtering."""
    args = q.recent_events(DATE, building="Library-A")
    assert args["IndexName"] == q.BUILDING_INDEX
    assert args["ExpressionAttributeValues"][":pk"] == "BLD#Library-A#2026-10-04"
    assert "FilterExpression" not in args


# --- access pattern 3: alerts ----------------------------------------------

def test_alerts_use_the_sparse_index():
    args = q.alerts(DATE)
    assert args["IndexName"] == q.ALERT_INDEX
    assert args["ExpressionAttributeValues"][":pk"] == "ALERT#2026-10-04"


def test_severity_filter_applied_on_the_small_index():
    args = q.alerts(DATE, severity="critical")
    assert args["FilterExpression"] == "severity = :sev"
    assert args["ExpressionAttributeValues"][":sev"] == "critical"


def test_invalid_severity_rejected():
    with pytest.raises(ValidationError):
        q.alerts(DATE, severity="catastrophic")


# --- access pattern 4: stats -----------------------------------------------

def test_stats_query_uses_max_page_size():
    assert q.day_events_for_stats(DATE)["Limit"] == q.MAX_LIMIT


def test_stats_can_be_scoped_to_one_building():
    assert q.day_events_for_stats(DATE, building="Science-B")["IndexName"] == q.BUILDING_INDEX


def test_resume_token_becomes_exclusive_start_key():
    token = {"pk": "DAY#2026-10-04", "sk": "x"}
    assert q.recent_events(DATE, token=token)["ExclusiveStartKey"] == token


# --- the design guarantee --------------------------------------------------

def test_no_builder_can_produce_a_scan():
    """
    Every access pattern supplies a partition key, which is what makes it a
    Query. If this test ever fails, the key design has gone wrong - see the
    'no Scan anywhere' rule in docs/architecture/04-data-model.md.
    """
    builders = [
        q.recent_events(DATE),
        q.recent_events(DATE, building="Arts-C"),
        q.alerts(DATE),
        q.alerts(DATE, severity="warning"),
        q.day_events_for_stats(DATE),
    ]
    for args in builders:
        assert "KeyConditionExpression" in args
        assert ":pk" in args["ExpressionAttributeValues"]
