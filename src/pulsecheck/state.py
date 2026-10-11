import sqlite3
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
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

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
