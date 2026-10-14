"""
GET /stats - the aggregated campus picture.

This is the endpoint that answers every operational question in the project
brief: which rooms are overloaded, which building uses the most energy, what
is abnormal, how many urgent requests are waiting.

HOW IT WORKS, AND ITS ONE HONEST LIMIT
--------------------------------------
It queries one day's partition, pages through up to MAX_STATS_PAGES pages, and
summarises the items in memory with a pure function. At our volume - a few
hundred events a day - that is one or two queries and a few milliseconds.

The limit is real and we state it rather than hide it: a day with tens of
thousands of events would hit the page cap and the statistics would cover only
the most recent slice. The response says so in `truncated`, and the
scalability section explains the fix (maintain counters on write, or
pre-aggregate per hour) instead of pretending the ceiling does not exist.
"""

from botocore.exceptions import ClientError

from common import aggregate, auth, db, log, queries, responses
from common.validation import ValidationError


def handler(event, context):
    request_id = getattr(context, "aws_request_id", None)

    # Both roles: administrators get the operational picture, students use the
    # same numbers to find a free room. Nothing personal is in this response.
    refusal = auth.check_group(event, (auth.ADMIN, auth.STUDENT))
    if refusal:
        return responses.forbidden(refusal, request_id)

    params = event.get("queryStringParameters") or {}

    try:
        date = queries.parse_date(params.get("date"))
        building = (params.get("building") or "").strip() or None
    except ValidationError as exc:
        return responses.bad_request(exc.message, request_id)

    items = []
    token = None
    pages = 0
    truncated = False

    try:
        while True:
            args = queries.day_events_for_stats(date, building, token)
            result = db.table().query(**args)
            items.extend(result.get("Items", []))
            pages += 1

            token = result.get("LastEvaluatedKey")
            if not token:
                break
            if pages >= queries.MAX_STATS_PAGES:
                truncated = True
                log.warn("stats truncated at page cap", request_id,
                         date=date, pages=pages, items=len(items))
                break
    except ClientError as exc:
        log.error("stats query failed", request_id,
                  reason=exc.response.get("Error", {}).get("Code", ""))
        return responses.server_error(request_id)

    summary = aggregate.summarise(items, date)
    summary["truncated"] = truncated
    if building:
        summary["building_filter"] = building

    log.info("stats served", request_id, date=date, pages=pages,
             events=summary["total_events"], alerts=summary["alert_count"])
    log.metric("StatsRequested", 1)

    return responses.ok(summary)
