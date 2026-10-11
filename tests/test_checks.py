import shutil
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from pulsecheck.checks import run_check
from pulsecheck.config import Site


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/slow":
            time.sleep(0.2)
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        ok = body == b'{"ping": true}' and self.headers.get("Authorization") == "Bearer t"
        self.send_response(201 if ok else 400)
        self.end_headers()

    def log_message(self, *a):
        pass


@pytest.fixture
def server():
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/"
    srv.shutdown()


def post(url, **kw):
    return Site(name="a", url=url, method="POST", body='{"ping": true}', headers={"Authorization": "Bearer t"}, **kw)


def test_post_headers_body_expected_status(server):
    assert run_check(post(server, expected_status=[201])).ok
    assert run_check(post(server)).ok  # no expected_status: any 2xx
    assert not run_check(post(server, expected_status=[200])).ok
    r = run_check(Site(name="a", url=server, method="POST", body="x", expected_status=[201]))
    assert not r.ok and r.status == 400


def test_max_response_ms(server):
    r = run_check(post(server + "slow", max_response_ms=50))
    assert not r.ok and "max" in r.error
    assert run_check(post(server + "slow", max_response_ms=5000)).ok


@pytest.mark.skipif(not shutil.which("ping"), reason="no ping binary")
def test_ping():
    assert run_check(Site(name="p", type="ping", host="127.0.0.1")).ok
    assert not run_check(Site(name="p", type="ping", host="no-such-host.invalid", timeout=1)).ok


# ---------------------------------------------------------------- ip_version
import socket  # noqa: E402


def _has_ipv6_loopback() -> bool:
    try:
        s = socket.socket(socket.AF_INET6)
        s.bind(("::1", 0))
        s.close()
        return True
    except OSError:
        return False


needs_v6 = pytest.mark.skipif(not _has_ipv6_loopback(), reason="no IPv6 loopback")


class _V6Server(HTTPServer):
    address_family = socket.AF_INET6


@pytest.fixture
def v6_server():
    srv = _V6Server(("::1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_port
    srv.shutdown()


def test_ip_version_is_validated():
    with pytest.raises(ValueError, match="ip_version must be 4 or 6"):
        Site(name="a", url="http://x", ip_version=5)
    assert Site(name="a", url="http://x", ip_version=6).ip_version == 6


@needs_v6
def test_tcp_over_ipv6_literal_and_family_filter(v6_server):
    # an IPv6 literal works with and without ip_version
    assert run_check(Site(name="t", type="tcp", host="::1", port=v6_server)).ok
    assert run_check(Site(name="t", type="tcp", host="::1", port=v6_server, ip_version=6)).ok
    # forcing IPv4 against an address that only exists as IPv6 must fail, not silently fall back
    r = run_check(Site(name="t", type="tcp", host="::1", port=v6_server, ip_version=4))
    assert not r.ok


@needs_v6
def test_http_over_ipv6(v6_server):
    url = f"http://[::1]:{v6_server}/"
    ok = run_check(Site(name="h", url=url, method="POST", body="x", expected_status=[400], ip_version=6))
    assert ok.ok and ok.status == 400
    assert not run_check(Site(name="h", url=url, method="POST", body="x", expected_status=[400], ip_version=4, timeout=2)).ok


def test_ip_version_decides_which_family_localhost_uses(server):
    # the fixture listens on 127.0.0.1 only: IPv4 works, IPv6 to the same name must not
    port = server.rsplit(":", 1)[1].rstrip("/")
    assert run_check(Site(name="t", type="tcp", host="127.0.0.1", port=int(port), ip_version=4)).ok
    if _has_ipv6_loopback():
        assert not run_check(Site(name="t", type="tcp", host="localhost", port=int(port), ip_version=6, timeout=2)).ok


def test_ping_gets_the_family_flag(monkeypatch):
    from pulsecheck import checks

    seen = []

    def fake_run(cmd, **kw):
        seen.append(cmd)
        return type("P", (), {"returncode": 0})()

    monkeypatch.setattr(checks.subprocess, "run", fake_run)
    run_check(Site(name="p", type="ping", host="example.com", ip_version=6))
    run_check(Site(name="p", type="ping", host="example.com"))
    assert seen[0][:2] == ["ping", "-6"] and "-4" not in seen[1] and "-6" not in seen[1]
