"""
GET /requests - student service requests.

One route, two answers, decided by the caller's Cognito group:

  * student -> THEIR OWN requests only (any day), read from the sparse GSI3
               with a key built from their verified `sub`. A student cannot
               ask for another student's requests because there is no
               parameter to ask with.
  * admin   -> every request raised on one day (?date=YYYY-MM-DD, default
               today), including who raised it, so the operations team can
               triage and escalate.

POST /requests (raising one) is handled by ingest.py.
"""

from botocore.exceptions import ClientError

from common import auth, db, log, queries, responses
from common.validation import ValidationError

from handlers.query import REQUEST_FIELDS, _public

PRIORITY_LABELS = {1: "low", 2: "normal", 3: "urgent"}


def _shape(item: dict, include_requester: bool) -> dict:
    fields = REQUEST_FIELDS if include_requester else tuple(
        f for f in REQUEST_FIELDS if f != "requested_by")
    out = _public(item, fields)
    priority = int(out.get("value", 2))
    out["priority"] = priority
    out["priority_label"] = PRIORITY_LABELS.get(priority, str(priority))
    return out


def handler(event, context):
    request_id = getattr(context, "aws_request_id", None)

    refusal = auth.check_group(event, (auth.ADMIN, auth.STUDENT))
    if refusal:
        return responses.forbidden(refusal, request_id)

    is_admin = auth.has_group(event, auth.ADMIN)
    params = event.get("queryStringParameters") or {}

    try:
        limit = queries.parse_limit(params.get("limit"))
        token = queries.decode_token(params.get("next_token"))
        if is_admin:
            date = queries.parse_date(params.get("date"))
        else:
            date = None
            user_id = auth.get_user_id(auth.get_claims(event))
            args = queries.my_requests(user_id, limit, token)
    except ValidationError as exc:
        return responses.bad_request(exc.message, request_id)

    raw, last_key = [], None
    try:
        if is_admin:
            # Page through the day (Limit applies before the filter, so one
            # page is not enough), stopping at `limit` requests or the cap.
            pages = 0
            while True:
                result = db.table().query(**queries.day_requests(date, token))
                raw.extend(result.get("Items", []))
                pages += 1
                token = result.get("LastEvaluatedKey")
                if not token or len(raw) >= limit or pages >= queries.MAX_STATS_PAGES:
                    break
            raw, last_key = raw[:limit], token
        else:
            result = db.table().query(**args)
            raw, last_key = result.get("Items", []), result.get("LastEvaluatedKey")
    except ClientError as exc:
        log.error("requests query failed", request_id,
                  reason=exc.response.get("Error", {}).get("Code", ""))
        return responses.server_error(request_id)

    items = [_shape(i, include_requester=is_admin) for i in raw]
    log.info("requests served", request_id, scope="day" if is_admin else "own",
             count=len(items))

    body = {
        "scope": "all requests for the day" if is_admin else "your requests",
        "count": len(items),
        "urgent_count": sum(1 for i in items if i["priority"] == 3),
        "requests": items,
        "next_token": queries.encode_token(last_key),
    }
    if date:
        body["date"] = date
    return responses.ok(body)
