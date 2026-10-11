#!/usr/bin/env bash
# Copy the package and your config into the Worker, then deploy. Needs uv >= 0.12.3, node, and `wrangler login`.
# Usage: deploy/cloudflare/deploy.sh [path/to/pulsecheck.yml]   (extra args after -- go to pywrangler)
set -euo pipefail
cd "$(dirname "$0")"
CONFIG=${1:-../../pulsecheck.yml}
[ -f "$CONFIG" ] || { echo "config not found: $CONFIG (copy pulsecheck.example.yml first)" >&2; exit 1; }
rm -rf src/pulsecheck && cp -r ../../src/pulsecheck src/pulsecheck
find src/pulsecheck -name __pycache__ -prune -exec rm -rf {} +
cp "$CONFIG" src/pulsecheck.yml
uv run pywrangler deploy
