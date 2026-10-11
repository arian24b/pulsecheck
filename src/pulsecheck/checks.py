import socket
import subprocess
import time
from dataclasses import dataclass

import httpx

from .config import Site


@dataclass
class Result:
    ok: bool
    ms: int
    status: int | None = None
    error: str = ""


def _http(s: Site) -> Result:
    t = time.perf_counter()
    with httpx.Client(follow_redirects=True, max_redirects=s.max_redirects, timeout=s.timeout) as c:
        r = c.request(s.method, s.url, headers=s.headers, content=s.body)
    ms = int((time.perf_counter() - t) * 1000)
    good = r.status_code in s.expected_status if s.expected_status else 200 <= r.status_code < 300
    return Result(good, ms, r.status_code, "" if good else f"unexpected status {r.status_code}")


def _tcp(s: Site) -> Result:
    t = time.perf_counter()
    socket.create_connection((s.host, s.port), timeout=s.timeout).close()
    return Result(True, int((time.perf_counter() - t) * 1000))


def _ping(s: Site) -> Result:
    t = time.perf_counter()
    p = subprocess.run(["ping", "-c", "1", "-W", str(s.timeout), s.host], capture_output=True, text=True)
    ms = int((time.perf_counter() - t) * 1000)
    return Result(p.returncode == 0, ms, error="" if p.returncode == 0 else "no ping reply")


def run_check(s: Site) -> Result:
    try:
        r = {"http": _http, "tcp": _tcp, "ping": _ping}[s.type](s)
    except Exception as e:  # any transport failure is a failed check
        return Result(False, 0, error=f"{type(e).__name__}: {e}")
    if r.ok and s.max_response_ms and r.ms > s.max_response_ms:
        r.ok, r.error = False, f"response {r.ms}ms > max {s.max_response_ms}ms"
    return r
