# Getting started

**Language:** English · [فارسی](../fa/Getting-Started.md)

## One-line install (Linux)
```bash
curl -fsSL https://raw.githubusercontent.com/arian24b/pulsecheck/main/install.sh | bash
```
It installs uv if missing, puts the code in `~/.local/share/pulsecheck`, adds a `pulsecheck` command to `~/.local/bin`, prepares shoutrrr (docker image if Docker works, otherwise the binary) and creates `~/.config/pulsecheck/pulsecheck.yml`. Run it again to update. Then use `pulsecheck -c ~/.config/pulsecheck/pulsecheck.yml validate`. Settings for the script (`PULSECHECK_HOME`, `PULSECHECK_BIN`, `PULSECHECK_CONFIG`, `PULSECHECK_REF`, `SHOUTRRR_VERSION`, `PULSECHECK_SHOUTRRR=binary`) are listed at the top of `install.sh`.

## Manual install
### Requirements
- [uv](https://docs.astral.sh/uv/) (it installs the right Python for you; Python 3.12–3.15 is supported, 3.15 preferred)
- Docker, **or** the `shoutrrr` binary on `PATH` (see [Notifications](Notifications.md))
- `ping` only if you use `type: ping` (Linux `iputils-ping`)

### Get the code
```bash
git clone https://github.com/arian24b/pulsecheck && cd pulsecheck
# or click "Use this template" on GitHub to get your own copy
uv sync
cp pulsecheck.example.yml pulsecheck.yml
```

## Check the config and the alerts
```bash
export TG_TOKEN=... TG_CHAT=@mychannel API_TOKEN=...   # whatever ${VARS} your file uses
uv run pulsecheck validate        # parses the file, fails on mistakes
uv run pulsecheck test-notify     # sends a test message to the global notify urls
```

## Run
```bash
uv run pulsecheck run             # check every site that is due
uv run pulsecheck run --force     # ignore per-site intervals
uv run pulsecheck run --fail-on-down   # exit code 1 if any site is down (shows red in CI)
uv run pulsecheck report          # uptime % and response times
uv run pulsecheck report --json
uv run pulsecheck -c other.yml run     # use another config file (put -c before the command)
```
Output is one line per site, for example `web: up 131ms`.

Next: [schedule it](Scheduling.md).
