#!/usr/bin/env python3
"""
CampusPulse 2026 - API test suite.

Runs against a DEPLOYED stack. The unit tests in backend/tests and
simulator/tests prove the logic; these prove the deployment - that the pieces
are wired together, that IAM allows what it should, and that the two roles
really do get different answers.

Zero dependencies, standard library only, same reasoning as the simulator:
anybody can run it immediately and nothing can fail because of an install.

USAGE
    export CAMPUSPULSE_API=https://xxxx.execute-api.eu-west-3.amazonaws.com
    export ADMIN_USER=admin@northbridge.edu       ADMIN_PASSWORD='...'
    export STUDENT_USER=student@northbridge.edu   STUDENT_PASSWORD='...'

    python tests/api/run_api_tests.py

Exits 0 if every test passes, 1 otherwise. Writes docs/evidence/api-test-results.json,
which is the artefact the report cites - real output, never retyped by hand.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = (os.environ.get("CAMPUSPULSE_API") or "").rstrip("/")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin@northbridge.edu")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
STUDENT_USER = os.environ.get("STUDENT_USER", "student@northbridge.edu")
STUDENT_PASSWORD = os.environ.get("STUDENT_PASSWORD", "")

results = []
tokens = {}


# ---------------------------------------------------------------------------
# A very small test harness. Writing one is three lines; pulling in a framework
# that needs installing would cost more than it saves for 23 checks.
# ---------------------------------------------------------------------------

def call(method, path, body=None, token=None):
    """Returns (status, parsed_body, elapsed_ms). Never raises on an HTTP status."""
    url = API + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)

    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            elapsed = int((time.time() - started) * 1000)
            return response.status, json.loads(response.read() or b"{}"), elapsed
    except urllib.error.HTTPError as exc:
        elapsed = int((time.time() - started) * 1000)
        raw = exc.read()
        try:
            return exc.code, json.loads(raw or b"{}"), elapsed
        except json.JSONDecodeError:
            return exc.code, {"raw": raw[:200].decode(errors="replace")}, elapsed
    except urllib.error.URLError as exc:
        return 0, {"error": "ConnectionError", "message": str(exc.reason)}, 0


def check(test_id, description, condition, detail=""):
    ok = bool(condition)
    results.append({"id": test_id, "description": description,
                    "status": "PASS" if ok else "FAIL", "detail": detail})
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {test_id}  {description}")
    if not ok and detail:
        print(f"         {detail}")
    return ok


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def event(**overrides):
    base = {
        "event_id": f"test-{int(time.time() * 1000)}",
        "building": "Library-A", "room": "A203",
        "event_type": "occupancy", "value": 10, "unit": "people",
        "severity": "normal", "timestamp": utc_now(),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# T1 - reachability
# ---------------------------------------------------------------------------
def test_health():
    print("\nT1  Reachability")
    status, body, ms = call("GET", "/health")
    check("T1.1", "GET /health returns 200 without a token", status == 200, f"got {status}")
    check("T1.2", "health reports a version", bool(body.get("version")), str(body))
    print(f"         (first call took {ms} ms - cold start if this is high)")


# ---------------------------------------------------------------------------
# T2 - authentication
# ---------------------------------------------------------------------------
def test_authentication():
    print("\nT2  Authentication")

    status, body, _ = call("POST", "/login", {"username": ADMIN_USER, "password": ADMIN_PASSWORD})
    if check("T2.1", "valid admin credentials return a token", status == 200 and "id_token" in body,
             f"got {status}: {body.get('message', '')}"):
        tokens["admin"] = body["id_token"]
        check("T2.2", "login reports the admin role", body.get("role") == "admin", str(body.get("role")))

    status, body, _ = call("POST", "/login", {"username": STUDENT_USER, "password": STUDENT_PASSWORD})
    if check("T2.3", "valid student credentials return a token", status == 200 and "id_token" in body,
             f"got {status}: {body.get('message', '')}"):
        tokens["student"] = body["id_token"]
        check("T2.4", "login reports the student role", body.get("role") == "student", str(body.get("role")))

    status, wrong_pw, _ = call("POST", "/login", {"username": ADMIN_USER, "password": "definitely-wrong-123!"})
    check("T2.5", "wrong password is rejected with 401", status == 401, f"got {status}")

    status, unknown, _ = call("POST", "/login", {"username": "nobody@northbridge.edu", "password": "whatever-123!"})
    check("T2.6", "unknown user is rejected with 401", status == 401, f"got {status}")

    # Security property: if these messages differed, the login form could be
    # used to discover which email addresses have accounts.
    check("T2.7", "wrong password and unknown user give the SAME message (no account enumeration)",
          wrong_pw.get("message") == unknown.get("message"),
          f"{wrong_pw.get('message')!r} vs {unknown.get('message')!r}")

    status, _, _ = call("POST", "/login", {"username": ADMIN_USER})
    check("T2.8", "missing password is rejected with 400", status == 400, f"got {status}")


# ---------------------------------------------------------------------------
# T3 - authorization: the two roles really differ
# ---------------------------------------------------------------------------
def test_authorization():
    print("\nT3  Authorization")

    status, _, _ = call("POST", "/events", event())
    check("T3.1", "POST /events without a token returns 401", status == 401, f"got {status}")

    status, _, _ = call("GET", "/stats")
    check("T3.2", "GET /stats without a token returns 401", status == 401, f"got {status}")

    status, _, _ = call("POST", "/events", event(), tokens.get("student"))
    check("T3.3", "student CANNOT submit sensor events (403)", status == 403, f"got {status}")

    status, _, _ = call("GET", "/alerts", token=tokens.get("student"))
    check("T3.4", "student CANNOT read alerts (403)", status == 403, f"got {status}")

    status, _, _ = call("GET", "/events?limit=5", token=tokens.get("student"))
    check("T3.5", "student CANNOT read raw events (403)", status == 403, f"got {status}")

    status, _, _ = call("GET", "/stats", token=tokens.get("student"))
    check("T3.6", "student CAN read statistics (200)", status == 200, f"got {status}")

    status, _, _ = call("GET", "/alerts", token=tokens.get("admin"))
    check("T3.7", "admin CAN read alerts (200)", status == 200, f"got {status}")

    status, _, _ = call("GET", "/stats", token="not.a.real.token")
    check("T3.8", "a malformed token returns 401", status == 401, f"got {status}")


# ---------------------------------------------------------------------------
# T4 - ingestion and the severity override
# ---------------------------------------------------------------------------
def test_ingestion():
    print("\nT4  Event ingestion")
    admin = tokens.get("admin")

    body_sent = event(value=10)
    status, body, ms = call("POST", "/events", body_sent, admin)
    check("T4.1", "a valid event is stored (201)", status == 201, f"got {status}: {body}")
    check("T4.2", "a normal event is classified normal",
          body.get("severity") == "normal" and body.get("alert") is False, str(body))
    print(f"         (ingest latency {ms} ms)")

    # A203 holds 45. 58 is 129% - critical. The client claims "normal" and the
    # server must overrule it: a device that could declare itself normal could
    # silence any alert.
    over = event(value=58, severity="normal")
    status, body, _ = call("POST", "/events", over, admin)
    check("T4.3", "an over-capacity event is stored (201)", status == 201, f"got {status}")
    check("T4.4", "SERVER OVERRULES the client's severity -> critical",
          body.get("severity") == "critical" and body.get("alert") is True, str(body))
    check("T4.5", "the alert carries a human-readable reason",
          "capacity" in (body.get("reason") or ""), str(body.get("reason")))

    globals()["_alert_event_id"] = body.get("event_id")

    status, body, _ = call("POST", "/requests",
                           {"building": "Library-A", "room": "A203",
                            "message": "API test - projector not working", "priority": 3},
                           tokens.get("student"))
    check("T4.6", "student CAN raise a service request (201)", status == 201, f"got {status}: {body}")
    globals()["_request_id"] = body.get("event_id")
    check("T4.7", "an urgent request is critical", body.get("severity") == "critical", str(body))


# ---------------------------------------------------------------------------
# T5 - invalid input is rejected, not repaired
# ---------------------------------------------------------------------------
def test_validation():
    print("\nT5  Invalid input")
    admin = tokens.get("admin")

    cases = [
        ("T5.1", "missing required field", {k: v for k, v in event().items() if k != "building"}),
        ("T5.2", "wrong unit for the event type", event(event_type="temperature", unit="fahrenheit", value=71)),
        ("T5.3", "non-numeric value", event(value="forty-two")),
        ("T5.4", "unknown building", event(building="Hogwarts")),
        ("T5.5", "unknown room", event(room="Z999")),
        ("T5.6", "implausible value", event(event_type="temperature", unit="celsius", value=4000)),
        ("T5.7", "timestamp in the future",
         event(timestamp=(datetime.now(timezone.utc) + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"))),
        ("T5.8", "timestamp older than 24 hours",
         event(timestamp=(datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"))),
    ]
    for test_id, description, payload in cases:
        status, body, _ = call("POST", "/events", payload, admin)
        check(test_id, f"{description} -> 400", status == 400,
              f"got {status}: {body.get('message', body)}")

    status, body, _ = call("GET", "/events?limit=9999", token=admin)
    check("T5.9", "limit above the maximum -> 400", status == 400, f"got {status}")

    status, body, _ = call("GET", "/events?date=05-10-2026", token=admin)
    check("T5.10", "malformed date -> 400", status == 400, f"got {status}")

    # Every rejection must explain itself: an error the caller cannot act on
    # is barely better than no error.
    check("T5.11", "rejections include a useful message",
          bool(body.get("message")) and bool(body.get("request_id")), str(body))


# ---------------------------------------------------------------------------
# T6 - reading it back
# ---------------------------------------------------------------------------
def test_reads():
    print("\nT6  Queries and statistics")
    admin = tokens.get("admin")

    status, body, ms = call("GET", "/events?limit=10", token=admin)
    check("T6.1", "GET /events returns a list", status == 200 and isinstance(body.get("events"), list),
          f"got {status}")
    check("T6.2", "events are newest first",
          len(body.get("events", [])) < 2 or
          body["events"][0]["timestamp"] >= body["events"][1]["timestamp"], "ordering wrong")

    status, body, _ = call("GET", "/events?building=Library-A&limit=5", token=admin)
    check("T6.3", "filtering by building returns only that building",
          status == 200 and all(e["building"] == "Library-A" for e in body.get("events", [])),
          f"got {status}")

    status, body, _ = call("GET", "/alerts", token=admin)
    check("T6.4", "GET /alerts returns only abnormal events",
          status == 200 and all(e["severity"] != "normal" for e in body.get("alerts", [])),
          f"got {status}")

    status, stats, ms = call("GET", "/stats", token=admin)
    required = ["total_events", "alert_count", "events_by_type", "events_by_severity",
                "current_occupancy", "energy_kwh_by_building", "urgent_requests"]
    missing = [f for f in required if f not in stats]
    check("T6.5", "GET /stats returns every documented field", status == 200 and not missing,
          f"missing: {missing}")
    check("T6.6", "statistics reflect the events we just submitted", stats.get("total_events", 0) > 0,
          str(stats.get("total_events")))
    print(f"         (stats latency {ms} ms)")


# ---------------------------------------------------------------------------
# T7 - the end-to-end path
# ---------------------------------------------------------------------------
def test_integration():
    print("\nT7  Integration: one event, all the way through")
    admin = tokens.get("admin")
    event_id = globals().get("_alert_event_id")

    if not event_id:
        check("T7.1", "integration skipped - no alert event was created", False, "T4 did not run")
        return

    status, body, _ = call("GET", "/alerts?limit=50", token=admin)
    found = any(a.get("event_id") == event_id for a in body.get("alerts", []))
    check("T7.1", "the critical event submitted in T4 appears in /alerts", found,
          f"looking for {event_id}")

    status, body, _ = call("GET", "/events?limit=50", token=admin)
    found = any(e.get("event_id") == event_id for e in body.get("events", []))
    check("T7.2", "the same event appears in /events", found, f"looking for {event_id}")

    status, stats, _ = call("GET", "/stats", token=admin)
    check("T7.3", "the alert is counted in the statistics", stats.get("alert_count", 0) > 0,
          f"alert_count={stats.get('alert_count')}")


# ---------------------------------------------------------------------------
# T8 - service requests: the student page and the admin page
# ---------------------------------------------------------------------------
def test_requests():
    print("\nT8  Service requests (student page / admin page)")
    request_id = globals().get("_request_id")

    status, body, _ = call("GET", "/requests", token=tokens.get("student"))
    mine = body.get("requests", [])
    check("T8.1", "student GET /requests returns their own requests (200)",
          status == 200 and any(r.get("event_id") == request_id for r in mine),
          f"got {status}, looking for {request_id}")
    check("T8.2", "student view does not expose who raised a request",
          all("requested_by" not in r for r in mine), "requested_by present")

    status, body, _ = call("GET", "/requests", token=tokens.get("admin"))
    rows = body.get("requests", [])
    match = [r for r in rows if r.get("event_id") == request_id]
    check("T8.3", "admin GET /requests sees the student's request (200)",
          status == 200 and bool(match), f"got {status}")
    check("T8.4", "admin view shows who raised it",
          bool(match) and match[0].get("requested_by") == STUDENT_USER,
          str(match[0].get("requested_by")) if match else "not found")

    status, _, _ = call("GET", "/requests")
    check("T8.5", "GET /requests without a token returns 401", status == 401, f"got {status}")


# ---------------------------------------------------------------------------
def main():
    if not API:
        print("CAMPUSPULSE_API is not set. See the docstring at the top of this file.")
        return 2
    if not ADMIN_PASSWORD or not STUDENT_PASSWORD:
        print("ADMIN_PASSWORD and STUDENT_PASSWORD must be set.")
        return 2

    print(f"\nCampusPulse API tests")
    print(f"  target : {API}")
    print(f"  started: {utc_now()}")

    test_health()
    test_authentication()
    if "admin" not in tokens:
        print("\n  Cannot continue: admin login failed. Fix that first.")
        return 1
    test_authorization()
    test_ingestion()
    test_validation()
    test_reads()
    test_integration()
    test_requests()

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = len(results) - passed
    print(f"\n  {passed} passed, {failed} failed, {len(results)} total\n")

    # The evidence file the report cites. Real output, never retyped by hand.
    out = Path(__file__).resolve().parents[2] / "docs" / "evidence" / "api-test-results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "run_at": utc_now(), "api": API,
        "passed": passed, "failed": failed, "total": len(results),
        "results": results,
    }, indent=2))
    print(f"  results written to {out}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
