#!/usr/bin/env bash
# Install pulsecheck on Linux:
#   curl -fsSL https://raw.githubusercontent.com/arian24b/pulsecheck/main/install.sh | bash
# Env overrides: PULSECHECK_HOME (code dir), PULSECHECK_BIN (wrapper dir), PULSECHECK_CONFIG (config dir),
#   PULSECHECK_REPO, PULSECHECK_REF, SHOUTRRR_VERSION, PULSECHECK_SHOUTRRR=binary (always download the binary)
set -euo pipefail

REPO=${PULSECHECK_REPO:-https://github.com/arian24b/pulsecheck}
REF=${PULSECHECK_REF:-main}
HOME_DIR=${PULSECHECK_HOME:-$HOME/.local/share/pulsecheck}
BIN_DIR=${PULSECHECK_BIN:-$HOME/.local/bin}
CONF_DIR=${PULSECHECK_CONFIG:-$HOME/.config/pulsecheck}
SH_VER=${SHOUTRRR_VERSION:-0.21.2}

say() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

[ "$(uname -s)" = Linux ] || die "Linux only"
command -v curl >/dev/null || die "curl is required"
export PATH="$BIN_DIR:$HOME/.local/bin:$PATH"
mkdir -p "$BIN_DIR" "$CONF_DIR"

# 1. uv (brings the right Python by itself)
if ! command -v uv >/dev/null; then
  say "installing uv"
  curl -fsSL https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

# 2. the code (update in place if already installed)
if [ -d "$HOME_DIR/.git" ]; then
  say "updating $HOME_DIR"
  git -C "$HOME_DIR" fetch -q origin "$REF" && git -C "$HOME_DIR" checkout -q FETCH_HEAD
elif command -v git >/dev/null; then
  say "cloning into $HOME_DIR"
  git clone -q "$REPO" "$HOME_DIR" && git -C "$HOME_DIR" checkout -q "$REF"
else
  say "git not found, downloading tarball"
  mkdir -p "$HOME_DIR"
  curl -fsSL "$REPO/archive/$REF.tar.gz" | tar xz --strip-components=1 -C "$HOME_DIR"
fi
say "installing dependencies"
uv sync --project "$HOME_DIR" --no-dev -q

# 3. command wrapper (runs in your current directory, so relative config paths work)
cat > "$BIN_DIR/pulsecheck" <<EOF
#!/usr/bin/env bash
exec uv run --project "$HOME_DIR" --no-dev pulsecheck "\$@"
EOF
chmod +x "$BIN_DIR/pulsecheck"

# 4. shoutrrr: docker image when docker works, else the binary
if [ "${PULSECHECK_SHOUTRRR:-auto}" != binary ] && command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  say "docker found: shoutrrr will run from the docker image (pulling it now)"
  docker pull -q "nickfedor/shoutrrr:$SH_VER" >/dev/null || say "pull failed, it will be pulled on first use"
elif command -v shoutrrr >/dev/null && [ "${PULSECHECK_SHOUTRRR:-auto}" != binary ]; then
  say "shoutrrr binary already installed"
else
  case "$(uname -m)" in
    x86_64) arch=amd64 ;; aarch64|arm64) arch=arm64v8 ;; armv7l|armv6l) arch=armhf ;;
    i386|i686) arch=i386 ;; riscv64) arch=riscv64 ;; *) die "no shoutrrr build for $(uname -m)" ;;
  esac
  say "no docker: downloading the shoutrrr $SH_VER binary ($arch)"
  curl -fsSL "https://github.com/nicholas-fedor/shoutrrr/releases/download/v$SH_VER/shoutrrr_linux_${arch}_$SH_VER.tar.gz" \
    | tar xz -C "$BIN_DIR" shoutrrr
fi

# 5. starter config (never overwrites yours)
if [ ! -e "$CONF_DIR/pulsecheck.yml" ]; then
  STATE_DIR=${PULSECHECK_STATE:-$HOME/.local/state/pulsecheck}
  mkdir -p "$STATE_DIR"
  sed "s|^state_file:.*|state_file: $STATE_DIR/pulsecheck.db|" "$HOME_DIR/pulsecheck.example.yml" > "$CONF_DIR/pulsecheck.yml"
  say "created $CONF_DIR/pulsecheck.yml (edit it)"
fi

cat <<EOF

Done. Next:
  1. edit $CONF_DIR/pulsecheck.yml  (add your sites and notify urls)
  2. pulsecheck -c $CONF_DIR/pulsecheck.yml validate
  3. pulsecheck -c $CONF_DIR/pulsecheck.yml test-notify
  4. cron, every 5 minutes:  crontab -e
     */5 * * * * flock -n /tmp/pulsecheck.lock $BIN_DIR/pulsecheck -c $CONF_DIR/pulsecheck.yml run >> \$HOME/pulsecheck.log 2>&1
$(case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "Add $BIN_DIR to your PATH.";; esac)
EOF
