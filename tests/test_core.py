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


def test_messages_override_and_validation():
    import pytest

    from pulsecheck import config

    cfg = config.Config(sites=[{"name": "a", "url": "http://x", "messages": {"down": "site {site} bad"}}],
                        messages={"up": "{site} back after {minutes}m"})
    s = cfg.sites[0]
    assert config.render(cfg, s, "down", site="a") == "site a bad"  # site beats global
    assert config.render(cfg, s, "up", site="a", minutes=3) == "a back after 3m"  # global beats built-in
    assert config.render(cfg, s, "degraded", site="a", ms=9) == "🟡 a is slow (9ms)"  # built-in default
    with pytest.raises(ValueError):
        config._check_messages({"nope": "x"})
    with pytest.raises(ValueError):  # a bad key under a site is rejected at load time too
        config.Site(name="a", url="http://x", messages={"nope": "x"})
    with pytest.raises(ValueError):
        config._check_messages({"down": "{bogus}"})
