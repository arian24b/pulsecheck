# pulsecheck guide

pulsecheck checks your websites, TCP ports and hosts on a schedule and sends alerts through [shoutrrr](https://github.com/nicholas-fedor/shoutrrr) (Slack, Telegram, Discord, email, ntfy and many more). Everything is set in one YAML file. There is no web dashboard and nothing is committed to git; the state is one SQLite file.

**Language:** English · [فارسی](../fa/Home.md)

| Page | What it covers |
|---|---|
| [Getting started](Getting-Started.md) | Install, first config, first run |
| [Configuration](Configuration.md) | Every YAML key, defaults, how alerts are decided |
| [Notifications](Notifications.md) | shoutrrr install, URL examples, routing |
| [Scheduling](Scheduling.md) | GitHub Actions, GitLab CI, cron |
| [Serverless](Serverless.md) | Vercel and Cloudflare Workers: setup and platform limits |
| [Troubleshooting](Troubleshooting.md) | Common problems |

## How a run works
1. Load `pulsecheck.yml` and replace `${ENV_VAR}` from the environment.
2. Skip sites checked less than their `interval` ago.
3. Check the remaining sites in parallel (HTTP, TCP or ping).
4. Compare each result with the saved state. Only a **change** (up → down, down → up, up → degraded …) can raise an alert.
5. Send the alert with shoutrrr unless a maintenance window is active.
6. Save the result and the new state.
