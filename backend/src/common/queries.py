"""
Builds the DynamoDB query arguments for the read path.

WHY THIS IS A SEPARATE MODULE
-----------------------------
A query builder is pure logic: parameters in, a dict of arguments out. Keeping
it out of the handlers means we can test every access pattern - and prove no
Scan exists anywhere - without an AWS account.

The five access patterns are listed in docs/architecture/04-data-model.md.
Each function below is one of them.
"""

import base64
import json
from datetime import datetime, timezone
from typing import Optional

from common import keys
from common.validation import ValidationError

TABLE_INDEX = None  # the table itself has no index name
BUILDING_INDEX = "gsi1-by-building"
ALERT_INDEX = "gsi2-alerts"
REQUESTER_INDEX = "gsi3-by-requester"

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

# A hard ceiling on how many pages /stats will read in one request. At our
# scale a day fits in one or two pages; this stops a pathological day from
# turning one dashboard refresh into hundreds of read units.
MAX_STATS_PAGES = 10


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def parse_date(value: Optional[str]) -> str:
    """Defaults to today (UTC). Rejects anything that is not YYYY-MM-DD."""
    if not value:
        return today()
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise ValidationError("date must be in YYYY-MM-DD format")
    return value


def parse_limit(value: Optional[str]) -> int:
    if value in (None, ""):
        return DEFAULT_LIMIT
    try:
        limit = int(value)
    except (ValueError, TypeError):
        raise ValidationError("limit must be an integer")
    if not 1 <= limit <= MAX_LIMIT:
        raise ValidationError(f"limit must be between 1 and {MAX_LIMIT}")
    return limit


def encode_token(last_key: Optional[dict]) -> Optional[str]:
    """
    DynamoDB returns LastEvaluatedKey - the key to resume from. We hand it to
    the client as an opaque base64 string rather than raw JSON, so nobody is
    tempted to construct one by hand and so the shape can change later without
    breaking callers.
    """
    if not last_key:
        return None
    return base64.urlsafe_b64encode(json.dumps(last_key, default=str).encode()).decode()


def decode_token(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    try:
        decoded = json.loads(base64.urlsafe_b64decode(token.encode()))
    except Exception:
        raise ValidationError("next_token is not valid")
    if not isinstance(decoded, dict):
        raise ValidationError("next_token is not valid")
    return decoded


def _base(limit: int, token: Optional[dict]) -> dict:
    args = {
        "Limit": limit,
        # Sort keys begin with the timestamp, so reading the index backwards
        # gives newest-first for free - no sorting, no extra reads.
        "ScanIndexForward": False,
    }
    if token:
        args["ExclusiveStartKey"] = token
    return args


def recent_events(date: str, limit: int = DEFAULT_LIMIT,
                  building: Optional[str] = None,
                  token: Optional[dict] = None) -> dict:
    """
    Access pattern 1 (whole campus) and 2 (one building).

    Note the index switch: asking for one building moves the query to GSI1
    instead of filtering the day's events in the function. Filtering after
    reading still pays to read everything; querying the right index does not.
    """
    args = _base(limit, token)
    if building:
        args["IndexName"] = BUILDING_INDEX
        args["KeyConditionExpression"] = "gsi1pk = :pk"
        args["ExpressionAttributeValues"] = {":pk": keys.building_partition(building, f"{date}T00:00:00Z")}
    else:
        args["KeyConditionExpression"] = "pk = :pk"
        args["ExpressionAttributeValues"] = {":pk": keys.day_partition(f"{date}T00:00:00Z")}
    return args


def alerts(date: str, limit: int = DEFAULT_LIMIT,
           severity: Optional[str] = None,
           token: Optional[dict] = None) -> dict:
    """
    Access pattern 3.

    Reads the sparse alerts index, which physically contains only abnormal
    events. A severity filter is applied with FilterExpression - acceptable
    here precisely because the index is already small; the same filter against
    the full table would be the wrong design.
    """
    if severity and severity not in ("warning", "critical"):
        raise ValidationError("severity must be 'warning' or 'critical'")

    args = _base(limit, token)
    args["IndexName"] = ALERT_INDEX
    args["KeyConditionExpression"] = "gsi2pk = :pk"
    args["ExpressionAttributeValues"] = {":pk": keys.alert_partition(f"{date}T00:00:00Z")}

    if severity:
        args["FilterExpression"] = "severity = :sev"
        args["ExpressionAttributeValues"][":sev"] = severity
    return args


def day_events_for_stats(date: str, building: Optional[str] = None,
                         token: Optional[dict] = None) -> dict:
    """
    Access pattern 4 - everything for one day, to aggregate.

    Limit is the maximum page size rather than a user-facing limit: the stats
    handler pages through up to MAX_STATS_PAGES of these.
    """
    args = recent_events(date, limit=MAX_LIMIT, building=building, token=token)
    return args


def my_requests(requester_id: str, limit: int = DEFAULT_LIMIT,
                token: Optional[dict] = None) -> dict:
    """
    Access pattern 5 - a student's own service requests, newest first.

    The partition key is built from the caller's verified Cognito `sub`, never
    from a query-string parameter, so there is no way to ask for someone
    else's requests: the key simply cannot be pointed at another user.
    """
    if not requester_id:
        raise ValidationError("no user identity on this request")
    args = _base(limit, token)
    args["IndexName"] = REQUESTER_INDEX
    args["KeyConditionExpression"] = "gsi3pk = :pk"
    args["ExpressionAttributeValues"] = {":pk": keys.requester_partition(requester_id)}
    return args


def day_requests(date: str, token: Optional[dict] = None) -> dict:
    """
    Access pattern 6 - every service request of one day (administrator view).

    Reads the day partition with a FilterExpression on event_type, one page of
    MAX_LIMIT items at a time; the handler pages through up to MAX_STATS_PAGES
    pages, exactly like /stats. Filtering after reading is normally the wrong
    design and we use it knowingly: a day is a few hundred items, so this is
    one or two pages. DynamoDB's Limit applies BEFORE the filter, which is why
    the handler must page rather than trust one page to hold every request.
    The scaling fix is a sparse index keyed REQ#<date>; documented, not built.
    """
    args = recent_events(date, limit=MAX_LIMIT, token=token)
    args["FilterExpression"] = "event_type = :sr"
    args["ExpressionAttributeValues"][":sr"] = "service_request"
    return args
