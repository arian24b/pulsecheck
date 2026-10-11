#!/usr/bin/env bash
# Build the Worker and deploy it with the `cf` CLI (https://developers.cloudflare.com/cf/).
# Needs: cf (npm install --global cf), `cf auth login`, uv. Export every ${VAR} your YAML uses (and optionally STATUS_TOKEN) first.
# Usage: deploy/cloudflare/deploy.sh [pulsecheck.yml] [--cron "*/5 * * * *"] [--name pulsecheck]
set -euo pipefail
cd "$(dirname "$0")"
CONFIG=${1:-../../pulsecheck.yml}
[ $# -gt 0 ] && shift
uv run --project ../.. python build.py "$CONFIG" "$@"
cf deploy --prebuilt --secrets-file .cloudflare/secrets.env
