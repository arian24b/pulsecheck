#!/usr/bin/env bash
# Install pulsecheck on Linux. The PyPI package is called `pulsecheckcli`; the command it installs is `pulsecheck`.
#   curl -fsSL https://raw.githubusercontent.com/arian24b/pulsecheck/main/install.sh | bash
#   curl -fsSL .../install.sh | bash -s -- --no-cron        # extra arguments go to `pulsecheck init`
# Env: PULSECHECK_SOURCE  what to install (default: pulsecheckcli; for example "git+https://github.com/arian24b/pulsecheck@main")
set -euo pipefail

SOURCE=${PULSECHECK_SOURCE:-pulsecheckcli}
FALLBACK=git+https://github.com/arian24b/pulsecheck

say() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

[ "$(uname -s)" = Linux ] || die "Linux only"
command -v curl >/dev/null || die "curl is required"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if ! command -v uv >/dev/null; then
  say "installing uv (it also provides the right Python)"
  curl -fsSL https://astral.sh/uv/install.sh | sh
fi

say "installing $SOURCE"
if ! uv tool install --upgrade "$SOURCE"; then
  # the package may not be on PyPI yet: fall back to the GitHub repository
  [ "$SOURCE" = pulsecheckcli ] || die "could not install $SOURCE"
  say "not found on PyPI, installing from GitHub instead"
  uv tool install --upgrade "$FALLBACK"
fi

command -v pulsecheck >/dev/null || die "pulsecheck is not on PATH; add \$HOME/.local/bin to PATH and open a new shell"
pulsecheck --version

# init asks before it adds the cron job and downloads shoutrrr; read the answers from the terminal even when piped
if (: </dev/tty) 2>/dev/null; then
  pulsecheck init "$@" </dev/tty
else
  say "no terminal: running init without questions (use --no-cron to skip the cron job)"
  pulsecheck init --yes "$@"
fi
