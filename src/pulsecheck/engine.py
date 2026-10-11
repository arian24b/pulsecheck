"""One check run, independent of where it runs (CLI, Vercel, Cloudflare). I/O is injected."""
import asyncio
import time
from datetime import datetime, timezone

from . import config
from .state import step


async def run(cfg, store, check, send, *, force=False, skip_types=(), concurrency=16, log=print) -> int:
    """check: async (Site) -> Result; send: async (urls, text) -> None. Returns how many sites are down."""
    await store.open()
    now = time.time()
    utc = datetime.now(timezone.utc)
    for s in cfg.sites:
        if s.type in skip_types:
            log(f"{s.name}: skipped, type '{s.type}' is not supported on this platform")
    due = [s for s in cfg.sites if s.type not in skip_types and (force or now - store.get(s.name)[3] >= s.interval * 60 - 60)]
    gate = asyncio.Semaphore(concurrency)

    async def one(s):
        async with gate:
            return await check(s)

    results = await asyncio.gather(*(one(s) for s in due))
    down = 0
    for s, r in zip(due, results):
        prev, fails, since, _ = store.get(s.name)
        new, fails, event = step(prev, fails, r, s.down_after, s.slow_ms)
        downtime = now - since
        store.save(s.name, r, new, fails, now if event else since, now)
        down += new == "down"
        log(f"{s.name}: {new} {r.ms}ms {r.error}".rstrip())
        n = s.notify or cfg.notify
        # ponytail: alerts raised during maintenance are dropped, not deferred
        if event and event in n.events and not any(m.active(utc, s.name) for m in cfg.maintenance):
            await send(n.urls, config.render(
                cfg, s, event, site=s.name, error=r.error, ms=r.ms, status=r.status or "", minutes=int(downtime // 60)))
    await store.close()
    return down
