"""Everything the command line needs around the checks: where files live, .env, init, cron, editing, updating."""

import importlib.metadata
import importlib.resources
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

BEGIN = "# >>> pulsecheck (managed by `pulsecheck init`) >>>"
END = "# <<< pulsecheck <<<"
DEFAULT_CRON = "*/5 * * * *"


def config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "pulsecheck"


def state_dir() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "pulsecheck"


def find_config(arg: str | None) -> Path:
    """-c wins, then ./pulsecheck.yml, then ~/.config/pulsecheck/pulsecheck.yml."""
    if arg:
        return Path(arg).expanduser()
    for p in (Path("pulsecheck.yml"), config_dir() / "pulsecheck.yml"):
        if p.exists():
            return p
    raise SystemExit("no config found. Run `pulsecheck init` to create ~/.config/pulsecheck/pulsecheck.yml, or pass -c FILE")


def parse_dotenv(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key.strip()] = value
    return out


def load_dotenv(config_path: Path) -> list[str]:
    """Load <config dir>/.env into os.environ. Variables that are already set win. Returns the names it added."""
    f = config_path.resolve().parent / ".env"
    if not f.is_file():
        return []
    added = []
    for k, v in parse_dotenv(f.read_text()).items():
        if v and k not in os.environ:  # an empty `KEY=` placeholder counts as not set
            os.environ[k] = v
            added.append(k)
    return added


def mask(url: str) -> str:
    """Show the service only: alert urls contain tokens."""
    return f"{urlparse(url).scheme or '?'}://***"


def example_text() -> str:
    return importlib.resources.files("pulsecheck").joinpath("example.yml").read_text()


def installed_version() -> str:
    try:
        return importlib.metadata.version("pulsecheck")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


# ---------------------------------------------------------------- cron


def with_block(existing: str, line: str | None) -> str:
    """Return the crontab text with our managed block replaced (or removed when line is None)."""
    kept = re.sub(rf"{re.escape(BEGIN)}.*?{re.escape(END)}\n?", "", existing, flags=re.S).rstrip("\n")
    if line is None:
        return kept + "\n" if kept else ""
    return (kept + "\n" if kept else "") + f"{BEGIN}\n{line}\n{END}\n"


def cron_line(schedule: str, config_path: Path) -> str:
    log = state_dir() / "run.log"
    run = f"{shlex.quote(sys.executable)} -m pulsecheck -c {shlex.quote(str(config_path.resolve()))} run"
    lock = f"flock -n /tmp/pulsecheck-{os.getuid()}.lock " if shutil.which("flock") else ""
    return f'{schedule} PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin" {lock}{run} >> {shlex.quote(str(log))} 2>&1'


def edit_crontab(line: str | None) -> str:
    """Install (line) or remove (None) the managed cron block in the user's crontab."""
    if not shutil.which("crontab"):
        raise RuntimeError("`crontab` not found. Install cron (for example `sudo apt install cron`) or use a systemd timer")
    cur = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = cur.stdout if cur.returncode == 0 else ""  # rc 1 = "no crontab for user"
    new = with_block(existing, line)
    r = subprocess.run(["crontab", "-"], input=new, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"crontab failed: {r.stderr.strip()}")
    return new


# ---------------------------------------------------------------- init / env


def ask(question: str, yes: bool) -> bool:
    if yes or not sys.stdin.isatty():
        return True
    return input(f"{question} [Y/n] ").strip().lower() in ("", "y", "yes")


def env_stub(config_path: Path) -> str:
    from . import config

    names = sorted(config.env_names(config_path.read_text())) if config_path.exists() else []
    lines = [
        "# Secrets for pulsecheck, loaded automatically (variables already set in the environment win).",
        "# KEY=value, no spaces around =",
        "",
    ]
    return "\n".join(lines + [f"{n}=" for n in names]) + "\n"


def ensure_env_file(config_path: Path) -> Path:
    f = config_path.resolve().parent / ".env"
    if not f.exists():
        f.write_text(env_stub(config_path))
    f.chmod(0o600)
    return f


def open_in_editor(path: Path) -> int:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or next((e for e in ("nano", "vim", "vi") if shutil.which(e)), None)
    if not editor:
        print(f"no editor found. Edit this file yourself: {path}")
        return 1
    return subprocess.call([*shlex.split(editor), str(path)])


def init(*, yes=False, force=False, cron=True, download=True, schedule=DEFAULT_CRON, say=print) -> Path:
    if not sys.platform.startswith("linux"):
        say("note: cron setup and the shoutrrr download are for Linux; only the config files are created here")
        cron = download = False
    cdir, sdir = config_dir(), state_dir()
    cdir.mkdir(parents=True, exist_ok=True)
    sdir.mkdir(parents=True, exist_ok=True)
    cfg = cdir / "pulsecheck.yml"
    if cfg.exists() and not force:
        say(f"config exists, kept: {cfg}  (use --force to replace it)")
    else:
        text = re.sub(r"^state_file:.*$", f"state_file: {sdir / 'pulsecheck.db'}", example_text(), flags=re.M)
        cfg.write_text(text)
        say(f"created config: {cfg}")
    say(f"secrets file:  {ensure_env_file(cfg)}  (edit with `pulsecheck env`)")
    if download:
        from . import notify

        if shutil.which("shoutrrr") or (Path.home() / ".local/bin/shoutrrr").exists():
            say("shoutrrr: already installed")
        elif shutil.which("docker") and subprocess.run(["docker", "info"], capture_output=True).returncode == 0:
            if ask("Docker found. Pull the shoutrrr image now?", yes):
                subprocess.run(["docker", "pull", f"nickfedor/shoutrrr:{notify.SHOUTRRR_VERSION}"], check=False)
        elif ask("No Docker and no shoutrrr. Download the shoutrrr binary to ~/.local/bin?", yes):
            try:
                say(f"shoutrrr: downloaded {notify.download_shoutrrr(str(Path.home() / '.local/bin'))}")
            except Exception as e:
                say(f"shoutrrr download failed ({e}). Install it from https://github.com/nicholas-fedor/shoutrrr/releases")
    if cron and ask(f"Add a cron job ({schedule}) that runs `pulsecheck run`?", yes):
        try:
            edit_crontab(cron_line(schedule, cfg))
            say(f"cron: installed ({schedule}); log: {sdir / 'run.log'}")
        except RuntimeError as e:
            say(f"cron: {e}")
    say(
        "\nNext: pulsecheck env      (add your tokens)\n      edit the sites in the config, then: pulsecheck validate && pulsecheck test-notify"
    )
    return cfg


# ---------------------------------------------------------------- update


def upgrade_command() -> list[str]:
    """How this copy of pulsecheck was installed decides how to upgrade it."""
    prefix = Path(sys.prefix).as_posix()
    if "/uv/tools/" in prefix:
        return ["uv", "tool", "upgrade", "pulsecheck"]
    if "/pipx/venvs/" in prefix:
        return ["pipx", "upgrade", "pulsecheck"]
    repo = Path(__file__).resolve().parents[2]
    if (repo / ".git").exists():  # install.sh / git clone
        return ["sh", "-c", f"git -C {shlex.quote(str(repo))} pull --ff-only && uv sync --project {shlex.quote(str(repo))} --no-dev -q"]
    return [sys.executable, "-m", "pip", "install", "--upgrade", "pulsecheck"]


def latest_version(timeout: int = 15) -> str | None:
    import json
    import urllib.request

    try:
        return json.load(urllib.request.urlopen("https://pypi.org/pypi/pulsecheck/json", timeout=timeout))["info"]["version"]
    except Exception:
        return None
