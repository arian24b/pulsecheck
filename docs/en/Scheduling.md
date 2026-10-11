# Scheduling

**Language:** English · [فارسی](../fa/Scheduling.md)

pulsecheck runs once and exits. Something else starts it every few minutes. Pick one.

## GitHub Actions
1. Click **Use this template** on the repository (prefer a **private** copy, because your `pulsecheck.yml` lists your hosts).
2. Copy `pulsecheck.example.yml` to `pulsecheck.yml`, edit it and commit it. Keep tokens as `${VARS}`.
3. Add each variable as a secret (Settings → Secrets and variables → Actions) and list it in the `env:` of the **Run checks** step in `.github/workflows/monitor.yml`. The template already lists `TG_TOKEN`, `TG_CHAT` and `API_TOKEN`.
4. Run it once with **Actions → monitor → Run workflow**.

Notes
- The workflow does not run inside the template repository itself (`github.repository != 'arian24b/pulsecheck'`). If you rename your copy this still works.
- shoutrrr runs from its docker image (Docker is preinstalled on GitHub's Ubuntu runners), so there is nothing to install.
- State is stored with `actions/cache` (restored from the newest entry, saved after each run). No commits are made.
- GitHub may delay scheduled runs by several minutes and disables schedules in repositories with no activity for 60 days.

## GitLab CI
1. Push the repository to GitLab and commit your `pulsecheck.yml`.
2. **Build → Pipeline schedules → New schedule**, cron `*/5 * * * *`.
3. The job image has no Docker, so `shoutrrr_bin: auto` uses the binary the job downloads (`SHOUTRRR_VERSION` in `.gitlab-ci.yml`).
4. **Settings → CI/CD → Variables**: add every `${VAR}` your file uses (mask the secrets).
5. The job only runs for scheduled pipelines and caches `pulsecheck.db` under one key. If your runners do not share a cache, state is lost between runs (see [Troubleshooting](Troubleshooting.md)).

## Vercel and Cloudflare Workers
Both have their own cron and their own limits (Vercel Hobby: one run per day; Cloudflare Free: 10 ms CPU per run). Setup and every limit are on the [Serverless](Serverless.md) page.

## Linux cron
```bash
# crontab -e
*/5 * * * * cd /opt/pulsecheck && TG_TOKEN=xxx TG_CHAT=@mychannel API_TOKEN=xxx flock -n /tmp/pulsecheck.lock uv run pulsecheck -c pulsecheck.yml run >> /var/log/pulsecheck.log 2>&1
```
State lives in `state_file` on disk. `flock -n` prevents overlapping runs. For secrets, use an env file loaded by a small wrapper script instead of writing them in the crontab.
