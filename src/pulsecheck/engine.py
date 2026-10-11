"""One check run, independent of where it runs (CLI, Vercel, Cloudflare). I/O is injected."""

import asyncio
import time
from datetime import UTC, datetime

from . import config, otel
from .state import step

WINDOWS = {"day": 1, "week": 7, "month": 30, "year": 365}


def _selected(cfg, tag):
    return [s for s in cfg.sites if not tag or tag in s.tags]


def _alerts(s, event, new, meta, r, since, now):
    """-> [(message key, event name used for the notify.events filter)]; updates meta."""
    out = []
    if event:
        out.append((event, event))
        meta["alert"] = now
    elif new == "down" and s.remind_every and now - meta.get("alert", since) >= s.remind_every * 60:
        out.append(("reminder", "down"))
        meta["alert"] = now
    if r.ssl_days is not None and s.ssl_warn_days is not None and 0 < r.ssl_days < s.ssl_warn_days:
        if now - meta.get("ssl_alert", 0) >= (s.remind_every or 1440) * 60:  # at most once a day unless remind_every is set
            out.append(("ssl_warn", "ssl_warn"))
            meta["ssl_alert"] = now
    return out


async def run(cfg, store, check, send, *, post=None, force=False, skip_types=(), concurrency=16, tag=None, log=print) -> int:
    """check: async (Site) -> Result; send: async (urls, text) -> None; post: async (url, headers, body) -> status, used for
    the OpenTelemetry export when cfg.otel is set. Returns how many sites are down."""
    await store.open()
    now = time.time()
    utc = datetime.now(UTC)
    sites = _selected(cfg, tag)
    for s in sites:
        if s.type in skip_types:
            log(f"{s.name}: skipped, type '{s.type}' is not supported on this platform")
    due = [s for s in sites if s.type not in skip_types and (force or now - store.get(s.name)[3] >= s.interval * 60 - 60)]
    gate = asyncio.Semaphore(concurrency)

    async def one(s):
        async with gate:
            return await check(s)

    results = await asyncio.gather(*(one(s) for s in due))
    down = 0
    records, events = [], []
    for s, r in zip(due, results, strict=True):
        prev, fails, since, _, meta = store.get(s.name)
        new, fails, event = step(prev, fails, r, s.down_after, s.slow_ms)
        downtime = now - since
        meta = dict(meta)
        alerts = _alerts(s, event, new, meta, r, since, now)
        store.save(s.name, r, new, fails, now if event else since, now, meta)
        down += new == "down"
        log(f"{s.name}: {new} {r.ms}ms {r.error}".rstrip())
        records.append(
            {
                "site": s.name,
                "type": s.type,
                "tags": s.tags,
                "state": new,
                "ok": r.ok,
                "ms": r.ms,
                "http_status": r.status,
                "ssl_days": r.ssl_days,
            }
        )
        n = s.notify or cfg.notify
        # ponytail: alerts raised during maintenance are dropped, not deferred
        if any(m.active(utc, s.name) for m in cfg.maintenance):
            continue
        for key, name in alerts:
            message = config.render(
                cfg,
                s,
                key,
                site=s.name,
                error=r.error,
                ms=r.ms,
                status=r.status or "",
                minutes=int(downtime // 60),
                tags=",".join(s.tags),
                days=r.ssl_days if r.ssl_days is not None else "",
            )
            events.append({"site": s.name, "event": key, "state": new, "message": message})
            if name in n.events:
                await send(n.urls, message)
    if cfg.otel and post:
        await otel.push(post, cfg.otel, records, events, now)
    await store.close()
    return down


async def status(cfg, store, tag=None) -> list[dict]:
    """Current state of every site, for `pulsecheck status` and the /status endpoints."""
    await store.open()
    now = time.time()
    out = []
    for s in _selected(cfg, tag):
        st, _, since, last, _ = store.get(s.name)
        day = store.report(s.name, 1)
        out.append(
            {
                "name": s.name,
                "type": s.type,
                "tags": s.tags,
                "status": st if last else "unknown",
                "since_s": int(now - since) if last else None,
                "last_check_s": int(now - last) if last else None,
                "uptime_24h": day["uptime_pct"] if day else None,
                "checks_24h": day["checks"] if day else 0,
            }
        )
    return out


def ago(sec) -> str:
    if sec is None:
        return "never"
    for unit, n in (("d", 86400), ("h", 3600), ("m", 60)):
        if sec >= n:
            return f"{sec // n}{unit}"
    return f"{sec}s"


def format_status(rows: list[dict], markdown: bool = False) -> str:
    icon = {"up": "🟢", "down": "🔴", "degraded": "🟡", "unknown": "⚪"}
    lines = []
    if markdown:
        lines += ["| | Site | Status | For | Last check | Uptime 24h | Tags |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        up = f"{r['uptime_24h']}%" if r["uptime_24h"] is not None else "-"
        if markdown:
            lines.append(
                f"| {icon[r['status']]} | {r['name']} | {r['status']} | {ago(r['since_s'])} | {ago(r['last_check_s'])} ago | {up} | {', '.join(r['tags'])} |"
            )
        else:
            lines.append(
                f"{icon[r['status']]} {r['name']:<20} {r['status']:<9} for {ago(r['since_s']):<5} last {ago(r['last_check_s']):<6} 24h {up}"
            )
    return "\n".join(lines)
