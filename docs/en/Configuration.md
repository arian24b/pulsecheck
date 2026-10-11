# Configuration

**Language:** English · [فارسی](../fa/Configuration.md)

Default file name: `pulsecheck.yml` (change with `-c`). Any `${NAME}` inside a value is replaced with the environment variable `NAME`. A missing variable is an error, so keep secrets out of the file.

> Inside inline `{ ... }` mappings, quote values that contain `${VAR}`: `{name: api, url: "https://x.example.com/${TOKEN}"}`.

```yaml
state_file: pulsecheck.db
shoutrrr_bin: shoutrrr
notify:
  urls: ["telegram://${TG_TOKEN}@telegram?chats=${TG_CHAT}"]
  events: [down, up, degraded]
defaults: {timeout: 10, down_after: 2, interval: 5, slow_ms: 3000}
maintenance:
  - {name: weekly, start: "SUN 02:00", duration: 60, sites: [api]}
sites:
  - {name: web, url: https://example.com}
```

## Top level
| Key | Default | Meaning |
|---|---|---|
| `state_file` | `pulsecheck.db` | SQLite file holding current state and check history (kept 400 days) |
| `shoutrrr_bin` | `auto` | `auto` (docker image if Docker works, else the `shoutrrr` binary), `docker`, or a path to a binary |
| `shoutrrr_image` | `nickfedor/shoutrrr:0.21.2` | Docker image used in `auto`/`docker` mode |
| `notify` | none | Global alert targets, see below |
| `defaults` | `{}` | Any site key; merged into every site (a site's own value wins) |
| `messages` | built-in | Alert texts by key, see [Messages](#messages) |
| `maintenance` | `[]` | Windows where alerts are suppressed |
| `sites` | required | List of checks; `name` must be unique |

## Site keys
| Key | Default | Applies to | Meaning |
|---|---|---|---|
| `name` | required | all | Unique name, used in alerts and reports |
| `type` | `http` | all | `http`, `tcp` or `ping` |
| `url` | – | http | Full URL (required) |
| `host` | – | tcp, ping | Host name or IP (required) |
| `port` | – | tcp | Port (required) |
| `method` | `GET` | http | HTTP method |
| `headers` | `{}` | http | Request headers |
| `body` | – | http | Request body (string) |
| `expected_status` | any 2xx | http | List such as `[200, 301]` |
| `max_redirects` | `5` | http | Redirects are followed up to this number |
| `max_response_ms` | off | all | Slower than this counts as a **failure** |
| `slow_ms` | off | all | Slower than this (but successful) is **degraded** |
| `timeout` | `10` | all | Seconds |
| `down_after` | `2` | all | Consecutive failures before the site is marked down |
| `interval` | `5` | all | Minutes between checks (see below) |
| `notify` | global | all | Overrides the global `notify` for this site |
| `messages` | global | all | Overrides message texts for this site only |

## Status and alerts
- A successful check is `up`, or `degraded` if it took at least `slow_ms`.
- A failed check only marks the site `down` after `down_after` failures in a row. Shorter blips never alert.
- Alerts are sent **only when the status changes**: `down`, `degraded`, or `up` (recovery; the message includes how many minutes the site was affected).
- `events` filters which of `down`, `up`, `degraded` are sent. A site-level `notify` replaces the global one completely, including `events`.
- Alert failures (missing binary, bad URL) are printed to stderr and never stop the run.

## Intervals
Your scheduler decides how often pulsecheck runs; `interval` only skips sites whose last check is too recent. Example: run every 5 minutes, give a heavy check `interval: 60` and it runs hourly. A one-minute margin absorbs scheduler jitter, so `interval: 5` with a 5-minute schedule checks every run.

## Maintenance windows
Times are **UTC**. `start` is `"HH:MM"` (every day) or `"DAY HH:MM"` with `MON TUE WED THU FRI SAT SUN`. `duration` is in minutes and may cross midnight. Empty `sites` means all sites. Checks still run and are recorded, but alerts raised during the window are dropped, not delivered later.

## Messages
Every alert text has a key. The code uses only these keys, and you can change any of them under `messages:` (globally, or inside a single site). Keys you don't set keep the built-in text.

| Key | Sent when | Built-in text |
|---|---|---|
| `down` | site went down | `🔴 {site} is DOWN: {error}` |
| `degraded` | site is up but slow | `🟡 {site} is slow ({ms}ms)` |
| `up` | site recovered | `🟢 {site} is UP ({ms}ms) after {minutes}m` |
| `test` | `pulsecheck test-notify` | `pulsecheck test notification` |

Placeholders: `{site}` name, `{event}` (`down`/`degraded`/`up`), `{error}` failure reason (empty on success), `{ms}` response time, `{minutes}` minutes since the last status change, `{status}` HTTP status code (empty for tcp/ping). Use `{{` and `}}` for literal braces. Unknown keys or placeholders are rejected by `validate`. Order of precedence: site `messages` > global `messages` > built-in.

```yaml
messages:
  down: "ALERT {site} unreachable ({error})"
  up: "{site} recovered after {minutes} min"
sites:
  - name: payments
    url: https://pay.example.com
    messages: {down: "💳 payments DOWN, page on-call"}
```

## Reports
`pulsecheck report` shows, for day / week / month / year: uptime %, average and p95 response time of successful checks, and the number of checks. `--json` prints the same data for scripts. On Vercel/Cloudflare the state store keeps daily totals only, so `report` there has no p95 and covers the last 90 days.
