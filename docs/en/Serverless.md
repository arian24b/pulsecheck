# Serverless: Vercel and Cloudflare Workers

**Language:** English · [فارسی](../fa/Serverless.md)

Besides GitHub Actions, GitLab CI and cron, pulsecheck can run on **Vercel** (cron job + Python function) and **Cloudflare Workers** (cron trigger + Python Worker). Both platforms are sandboxes, so some features are missing there. Read the limits first.

> Status: the shared engine, the state store, the HTTP notifier and the Vercel handler are tested locally (Vercel with a fake Redis). The Cloudflare Worker is tested only against stand-ins for its runtime, and **neither platform has been deployed with real accounts by the author**. Report problems you hit.

## What works where
| Feature | CLI / CI / cron | Vercel | Cloudflare Worker |
|---|---|---|---|
| HTTP checks | yes | yes | yes (see notes) |
| TCP checks | yes | yes | **no** (skipped) |
| Ping checks | yes | **no** (skipped) | **no** (skipped) |
| Alerts | all shoutrrr services | telegram, discord, ntfy, generic | telegram, discord, ntfy, generic |
| State | SQLite file | Upstash Redis (REST) | Workers KV |
| Report with p95 | yes | no (uptime %, average only; last 90 days) | no (same) |
| `messages:`, maintenance, `down_after`, `interval` | yes | yes | yes |

Skipped sites are listed in the run log. `max_redirects` is ignored on Cloudflare (fetch follows redirects with its own limit).

## Limits found in the platform documentation
### Vercel
| Limit | Value | What we do |
|---|---|---|
| Cron frequency | Hobby: once per day, run time anywhere in the hour; Pro/Enterprise: per minute | `vercel.json` ships a **daily** schedule so any plan can deploy. On Pro set `*/5 * * * *`. On Hobby use the optional `trigger-vercel.yml` GitHub workflow (below). |
| Cron delivery | Best effort: a run can be missed or doubled; no retry; redirects are not followed | Runs are idempotent (state change based). Expect rare gaps. |
| Cron jobs per project | 100 | – |
| Python versions | 3.12 (default), 3.13, 3.14. **Not 3.15** | The repo prefers 3.15 locally; if the Vercel build rejects `.python-version`, set it to `3.14` in your copy. |
| Duration | 300 s default (Hobby max 300 s, Pro max 800 s) | Plenty for checks; each check has its own `timeout`. |
| Memory / bundle | 2 GB (Hobby) / 4 GB (Pro); 500 MB Python bundle | `excludeFiles` keeps docs and tests out. |
| File descriptors | 1,024 shared by all concurrent executions | Checks run 20 at a time. |
| Local disk | Not a place for state | State goes to Upstash Redis. |
| Docker / extra binaries | Not available to Python functions | shoutrrr is replaced by the built-in HTTP notifier. |
| Egress IPs | Dynamic by default | You cannot allow-list the monitor's IP without Vercel's paid static IP options. |
| `vercel dev` | Does not run cron jobs | Test by calling the endpoint yourself. |

Upstash free plan: 500K commands per month, 256 MB. One run uses 2 commands (about 17,000 per month at a 5-minute schedule).

### Cloudflare Workers (Python)
| Limit | Value | What we do |
|---|---|---|
| Runtime | Pyodide (Python in WebAssembly): Python 3.13, pydantic 2.10, ruamel.yaml 0.18 | `deploy/cloudflare/pyproject.toml` keeps dependencies loose. |
| Threads / subprocess / sqlite file | Not available | asyncio only; state in KV; no ping, no shoutrrr. |
| TCP | `connect()` API exists but blocks Cloudflare IPs, localhost, private IPs and port 25; Python access not verified | TCP sites are skipped. |
| CPU per cron run | **Free: 10 ms**; Paid: 30 s (interval under 1 h) | Python plus pydantic start-up probably does not fit 10 ms: plan on the **Paid plan ($5/month)**. |
| Wall clock per cron run | 15 min | – |
| Subrequests per run | Free 50, Paid 10,000 | Each site, alert and KV call counts. On Free keep under ~40 sites. |
| Simultaneous outgoing connections | 6 | Checks run 6 at a time. |
| Memory | 128 MB | – |
| Cron triggers | Free 5 per account, Paid 250; UTC; changes take up to 15 min to apply | – |
| KV (state) | Free: 1,000 writes/day, 100,000 reads/day; 1 write per second per key | One write per run: a 5-minute cron uses 288 writes/day. **A 1-minute cron needs the Paid plan.** |
| Tooling | `pywrangler` needs uv 0.12.3 or newer and downloads packages from `index.pyodide.org` | `uv self update` first. |

## Vercel setup
1. Fork or use this template, copy `pulsecheck.example.yml` to `pulsecheck.yml`, edit it (use `telegram://`, `discord://`, `ntfy://` or `generic://` alert URLs and `${VAR}` for secrets) and commit it. Keep the repo private if hostnames are sensitive.
2. Create the project: `vercel` (or import the repository in the dashboard). Vercel detects `app.py`.
3. Add storage: `vercel install upstash` (Upstash for Redis). It injects `KV_REST_API_URL` / `KV_REST_API_TOKEN` (or `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN`); both pairs are understood.
4. Add environment variables: `CRON_SECRET` (random, 16+ characters; Vercel sends it as `Authorization: Bearer …` and the endpoint refuses everything else) plus every `${VAR}` used in your YAML.
5. Schedule: edit `vercel.json`. Pro: `"schedule": "*/5 * * * *"`. Hobby: keep daily and add the GitHub trigger: in your GitHub repo set the variable `VERCEL_CRON_URL` (`https://<project>.vercel.app/api/cron`) and the secret `CRON_SECRET`; `.github/workflows/trigger-vercel.yml` then calls it every 5 minutes.
6. Deploy: `vercel --prod`. Check with `curl -H "Authorization: Bearer $CRON_SECRET" https://<project>.vercel.app/api/cron`. The answer lists every site and its status.

## Cloudflare setup
1. Copy `pulsecheck.example.yml` to `pulsecheck.yml` and edit it (HTTP sites only; same alert URL types as above).
2. Create the KV namespace and put its id into `deploy/cloudflare/wrangler.jsonc`: `npx wrangler kv namespace create STATE`.
3. `npx wrangler login`, then `cd deploy/cloudflare` and add secrets used by your YAML: `npx wrangler secret put TG_TOKEN` (one per `${VAR}`).
4. Optionally change `triggers.crons` in `wrangler.jsonc`.
5. Deploy: `deploy/cloudflare/deploy.sh` (copies the package and your YAML into the Worker, then runs `pywrangler deploy`).
6. Watch logs with `npx wrangler tail`.

## YAML tip
Inside inline `{ ... }` mappings, quote any value containing `${VAR}`: `{name: api, url: "https://x.example.com/${TOKEN}"}`.
