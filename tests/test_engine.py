import asyncio
import json
import os
import subprocess
import sys

import pytest

from pulsecheck import config, engine, httpnotify, web
from pulsecheck.checks import Result
from pulsecheck.state import BlobStore


def make_cfg(**extra):
    return config.from_dict(
        {
            "notify": {"urls": ["x://"]},
            "sites": [{"name": "a", "url": "http://a", "down_after": 1}, {"name": "p", "type": "ping", "host": "h"}],
            **extra,
        }
    )


def run(cfg, results, store=None, **kw):
    sent, mem = [], {}
    store = store or BlobStore(lambda: _get(mem), lambda t: _put(mem, t))

    async def check(s):
        return results.pop(0)

    async def send(urls, text):
        sent.append(text)

    down = asyncio.run(engine.run(cfg, store, check, send, log=lambda *_: None, **kw))
    return down, sent, store, mem


async def _get(mem):
    return mem.get("doc")


async def _put(mem, t):
    mem["doc"] = t


def test_down_then_up_alerts_once_each_and_state_persists():
    cfg, mem = make_cfg(), {}
    store = lambda: BlobStore(lambda: _get(mem), lambda t: _put(mem, t))  # noqa: E731
    down, sent, *_ = run(cfg, [Result(False, 0, error="boom")], store(), force=True, skip_types=("ping",))
    assert down == 1 and len(sent) == 1 and "DOWN" in sent[0]
    down, sent, *_ = run(cfg, [Result(False, 0, error="boom")], store(), force=True, skip_types=("ping",))
    assert down == 1 and sent == []  # still down: no repeat, state came back from the stored document
    down, sent, st, _ = run(cfg, [Result(True, 20)], store(), force=True, skip_types=("ping",))
    assert down == 0 and len(sent) == 1 and "UP" in sent[0]
    assert st.report("a", 1)["checks"] == 3 and st.report("a", 1)["uptime_pct"] == 33.33


def test_skip_types_and_interval():
    cfg = make_cfg()
    res = [Result(True, 5)]
    _, _, st, mem = run(cfg, res, skip_types=("ping",))
    assert res == [] and "p" not in st.doc["sites"]  # ping skipped, a checked
    mem_store = BlobStore(lambda: _get(mem), lambda t: _put(mem, t))
    res = [Result(True, 5)]
    run(cfg, res, mem_store, skip_types=("ping",))  # interval 5min not elapsed -> not checked again
    assert len(res) == 1


def test_maintenance_suppresses_alert():
    cfg = make_cfg(maintenance=[{"start": "00:00", "duration": 24 * 60}])
    down, sent, *_ = run(cfg, [Result(False, 0, error="x")], force=True, skip_types=("ping",))
    assert down == 1 and sent == []


def test_http_notify_requests():
    r = httpnotify.requests_for("telegram://123:abc@telegram?chats=@a,@b", "hi")
    assert [x["url"] for x in r] == ["https://api.telegram.org/bot123:abc/sendMessage"] * 2
    assert '"chat_id": "@b"' in r[1]["body"]
    assert httpnotify.requests_for("discord://tok@999", "m")[0]["url"] == "https://discord.com/api/webhooks/999/tok"
    n = httpnotify.requests_for("ntfy://u:p@ntfy.example.com/topic", "m")[0]
    assert n["url"] == "https://ntfy.example.com/topic" and n["headers"]["Authorization"].startswith("Basic ")
    g = httpnotify.requests_for("generic://h.example.com/hook?disabletls=yes", "m")[0]
    assert g["url"] == "http://h.example.com/hook" and g["body"] == '{"message": "m"}'
    with pytest.raises(ValueError):
        httpnotify.requests_for("slack://x@y", "m")


def test_http_send_never_raises(capsys):
    async def post(url, headers, body):
        return 500

    asyncio.run(httpnotify.send(post, ["discord://t@1", "nope://x"], "m"))
    err = capsys.readouterr().err
    assert "HTTP 500" in err and "not supported" in err


def test_vercel_app_requires_secret():
    code = "import app;r=app.app({'PATH_INFO':'/api/cron','HTTP_AUTHORIZATION':'Bearer wrong'},lambda s,h:print(s));"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={**os.environ, "CRON_SECRET": "right"})
    assert "401" in out.stdout
    out = subprocess.run(
        [sys.executable, "-c", code.replace("wrong", "right")],
        capture_output=True,
        text=True,
        env={**os.environ, "CRON_SECRET": "right", "UPSTASH_REDIS_REST_URL": ""},
    )
    assert "500" in out.stdout  # authorized, then fails because no state store/config is set
    assert web.redis_creds({"KV_REST_API_URL": "u", "KV_REST_API_TOKEN": "t"}) == ("u", "t")


def test_reminders_ssl_warning_tags_and_status():
    cfg = config.from_dict(
        {
            "notify": {"urls": ["x://"]},
            "sites": [
                {"name": "a", "url": "http://a", "down_after": 1, "remind_every": 10, "ssl_warn_days": 14, "tags": ["prod", "web"]},
                {"name": "b", "url": "http://b", "tags": ["dev"]},
            ],
        }
    )
    mem = {}
    store = lambda: BlobStore(lambda: _get(mem), lambda t: _put(mem, t))  # noqa: E731
    kw = dict(force=True, tag="prod")
    _, sent, *_ = run(cfg, [Result(False, 0, error="x")], store(), **kw)
    assert len(sent) == 1 and "is DOWN" in sent[0]
    _, sent, *_ = run(cfg, [Result(False, 0, error="x")], store(), **kw)
    assert sent == []  # reminder interval (10 min) not reached
    doc = json.loads(mem["doc"])
    doc["sites"]["a"][4]["alert"] -= 11 * 60  # pretend the last alert was 11 minutes ago
    mem["doc"] = json.dumps(doc)
    _, sent, *_ = run(cfg, [Result(False, 0, error="x")], store(), **kw)
    assert len(sent) == 1 and "still DOWN" in sent[0]
    # certificate: warns (once a day) when inside the window, silent when far from expiry
    _, sent, *_ = run(cfg, [Result(True, 5, ssl_days=7)], store(), **kw)
    assert any("certificate expires in 7 days" in m for m in sent) and any("UP" in m for m in sent)
    _, sent, *_ = run(cfg, [Result(True, 5, ssl_days=7)], store(), **kw)
    assert not any("certificate" in m for m in sent)  # already warned today
    _, sent, *_ = run(cfg, [Result(True, 5, ssl_days=60)], store(), **kw)
    assert sent == []
    # tag filter: site b was never checked
    rows = asyncio.run(engine.status(cfg, store()))
    assert [(r["name"], r["status"]) for r in rows] == [("a", "up"), ("b", "unknown")]
    assert [r["name"] for r in asyncio.run(engine.status(cfg, store(), tag="dev"))] == ["b"]
    text = engine.format_status(rows)
    assert "🟢 a" in text and "⚪ b" in text and "| a |" in engine.format_status(rows, markdown=True)


def test_more_http_notify_services():
    f = httpnotify.requests_for
    assert f("slack://hook:T1-B2-X3@webhook", "m")[0]["url"] == "https://hooks.slack.com/services/T1/B2/X3"
    bot = f("slack://xoxb:123-456-abc@c01abc", "m")[0]
    assert bot["headers"]["Authorization"] == "Bearer xoxb-123-456-abc" and '"channel": "C01ABC"' in bot["body"]
    assert f("gotify://g.example.com/sub/Atoken", "m")[0]["url"] == "https://g.example.com/sub/message?token=Atoken"
    po = f("pushover://:tok@userkey?devices=ph", "m")[0]
    assert po["body"] == "token=tok&user=userkey&message=m&device=ph"
    mm = f("mattermost://bot@mm.example.com/hook/town", "m")[0]
    assert mm["url"] == "https://mm.example.com/hooks/hook" and '"channel": "#town"' in mm["body"]
    assert f("rocketchat://rc.example.com/ta/tb/general", "m")[0]["url"] == "https://rc.example.com/hooks/ta/tb"
    assert (
        f("googlechat://chat.googleapis.com/v1/spaces/F/messages?key=k&token=t", "m")[0]["url"]
        == "https://chat.googleapis.com/v1/spaces/F/messages?key=k&token=t"
    )
    z = f("zulip://bot%40z.example.com:key@z.example.com/?stream=s&topic=t", "m")[0]
    assert z["url"] == "https://z.example.com/api/v1/messages" and "stream=s" not in z["body"] and "to=s" in z["body"]
    assert f("bark://:dk@bark.example.com/", "m")[0]["url"] == "https://bark.example.com/push"


def test_ssl_days_left_ignores_non_https():
    from pulsecheck.checks import ssl_days_left

    assert ssl_days_left(config.Site(name="a", url="http://x")) is None


def test_unsupported_scheme_uses_fallback(capsys):
    got = []

    async def post(url, headers, body):
        return 200

    async def fallback(u, text):
        got.append((u, text))

    asyncio.run(httpnotify.send(post, ["smtp://u:p@h/?to=a", "discord://t@1"], "m", fallback=fallback))
    assert got == [("smtp://u:p@h/?to=a", "m")] and capsys.readouterr().err == ""
    asyncio.run(httpnotify.send(post, ["smtp://u:p@h/?to=a"], "m"))
    assert "not supported here" in capsys.readouterr().err


def test_download_shoutrrr_verifies_checksum(tmp_path, monkeypatch):
    import hashlib
    import io
    import tarfile

    from pulsecheck import notify

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        info = tarfile.TarInfo("shoutrrr")
        payload = b"#!/bin/sh\necho ok\n"
        info.size = len(payload)
        tf.addfile(info, io.BytesIO(payload))
    blob = buf.getvalue()
    monkeypatch.setattr(notify.platform, "machine", lambda: "x86_64")
    name = "shoutrrr_linux_amd64_9.9.9.tar.gz"

    def fake(sha):
        def urlopen(url, timeout=0):
            return io.BytesIO(blob if url.endswith(".tar.gz") else f"{sha}  {name}\n".encode())

        return urlopen

    import pytest

    monkeypatch.setattr(notify.urllib.request, "urlopen", fake("0" * 64))
    with pytest.raises(RuntimeError, match="checksum"):
        notify.download_shoutrrr(str(tmp_path / "bad"), "9.9.9")
    monkeypatch.setattr(notify.urllib.request, "urlopen", fake(hashlib.sha256(blob).hexdigest()))
    path = notify.download_shoutrrr(str(tmp_path / "good"), "9.9.9")
    assert open(path, "rb").read() == payload and os.access(path, os.X_OK)
