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
uv tool install pulsecheck        # or: pipx install pulsecheck   (once the first release is on PyPI)
pulsecheck init                   # config + .env + shoutrrr + cron job (Linux)
pulsecheck env                    # add your tokens
pulsecheck validate && pulsecheck test-notify
```
All commands: [Commands](https://github.com/arian24b/pulsecheck/wiki/Commands).

### Or: one line from GitHub (Linux)
```bash
curl -fsSL https://raw.githubusercontent.com/arian24b/pulsecheck/main/install.sh | bash
```
Then edit `~/.config/pulsecheck/pulsecheck.yml` and run `pulsecheck -c ~/.config/pulsecheck/pulsecheck.yml validate`.

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

Use **Use this template** to get your own copy with the GitHub Actions workflow ready. **Keep your copy private**: your `pulsecheck.yml` lists your hostnames.

## Documentation (wiki)
| | English | فارسی |
|---|---|---|
| Overview | [Home](https://github.com/arian24b/pulsecheck/wiki/Home) | [خانه](https://github.com/arian24b/pulsecheck/wiki/FA-Home) |
| Every command | [Commands](https://github.com/arian24b/pulsecheck/wiki/Commands) | [دستورها](https://github.com/arian24b/pulsecheck/wiki/FA-Commands) |
| Install and first run | [Getting started](https://github.com/arian24b/pulsecheck/wiki/Getting-Started) | [شروع سریع](https://github.com/arian24b/pulsecheck/wiki/FA-Getting-Started) |
| Every setting | [Configuration](https://github.com/arian24b/pulsecheck/wiki/Configuration) | [تنظیمات](https://github.com/arian24b/pulsecheck/wiki/FA-Configuration) |
| Alert services | [Notifications](https://github.com/arian24b/pulsecheck/wiki/Notifications) | [اعلان‌ها](https://github.com/arian24b/pulsecheck/wiki/FA-Notifications) |
| GitHub / GitLab / cron | [Scheduling](https://github.com/arian24b/pulsecheck/wiki/Scheduling) | [زمان‌بندی](https://github.com/arian24b/pulsecheck/wiki/FA-Scheduling) |
| Vercel / Cloudflare | [Serverless](https://github.com/arian24b/pulsecheck/wiki/Serverless) | [سرورلس](https://github.com/arian24b/pulsecheck/wiki/FA-Serverless) |
| Problems | [Troubleshooting](https://github.com/arian24b/pulsecheck/wiki/Troubleshooting) | [عیب‌یابی](https://github.com/arian24b/pulsecheck/wiki/FA-Troubleshooting) |

Questions: [Discussions](https://github.com/arian24b/pulsecheck/discussions). Contributing: [CONTRIBUTING](https://github.com/arian24b/pulsecheck/blob/main/.github/CONTRIBUTING.md). Security: [SECURITY](https://github.com/arian24b/pulsecheck/blob/main/.github/SECURITY.md).

## Development
```bash
uv run pytest -q && uv run ruff check . && uv run ruff format --check .
```

## License
MIT
