"""
GET /events and GET /alerts - reading events back.

Since October 2026 this is a route of the single API function, not its own
Lambda. Both routes are administrator-only: raw telemetry and the alert list
are operations views. Students see the campus through GET /stats and their own
requests through GET /requests.

Both routes are thin: validate the query string, build a key condition, run
one Query, shape the response. No filtering in Python over data we paid to
read, because the right index was chosen instead.
"""

from botocore.exceptions import ClientError

from common import auth, db, log, queries, responses
from common.validation import ValidationError

# Fields returned to the client. Listing them explicitly means the internal
# key attributes (pk, sk, gsi1pk, expires_at) never leak into the API, so the
# storage design can change without breaking the dashboard.
PUBLIC_FIELDS = (
    "event_id", "building", "room", "event_type", "value", "unit",
    "severity", "reason", "timestamp", "received_at", "source", "message",
)

# Service requests additionally show who raised them - to administrators only.
REQUEST_FIELDS = PUBLIC_FIELDS + ("requested_by",)


def _public(item: dict, fields: tuple = PUBLIC_FIELDS) -> dict:
    out = {}
    for field in fields:
        if field in item:
            value = item[field]
            # Decimal is not JSON-serialisable; value is the only number here.
            out[field] = float(value) if field == "value" else value
    return out


def handler(event, context):
    request_id = getattr(context, "aws_request_id", None)
    route = event.get("routeKey") or event.get("rawPath", "")
    wants_alerts = "/alerts" in route

    refusal = auth.check_group(event, (auth.ADMIN,))
    if refusal:
        return responses.forbidden(refusal, request_id)

    params = event.get("queryStringParameters") or {}

    try:
        date = queries.parse_date(params.get("date"))
        limit = queries.parse_limit(params.get("limit"))
        token = queries.decode_token(params.get("next_token"))

        if wants_alerts:
            args = queries.alerts(date, limit, params.get("severity"), token)
        else:
            building = (params.get("building") or "").strip() or None
            args = queries.recent_events(date, limit, building, token)
    except ValidationError as exc:
        return responses.bad_request(exc.message, request_id)

    try:
        result = db.table().query(**args)
    except ClientError as exc:
        log.error("query failed", request_id,
                  reason=exc.response.get("Error", {}).get("Code", ""), route=route)
        return responses.server_error(request_id)

    items = [_public(item) for item in result.get("Items", [])]
    next_token = queries.encode_token(result.get("LastEvaluatedKey"))

    log.info("query served", request_id, route=route, date=date,
             count=len(items), scanned=result.get("ScannedCount"))

    if wants_alerts:
        return responses.ok({
            "count": len(items),
            "critical_count": sum(1 for i in items if i.get("severity") == "critical"),
            "warning_count": sum(1 for i in items if i.get("severity") == "warning"),
            "date": date,
            "alerts": items,
            "next_token": next_token,
        })

    return responses.ok({
        "count": len(items),
        "date": date,
        "events": items,
        "next_token": next_token,
    })
