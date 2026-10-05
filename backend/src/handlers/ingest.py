"""
POST /events and POST /requests - the only write path in the system.

THE SHAPE OF THIS FUNCTION IS THE SECURITY ARGUMENT
---------------------------------------------------
This is the function exposed to the internet, so it is the one an attacker
reaches first. Its IAM role allows exactly one action: dynamodb:PutItem on one
table. It cannot Query, cannot Scan, cannot Delete, cannot read a single
stored event. If someone found a flaw in the code below, the worst they could
do is add junk events - not read one student service request.

Order of work, and none of it is interchangeable:
  1. authorize   - is this caller's group allowed on this route?  (403)
  2. validate    - is this payload well-formed and plausible?     (400)
  3. classify    - what severity does OUR rule give it?
  4. build item  - construct the keys, including the sparse alert key
  5. store       - one PutItem
  6. observe     - one structured log line, one or two metrics
"""

import os
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from common import auth, keys, log, responses, rules
from common.validation import ValidationError, validate_event, validate_service_request

# Module scope: reused across warm invocations.
_table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])


def handler(event, context):
    request_id = getattr(context, "aws_request_id", None)
    route = event.get("routeKey") or f"{event.get('rawPath', '')}"
    is_service_request = "/requests" in route

    # ---- 1. Authorization ------------------------------------------------
    # Submitting sensor data is an operations action. Staff may raise a
    # service request but may not inject readings into the campus telemetry.
    allowed = (auth.OPS, auth.STAFF) if is_service_request else (auth.OPS,)
    refusal = auth.check_group(event, allowed)
    if refusal:
        claims = auth.get_claims(event)
        log.warn("forbidden", request_id, route=route, user=auth.get_username(claims))
        return responses.forbidden(refusal, request_id)

    now = datetime.now(timezone.utc)

    # ---- 2. Validation ---------------------------------------------------
    try:
        if is_service_request:
            username = auth.get_username(auth.get_claims(event))
            clean = validate_service_request(event.get("body"), username, now=now)
        else:
            clean = validate_event(event.get("body"), now=now)
    except ValidationError as exc:
        log.warn("validation failed", request_id, route=route, reason=exc.message)
        return responses.bad_request(exc.message, request_id)

    # ---- 3. Classification ----------------------------------------------
    # Whatever severity the client sent was discarded during validation. This
    # is where the real one is decided.
    severity, reason = rules.classify(clean)
    alert = rules.is_alert(severity)

    # ---- 4 & 5. Build and store -----------------------------------------
    item = keys.build_item(clean, severity, reason, now=now)

    try:
        _table.put_item(Item=_to_dynamo(item))
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        log.error("failed to store event", request_id, reason=code, event_id=clean["event_id"])
        # AccessDenied here means the IAM policy is wrong; throttling means we
        # outgrew on-demand's instant capacity. Both are our problem, not the
        # caller's, so both are a 500.
        return responses.server_error(request_id)

    # ---- 6. Observability ------------------------------------------------
    latency_ms = int((datetime.now(timezone.utc) - now).total_seconds() * 1000)
    log.info(
        "event stored",
        request_id,
        event_id=clean["event_id"],
        building=clean["building"],
        room=clean["room"],
        event_type=clean["event_type"],
        value=clean["value"],
        severity=severity,
        reason=reason,
        alert=alert,
        latency_ms=latency_ms,
    )
    log.metric("EventsIngested", 1, Severity=severity)
    if alert:
        log.metric("AlertsRaised", 1, Severity=severity)

    return responses.created({
        "event_id": clean["event_id"],
        "severity": severity,
        "reason": reason,
        "alert": alert,
        "stored_at": item["received_at"],
    })


def _to_dynamo(item: dict) -> dict:
    """
    DynamoDB stores numbers as Decimal and rejects Python floats.

    Converting through str() rather than float() avoids binary floating-point
    surprises - Decimal(0.1) is 0.1000000000000000055511151231257827, while
    Decimal("0.1") is exactly 0.1.
    """
    from decimal import Decimal

    out = {}
    for key, value in item.items():
        if isinstance(value, float):
            out[key] = Decimal(str(value))
        elif isinstance(value, bool) or value is None:
            out[key] = value
        else:
            out[key] = value
    return out
