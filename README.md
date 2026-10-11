# pulsecheck

**English** · [فارسی](README.fa.md)

Self-hosted uptime monitor. It checks HTTP(S) endpoints, TCP ports and hosts (ping) on a schedule, tracks up / down / slow state, and sends alerts through [shoutrrr](https://github.com/nicholas-fedor/shoutrrr) (Slack, Telegram, Discord, email, ntfy and more). One YAML file, one SQLite state file, no dashboard, no git history.

## Features
- HTTP checks with method, headers, body, expected status codes, redirect limit, max response time and a "slow" (degraded) threshold
- TCP and ping checks
- `${ENV}` substitution, so secrets stay out of the config
- Alerts only on change, with `down_after` to ignore short blips
- Editable alert texts by key (`messages:` in the YAML, global or per site)
- Per-site check intervals, per-site alert routing, UTC maintenance windows
- Uptime % and response-time report (`report`, `--json`)
- Runs from GitHub Actions, GitLab CI or cron
- Python 3.12–3.15 (3.15 preferred), managed with [uv](https://docs.astral.sh/uv/)

## Install on Linux (one line)
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
uv run pulsecheck run [--force] [--fail-on-down]
uv run pulsecheck report [--json]
```
shoutrrr runs from its docker image when Docker works, otherwise from the `shoutrrr` binary on `PATH` (`shoutrrr_bin` in the config overrides this). `ping` is needed for `type: ping`.

Use **Use this template** on GitHub to get your own copy with the GitHub Actions workflow ready, or keep `.gitlab-ci.yml` for GitLab and `deploy/cron.example` for cron.

## Documentation
| | English | فارسی |
|---|---|---|
| Overview | [Home](docs/en/Home.md) | [خانه](docs/fa/Home.md) |
| Install and first run | [Getting started](docs/en/Getting-Started.md) | [شروع سریع](docs/fa/Getting-Started.md) |
| Every setting | [Configuration](docs/en/Configuration.md) | [تنظیمات](docs/fa/Configuration.md) |
| Alert services | [Notifications](docs/en/Notifications.md) | [اعلان‌ها](docs/fa/Notifications.md) |
| GitHub / GitLab / cron | [Scheduling](docs/en/Scheduling.md) | [زمان‌بندی](docs/fa/Scheduling.md) |
| Problems | [Troubleshooting](docs/en/Troubleshooting.md) | [عیب‌یابی](docs/fa/Troubleshooting.md) |

Also published as the [GitHub wiki](https://github.com/arian24b/pulsecheck/wiki) (English and Persian; `deploy/sync-wiki.sh` refreshes it from `docs/`).

## Development
```bash
uv run pytest
```

## License
MIT
