import asyncio
import os
import time
import urllib.error
import urllib.request

from cfui import App, Arg, Fail, ui

from . import config, engine, notify, otel, setup
from .checks import run_check
from .state import Store


def _ms(v):
    return "-" if v is None else f"{v}ms"


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
    ui.data(rows) if fmt == "json" else ui.out(engine.format_status(rows, fmt == "md"))


def report(cfg: config.Config, as_json: bool, tag: str | None = None) -> None:
    store = Store(cfg.state_file)
    out = {s.name: {w: store.report(s.name, d) for w, d in engine.WINDOWS.items()} for s in cfg.sites if not tag or tag in s.tags}
    if as_json:
        ui.data(out)
        return
    rows = [
        (name, w, f"{v['uptime_pct']}%", _ms(v["avg_ms"]), _ms(v["p95_ms"]), v["checks"]) if v else (name, w, "no data", "", "", "")
        for name, ws in out.items()
        for w, v in ws.items()
    ]
    ui.table(rows, ["Site", "Window", "Uptime", "Avg", "p95", "Checks"])


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
    ui.success(f"config ok: {path}")
    ui.info(
        f"{len(cfg.sites)} sites ("
        + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items()))
        + f"), {len(cfg.maintenance)} maintenance windows"
    )
    problems = 0
    chans = channels(cfg)
    if not chans:
        ui.warning("no alert urls (notify.urls is empty), nothing will be sent")
    if cfg.otel:
        ui.info(f"opentelemetry: {cfg.otel.endpoint}")
    if chans and not skip_verify:
        cmd = notify.command(cfg.shoutrrr_bin, cfg.shoutrrr_image)
        for where, u in chans:
            ok, detail = notify.verify(cmd, u)
            if "No such file" in detail or "not found" in detail:
                ui.warning("shoutrrr is not available here, alert urls were not verified (use --no-verify to silence)")
                break
            (ui.success if ok else ui.error)(f"{setup.mask(u)} ({where}){'' if ok else ': ' + detail}")
            problems += not ok
    return 1 if problems else 0


def test_notify(cfg: config.Config) -> int:
    cmd = notify.command(cfg.shoutrrr_bin, cfg.shoutrrr_image)
    text = config.render(cfg, None, "test")
    bad = 0
    chans = channels(cfg)
    if not chans and not cfg.otel:
        ui.error("no alert urls configured")
        return 1
    for where, u in chans:
        ok, detail = notify.send_one(cmd, u, text)
        (ui.success if ok else ui.error)(f"{'sent' if ok else 'FAILED'} {setup.mask(u)} ({where}){'' if ok else ': ' + detail}")
        bad += not ok
    if cfg.otel:
        ev = [{"site": "pulsecheck", "event": "up", "state": "up", "message": text}]
        ok = asyncio.run(otel.push(post, cfg.otel, [], ev, time.time()))
        (ui.success if ok else ui.error)(f"{'sent' if ok else 'FAILED'} opentelemetry {cfg.otel.endpoint}")
        bad += not ok
    return 1 if bad else 0


def env_command(path, show_path: bool) -> int:
    f = setup.ensure_env_file(path)
    if show_path:
        ui.out(f)
        return 0
    rc = setup.open_in_editor(f)
    want = config.env_names(path.read_text())
    have = setup.parse_dotenv(f.read_text())
    missing = sorted(n for n in want if not (have.get(n) or os.environ.get(n)))
    ui.success(f"saved: {f}")
    if missing:
        ui.warning(f"still empty: {', '.join(missing)}")
    else:
        ui.info("all variables used by the config have a value")
    return rc


CONFIG = Arg("-c", "--config", help="config file (default: ./pulsecheck.yml, then ~/.config/pulsecheck/pulsecheck.yml)")
TAG = Arg("--tag", help="only sites with this tag")

app = App(
    "pulsecheck",
    repo="https://github.com/arian24b/pulsecheck",
    pypi=setup.PACKAGE,
    description="Self-hosted uptime monitor with shoutrrr alerts.",
    global_args=[CONFIG],
    upgrade=setup.upgrade_command,
)


def load(a):
    """Find, load and finish the config named by -c (or the defaults)."""
    path = setup.find_config(a.config)
    setup.load_dotenv(path)
    try:
        cfg = config.load(str(path))
    except Exception as e:
        raise Fail(f"config error: {e}") from e
    cfg.state_file = os.path.expanduser(cfg.state_file)
    if not os.path.isabs(cfg.state_file):  # relative to the config file, so cron (cwd = $HOME) finds the same state
        cfg.state_file = str(path.resolve().parent / cfg.state_file)
    return path, cfg


@app.command(
    "init",
    "Create the config and .env, download shoutrrr, add the cron job (Linux)",
    banner=True,
    args=[
        Arg("--force", action="store_true", help="replace an existing config"),
        Arg("--no-cron", action="store_true", help="do not add the cron job"),
        Arg("--no-download", action="store_true", help="do not fetch shoutrrr"),
        Arg("--cron", default=setup.DEFAULT_CRON, metavar="EXPR", help="cron schedule"),
        Arg("--remove-cron", action="store_true", help="only remove the cron job that init added"),
    ],
)
def init_cmd(a):
    if a.remove_cron:
        setup.edit_crontab(None)
        ui.success("cron job removed")
        return 0
    setup.init(force=a.force, cron=not a.no_cron, download=not a.no_download, schedule=a.cron)
    ui.hint("next: pulsecheck env (add your tokens), then pulsecheck validate && pulsecheck test-notify")


@app.command(
    "env",
    "Open the .env file (secrets for ${VARS}) in your editor",
    args=[Arg("--path", action="store_true", help="only print the file path")],
)
def env_cmd(a):
    return env_command(setup.find_config(a.config), a.path)


@app.command(
    "validate",
    "Check the config file (syntax, keys, alert urls)",
    args=[Arg("--no-verify", action="store_true", help="do not ask shoutrrr to verify alert urls")],
)
def validate_cmd(a):
    path, cfg = load(a)
    return validate(cfg, path, a.no_verify)


@app.command("test-notify", "Send a test message to every alert channel in the config")
def test_notify_cmd(a):
    return test_notify(load(a)[1])


@app.command(
    "run",
    "Check all due sites once",
    args=[
        Arg("--fail-on-down", action="store_true", help="exit 1 when a site is down"),
        Arg("--force", action="store_true", help="ignore per-site intervals"),
        TAG,
    ],
)
def run_cmd(a):
    return run(load(a)[1], a.fail_on_down, a.force, a.tag)


@app.command(
    "status",
    "Current state of every site",
    args=[
        Arg("--json", dest="fmt", action="store_const", const="json", help="JSON output"),
        Arg("--md", dest="fmt", action="store_const", const="md", help="markdown table, e.g. for $GITHUB_STEP_SUMMARY"),
        TAG,
    ],
)
def status_cmd(a):
    status(load(a)[1], a.fmt or "text", a.tag)


@app.command("report", "Uptime and response times", args=[Arg("--json", action="store_true", help="JSON output"), TAG])
def report_cmd(a):
    report(load(a)[1], a.json, a.tag)


def main(argv=None) -> None:
    app.main(argv)
