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

Debug tip: `uv run pulsecheck run --force` prints one line per site with status, time and error.
