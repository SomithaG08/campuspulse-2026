#!/usr/bin/env python3
"""
CampusPulse 2026 - campus IoT simulator.

WHAT THIS IS
------------
We have no real sensors, so this program pretends to be them. It invents
plausible readings for rooms that exist on our campus, signs in to Cognito
like any other client, and POSTs each reading to the API over HTTPS.

The project brief asks for "simulated campus data generation" (section 7), and
this is it. Nothing about the backend knows or cares that the events are
synthetic - the same code path would serve real hardware.

WHY IT IMPORTS backend/src/common/campus_config.py
--------------------------------------------------
Because the simulator and the server MUST agree about the campus. If the
simulator believed room A203 held 60 people and the backend believed 45, every
alert would be wrong and neither side would be obviously at fault. Both import
the same file, so disagreement is impossible by construction.

WHY NO `requests` LIBRARY
-------------------------
This uses only the Python standard library. `requests` is nicer to read, but
"no pip install" means four teammates on four laptops can run this immediately,
and nothing can break on demo day because a dependency failed to install. For
a tool whose whole purpose is to work during a live demonstration, that trade
is worth the slightly clumsier HTTP code.

USAGE
-----
    export CAMPUSPULSE_API=https://xxxx.execute-api.eu-west-3.amazonaws.com
    export CAMPUSPULSE_USER=admin@northbridge.edu    # must be in the 'admin' group
    export CAMPUSPULSE_PASSWORD='...'

    python simulator.py --number-of-events 100     # send 100 and stop
    python simulator.py --interval 5               # one every 5s until Ctrl-C
    python simulator.py --dry-run -n 10            # print, send nothing
    python simulator.py --force-alert              # guarantee a critical event
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# The shared source of truth, imported rather than duplicated.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))
from common import campus_config as cfg  # noqa: E402
from common import rules  # noqa: E402

DEFAULT_INTERVAL = 5.0
DEFAULT_ANOMALY_RATE = 0.12   # roughly one event in eight is abnormal
HTTP_TIMEOUT = 10
TOKEN_REFRESH_MARGIN = 300    # refresh 5 minutes before expiry

# How often each event type is chosen. Occupancy and temperature dominate
# because that is what a real campus mostly measures; equipment failures and
# service requests are rare, which is exactly what makes them interesting.
TYPE_WEIGHTS = {
    "occupancy": 35,
    "temperature": 30,
    "humidity": 15,
    "energy": 12,
    "equipment": 5,
    "service_request": 3,
}

REQUEST_MESSAGES = [
    "Projector not working",
    "Air conditioning too cold",
    "Door lock jammed",
    "Whiteboard markers missing",
    "Network socket dead",
    "Chair broken",
    "Window will not close",
]


# ---------------------------------------------------------------------------
# Event generation - the interesting part, and the part with no network in it
# ---------------------------------------------------------------------------

class Generator:
    """
    Produces events. Deliberately has no idea that an API exists, which is why
    it can be unit-tested without a deployment.
    """

    def __init__(self, anomaly_rate: float = DEFAULT_ANOMALY_RATE, seed=None):
        self.anomaly_rate = anomaly_rate
        self.rng = random.Random(seed)
        self.counter = 0

    # -- occupancy ---------------------------------------------------------
    def _occupancy_factor(self, hour: int) -> float:
        """
        A campus is not uniformly busy. Rough shape of a teaching day:
        empty overnight, filling from 8, peak late morning and mid afternoon,
        emptying after 18.

        This matters for the demo: a dashboard showing random noise looks like
        a toy, while one showing a plausible daily rhythm looks like a system.
        """
        if hour < 7 or hour >= 22:
            return self.rng.uniform(0.0, 0.05)
        if 7 <= hour < 9:
            return self.rng.uniform(0.1, 0.4)
        if 9 <= hour < 12:
            return self.rng.uniform(0.5, 0.95)
        if 12 <= hour < 14:
            return self.rng.uniform(0.3, 0.6)   # lunch
        if 14 <= hour < 18:
            return self.rng.uniform(0.5, 0.9)
        return self.rng.uniform(0.1, 0.3)

    def _occupancy(self, building, room, hour, anomalous, critical=False):
        capacity = cfg.get_capacity(building, room)
        if critical:
            # Comfortably past the 120% critical ratio, so --force-alert is
            # reliable. A demo alert that sometimes comes out as a mere
            # warning is a demo that sometimes does not land.
            value = int(capacity * self.rng.uniform(1.3, 1.6)) + 1
        elif anomalous:
            value = int(capacity * self.rng.uniform(1.05, 1.45))
        else:
            value = int(capacity * self._occupancy_factor(hour))
        return max(0, value)

    # -- environment -------------------------------------------------------
    def _temperature(self, anomalous, critical=False):
        if critical:
            return round(self.rng.choice([
                self.rng.uniform(8.0, 14.0),    # heating failure
                self.rng.uniform(30.5, 38.0),   # cooling failure
            ]), 1)
        if anomalous:
            # Either a failed heater or a failed chiller
            return round(self.rng.choice([
                self.rng.uniform(10.0, 17.5),
                self.rng.uniform(26.5, 34.0),
            ]), 1)
        return round(self.rng.uniform(19.0, 25.0), 1)

    def _humidity(self, anomalous, critical=False):
        if critical:
            return round(self.rng.choice([
                self.rng.uniform(5.0, 19.0),
                self.rng.uniform(71.0, 90.0),
            ]), 1)
        if anomalous:
            return round(self.rng.choice([
                self.rng.uniform(12.0, 29.0),
                self.rng.uniform(61.0, 85.0),
            ]), 1)
        return round(self.rng.uniform(33.0, 57.0), 1)

    def _energy(self, building, hour, anomalous, critical=False):
        baseline = cfg.get_energy_baseline(building)
        if critical:
            return round(baseline * self.rng.uniform(2.05, 2.6), 1)
        if anomalous:
            return round(baseline * self.rng.uniform(1.55, 2.4), 1)
        # Daytime draws more than night, but stays under the warning ratio
        day = 0.55 if 8 <= hour < 19 else 0.2
        return round(baseline * self.rng.uniform(day, day + 0.5), 1)

    # -- discrete ----------------------------------------------------------
    def _equipment(self, anomalous, critical=False):
        if critical:
            return 2          # failed
        if anomalous:
            return self.rng.choice([1, 2])
        return 0

    def _service_priority(self, anomalous, critical=False):
        if anomalous or critical:
            return 3          # urgent
        return self.rng.choice([1, 1, 2])

    # -- assembly ----------------------------------------------------------
    def next_event(self, force_alert: bool = False, now: datetime = None) -> dict:
        """One event, ready to POST."""
        now = now or datetime.now(timezone.utc)
        self.counter += 1
        # anomalous -> at least a warning. critical -> guaranteed critical,
        # which is what --force-alert is for.
        critical = force_alert
        anomalous = critical or self.rng.random() < self.anomaly_rate

        event_type = self.rng.choices(
            list(TYPE_WEIGHTS), weights=list(TYPE_WEIGHTS.values())
        )[0]

        # Energy meters are building-level; everything else is in a room.
        if event_type == "energy":
            building = self.rng.choice(list(cfg.BUILDINGS))
            room = cfg.BUILDING_LEVEL_ROOM
        else:
            building, room = self.rng.choice(cfg.all_rooms())

        hour = now.hour

        if event_type == "occupancy":
            value = self._occupancy(building, room, hour, anomalous, critical)
        elif event_type == "temperature":
            value = self._temperature(anomalous, critical)
        elif event_type == "humidity":
            value = self._humidity(anomalous, critical)
        elif event_type == "energy":
            value = self._energy(building, hour, anomalous, critical)
        elif event_type == "equipment":
            value = self._equipment(anomalous, critical)
        else:
            value = self._service_priority(anomalous, critical)

        event = {
            "event_id": f"evt-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}-{self.counter:04d}",
            "building": building,
            "room": room,
            "event_type": event_type,
            "value": value,
            "unit": cfg.expected_unit(event_type),
            # We send a severity because the brief's example event has one -
            # and the server ignores it and computes its own. That is the
            # point: a device must not be able to declare itself normal.
            "severity": "normal",
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        if event_type == "service_request":
            event["message"] = self.rng.choice(REQUEST_MESSAGES)

        return event


# ---------------------------------------------------------------------------
# HTTP - small, explicit, stdlib only
# ---------------------------------------------------------------------------

def post_json(url: str, payload: dict, token: str = None) -> tuple:
    """Returns (status_code, parsed_body). Never raises on an HTTP error status."""
    data = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            return exc.code, json.loads(body or b"{}")
        except json.JSONDecodeError:
            return exc.code, {"error": "NonJSONResponse", "message": body[:200].decode(errors="replace")}
    except urllib.error.URLError as exc:
        # DNS failure, refused connection, no network. Not an HTTP status.
        return 0, {"error": "ConnectionError", "message": str(exc.reason)}


class Session:
    """Holds the API URL and the token, and refreshes the token before it expires."""

    def __init__(self, api_url: str, username: str, password: str):
        self.api_url = api_url.rstrip("/")
        self.username = username
        self.password = password
        self.token = None
        self.expires_at = None

    def login(self) -> None:
        status, body = post_json(
            f"{self.api_url}/login",
            {"username": self.username, "password": self.password},
        )
        if status != 200:
            raise SystemExit(
                f"Login failed ({status}): {body.get('message', body)}\n"
                "Check CAMPUSPULSE_USER / CAMPUSPULSE_PASSWORD, and that the user "
                "has a permanent password and is in the 'admin' group."
            )
        self.token = body["id_token"]
        self.expires_at = time.time() + int(body.get("expires_in", 3600))
        print(f"  signed in as {self.username} (role: {body.get('role')})")

    def ensure_token(self) -> None:
        """A long run outlives a one-hour token, so refresh before it dies."""
        if self.token is None or time.time() > self.expires_at - TOKEN_REFRESH_MARGIN:
            self.login()

    def send(self, event: dict) -> tuple:
        self.ensure_token()
        return post_json(f"{self.api_url}/events", event, self.token)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

SEVERITY_MARK = {"normal": "  ", "warning": "! ", "critical": "!!"}


def describe(event: dict, status: int = None, response: dict = None) -> str:
    where = f"{event['building']}/{event['room']}"
    what = f"{event['event_type']}={event['value']:g}{'' if event['unit'] in ('status', 'priority') else ' ' + event['unit']}"

    if response is None:
        # Dry run: show what the SERVER would decide, computed with the very
        # same rules module the backend uses. If this preview ever disagreed
        # with the real response, the shared-config claim would be broken.
        severity, reason = rules.classify(event)
        mark = SEVERITY_MARK.get(severity, "??")
        line = f"  {mark} {event['timestamp']}  {where:<22} {what:<28} {severity}"
        if rules.is_alert(severity):
            line += f"\n        -> {reason}"
        return line

    severity = response.get("severity", "?")
    mark = SEVERITY_MARK.get(severity, "??")
    if status not in (200, 201):
        return f"  ERR {status} {where:<22} {what}  -> {response.get('message', response)}"
    line = f"  {mark} {event['timestamp']}  {where:<22} {what:<28} {severity}"
    if response.get("alert"):
        line += f"\n        -> {response.get('reason', '')}"
    return line


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="CampusPulse 2026 campus IoT simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Credentials come from CAMPUSPULSE_USER / CAMPUSPULSE_PASSWORD, "
               "never from the command line, so they stay out of your shell history.",
    )
    parser.add_argument("--api-url", default=os.environ.get("CAMPUSPULSE_API"),
                        help="API base URL (or set CAMPUSPULSE_API)")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL,
                        help=f"seconds between events (default {DEFAULT_INTERVAL})")
    parser.add_argument("-n", "--number-of-events", type=int, default=None,
                        help="send this many and stop (default: run until Ctrl-C)")
    parser.add_argument("--anomaly-rate", type=float, default=DEFAULT_ANOMALY_RATE,
                        help=f"fraction of abnormal events, 0 to 1 (default {DEFAULT_ANOMALY_RATE})")
    parser.add_argument("--force-alert", action="store_true",
                        help="make every event abnormal - use this for the live demo")
    parser.add_argument("--dry-run", action="store_true",
                        help="print events without sending anything (no AWS, no cost)")
    parser.add_argument("--seed", type=int, default=None,
                        help="fix the random seed for reproducible runs")
    args = parser.parse_args(argv)

    # Guard rails: the brief warns about runaway cost, and an interval of
    # 0.001 is how a student project burns its credits in an afternoon.
    if args.interval < 0.5:
        parser.error("--interval below 0.5s is refused: it risks the credit budget")
    if not 0.0 <= args.anomaly_rate <= 1.0:
        parser.error("--anomaly-rate must be between 0 and 1")
    if args.number_of_events is not None and not 1 <= args.number_of_events <= 10000:
        parser.error("--number-of-events must be between 1 and 10000")
    if not args.dry_run and not args.api_url:
        parser.error("no API URL: pass --api-url or set CAMPUSPULSE_API (or use --dry-run)")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    generator = Generator(anomaly_rate=1.0 if args.force_alert else args.anomaly_rate,
                          seed=args.seed)

    totals = {"sent": 0, "alerts": 0, "failed": 0}
    campus = cfg.campus_totals()

    print(f"\nCampusPulse simulator - {campus['buildings']} buildings, {campus['rooms']} rooms")
    if args.dry_run:
        print("  DRY RUN: nothing is sent, --interval ignored,")
        print("  severity shown is what the server would decide\n")
        session = None
    else:
        username = os.environ.get("CAMPUSPULSE_USER")
        password = os.environ.get("CAMPUSPULSE_PASSWORD")
        if not username or not password:
            print("  CAMPUSPULSE_USER and CAMPUSPULSE_PASSWORD must be set", file=sys.stderr)
            return 2
        print(f"  target: {args.api_url}")
        session = Session(args.api_url, username, password)
        session.login()
        print()

    try:
        while args.number_of_events is None or totals["sent"] + totals["failed"] < args.number_of_events:
            event = generator.next_event(force_alert=args.force_alert)

            if session is None:
                print(describe(event))
                totals["sent"] += 1
            else:
                status, response = session.send(event)
                print(describe(event, status, response))
                if status == 201:
                    totals["sent"] += 1
                    if response.get("alert"):
                        totals["alerts"] += 1
                else:
                    totals["failed"] += 1

            if args.dry_run and rules.is_alert(rules.classify(event)[0]):
                totals["alerts"] += 1

            # A dry run sends nothing, so pacing it serves no purpose - it just
            # makes you wait. Real runs honour --interval.
            remaining = (args.number_of_events is None or
                         totals["sent"] + totals["failed"] < args.number_of_events)
            if remaining and not args.dry_run:
                time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n  stopped")

    print(f"\n  sent {totals['sent']}, alerts {totals['alerts']}, failed {totals['failed']}\n")
    return 1 if totals["failed"] and not totals["sent"] else 0


if __name__ == "__main__":
    sys.exit(main())
