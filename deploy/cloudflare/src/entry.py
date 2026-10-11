"""Cloudflare Python Worker: cron trigger -> one pulsecheck run. HTTP checks only (no threads, sockets or subprocess here).
Uses only the standard library plus pulsecheck itself: the YAML is converted to pulsecheck.json by build.py."""

import hmac
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from js import AbortSignal, Object, fetch
from pyodide.ffi import to_js
from workers import Response, WorkerEntrypoint

from pulsecheck import config, engine, httpnotify
from pulsecheck.result import Result, limit
from pulsecheck.state import BlobStore

KEY = "pulsecheck"
CONFIG_TEXT = globals().get("CONFIG_TEXT")  # build.py defines it above this line; local runs read pulsecheck.json instead


def js(obj):
    return to_js(obj, dict_converter=Object.fromEntries)


async def http_check(s):
    init = {"method": s.method, "headers": s.headers, "redirect": "follow", "signal": AbortSignal.timeout(s.timeout * 1000)}
    if s.body is not None and s.method not in ("GET", "HEAD"):
        init["body"] = s.body
    t = time.perf_counter()
    try:
        r = await fetch(s.url, js(init))
    except Exception as e:
        return Result(False, 0, error=f"{type(e).__name__}: {e}")
    ms = int((time.perf_counter() - t) * 1000)
    good = r.status in s.expected_status if s.expected_status else 200 <= r.status < 300
    return limit(Result(good, ms, r.status, "" if good else f"unexpected status {r.status}"), s)


async def post(url, headers, body):
    return (await fetch(url, js({"method": "POST", "headers": headers, "body": body}))).status


def load_config(env):
    text = CONFIG_TEXT or (Path(__file__).parent / "pulsecheck.json").read_text()
    # ${VAR} in the config comes from Worker secrets / vars
    names = {n: getattr(env, n, None) for n in config.env_names(text)}
    return config.loads(text, {n: str(v) for n, v in names.items() if v is not None})


def make_store(env):
    return BlobStore(lambda: env.STATE.get(KEY), lambda doc: env.STATE.put(KEY, doc))


async def run_once(env, tag=None, force=False):
    cfg = load_config(env)
    lines = []

    async def send(urls, msg):
        await httpnotify.send(post, urls, msg)

    # Workers allow 6 simultaneous outgoing connections; ping/tcp checks and TLS expiry are not available here
    down = await engine.run(
        cfg,
        make_store(env),
        http_check,
        send,
        skip_types=("ping", "tcp"),
        unsupported=lambda s: "ip_version is not supported on Cloudflare (fetch picks the address family)" if s.ip_version else None,
        concurrency=6,
        tag=tag,
        post=post,
        force=force,
        log=lambda m: (lines.append(m), print(m)),
    )
    return {"down": down, "sites": lines}


class Default(WorkerEntrypoint):
    async def scheduled(self, controller, env, ctx):
        env = self.env  # the `env` argument is None in the Python runtime (seen in the logs); self.env is the real one
        try:
            await run_once(env)
        except Exception as e:  # keep the reason where `cf kv keys get pulsecheck-error` (or /status) can find it
            await env.STATE.put(KEY + "-error", json.dumps({"at": int(time.time()), "error": f"{type(e).__name__}: {e}"}))
            raise

    async def fetch(self, request):
        u = urlparse(request.url)
        token = str(getattr(self.env, "STATUS_TOKEN", "") or "")
        if u.path not in ("/status", "/run") or not token:
            return Response("pulsecheck worker: runs on its cron trigger")
        if not hmac.compare_digest(request.headers.get("authorization") or "", f"Bearer {token}"):
            return Response("unauthorized", status=401)
        q = parse_qs(u.query)
        if u.path == "/run":  # run now (same as the cron trigger); ?force=1 ignores per-site intervals
            out = await run_once(self.env, (q.get("tag") or [None])[0], q.get("force") == ["1"])
            return Response(json.dumps(out), headers={"Content-Type": "application/json"})
        rows = await engine.status(load_config(self.env), make_store(self.env), (q.get("tag") or [None])[0])
        fmt = (q.get("format") or ["json"])[0]
        if fmt in ("md", "text"):
            return Response(engine.format_status(rows, fmt == "md"), headers={"Content-Type": "text/plain; charset=utf-8"})
        return Response(json.dumps(rows), headers={"Content-Type": "application/json"})
