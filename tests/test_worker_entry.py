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
        "js": types.SimpleNamespace(fetch=fetch, Object=types.SimpleNamespace(fromEntries=None), AbortSignal=types.SimpleNamespace(timeout=lambda ms: ms)),
        "pyodide": types.ModuleType("pyodide"),
        "pyodide.ffi": types.SimpleNamespace(to_js=lambda obj, **_: obj),
        "workers": types.SimpleNamespace(WorkerEntrypoint=object, Response=lambda body: body),
    }
    sys.modules.update(mods)
    sys.path.insert(0, str(ROOT / "src"))
    (tmp_path / "pulsecheck.yml").write_text(
        'notify: {urls: ["generic://hooks.example.com/x"]}\n'
        "defaults: {down_after: 1}\n"
        "sites:\n  - {name: web, url: https://ok.example.com}\n  - {name: api, url: 'https://bad.example.com/${TOKEN}'}\n"
        "  - {name: db, type: tcp, host: h, port: 1}\n"
    )
    spec = importlib.util.spec_from_file_location("entry", ROOT / "deploy/cloudflare/src/entry.py")
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(tmp_path / "entry.py")  # the Worker reads pulsecheck.yml next to itself
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

    env = types.SimpleNamespace(STATE=KV(), TOKEN="abc")
    asyncio.run(entry.Default().scheduled(None, env, None))
    urls = [c[0] for c in calls]
    assert "https://bad.example.com/abc" in urls  # ${TOKEN} came from the Worker env
    hook = [c for c in calls if c[0] == "https://hooks.example.com/x"]
    assert len(hook) == 1 and "api is DOWN" in json.loads(hook[0][1]["body"])["message"]
    assert json.loads(kv["pulsecheck"])["sites"]["api"][0] == "down"
    assert "db" not in json.loads(kv["pulsecheck"])["sites"]  # tcp is skipped on Workers
