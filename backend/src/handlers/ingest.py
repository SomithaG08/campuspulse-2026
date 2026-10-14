"""
POST /events and POST /requests - the only write path in the system.

THE SHAPE OF THIS FUNCTION IS THE SECURITY ARGUMENT
---------------------------------------------------
Since the October 2026 consolidation this module is no longer its own Lambda:
it is one route of the single API function (handlers/api.py). The IAM role of
that function allows PutItem and Query on one table and nothing else - no
Scan, no Delete, no other table - and the function runs in private subnets
whose only network path leads to that table (see vpc.tf). The trade-off
against the old write-only role is recorded in AD-11.

Order of work, and none of it is interchangeable:
  1. authorize   - is this caller's group allowed on this route?  (403)
  2. validate    - is this payload well-formed and plausible?     (400)
  3. classify    - what severity does OUR rule give it?
  4. build item  - construct the keys, including the sparse alert key
  5. store       - one PutItem
  6. observe     - one structured log line, one or two metrics
"""

from datetime import datetime, timezone

from botocore.exceptions import ClientError

from common import auth, db, keys, log, responses, rules
from common.validation import ValidationError, validate_event, validate_service_request


def handler(event, context):
    request_id = getattr(context, "aws_request_id", None)
    route = event.get("routeKey") or f"{event.get('rawPath', '')}"
    is_service_request = "/requests" in route

    # ---- 1. Authorization ------------------------------------------------
    # Submitting sensor data is an administrator action (the simulator signs
    # in as an admin). Students may raise a service request but may never
    # inject readings into the campus telemetry.
    allowed = (auth.ADMIN, auth.STUDENT) if is_service_request else (auth.ADMIN,)
    refusal = auth.check_group(event, allowed)
    if refusal:
        claims = auth.get_claims(event)
        log.warn("forbidden", request_id, route=route, user=auth.get_username(claims))
        return responses.forbidden(refusal, request_id)

    now = datetime.now(timezone.utc)

    # ---- 2. Validation ---------------------------------------------------
    try:
        if is_service_request:
            claims = auth.get_claims(event)
            clean = validate_service_request(event.get("body"), auth.get_email(claims), now=now)
            # The stable id is what GET /requests keys on, so a student can
            # only ever list requests stored under their own Cognito sub.
            clean["requester_id"] = auth.get_user_id(claims)
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
        db.table().put_item(Item=_to_dynamo(item))
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
    log.metric("EventsIngested", 1, aggregate=True, Severity=severity)
    if alert:
        # Published with and without the Severity dimension: the alarms that
        # email the team watch the critical series and the campus-wide total.
        log.metric("AlertsRaised", 1, aggregate=True, Severity=severity)
    if clean["event_type"] == "service_request" and severity == rules.CRITICAL:
        # An urgent student request: its own metric so its own alarm can email
        # the team immediately (alarms.tf, urgent_request).
        log.metric("UrgentRequests", 1)

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
