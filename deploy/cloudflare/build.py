"""Build the Cloudflare Worker for `cf deploy --prebuilt`.

Usage: uv run python deploy/cloudflare/build.py [pulsecheck.yml] [--cron "*/5 * * * *"] [--name pulsecheck]
Writes .cloudflare/output/v0/ (Build Output) and .cloudflare/secrets.env (values of the ${VARS} your YAML uses,
taken from the environment). The Worker has no third-party packages: the YAML is converted to JSON here.
"""

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from pulsecheck import config

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / ".cloudflare" / "output" / "v0"

ap = argparse.ArgumentParser()
ap.add_argument("config", nargs="?", default=str(ROOT / "pulsecheck.yml"))
ap.add_argument("--cron", default="*/5 * * * *")
ap.add_argument("--name", default="pulsecheck")
ap.add_argument(
    "--kv-id", help="existing KV namespace id (default: reuse the namespace named <name>-state if it exists, else cf creates it)"
)
ap.add_argument("--no-logs", action="store_true", help="do not enable Workers Logs (read them with `cf o11y telemetry query`)")
ap.add_argument("--date", default="2025-10-01", help="Workers compatibility date")
a = ap.parse_args()

text = Path(a.config).read_text()
raw = config.parse(text)
config.from_dict(raw)  # fail here, not at 3 a.m. in the Worker
needed = sorted(config.env_names(text))
missing = [n for n in needed if n not in os.environ]
if missing:
    raise SystemExit(f"export these environment variables first (they hold the values of ${{VAR}} in your YAML): {', '.join(missing)}")
names = needed + (["STATUS_TOKEN"] if "STATUS_TOKEN" in os.environ else [])  # STATUS_TOKEN enables the /status and /run endpoints

shutil.rmtree(HERE / ".cloudflare", ignore_errors=True)
bundle = OUT / "workers" / "default" / "bundle"
bundle.mkdir(parents=True)

# Cloudflare mounts only the main module for Python Workers (other modules are not importable, verified with `cf deploy`),
# so everything goes into ONE entry.py: the package sources are embedded and registered as pulsecheck.* at import time.
ORDER = ["config", "result", "state", "httpnotify", "otel", "engine"]  # dependency order; cli/web/notify/checks are not used in the Worker
sources = {n: (ROOT / "src" / "pulsecheck" / f"{n}.py").read_text() for n in ORDER}
loader = """import sys as _sys, types as _types

_SRC = %s
_pkg = _types.ModuleType("pulsecheck")
_pkg.__path__ = []
_sys.modules["pulsecheck"] = _pkg
for _n, _s in _SRC.items():
    _m = _types.ModuleType("pulsecheck." + _n)
    _m.__package__ = "pulsecheck"
    _sys.modules[_m.__name__] = _m
    setattr(_pkg, _n, _m)
    exec(compile(_s, "pulsecheck/" + _n + ".py", "exec"), _m.__dict__)
del _n, _s, _m

CONFIG_TEXT = %s
""" % (repr(sources), repr(json.dumps(raw)))  # noqa: UP031 (the template contains braces)
(bundle / "entry.py").write_text(loader + (HERE / "src" / "entry.py").read_text())
modules = {"entry.py": {"type": "python"}}

kv = {"type": "kv"}
kv_id = a.kv_id
if not kv_id:
    try:  # redeploys must reuse the namespace that the first deploy created
        found = json.loads(subprocess.run(["cf", "kv", "namespaces", "list"], capture_output=True, text=True, timeout=60).stdout or "[]")
        kv_id = next((n["id"] for n in found if n["title"] == f"{a.name}-state"), None)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
if kv_id:
    kv["id"] = kv_id
env = {"STATE": kv, **{n: {"type": "secret"} for n in names}}
(OUT / "config.json").write_text(json.dumps({"buildContext": {"isPreview": False}}))
(OUT / "workers" / "default" / "worker.config.json").write_text(
    json.dumps(
        {
            "name": a.name,
            "compatibilityDate": a.date,
            "compatibilityFlags": ["python_workers"],
            "triggers": [{"type": "scheduled", "schedule": a.cron}],
            "env": env,
            "observability": {"enabled": not a.no_logs},
            "manifest": {"type": "complete", "mainModule": "entry.py", "modules": modules},
        }
    )
)
secrets = {n: os.environ[n] for n in names if n in os.environ}
(HERE / ".cloudflare" / "secrets.env").write_text("".join(f"{k}={v}\n" for k, v in secrets.items()))
print(f"built {OUT} ({len(modules)} module). secrets: {sorted(secrets)}")
