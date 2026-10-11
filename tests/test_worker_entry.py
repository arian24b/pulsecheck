"""Runs deploy/cloudflare/src/entry.py against stand-ins for Cloudflare's `js`, `pyodide` and `workers` modules.
This checks our wiring only; it does not prove the code works inside the real Workers runtime."""

import asyncio
import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_entry(tmp_path, fetch):
    mods = {
        "js": types.SimpleNamespace(
            fetch=fetch, Object=types.SimpleNamespace(fromEntries=None), AbortSignal=types.SimpleNamespace(timeout=lambda ms: ms)
        ),
        "pyodide": types.ModuleType("pyodide"),
        "pyodide.ffi": types.SimpleNamespace(to_js=lambda obj, **_: obj),
        "workers": types.SimpleNamespace(WorkerEntrypoint=object, Response=lambda body, **kw: (body, kw)),
    }
    sys.modules.update(mods)
    sys.path.insert(0, str(ROOT / "src"))
    (tmp_path / "pulsecheck.json").write_text(
        json.dumps(
            {
                "notify": {"urls": ["generic://hooks.example.com/x"]},
                "defaults": {"down_after": 1},
                "sites": [
                    {"name": "web", "url": "https://ok.example.com"},
                    {"name": "api", "url": "https://bad.example.com/${TOKEN}"},
                    {"name": "db", "type": "tcp", "host": "h", "port": 1},
                    {"name": "v6", "url": "https://v6.example.com", "ip_version": 6},
                ],
            }
        )
    )
    spec = importlib.util.spec_from_file_location("entry", ROOT / "deploy/cloudflare/src/entry.py")
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(tmp_path / "entry.py")  # the Worker reads pulsecheck.json next to itself
    spec.loader.exec_module(mod)
    return mod


def test_scheduled_run(tmp_path):
    calls, kv = [], {}

    async def fetch(url, init=None):
        calls.append((url, init))
        return types.SimpleNamespace(status=500 if "bad" in url else 200)

    entry = load_entry(tmp_path, fetch)

    class KV:
        async def get(self, k):
            return kv.get(k)

        async def put(self, k, v):
            kv[k] = v

    w = entry.Default()
    w.env = types.SimpleNamespace(STATE=KV(), TOKEN="abc")
    asyncio.run(w.scheduled(None, None, None))  # Cloudflare passes env=None here; the Worker must use self.env
    urls = [c[0] for c in calls]
    assert "https://bad.example.com/abc" in urls  # ${TOKEN} came from the Worker env
    hook = [c for c in calls if c[0] == "https://hooks.example.com/x"]
    assert len(hook) == 1 and "api is DOWN" in json.loads(hook[0][1]["body"])["message"]
    assert json.loads(kv["pulsecheck"])["sites"]["api"][0] == "down"
    assert "db" not in json.loads(kv["pulsecheck"])["sites"]  # tcp is skipped on Workers
    assert "v6" not in json.loads(kv["pulsecheck"])["sites"] and "https://v6.example.com" not in urls  # fetch cannot pick IPv6


def test_status_endpoint_needs_token(tmp_path):
    async def fetch(url, init=None):
        return types.SimpleNamespace(status=200)

    entry = load_entry(tmp_path, fetch)
    kv = {}

    class KV:
        async def get(self, k):
            return kv.get(k)

        async def put(self, k, v):
            kv[k] = v

    w = entry.Default()
    w.env = types.SimpleNamespace(STATE=KV(), TOKEN="abc", STATUS_TOKEN="s3")
    req = lambda auth: types.SimpleNamespace(url="https://w.example.com/status?format=text", headers={"authorization": auth})  # noqa: E731
    assert asyncio.run(w.fetch(req("Bearer wrong")))[1] == {"status": 401}
    body, _ = asyncio.run(w.fetch(req("Bearer s3")))
    assert "web" in body and "api" in body


def test_generated_bundle_is_self_contained(tmp_path, monkeypatch):
    """build.py output (one entry.py with the package embedded) must run with nothing but the standard library."""
    import subprocess

    cfg = tmp_path / "c.yml"
    cfg.write_text(
        "notify: {urls: ['generic://hooks.example.com/x']}\ndefaults: {down_after: 1}\nsites:\n  - {name: web, url: 'https://${HOST}'}\n"
    )
    env = {**__import__("os").environ, "HOST": "bad.example.com"}
    out = subprocess.run(
        [sys.executable, str(ROOT / "deploy/cloudflare/build.py"), str(cfg), "--kv-id", "k"], capture_output=True, text=True, env=env
    )
    assert out.returncode == 0, out.stderr
    base = ROOT / "deploy/cloudflare/.cloudflare/output/v0/workers/default"
    worker = json.loads((base / "worker.config.json").read_text())
    assert list(worker["manifest"]["modules"]) == ["entry.py"] and worker["env"]["HOST"] == {"type": "secret"}
    assert worker["env"]["STATE"] == {"type": "kv", "id": "k"} and worker["triggers"][0]["type"] == "scheduled"

    calls, kv = [], {}

    async def fetch(url, init=None):
        calls.append(url)
        return types.SimpleNamespace(status=500)

    for name in [m for m in sys.modules if m == "pulsecheck" or m.startswith("pulsecheck.")]:
        monkeypatch.delitem(sys.modules, name)  # the bundle must bring its own copy
    monkeypatch.setattr(sys, "path", [p for p in sys.path if not p.endswith("/src")])
    sys.modules.update(
        js=types.SimpleNamespace(
            fetch=fetch, Object=types.SimpleNamespace(fromEntries=None), AbortSignal=types.SimpleNamespace(timeout=lambda ms: ms)
        ),
        pyodide=types.ModuleType("pyodide"),
    )
    sys.modules["pyodide.ffi"] = types.SimpleNamespace(to_js=lambda obj, **_: obj)
    sys.modules["workers"] = types.SimpleNamespace(WorkerEntrypoint=object, Response=lambda body, **kw: (body, kw))
    spec = importlib.util.spec_from_file_location("bundled_entry", base / "bundle/entry.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class KV:
        async def get(self, k):
            return kv.get(k)

        async def put(self, k, v):
            kv[k] = v

    w = mod.Default()
    w.env = types.SimpleNamespace(STATE=KV(), HOST="bad.example.com")
    asyncio.run(w.scheduled(None, None, None))
    assert "https://bad.example.com" in calls and "https://hooks.example.com/x" in calls
    assert json.loads(kv["pulsecheck"])["sites"]["web"][0] == "down"
