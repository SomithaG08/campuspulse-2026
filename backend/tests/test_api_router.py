"""
Tests for the consolidated API function (handlers/api.py) and the role rules
introduced by the October 2026 review: two Cognito groups, admin and student.

No AWS is needed: the DynamoDB table is replaced by a stub that records what
it was asked to do, so we can prove both WHO may call a route and WHAT the
route would ask DynamoDB for.
"""

import io
import json
from contextlib import redirect_stdout
from datetime import datetime, timezone

import pytest

from common import auth, db, keys, log, queries
from handlers import api


class StubTable:
    def __init__(self, items=None):
        self.items = items or []
        self.puts = []
        self.queries = []

    def put_item(self, Item):
        self.puts.append(Item)

    def query(self, **kwargs):
        self.queries.append(kwargs)
        return {"Items": self.items}


class Ctx:
    aws_request_id = "test-request"


@pytest.fixture
def table():
    stub = StubTable()
    db.set_table(stub)
    yield stub
    db.set_table(None)


def ev(route, groups=None, body=None, params=None, sub="user-sub-1", email="s@nb.edu"):
    event = {"routeKey": route, "queryStringParameters": params}
    if body is not None:
        event["body"] = json.dumps(body)
    if groups is not None:
        event["requestContext"] = {"authorizer": {"jwt": {"claims": {
            "cognito:groups": groups, "sub": sub, "email": email,
            "cognito:username": sub,
        }}}}
    return event


def call(event):
    with redirect_stdout(io.StringIO()):
        response = api.handler(event, Ctx())
    return response["statusCode"], json.loads(response["body"])


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sensor_event():
    return {"event_id": "evt-t1", "building": "Library-A", "room": "A203",
            "event_type": "occupancy", "value": 20, "unit": "people",
            "timestamp": now_iso()}


def request_body(priority=2):
    return {"building": "Library-A", "room": "A203", "priority": priority,
            "message": "Projector not working"}


# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------

def test_every_terraform_route_has_a_handler():
    # Must match the routes in apigateway.tf (POST /login is the auth function).
    expected = {"GET /health", "POST /events", "POST /requests", "GET /requests",
                "GET /events", "GET /alerts", "GET /stats"}
    assert set(api.ROUTES) == expected


def test_unknown_route_is_404(table):
    status, body = call(ev("DELETE /events", groups=["admin"]))
    assert status == 404
    assert body["error"] == "NotFound"


def test_health_needs_no_identity(table):
    status, body = call(ev("GET /health"))
    assert status == 200 and body["status"] == "ok"


# --------------------------------------------------------------------------
# Role matrix - who may call what
# --------------------------------------------------------------------------

@pytest.mark.parametrize("route,groups,body,expected", [
    ("POST /events", ["admin"], sensor_event(), 201),
    ("POST /events", ["student"], sensor_event(), 403),
    ("GET /events", ["admin"], None, 200),
    ("GET /events", ["student"], None, 403),
    ("GET /alerts", ["admin"], None, 200),
    ("GET /alerts", ["student"], None, 403),
    ("GET /stats", ["admin"], None, 200),
    ("GET /stats", ["student"], None, 200),
    ("POST /requests", ["student"], request_body(), 201),
    ("POST /requests", ["admin"], request_body(), 201),
    ("GET /requests", ["student"], None, 200),
    ("GET /requests", ["admin"], None, 200),
    ("GET /stats", ["ops"], None, 403),      # old group names no longer work
    ("GET /stats", [], None, 403),
])
def test_role_matrix(table, route, groups, body, expected):
    status, _ = call(ev(route, groups=groups, body=body))
    assert status == expected


def test_no_identity_is_refused(table):
    status, _ = call(ev("GET /stats"))
    assert status == 403


# --------------------------------------------------------------------------
# Service requests: ownership
# --------------------------------------------------------------------------

def test_student_request_is_stored_under_their_sub(table):
    status, body = call(ev("POST /requests", groups=["student"], body=request_body(),
                           sub="sub-alice", email="alice@nb.edu"))
    assert status == 201
    item = table.puts[0]
    assert item["gsi3pk"] == "USER#sub-alice"
    assert item["requested_by"] == "alice@nb.edu"
    assert item["source"] == "student-portal"


def test_sensor_events_do_not_enter_the_requester_index(table):
    call(ev("POST /events", groups=["admin"], body=sensor_event()))
    assert "gsi3pk" not in table.puts[0]


def test_student_lists_only_their_own_requests(table):
    status, body = call(ev("GET /requests", groups=["student"], sub="sub-alice",
                           params={"requester": "sub-bob"}))  # a param cannot redirect it
    assert status == 200
    q = table.queries[0]
    assert q["IndexName"] == queries.REQUESTER_INDEX
    assert q["ExpressionAttributeValues"][":pk"] == "USER#sub-alice"
    assert body["scope"] == "your requests"


def test_admin_lists_the_days_requests_with_requester(table):
    table.items = [{"event_id": "req-1", "building": "Library-A", "room": "A203",
                    "event_type": "service_request", "value": 3, "unit": "priority",
                    "severity": "critical", "requested_by": "alice@nb.edu"}]
    status, body = call(ev("GET /requests", groups=["admin"], params={"date": "2026-10-12"}))
    assert status == 200
    q = table.queries[0]
    assert q["FilterExpression"] == "event_type = :sr"
    assert q["ExpressionAttributeValues"][":pk"] == "DAY#2026-10-12"
    assert body["requests"][0]["requested_by"] == "alice@nb.edu"
    assert body["requests"][0]["priority_label"] == "urgent"
    assert body["urgent_count"] == 1


def test_student_view_hides_requester_field(table):
    table.items = [{"event_id": "req-1", "event_type": "service_request", "value": 1,
                    "requested_by": "alice@nb.edu"}]
    _, body = call(ev("GET /requests", groups=["student"]))
    assert "requested_by" not in body["requests"][0]


def test_stats_includes_layout_for_the_room_picker(table):
    _, body = call(ev("GET /stats", groups=["student"]))
    assert "Library-A" in body["layout"]
    assert "A203" in body["layout"]["Library-A"]


# --------------------------------------------------------------------------
# Alert metrics - what the email alarms watch
# --------------------------------------------------------------------------

def _emf_lines(output):
    return [json.loads(l) for l in output.splitlines() if l.startswith('{"_aws"')]


def test_urgent_request_emits_urgent_metric(table):
    out = io.StringIO()
    with redirect_stdout(out):
        api.handler(ev("POST /requests", groups=["student"], body=request_body(priority=3)), Ctx())
    names = [list(l["_aws"]["CloudWatchMetrics"][0]["Metrics"])[0]["Name"] for l in _emf_lines(out.getvalue())]
    assert "UrgentRequests" in names
    assert "AlertsRaised" in names


def test_alert_metric_has_a_campus_wide_series():
    out = io.StringIO()
    with redirect_stdout(out):
        log.metric("AlertsRaised", 1, aggregate=True, Severity="critical")
    line = _emf_lines(out.getvalue())[0]
    assert line["_aws"]["CloudWatchMetrics"][0]["Dimensions"] == [["Severity"], []]


def test_role_reported_at_login_prefers_admin():
    import base64
    import os
    os.environ.setdefault("COGNITO_CLIENT_ID", "test-client")
    os.environ.setdefault("AWS_DEFAULT_REGION", "eu-west-3")
    from handlers import auth as auth_handler

    payload = base64.urlsafe_b64encode(json.dumps(
        {"cognito:groups": ["student", "admin"]}).encode()).decode().rstrip("=")
    token = f"x.{payload}.y"
    assert auth_handler._role_from_id_token(token) == "admin"


def test_keys_requester_partition():
    assert keys.requester_partition("abc") == "USER#abc"


def test_my_requests_refuses_empty_identity():
    from common.validation import ValidationError
    with pytest.raises(ValidationError):
        queries.my_requests("")


def test_admin_requests_page_past_the_filter(table):
    # Page 1 holds only sensor events (filtered out -> no items) but has more;
    # page 2 holds the request. One page would have shown nothing.
    pages = [
        {"Items": [], "LastEvaluatedKey": {"pk": "DAY#2026-10-12", "sk": "x"}},
        {"Items": [{"event_id": "req-9", "event_type": "service_request", "value": 2}]},
    ]
    table.query = lambda **kw: (table.queries.append(kw), pages[len(table.queries) - 1])[1]
    status, body = call(ev("GET /requests", groups=["admin"]))
    assert status == 200
    assert len(table.queries) == 2
    assert body["requests"][0]["event_id"] == "req-9"
    assert body["next_token"] is None
