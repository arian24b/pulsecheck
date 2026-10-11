#!/usr/bin/env bash
# Publish docs/en and docs/fa to the GitHub wiki (English pages keep their names, Persian ones get an FA- prefix).
# Needs the wiki to exist (create its first page once in the web UI). Usage: deploy/sync-wiki.sh [repo-url]
set -euo pipefail
cd "$(dirname "$0")/.."
WIKI=${1:-$(git remote get-url origin | sed 's/\.git$//').wiki.git}
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
git clone -q "$WIKI" "$TMP"
find "$TMP" -maxdepth 1 -name '*.md' -delete
for f in docs/en/*.md; do
  sed -E 's#\]\(\.\./fa/([A-Za-z-]+)\.md\)#](FA-\1)#g; s#\]\(([A-Za-z-]+)\.md\)#](\1)#g' "$f" > "$TMP/$(basename "$f")"
done
for f in docs/fa/*.md; do
  sed -E 's#\]\(\.\./en/([A-Za-z-]+)\.md\)#](\1)#g; s#\]\(([A-Za-z-]+)\.md\)#](FA-\1)#g' "$f" > "$TMP/FA-$(basename "$f")"
done
cd "$TMP"
git add -A
git diff --cached --quiet && { echo "wiki already up to date"; exit 0; }
git commit -qm "Sync docs"
git push -q
echo "wiki updated"
