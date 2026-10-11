from datetime import UTC, datetime

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
    sun = datetime(2026, 10, 11, 2, 30, tzinfo=UTC)  # a Sunday
    assert Maintenance(start="SUN 02:00", duration=60).active(sun, "a")
    assert not Maintenance(start="MON 02:00", duration=60).active(sun, "a")
    assert Maintenance(start="02:00", duration=60).active(sun, "a")
    assert not Maintenance(start="02:00", duration=10).active(sun, "a")
    assert not Maintenance(start="02:00", duration=60, sites=["b"]).active(sun, "a")


def test_messages_override_and_validation():
    import pytest

    from pulsecheck import config

    cfg = config.from_dict(
        {
            "sites": [{"name": "a", "url": "http://x", "messages": {"down": "site {site} bad"}}],
            "messages": {"up": "{site} back after {minutes}m"},
        }
    )
    s = cfg.sites[0]
    assert config.render(cfg, s, "down", site="a") == "site a bad"  # site beats global
    assert config.render(cfg, s, "up", site="a", minutes=3) == "a back after 3m"  # global beats built-in
    assert config.render(cfg, s, "degraded", site="a", ms=9) == "🟡 a is slow (9ms)"  # built-in default
    with pytest.raises(ValueError):
        config._check_messages({"nope": "x"})
    with pytest.raises(ValueError):  # a bad key under a site is rejected at load time too
        config.build(config.Site, {"name": "a", "url": "http://x", "messages": {"nope": "x"}})
    with pytest.raises(ValueError):
        config._check_messages({"down": "{bogus}"})


def test_ssl_expired_detection(monkeypatch):
    import ssl

    from pulsecheck import checks, config

    err = ssl.SSLCertVerificationError(1, "certificate has expired")
    err.verify_code = 10

    def boom(*a, **k):
        raise err

    monkeypatch.setattr(checks.socket, "create_connection", boom)
    s = config.Site(name="a", url="https://x.example.com", ssl_warn_days=14)
    assert checks.ssl_days_left(s) == 0
    monkeypatch.setattr(checks, "_http", lambda s: checks.Result(False, 1, error="verify failed"))
    r = checks.run_check(s)
    assert not r.ok and r.error == "TLS certificate has expired"


def test_dotenv_and_cron_block(tmp_path, monkeypatch):
    import os

    from pulsecheck import setup

    assert setup.parse_dotenv("# c\nA=1\nexport B=\"two words\"\nC='x'\nbad line\nD=\n") == {"A": "1", "B": "two words", "C": "x", "D": ""}
    cfg = tmp_path / "pulsecheck.yml"
    cfg.write_text("sites: []")
    (tmp_path / ".env").write_text("PC_T1=hello\nPC_T2=\nPC_T3=fromfile\n")
    monkeypatch.delenv("PC_T1", raising=False)
    monkeypatch.delenv("PC_T2", raising=False)
    monkeypatch.setenv("PC_T3", "fromenv")
    assert setup.load_dotenv(cfg) == ["PC_T1"] and os.environ["PC_T1"] == "hello"
    assert "PC_T2" not in os.environ and os.environ["PC_T3"] == "fromenv"  # empty placeholder skipped, real env wins
    monkeypatch.delenv("PC_T1")
    # the managed cron block is added once, replaced in place, and removable without touching other lines
    base = "MAILTO=me\n0 1 * * * backup\n"
    one = setup.with_block(base, "*/5 * * * * a")
    two = setup.with_block(one, "*/10 * * * * b")
    assert two.count(setup.BEGIN) == 1 and "*/10 * * * * b" in two and "*/5 * * * * a" not in two and "0 1 * * * backup" in two
    assert setup.with_block(two, None) == base and setup.with_block("", None) == ""
    assert setup.mask("telegram://123:secret@telegram?chats=@x") == "telegram://***"


def test_upgrade_command_and_step_helpers(monkeypatch):
    from pulsecheck import setup

    monkeypatch.setattr(setup.sys, "prefix", "/home/u/.local/share/uv/tools/pulsecheck")
    assert setup.upgrade_command() == ["uv", "tool", "upgrade", "pulsecheck"]
    monkeypatch.setattr(setup.sys, "prefix", "/home/u/.local/pipx/venvs/pulsecheck")
    assert setup.upgrade_command() == ["pipx", "upgrade", "pulsecheck"]


def test_init_creates_files_and_cron(tmp_path, monkeypatch):
    from pulsecheck import setup

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    installed = []
    monkeypatch.setattr(setup, "edit_crontab", lambda line: installed.append(line))
    cfg = setup.init(yes=True, download=False, say=lambda *_: None)
    assert cfg == tmp_path / "cfg/pulsecheck/pulsecheck.yml" and f"state_file: {tmp_path}/state/pulsecheck/pulsecheck.db" in cfg.read_text()
    env = tmp_path / "cfg/pulsecheck/.env"
    assert "TG_TOKEN=" in env.read_text() and oct(env.stat().st_mode)[-3:] == "600"
    assert len(installed) == 1 and "-m pulsecheck" in installed[0] and installed[0].startswith("*/5 * * * *")
    cfg.write_text("keep me")
    setup.init(yes=True, download=False, cron=False, say=lambda *_: None)
    assert cfg.read_text() == "keep me"  # an existing config is never overwritten without --force
