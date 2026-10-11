import json
import statistics
import time

from .checks import Result

SCHEMA = """
create table if not exists checks(site text, ts real, ok int, status int, ms int, error text);
create index if not exists checks_site_ts on checks(site, ts);
create table if not exists state(site text primary key, status text, fails int, since real, last real);
"""


def step(prev: str, fails: int, r: Result, down_after: int, slow_ms: int | None):
    """Pure transition: returns (new_status, new_fails, event or None)."""
    if not r.ok:
        fails += 1
        new = "down" if fails >= down_after else prev
    else:
        fails = 0
        new = "degraded" if slow_ms and r.ms >= slow_ms else "up"
    return new, fails, (new if new != prev else None)


class Store:
    def __init__(self, path: str):
        import sqlite3  # lazy: not available in the Cloudflare Worker

        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

    async def open(self):
        pass

    async def close(self):
        self.prune()

    def get(self, site: str):
        row = self.db.execute("select status, fails, since, last from state where site=?", (site,)).fetchone()
        return row or ("up", 0, time.time(), 0)

    def save(self, site: str, r: Result, status: str, fails: int, since: float, now: float):
        self.db.execute("insert into checks values (?,?,?,?,?,?)", (site, now, int(r.ok), r.status, r.ms, r.error))
        self.db.execute("insert or replace into state values (?,?,?,?,?)", (site, status, fails, since, now))
        self.db.commit()

    def prune(self, days: int = 400):
        self.db.execute("delete from checks where ts < ?", (time.time() - days * 86400,))
        self.db.commit()

    def report(self, site: str, days: int):
        rows = self.db.execute(
            "select ok, ms from checks where site=? and ts > ?", (site, time.time() - days * 86400)
        ).fetchall()
        if not rows:
            return None
        ms = sorted(m for ok, m in rows if ok)
        return {
            "uptime_pct": round(100 * sum(ok for ok, _ in rows) / len(rows), 2),
            "avg_ms": int(statistics.mean(ms)) if ms else None,
            "p95_ms": int(ms[int(0.95 * (len(ms) - 1))]) if ms else None,
            "checks": len(rows),
        }


KEEP_DAYS = 90  # blob stores keep daily totals only, so the document stays small


class BlobStore:
    """State + daily totals as one JSON document in a key-value service (Redis REST, Workers KV, ...).
    ponytail: read-modify-write of one document, so overlapping runs lose updates; cron spacing makes that rare."""

    def __init__(self, read, write):
        self._read, self._write = read, write  # async () -> str | None, async (str) -> None
        self.doc = {"sites": {}, "daily": {}}

    async def open(self):
        raw = await self._read()
        if raw:
            self.doc = json.loads(raw)

    async def close(self):
        self.prune()
        await self._write(json.dumps(self.doc, separators=(",", ":")))

    def get(self, site: str):
        s = self.doc["sites"].get(site)
        return tuple(s) if s else ("up", 0, time.time(), 0)

    def save(self, site: str, r: Result, status: str, fails: int, since: float, now: float):
        self.doc["sites"][site] = [status, fails, since, now]
        day = self.doc["daily"].setdefault(site, {}).setdefault(time.strftime("%Y%m%d", time.gmtime(now)), [0, 0, 0, 0])
        day[0] += 1
        if r.ok:
            day[1] += 1
            day[2] += r.ms
            day[3] += 1

    def prune(self, days: int = KEEP_DAYS):
        cutoff = time.strftime("%Y%m%d", time.gmtime(time.time() - days * 86400))
        for d in self.doc["daily"].values():
            for k in [k for k in d if k < cutoff]:
                del d[k]

    def report(self, site: str, days: int):
        cutoff = time.strftime("%Y%m%d", time.gmtime(time.time() - days * 86400))
        rows = [v for k, v in self.doc["daily"].get(site, {}).items() if k > cutoff]
        n = sum(r[0] for r in rows)
        if not n:
            return None
        ms_n = sum(r[3] for r in rows)
        return {
            "uptime_pct": round(100 * sum(r[1] for r in rows) / n, 2),
            "avg_ms": int(sum(r[2] for r in rows) / ms_n) if ms_n else None,
            "p95_ms": None,  # not kept in daily totals
            "checks": n,
        }
