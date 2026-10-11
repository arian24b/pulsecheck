import argparse
import asyncio
import json
import sys

from . import config, engine, notify
from .checks import run_check
from .state import Store


def run(cfg: config.Config, fail_on_down: bool = False, force: bool = False, tag: str | None = None) -> int:
    cmd = notify.command(cfg.shoutrrr_bin, cfg.shoutrrr_image)

    async def check(s):
        return await asyncio.to_thread(run_check, s)

    async def send(urls, text):
        await asyncio.to_thread(notify.send, cmd, urls, text)

    down = asyncio.run(engine.run(cfg, Store(cfg.state_file), check, send, force=force, tag=tag))
    return 1 if fail_on_down and down else 0


def status(cfg: config.Config, fmt: str, tag: str | None) -> None:
    rows = asyncio.run(engine.status(cfg, Store(cfg.state_file), tag))
    print(json.dumps(rows, indent=2) if fmt == "json" else engine.format_status(rows, fmt == "md"))


def report(cfg: config.Config, as_json: bool, tag: str | None = None) -> None:
    store = Store(cfg.state_file)
    out = {s.name: {w: store.report(s.name, d) for w, d in engine.WINDOWS.items()} for s in cfg.sites if not tag or tag in s.tags}
    if as_json:
        print(json.dumps(out, indent=2))
        return
    for name, ws in out.items():
        print(name)
        for w, v in ws.items():
            print(
                f"  {w:6} " + (f"{v['uptime_pct']}%  avg {v['avg_ms']}ms  p95 {v['p95_ms']}ms  ({v['checks']} checks)" if v else "no data")
            )


def main() -> None:
    p = argparse.ArgumentParser(prog="pulsecheck")
    p.add_argument("-c", "--config", default="pulsecheck.yml")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="check all due sites once")
    r.add_argument("--fail-on-down", action="store_true")
    r.add_argument("--force", action="store_true", help="ignore per-site intervals")
    r.add_argument("--tag", help="only sites with this tag")
    rp = sub.add_parser("report")
    rp.add_argument("--json", action="store_true")
    rp.add_argument("--tag")
    st = sub.add_parser("status", help="current state of every site")
    st.add_argument("--json", action="store_const", const="json", dest="fmt")
    st.add_argument("--md", action="store_const", const="md", dest="fmt", help="markdown table, e.g. for $GITHUB_STEP_SUMMARY")
    st.add_argument("--tag")
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
        report(cfg, a.json, a.tag)
    elif a.cmd == "status":
        status(cfg, a.fmt or "text", a.tag)
    else:
        sys.exit(run(cfg, a.fail_on_down, a.force, a.tag))
