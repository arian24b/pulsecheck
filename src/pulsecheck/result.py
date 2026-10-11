"""Check result type; kept free of heavy imports so the Cloudflare Worker can load it."""

from dataclasses import dataclass


@dataclass
class Result:
    ok: bool
    ms: int
    status: int | None = None
    error: str = ""
    ssl_days: int | None = None  # days until the https certificate expires, when ssl_warn_days is set


def limit(r: Result, s) -> Result:
    if r.ok and s.max_response_ms and r.ms > s.max_response_ms:
        r.ok, r.error = False, f"response {r.ms}ms > max {s.max_response_ms}ms"
    return r
