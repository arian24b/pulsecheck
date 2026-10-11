import socket
import ssl
import subprocess
import time
from urllib.parse import urlparse

from .config import Site
from .result import Result, limit  # noqa: F401  (re-exported)


def _http(s: Site) -> Result:
    import httpx  # lazy: the Cloudflare Worker uses fetch instead

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


def ssl_days_left(s: Site) -> int | None:
    """Days until the certificate expires (<= 0 = expired); None if unknown or not https."""
    u = urlparse(s.url or "")
    if u.scheme != "https" or not u.hostname:
        return None
    try:
        with socket.create_connection((u.hostname, u.port or 443), timeout=s.timeout) as sock:
            with ssl.create_default_context().wrap_socket(sock, server_hostname=u.hostname) as tls:
                cert = tls.getpeercert()
        return int((ssl.cert_time_to_seconds(cert["notAfter"]) - time.time()) // 86400)
    except ssl.SSLCertVerificationError as e:
        return 0 if e.verify_code == 10 else None  # 10 = X509_V_ERR_CERT_HAS_EXPIRED
    except Exception:
        return None


def run_check(s: Site) -> Result:
    try:
        r = {"http": _http, "tcp": _tcp, "ping": _ping}[s.type](s)
    except Exception as e:  # any transport failure is a failed check
        return Result(False, 0, error=f"{type(e).__name__}: {e}")
    r = limit(r, s)
    if s.ssl_warn_days is not None and s.type == "http":
        r.ssl_days = ssl_days_left(s)
        if r.ssl_days is not None and r.ssl_days <= 0:
            r.ok, r.error = False, "TLS certificate has expired"
    return r
