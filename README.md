# pulsecheck

**English** · [فارسی](https://github.com/arian24b/pulsecheck/blob/main/README.fa.md)

Self-hosted uptime monitor. It checks HTTP(S) endpoints, TCP ports and hosts (ping) on a schedule, tracks up / down / slow state, and sends alerts through [shoutrrr](https://github.com/nicholas-fedor/shoutrrr) (Slack, Telegram, Discord, email, ntfy and 20+ more). One YAML file, one state file, no dashboard, no git history.

## Features
- HTTP checks: method, headers, body, expected status, redirect limit, max response time, "slow" (degraded) threshold
- TLS certificate expiry warnings (`ssl_warn_days`) and expired-certificate failures
- TCP and ping checks
- Alerts only on change, `down_after` to ignore blips, optional repeat reminders (`remind_every`)
- Per-site tags, intervals and alert routing; UTC maintenance windows
- Editable alert texts by key (`messages:`)
- `status` (text, JSON, markdown) and `report` (uptime %, response times) without a dashboard
- OpenTelemetry push (OTLP/HTTP JSON metrics and logs) to any collector or webhook
- Guided setup: `init` (config, `.env`, shoutrrr, cron), `env`, `validate`, `test-notify` to every channel, `update`
- `${ENV}` substitution, so secrets stay out of the config
- Runs from GitHub Actions, GitLab CI, cron, or serverless on Vercel and Cloudflare Workers (see the [limits](https://github.com/arian24b/pulsecheck/wiki/Serverless))
- Python 3.12–3.15 (3.15 preferred), managed with [uv](https://docs.astral.sh/uv/)

## Install
```bash
uv tool install pulsecheckcli     # or: pipx install pulsecheckcli
pulsecheck init                   # config + .env + shoutrrr + cron job (Linux)
pulsecheck env                    # add your tokens
pulsecheck validate && pulsecheck test-notify
```
The package is `pulsecheckcli`; the command is `pulsecheck`, and `pck` is a short alias for it. All commands: [Commands](https://github.com/arian24b/pulsecheck/wiki/Commands).

### Or: one line from GitHub (Linux)
```bash
curl -fsSL https://raw.githubusercontent.com/arian24b/pulsecheck/main/install.sh | bash
```
It installs the PyPI package `pulsecheckcli` with `uv tool` and runs `pulsecheck init`. Then run `pulsecheck env`, `pulsecheck validate` and `pulsecheck test-notify`.

## Quick start (from a clone)
```bash
uv sync
cp pulsecheck.example.yml pulsecheck.yml     # edit it
uv run pulsecheck validate
uv run pulsecheck test-notify
uv run pulsecheck run [--force] [--fail-on-down] [--tag prod]
uv run pulsecheck status [--json|--md]
uv run pulsecheck report [--json]
```
shoutrrr runs from its docker image when Docker works, otherwise from the `shoutrrr` binary on `PATH`. `ping` is needed for `type: ping`.

Want it running on GitHub Actions with the fewest files? Click **Use this template** on [pulsecheck-template](https://github.com/arian24b/pulsecheck-template): you get just `pulsecheck.yml`, one workflow and a short README. **Keep your copy private**: `pulsecheck.yml` lists your hostnames.

## Documentation (wiki)
| | English | فارسی |
|---|---|---|
| Overview | [Home](https://github.com/arian24b/pulsecheck/wiki/Home) | [خانه](https://github.com/arian24b/pulsecheck/wiki/FA-Home) |
| Every command | [Commands](https://github.com/arian24b/pulsecheck/wiki/Commands) | [دستورها](https://github.com/arian24b/pulsecheck/wiki/FA-Commands) |
| Install and first run | [Getting started](https://github.com/arian24b/pulsecheck/wiki/Getting-Started) | [شروع سریع](https://github.com/arian24b/pulsecheck/wiki/FA-Getting-Started) |
| Every YAML key (types, defaults) | [YAML reference](https://github.com/arian24b/pulsecheck/wiki/YAML-Reference) | [مرجع YAML](https://github.com/arian24b/pulsecheck/wiki/FA-YAML-Reference) |
| Every setting, explained | [Configuration](https://github.com/arian24b/pulsecheck/wiki/Configuration) | [تنظیمات](https://github.com/arian24b/pulsecheck/wiki/FA-Configuration) |
| Alert services | [Notifications](https://github.com/arian24b/pulsecheck/wiki/Notifications) | [اعلان‌ها](https://github.com/arian24b/pulsecheck/wiki/FA-Notifications) |
| GitHub / GitLab / cron | [Scheduling](https://github.com/arian24b/pulsecheck/wiki/Scheduling) | [زمان‌بندی](https://github.com/arian24b/pulsecheck/wiki/FA-Scheduling) |
| Vercel / Cloudflare | [Serverless](https://github.com/arian24b/pulsecheck/wiki/Serverless) | [سرورلس](https://github.com/arian24b/pulsecheck/wiki/FA-Serverless) |
| How it works, what is tested | [Design notes](https://github.com/arian24b/pulsecheck/wiki/Design-Notes) | [یادداشت‌های طراحی](https://github.com/arian24b/pulsecheck/wiki/FA-Design-Notes) |
| Problems | [Troubleshooting](https://github.com/arian24b/pulsecheck/wiki/Troubleshooting) | [عیب‌یابی](https://github.com/arian24b/pulsecheck/wiki/FA-Troubleshooting) |

Questions: [Discussions](https://github.com/arian24b/pulsecheck/discussions). Contributing: [CONTRIBUTING](https://github.com/arian24b/pulsecheck/blob/main/.github/CONTRIBUTING.md). Security: [SECURITY](https://github.com/arian24b/pulsecheck/blob/main/.github/SECURITY.md).

## Development
```bash
uv run pytest -q && uv run ruff check . && uv run ruff format --check .
```
Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, ...): the version, `CHANGELOG.md`, the GitHub release and the PyPI upload are generated from them by python-semantic-release.

## License
MIT
