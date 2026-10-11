from datetime import datetime, timezone

from pulsecheck.checks import Result
from pulsecheck.config import Maintenance
from pulsecheck.state import step


def ok(ms=10):
    return Result(True, ms)


def bad():
    return Result(False, 0, error="x")


def test_down_after_threshold_and_recovery():
    s, f, e = step("up", 0, bad(), 2, None)
    assert (s, f, e) == ("up", 1, None)  # first failure: no alert
    s, f, e = step(s, f, bad(), 2, None)
    assert (s, e) == ("down", "down")
    s, f, e = step(s, f, bad(), 2, None)
    assert e is None  # no repeat alert
    s, f, e = step(s, f, ok(), 2, None)
    assert (s, e) == ("up", "up")


def test_degraded():
    assert step("up", 0, ok(5000), 2, 3000)[2] == "degraded"
    assert step("degraded", 0, ok(5000), 2, 3000)[2] is None
    assert step("degraded", 0, ok(10), 2, 3000)[2] == "up"


def test_maintenance_daily_and_weekly():
    sun = datetime(2026, 10, 11, 2, 30, tzinfo=timezone.utc)  # a Sunday
    assert Maintenance(start="SUN 02:00", duration=60).active(sun, "a")
    assert not Maintenance(start="MON 02:00", duration=60).active(sun, "a")
    assert Maintenance(start="02:00", duration=60).active(sun, "a")
    assert not Maintenance(start="02:00", duration=10).active(sun, "a")
    assert not Maintenance(start="02:00", duration=60, sites=["b"]).active(sun, "a")
