"""Cloudflare Python Worker: cron trigger -> one pulsecheck run. HTTP checks only (no threads, sockets or subprocess here)."""
import time
from pathlib import Path

from js import AbortSignal, Object, fetch
from pyodide.ffi import to_js
from workers import Response, WorkerEntrypoint

from pulsecheck import config, engine, httpnotify
from pulsecheck.checks import Result, limit
from pulsecheck.state import BlobStore

KEY = "pulsecheck"


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


class Default(WorkerEntrypoint):
    async def scheduled(self, controller, env, ctx):
        text = (Path(__file__).parent / "pulsecheck.yml").read_text()
        # ${VAR} in the YAML comes from Worker vars/secrets
        names = {n: getattr(env, n, None) for n in config.env_names(text)}
        cfg = config.loads(text, {n: str(v) for n, v in names.items() if v is not None})

        async def send(urls, msg):
            await httpnotify.send(post, urls, msg)

        store = BlobStore(lambda: env.STATE.get(KEY), lambda doc: env.STATE.put(KEY, doc))
        # Workers allow 6 simultaneous outgoing connections; ping and tcp checks are not available here
        await engine.run(cfg, store, http_check, send, skip_types=("ping", "tcp"), concurrency=6)

    async def fetch(self, request):
        return Response("pulsecheck worker: runs on its cron trigger")
