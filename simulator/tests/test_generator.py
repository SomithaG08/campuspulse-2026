"""
Simulator tests.

The important one is test_generated_events_always_pass_server_validation: it
feeds generated events through the REAL backend validator. If the simulator
could ever produce something the API rejects, we would find out here rather
than during a live demonstration.
"""
import json
from datetime import datetime, timezone

import pytest

from common import campus_config as cfg
from common.rules import CRITICAL, classify, is_alert
from common.validation import ValidationError, validate_event
from simulator import TYPE_WEIGHTS, Generator, parse_args

NOW = datetime(2026, 10, 4, 10, 30, 0, tzinfo=timezone.utc)


# --- the contract between simulator and server ----------------------------

def test_generated_events_always_pass_server_validation():
    """
    1000 events through the actual validator the API uses. Not one may be
    rejected - the simulator must never be the reason a demo shows an error.
    """
    gen = Generator(anomaly_rate=0.3, seed=1234)
    for _ in range(1000):
        event = gen.next_event(now=NOW)
        try:
            validate_event(json.dumps(event), now=NOW)
        except ValidationError as exc:
            pytest.fail(f"simulator produced an invalid event: {exc.message}\n{event}")


def test_forced_alerts_are_always_critical():
    """--force-alert exists for the live demo, so it must never produce a mere warning."""
    gen = Generator(seed=99)
    for _ in range(300):
        event = gen.next_event(force_alert=True, now=NOW)
        severity, reason = classify(event)
        assert severity == CRITICAL, f"{event['event_type']} gave {severity}: {reason}"


def test_default_run_is_mostly_normal_with_some_alerts():
    """A stream of all-normal events is a boring demo; all-critical is not plausible."""
    gen = Generator(anomaly_rate=0.12, seed=7)
    events = [gen.next_event(now=NOW) for _ in range(500)]
    alerts = sum(1 for e in events if is_alert(classify(e)[0]))
    assert 20 < alerts < 150, f"{alerts} alerts in 500 events is implausible"


def test_zero_anomaly_rate_produces_no_sensor_alerts():
    """
    With no anomalies injected, no SENSOR reading should cross a threshold.

    Service requests are the deliberate exception and this test taught us
    why: a request's severity comes from the priority the requester chose,
    not from a sensor being out of range. Priority 2 maps to `warning` in the
    data model - an open request genuinely does want attention - so a request
    is an alert by design rather than by anomaly. Excluded here, asserted
    separately below.
    """
    gen = Generator(anomaly_rate=0.0, seed=5)
    for _ in range(500):
        event = gen.next_event(now=NOW)
        if event["event_type"] == "service_request":
            continue
        assert not is_alert(classify(event)[0]), f"unexpected sensor alert: {event}"


def test_routine_service_requests_are_never_critical():
    """Only an urgent (priority 3) request is critical; routine ones are at most warnings."""
    gen = Generator(anomaly_rate=0.0, seed=8)
    seen = 0
    for _ in range(2000):
        event = gen.next_event(now=NOW)
        if event["event_type"] == "service_request":
            seen += 1
            assert classify(event)[0] != CRITICAL
    assert seen > 0


# --- the campus it claims to represent ------------------------------------

def test_only_real_buildings_and_rooms():
    gen = Generator(seed=11)
    for _ in range(500):
        event = gen.next_event(now=NOW)
        assert cfg.is_known_building(event["building"])
        assert cfg.is_known_room(event["building"], event["room"])


def test_units_always_match_the_event_type():
    gen = Generator(seed=13)
    for _ in range(300):
        event = gen.next_event(now=NOW)
        assert event["unit"] == cfg.expected_unit(event["event_type"])


def test_energy_is_building_level_and_others_are_rooms():
    gen = Generator(seed=17)
    for _ in range(400):
        event = gen.next_event(now=NOW)
        if event["event_type"] == "energy":
            assert event["room"] == cfg.BUILDING_LEVEL_ROOM
        else:
            assert event["room"] != cfg.BUILDING_LEVEL_ROOM


def test_service_requests_carry_a_message():
    gen = Generator(anomaly_rate=0.5, seed=19)
    found = 0
    for _ in range(1000):
        event = gen.next_event(now=NOW)
        if event["event_type"] == "service_request":
            found += 1
            assert event.get("message")
    assert found > 0, "no service requests generated in 1000 events"


def test_all_six_event_types_appear():
    gen = Generator(seed=23)
    seen = {gen.next_event(now=NOW)["event_type"] for _ in range(1000)}
    assert seen == set(TYPE_WEIGHTS) == set(cfg.EVENT_TYPES)


def test_event_ids_are_unique_within_a_run():
    gen = Generator(seed=29)
    ids = [gen.next_event(now=NOW)["event_id"] for _ in range(500)]
    assert len(set(ids)) == 500


def test_same_seed_gives_the_same_run():
    """Reproducibility matters: a bug you cannot replay is a bug you cannot fix."""
    a = [Generator(seed=42).next_event(now=NOW) for _ in range(5)]
    b = [Generator(seed=42).next_event(now=NOW) for _ in range(5)]
    assert a == b


# --- realism ---------------------------------------------------------------

@pytest.mark.parametrize("hour,label", [(3, "night"), (10, "morning peak")])
def test_occupancy_follows_the_time_of_day(hour, label):
    """A dashboard showing random noise looks like a toy; a daily rhythm looks like a system."""
    gen = Generator(anomaly_rate=0.0, seed=31)
    when = NOW.replace(hour=hour)
    values = [gen._occupancy("Library-A", "A101", hour, False) for _ in range(200)]
    average = sum(values) / len(values)
    capacity = cfg.get_capacity("Library-A", "A101")
    if hour == 3:
        assert average < capacity * 0.1, f"{label} should be nearly empty"
    else:
        assert average > capacity * 0.4, f"{label} should be busy"


# --- the cost guard rails in the CLI --------------------------------------

def test_interval_below_half_a_second_is_refused():
    """The brief warns about runaway cost; this is the guard rail."""
    with pytest.raises(SystemExit):
        parse_args(["--interval", "0.001", "--dry-run"])


def test_absurd_event_count_is_refused():
    with pytest.raises(SystemExit):
        parse_args(["-n", "999999", "--dry-run"])


def test_missing_api_url_is_refused_unless_dry_run():
    import os
    saved = os.environ.pop("CAMPUSPULSE_API", None)
    try:
        with pytest.raises(SystemExit):
            parse_args(["-n", "5"])
        assert parse_args(["-n", "5", "--dry-run"]).dry_run is True
    finally:
        if saved:
            os.environ["CAMPUSPULSE_API"] = saved


def test_anomaly_rate_bounds():
    with pytest.raises(SystemExit):
        parse_args(["--anomaly-rate", "1.5", "--dry-run"])
