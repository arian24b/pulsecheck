import socket
import ssl
import subprocess
import time
from urllib.parse import urlparse

from .config import Site
from .result import Result, limit  # noqa: F401  (re-exported)


def connect(host: str, port: int, timeout: float, ip_version: int | None = None) -> socket.socket:
    """Open a TCP connection, optionally only over IPv4 (4) or IPv6 (6). IPv6 literals such as 2001:db8::1 work as host."""
    if not ip_version:
        return socket.create_connection((host, port), timeout=timeout)
    family = socket.AF_INET if ip_version == 4 else socket.AF_INET6
    last: OSError | None = None
    for fam, kind, proto, _, addr in socket.getaddrinfo(host, port, family, socket.SOCK_STREAM):  # gaierror if no such address
        sock = socket.socket(fam, kind, proto)
        sock.settimeout(timeout)
        try:
            sock.connect(addr)
            return sock
        except OSError as e:
            sock.close()
            last = e
    raise last or OSError(f"no IPv{ip_version} address for {host}")


def _http(s: Site) -> Result:
    import httpx  # lazy: the Cloudflare Worker uses fetch instead

    t = time.perf_counter()
    kw = {}
    if s.ip_version:  # binding the local side to 0.0.0.0 / :: makes httpx connect over that family only
        kw["transport"] = httpx.HTTPTransport(local_address="0.0.0.0" if s.ip_version == 4 else "::")
    with httpx.Client(follow_redirects=True, max_redirects=s.max_redirects, timeout=s.timeout, **kw) as c:
        r = c.request(s.method, s.url, headers=s.headers, content=s.body)
    ms = int((time.perf_counter() - t) * 1000)
    good = r.status_code in s.expected_status if s.expected_status else 200 <= r.status_code < 300
    return Result(good, ms, r.status_code, "" if good else f"unexpected status {r.status_code}")


def _tcp(s: Site) -> Result:
    t = time.perf_counter()
    connect(s.host, s.port, s.timeout, s.ip_version).close()
    return Result(True, int((time.perf_counter() - t) * 1000))


def _ping(s: Site) -> Result:
    t = time.perf_counter()
    family = [f"-{s.ip_version}"] if s.ip_version else []
    p = subprocess.run(["ping", *family, "-c", "1", "-W", str(s.timeout), s.host], capture_output=True, text=True)
    ms = int((time.perf_counter() - t) * 1000)
    return Result(p.returncode == 0, ms, error="" if p.returncode == 0 else "no ping reply")


def ssl_days_left(s: Site) -> int | None:
    """Days until the certificate expires (<= 0 = expired); None if unknown or not https."""
    u = urlparse(s.url or "")
    if u.scheme != "https" or not u.hostname:
        return None
    try:
        with connect(u.hostname, u.port or 443, s.timeout, s.ip_version) as sock:
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
