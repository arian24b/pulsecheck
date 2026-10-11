import asyncio
import os
import subprocess
import sys

import pytest

from pulsecheck import config, engine, httpnotify, web
from pulsecheck.checks import Result
from pulsecheck.state import BlobStore


def make_cfg(**extra):
    return config.Config(
        notify={"urls": ["x://"]}, defaults={}, sites=[{"name": "a", "url": "http://a", "down_after": 1}, {"name": "p", "type": "ping", "host": "h"}], **extra
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
    code = "import app;" "r=app.app({'PATH_INFO':'/api/cron','HTTP_AUTHORIZATION':'Bearer wrong'},lambda s,h:print(s));"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={**os.environ, "CRON_SECRET": "right"})
    assert "401" in out.stdout
    out = subprocess.run([sys.executable, "-c", code.replace("wrong", "right")], capture_output=True, text=True, env={**os.environ, "CRON_SECRET": "right", "UPSTASH_REDIS_REST_URL": ""})
    assert "500" in out.stdout  # authorized, then fails because no state store/config is set
    assert web.redis_creds({"KV_REST_API_URL": "u", "KV_REST_API_TOKEN": "t"}) == ("u", "t")
