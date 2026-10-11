import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from . import config, engine, notify, otel, setup
from .checks import run_check
from .state import Store


def http_post(url, headers, body):  # sync; callers run it in a thread
    req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
    try:
        return urllib.request.urlopen(req, timeout=15).status
    except urllib.error.HTTPError as e:
        return e.code


async def post(url, headers, body):
    return await asyncio.to_thread(http_post, url, headers, body)


def run(cfg: config.Config, fail_on_down: bool = False, force: bool = False, tag: str | None = None) -> int:
    cmd = notify.command(cfg.shoutrrr_bin, cfg.shoutrrr_image)

    async def check(s):
        return await asyncio.to_thread(run_check, s)

    async def send(urls, text):
        await asyncio.to_thread(notify.send, cmd, urls, text)

    down = asyncio.run(engine.run(cfg, Store(cfg.state_file), check, send, post=post, force=force, tag=tag))
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


def channels(cfg: config.Config) -> list[tuple[str, str]]:
    """Every alert url in the config as (label, url): the global ones and each site's own, without duplicates."""
    out, seen = [], set()
    for where, urls in [("global", cfg.notify.urls), *[(f"site {s.name}", s.notify.urls) for s in cfg.sites if s.notify]]:
        for u in urls:
            if u not in seen:
                seen.add(u)
                out.append((where, u))
    return out


def validate(cfg: config.Config, path, skip_verify: bool) -> int:
    kinds = {}
    for s in cfg.sites:
        kinds[s.type] = kinds.get(s.type, 0) + 1
    print(f"ok: {path}")
    print(
        f"  {len(cfg.sites)} sites ("
        + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items()))
        + f"), {len(cfg.maintenance)} maintenance windows"
    )
    problems = 0
    chans = channels(cfg)
    if not chans:
        print("  warning: no alert urls (notify.urls is empty), nothing will be sent")
    if cfg.otel:
        print(f"  opentelemetry: {cfg.otel.endpoint}")
    if chans and not skip_verify:
        cmd = notify.command(cfg.shoutrrr_bin, cfg.shoutrrr_image)
        for where, u in chans:
            ok, detail = notify.verify(cmd, u)
            if "No such file" in detail or "not found" in detail:
                print("  note: shoutrrr is not available here, alert urls were not verified (use --no-verify to silence)")
                break
            print(f"  {'ok  ' if ok else 'BAD '} {setup.mask(u)} ({where}){'' if ok else ': ' + detail}")
            problems += not ok
    return 1 if problems else 0


def test_notify(cfg: config.Config) -> int:
    cmd = notify.command(cfg.shoutrrr_bin, cfg.shoutrrr_image)
    text = config.render(cfg, None, "test")
    bad = 0
    chans = channels(cfg)
    if not chans and not cfg.otel:
        print("no alert urls configured")
        return 1
    for where, u in chans:
        ok, detail = notify.send_one(cmd, u, text)
        print(f"{'sent  ' if ok else 'FAILED'} {setup.mask(u)} ({where}){'' if ok else ': ' + detail}")
        bad += not ok
    if cfg.otel:
        ev = [{"site": "pulsecheck", "event": "up", "state": "up", "message": text}]
        ok = asyncio.run(otel.push(post, cfg.otel, [], ev, time.time()))
        print(f"{'sent  ' if ok else 'FAILED'} opentelemetry {cfg.otel.endpoint}")
        bad += not ok
    return 1 if bad else 0


def env_command(path, show_path: bool) -> int:
    f = setup.ensure_env_file(path)
    if show_path:
        print(f)
        return 0
    rc = setup.open_in_editor(f)
    want = config.env_names(path.read_text())
    have = setup.parse_dotenv(f.read_text())
    missing = sorted(n for n in want if not (have.get(n) or os.environ.get(n)))
    print(f"saved: {f}" + (f"\nstill empty: {', '.join(missing)}" if missing else "\nall variables used by the config have a value"))
    return rc


def update_command(check_only: bool) -> int:
    now, latest = setup.installed_version(), setup.latest_version()
    print(f"installed: {now}\nlatest on PyPI: {latest or 'unknown (offline or not published yet)'}")
    if check_only:
        return 0
    if latest and latest == now:
        print("already up to date")
        return 0
    cmd = setup.upgrade_command()
    print("running:", " ".join(cmd))
    return subprocess.call(cmd)


def build_parser():
    p = argparse.ArgumentParser(prog="pulsecheck", description="Self-hosted uptime monitor with shoutrrr alerts.")
    p.add_argument("-c", "--config", help="config file (default: ./pulsecheck.yml, then ~/.config/pulsecheck/pulsecheck.yml)")
    p.add_argument("--version", action="version", version=f"pulsecheck {setup.installed_version()}")
    sub = p.add_subparsers(dest="cmd", metavar="command")

    def add(name, help_):
        return sub.add_parser(name, help=help_, description=help_)

    sub.add_parser("help", help="show help for a command").add_argument("topic", nargs="?")
    i = add("init", "create the config and .env, download shoutrrr, add the cron job (Linux)")
    i.add_argument("-y", "--yes", action="store_true", help="do not ask questions")
    i.add_argument("--force", action="store_true", help="replace an existing config")
    i.add_argument("--no-cron", action="store_true")
    i.add_argument("--no-download", action="store_true", help="do not fetch shoutrrr")
    i.add_argument("--cron", default=setup.DEFAULT_CRON, metavar="EXPR", help="cron schedule (default: %(default)s)")
    i.add_argument("--remove-cron", action="store_true", help="only remove the cron job that init added")
    e = add("env", "open the .env file (secrets for ${VARS}) in your editor")
    e.add_argument("--path", action="store_true", help="only print the file path")
    v = add("validate", "check the config file (syntax, keys, alert urls)")
    v.add_argument("--no-verify", action="store_true", help="do not ask shoutrrr to verify alert urls")
    add("test-notify", "send a test message to every alert channel in the config")
    r = add("run", "check all due sites once")
    r.add_argument("--fail-on-down", action="store_true")
    r.add_argument("--force", action="store_true", help="ignore per-site intervals")
    r.add_argument("--tag", help="only sites with this tag")
    st = add("status", "current state of every site")
    st.add_argument("--json", action="store_const", const="json", dest="fmt")
    st.add_argument("--md", action="store_const", const="md", dest="fmt", help="markdown table, e.g. for $GITHUB_STEP_SUMMARY")
    st.add_argument("--tag")
    rp = add("report", "uptime and response times")
    rp.add_argument("--json", action="store_true")
    rp.add_argument("--tag")
    u = add("update", "upgrade pulsecheck to the latest version")
    u.add_argument("--check", action="store_true", help="only compare versions")
    return p, sub


def main(argv=None) -> None:
    p, sub = build_parser()
    a = p.parse_args(argv)
    if a.cmd is None:
        p.print_help()
        return
    if a.cmd == "help":
        (sub.choices[a.topic] if a.topic in sub.choices else p).print_help()
        return
    if a.cmd == "update":
        sys.exit(update_command(a.check))
    if a.cmd == "init":
        if a.remove_cron:
            setup.edit_crontab(None)
            print("cron job removed")
        else:
            setup.init(yes=a.yes, force=a.force, cron=not a.no_cron, download=not a.no_download, schedule=a.cron)
        return
    path = setup.find_config(a.config)
    if a.cmd == "env":
        sys.exit(env_command(path, a.path))
    setup.load_dotenv(path)
    try:
        cfg = config.load(str(path))
    except Exception as e:
        sys.exit(f"config error: {e}")
    cfg.state_file = os.path.expanduser(cfg.state_file)
    if not os.path.isabs(cfg.state_file):  # relative to the config file, so cron (cwd = $HOME) finds the same state
        cfg.state_file = str(path.resolve().parent / cfg.state_file)
    if a.cmd == "validate":
        sys.exit(validate(cfg, path, a.no_verify))
    elif a.cmd == "test-notify":
        sys.exit(test_notify(cfg))
    elif a.cmd == "report":
        report(cfg, a.json, a.tag)
    elif a.cmd == "status":
        status(cfg, a.fmt or "text", a.tag)
    else:
        sys.exit(run(cfg, a.fail_on_down, a.force, a.tag))
