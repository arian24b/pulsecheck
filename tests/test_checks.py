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
