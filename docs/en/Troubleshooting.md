# Troubleshooting

**Language:** English · [فارسی](../fa/Troubleshooting.md)

| Problem | Cause and fix |
|---|---|
| `config error: env var X is not set` | The file uses `${X}` but it is not exported. Set it, or add the secret to the CI job's `env:`. |
| No alert when a site is down | It must fail `down_after` times in a row (default 2). Check `events`, an active maintenance window (UTC), and stderr for `notify failed`. |
| `notify failed: ... No such file or directory: 'shoutrrr'` | No usable Docker and no binary on `PATH`. Start Docker, install the binary (`install.sh` does it) or set `shoutrrr_bin`. |
| Docker is installed but the binary is used | `docker info` fails for your user (daemon stopped, no permission). Fix that or set `shoutrrr_bin: docker`. |
| `notify failed:` plus a shoutrrr error | Wrong URL or token. Run `shoutrrr verify --url ...` and `pulsecheck test-notify`. |
| Same DOWN alert again and again | State was lost between runs (cache evicted, runners without shared cache, container without a volume). Keep `state_file` on persistent storage. |
| Site flaps between up and degraded | `slow_ms` is close to the normal response time. Raise it. |
| Ping always fails in Docker/CI | Install `iputils-ping`; some containers also forbid raw sockets. Use `type: tcp` instead. |
| HTTPS certificate error | The check fails with the error shown in the alert. Fix the certificate; there is no option to skip verification. |
| Scheduled GitHub run stopped | Schedules pause after 60 days without repository activity. Re-enable in the Actions tab. |
| Vercel endpoint answers `401` | `CRON_SECRET` is unset or the `Authorization: Bearer …` header does not match it. |
| Vercel answers `500 … state store missing` | Add Upstash Redis (`vercel install upstash`) or set `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`. |
| Vercel deploy fails on the cron expression | Hobby accepts one run per day only. Use `0 0 * * *`, or call the endpoint from GitHub (see [Serverless](Serverless.md)). |
| `notify failed: 'xyz://' is not supported here` | Vercel/Cloudflare only send telegram, discord, ntfy and generic URLs. Use another mode for other services. |
| `skipped, type 'tcp' is not supported on this platform` | Cloudflare runs HTTP checks only; Vercel also skips `ping`. |
| Cloudflare run stops with "exceeded CPU time" | The Free plan gives 10 ms CPU per cron run. Use the Paid plan. |
| Cloudflare KV write errors after some hours | Free KV allows 1,000 writes per day; a 1-minute cron needs 1,440. Use 2+ minutes or the Paid plan. |

Debug tip: `uv run pulsecheck run --force` prints one line per site with status, time and error.
