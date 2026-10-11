"""Vercel entry logic: one cron invocation = one run, state kept in Upstash Redis (REST)."""
import asyncio
import os

import httpx

from . import config, engine, httpnotify
from .checks import run_check
from .state import BlobStore

KEY = "pulsecheck"


def redis_creds(env) -> tuple[str, str]:
    url = env.get("UPSTASH_REDIS_REST_URL") or env.get("KV_REST_API_URL")
    token = env.get("UPSTASH_REDIS_REST_TOKEN") or env.get("KV_REST_API_TOKEN")
    if not url or not token:
        raise RuntimeError("state store missing: set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN (or KV_REST_API_URL / KV_REST_API_TOKEN)")
    return url, token


async def cron(env=None, path: str = "pulsecheck.yml") -> dict:
    env = os.environ if env is None else env
    cfg = config.load(path, env)
    url, token = redis_creds(env)
    lines: list[str] = []
    async with httpx.AsyncClient(timeout=30) as c:
        async def redis(*cmd):
            r = await c.post(url, headers={"Authorization": f"Bearer {token}"}, json=list(cmd))
            r.raise_for_status()
            return r.json()["result"]

        async def check(s):
            return await asyncio.to_thread(run_check, s)

        async def post(u, headers, body):
            return (await c.post(u, headers=headers, content=body)).status_code

        async def send(urls, text):
            await httpnotify.send(post, urls, text)

        store = BlobStore(lambda: redis("GET", KEY), lambda text: redis("SET", KEY, text))
        # 20 parallel checks keeps us far below Vercel's 1,024 shared file descriptors
        down = await engine.run(cfg, store, check, send, skip_types=("ping",), concurrency=20, log=lines.append)
    return {"down": down, "sites": lines}
