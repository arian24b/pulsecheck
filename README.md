# pulsecheck

Self-hosted uptime monitor: HTTP/TCP/ping checks, incident state, maintenance windows, uptime/latency reports, alerts via [shoutrrr](https://github.com/nicholas-fedor/shoutrrr). No dashboard, no git history; state is one SQLite file.

```
uv sync
cp pulsecheck.example.yml pulsecheck.yml   # commit it; secrets stay in ${ENV} / CI secrets
uv run pulsecheck validate
uv run pulsecheck test-notify
uv run pulsecheck run [--force] [--fail-on-down]
uv run pulsecheck report [--json]
```

Needs the `shoutrrr` binary on PATH (or set `shoutrrr_bin`) and `ping` for `type: ping`.

## Scheduling
- **GitHub Actions** (use "Use this template"): commit your `pulsecheck.yml` (the workflow does not run in the template repo itself), add secrets under Settings → Secrets. State persists via `actions/cache`. GitHub's shortest schedule is ~5 min and may be delayed.
- **GitLab CI**: keep `.gitlab-ci.yml`, add a pipeline schedule and CI/CD variables.
- **Linux cron**: see `deploy/cron.example`.

If state is lost (cache eviction), the only effect is a possible repeated alert and shorter report history.

Supports Python 3.12–3.15 (3.15 preferred, see `.python-version`).
