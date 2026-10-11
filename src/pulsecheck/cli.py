import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import config, notify
from .checks import run_check
from .state import Store, step

WINDOWS = {"day": 1, "week": 7, "month": 30, "year": 365}


def run(cfg: config.Config, fail_on_down: bool = False, force: bool = False) -> int:
    store = Store(cfg.state_file)
    now = time.time()
    utc = datetime.now(timezone.utc)
    due = [s for s in cfg.sites if force or now - store.get(s.name)[3] >= s.interval * 60 - 60]
    with ThreadPoolExecutor(max_workers=16) as ex:
        results = list(ex.map(run_check, due))
    down = 0
    for s, r in zip(due, results):
        prev, fails, since, _ = store.get(s.name)
        new, fails, event = step(prev, fails, r, s.down_after, s.slow_ms)
        downtime = now - since
        store.save(s.name, r, new, fails, now if event else since, now)
        down += new == "down"
        print(f"{s.name}: {new} {r.ms}ms {r.error}".rstrip())
        n = s.notify or cfg.notify
        # ponytail: alerts raised during maintenance are dropped, not deferred
        if event and event in n.events and not any(m.active(utc, s.name) for m in cfg.maintenance):
            notify.send(notify.command(cfg.shoutrrr_bin, cfg.shoutrrr_image), n.urls, config.render(
                cfg, s, event, site=s.name, error=r.error, ms=r.ms, status=r.status or "", minutes=int(downtime // 60)))
    store.prune()
    return 1 if fail_on_down and down else 0


def report(cfg: config.Config, as_json: bool) -> None:
    store = Store(cfg.state_file)
    out = {s.name: {w: store.report(s.name, d) for w, d in WINDOWS.items()} for s in cfg.sites}
    if as_json:
        print(json.dumps(out, indent=2))
        return
    for name, ws in out.items():
        print(name)
        for w, v in ws.items():
            print(f"  {w:6} " + (f"{v['uptime_pct']}%  avg {v['avg_ms']}ms  p95 {v['p95_ms']}ms  ({v['checks']} checks)" if v else "no data"))


def main() -> None:
    p = argparse.ArgumentParser(prog="pulsecheck")
    p.add_argument("-c", "--config", default="pulsecheck.yml")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="check all due sites once")
    r.add_argument("--fail-on-down", action="store_true")
    r.add_argument("--force", action="store_true", help="ignore per-site intervals")
    rp = sub.add_parser("report")
    rp.add_argument("--json", action="store_true")
    sub.add_parser("validate")
    sub.add_parser("test-notify")
    a = p.parse_args()
    try:
        cfg = config.load(a.config)
    except Exception as e:
        sys.exit(f"config error: {e}")
    if a.cmd == "validate":
        print(f"ok: {len(cfg.sites)} sites")
    elif a.cmd == "test-notify":
        notify.send(notify.command(cfg.shoutrrr_bin, cfg.shoutrrr_image), cfg.notify.urls, config.render(cfg, None, "test"))
    elif a.cmd == "report":
        report(cfg, a.json)
    else:
        sys.exit(run(cfg, a.fail_on_down, a.force))
