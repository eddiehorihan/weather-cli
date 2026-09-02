#!/usr/bin/env bash
# Self-healing macOS installer for weather-cli.
# Safe to re-run. Uses pipx via Homebrew — never pip --user (PEP 668).
#
# After this file is on main:
#   curl -fsSL https://raw.githubusercontent.com/eddiehorihan/weather-cli/main/scripts/install-macos.sh | bash
# From a clone:
#   bash scripts/install-macos.sh

set -euo pipefail

REPO_GIT_URL="https://github.com/eddiehorihan/weather-cli.git"
REPO_SPEC="git+${REPO_GIT_URL}"
APP_NAME="weather-cli"
MIN_UV="0.9.17"

# Documented pipx default when PIPX_BIN_DIR is unset.
DEFAULT_PIPX_BIN_DIR="${HOME}/.local/bin"

last_status=0

log() {
  printf '%s\n' "$*"
}

err() {
  printf '%s\n' "$*" >&2
}

have() {
  command -v "$1" >/dev/null 2>&1
}

# True when pipx failed because its default uv backend is too old.
# Eddie's error: "pipx needs uv>=0.9.17, but …/uv reports 0.9.11"
should_retry_with_pip_backend() {
  local output="$1"
  printf '%s' "$output" | grep -Eqi 'needs uv|requires uv|uv>=|uv >=[[:space:]]*[0-9]'
}

# Dotted numeric compare: 0 if $1 < $2. Ignores pre-release suffixes.
version_lt() {
  local left="${1%%[-+]*}"
  local right="${2%%[-+]*}"
  local i=1
  local lpart rpart
  while [[ "$i" -le 3 ]]; do
    lpart=$(printf '%s' "$left" | cut -d. -f"$i")
    rpart=$(printf '%s' "$right" | cut -d. -f"$i")
    lpart=$(printf '%s' "${lpart:-0}" | tr -cd '0-9')
    rpart=$(printf '%s' "${rpart:-0}" | tr -cd '0-9')
    lpart="${lpart:-0}"
    rpart="${rpart:-0}"
    if [[ "$lpart" -lt "$rpart" ]]; then
      return 0
    fi
    if [[ "$lpart" -gt "$rpart" ]]; then
      return 1
    fi
    i=$((i + 1))
  done
  return 1
}

uv_is_too_old() {
  local ver
  have uv || return 1
  ver=$(uv --version 2>/dev/null | awk '{print $2}')
  ver="${ver%%[-+]*}"
  [[ -n "$ver" ]] || return 1
  version_lt "$ver" "$MIN_UV"
}

# Run a command, print its output, store exit code in last_status.
# Always returns 0 so `set -e` does not abort around expected failures.
run_capture() {
  local output
  last_status=0
  output=$("$@" 2>&1) || last_status=$?
  if [[ -n "$output" ]]; then
    printf '%s\n' "$output"
  fi
  return 0
}

pipx_bin() {
  if [[ -n "${WEATHER_CLI_PIPX:-}" ]]; then
    printf '%s' "$WEATHER_CLI_PIPX"
  else
    printf '%s' "pipx"
  fi
}

expand_user_path() {
  local p="$1"
  case "$p" in
    "~")
      printf '%s' "$HOME"
      ;;
    ~/*)
      printf '%s' "${HOME}/${p#~/}"
      ;;
    *)
      printf '%s' "$p"
      ;;
  esac
}

# Pull a bin-dir path out of `pipx environment` / `--value PIPX_BIN_DIR` text.
parse_pipx_bin_from_text() {
  local raw="$1"
  local line candidate=""
  while IFS= read -r line || [[ -n "$line" ]]; do
    line=$(printf '%s' "$line" | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -n "$line" ]] || continue
    case "$line" in
      PIPX_BIN_DIR=*)
        candidate="${line#PIPX_BIN_DIR=}"
        candidate=$(printf '%s' "$candidate" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        ;;
      /*|~/*|./*)
        candidate="$line"
        ;;
    esac
  done <<PARSE
$raw
PARSE
  printf '%s' "$candidate"
}

# Prefer pipx's own answer, then PIPX_BIN_DIR, then ~/.local/bin.
# stdout is the directory only (no log lines).
resolve_pipx_bin_dir() {
  local px raw parsed
  px=$(pipx_bin)

  if [[ -n "$px" ]] && { [[ -x "$px" ]] || have "$px"; }; then
    raw=$("$px" environment --value PIPX_BIN_DIR 2>/dev/null) || raw=""
    parsed=$(parse_pipx_bin_from_text "$raw")
    if [[ -z "$parsed" ]]; then
      raw=$("$px" environment 2>/dev/null) || raw=""
      parsed=$(parse_pipx_bin_from_text "$raw")
    fi
    if [[ -n "$parsed" ]]; then
      expand_user_path "$parsed"
      return 0
    fi
  fi

  if [[ -n "${PIPX_BIN_DIR:-}" ]]; then
    expand_user_path "$PIPX_BIN_DIR"
    return 0
  fi

  printf '%s' "$DEFAULT_PIPX_BIN_DIR"
}

print_pipx_fix() {
  local output="$1"
  err ""
  err "pipx could not install ${APP_NAME}."
  if printf '%s' "$output" | grep -Eqi 'externally-managed-environment|externally managed'; then
    err "Homebrew Python is protected (PEP 668). Use pipx, not pip install --user."
    err "If pipx is missing: brew install pipx && pipx ensurepath"
  elif printf '%s' "$output" | grep -Eqi 'already been installed|already installed'; then
    err "It is already installed. Re-run this script, or:"
    err "  pipx install --force ${REPO_SPEC} --backend pip"
  elif printf '%s' "$output" | grep -Eqi 'git: command not found|is git installed|unable to find git'; then
    err "Need git on your PATH. Install it with: brew install git"
  elif printf '%s' "$output" | grep -Eqi 'requires-python|UnsupportedPythonVersion|Does not support Python'; then
    err "Need Python 3.9 or newer. Check with: python3 --version"
  elif printf '%s' "$output" | grep -Eqi 'permission denied'; then
    err "pipx could not write files. Check that you own ~/.local and ~/.local/bin."
  elif printf '%s' "$output" | grep -Eqi 'could not resolve|failed to resolve|timed out|network|SSL|github.com.*404|Not Found'; then
    err "Could not download the repo from GitHub. Check your network and try again."
  elif should_retry_with_pip_backend "$output"; then
    err "pipx's uv backend is too old. Retry with:"
    err "  pipx install --force ${REPO_SPEC} --backend pip"
  else
    err "Try this fallback (note where --force and --backend go):"
    err "  pipx install --force ${REPO_SPEC} --backend pip"
    err "If the command is still missing afterwards: pipx ensurepath"
    err "then open a new terminal."
  fi
}

ensure_macos() {
  if [[ "$(uname -s)" != "Darwin" ]]; then
    err "This installer is for macOS."
    err "On other systems, use pipx:"
    err "  pipx install ${REPO_SPEC}"
    err "If pipx complains about uv being too old:"
    err "  pipx install ${REPO_SPEC} --backend pip"
    exit 1
  fi
}

ensure_homebrew() {
  if have brew; then
    return 0
  fi
  err "Homebrew is required to install pipx, and it is not on your PATH."
  err "This script will not install Homebrew for you."
  err "Install it from https://brew.sh (the site shows one command), then re-run:"
  err "  curl -fsSL https://raw.githubusercontent.com/eddiehorihan/weather-cli/main/scripts/install-macos.sh | bash"
  exit 1
}

ensure_pipx() {
  local brew_prefix
  if have pipx; then
    log "pipx is already installed."
    return 0
  fi

  if brew_prefix=$(brew --prefix 2>/dev/null) && [[ -x "${brew_prefix}/bin/pipx" ]]; then
    export PATH="${brew_prefix}/bin:${PATH}"
    if have pipx; then
      log "Found pipx in the Homebrew prefix; added it to PATH for this session."
      return 0
    fi
  fi

  log "Installing pipx with Homebrew..."
  brew install pipx
  if ! have pipx; then
    if brew_prefix=$(brew --prefix 2>/dev/null); then
      export PATH="${brew_prefix}/bin:${PATH}"
    fi
  fi
  if ! have pipx; then
    err "brew install pipx finished, but pipx is still not on PATH."
    err "Try opening a new terminal, or run: eval \"\$(brew shellenv)\""
    exit 1
  fi
}

ensure_pipx_path() {
  local apps_bin
  apps_bin=$(resolve_pipx_bin_dir)
  export PATH="${apps_bin}:${PATH}"
  if have brew; then
    eval "$(brew shellenv 2>/dev/null)" || true
  fi
  log "Running pipx ensurepath so ${APP_NAME} lands on PATH..."
  run_capture "$(pipx_bin)" ensurepath
  if [[ "$last_status" -ne 0 ]]; then
    err "pipx ensurepath had a problem (continuing). If ${APP_NAME} is not found later, run:"
    err "  pipx ensurepath"
    err "then open a new terminal."
  fi
  # ensurepath updates the login profile; this session still needs the dir.
  # Re-resolve in case PIPX_BIN_DIR / pipx config differs from ~/.local/bin.
  apps_bin=$(resolve_pipx_bin_dir)
  export PATH="${apps_bin}:${PATH}"
  if [[ "$apps_bin" != "$DEFAULT_PIPX_BIN_DIR" ]]; then
    log "pipx app directory is ${apps_bin}."
  fi
}

# Install (or reinstall) from GitHub. On the uv-version pipx failure,
# automatically retries with --backend pip.
pipx_install_weather_cli() {
  local output
  local extra_backend=0

  if uv_is_too_old; then
    log "Found uv older than ${MIN_UV}; using pipx --backend pip from the start."
    extra_backend=1
  fi

  log "Installing ${APP_NAME} from ${REPO_SPEC}"
  last_status=0
  if [[ "$extra_backend" -eq 1 ]]; then
    output=$("$(pipx_bin)" install --force --backend pip "$REPO_SPEC" 2>&1) || last_status=$?
  else
    output=$("$(pipx_bin)" install --force "$REPO_SPEC" 2>&1) || last_status=$?
  fi
  if [[ -n "$output" ]]; then
    printf '%s\n' "$output"
  fi

  if [[ "$last_status" -eq 0 ]]; then
    return 0
  fi

  if [[ "$extra_backend" -eq 0 ]] && should_retry_with_pip_backend "$output"; then
    log "pipx failed because its uv backend is too old. Retrying with --backend pip..."
    last_status=0
    output=$("$(pipx_bin)" install --force --backend pip "$REPO_SPEC" 2>&1) || last_status=$?
    if [[ -n "$output" ]]; then
      printf '%s\n' "$output"
    fi
    if [[ "$last_status" -eq 0 ]]; then
      return 0
    fi
  fi

  print_pipx_fix "$output"
  return 1
}

verify_weather_cli() {
  local bin=""
  local apps_bin
  apps_bin=$(resolve_pipx_bin_dir)
  export PATH="${apps_bin}:${PATH}"

  if bin=$(command -v "$APP_NAME" 2>/dev/null); then
    log ""
    log "Found ${APP_NAME} at ${bin}"
    if ! "$APP_NAME" --help; then
      err "${APP_NAME} is on PATH but --help failed."
      return 1
    fi
    log ""
    log "Install looks good."
    log "If a new terminal says '${APP_NAME}: command not found', run:"
    log "  pipx ensurepath"
    log "then open a new terminal (do not type a \$ in front of the command)."
    return 0
  fi

  if [[ -x "${apps_bin}/${APP_NAME}" ]]; then
    err ""
    err "${APP_NAME} is installed at ${apps_bin}/${APP_NAME}"
    err "but that folder is not on PATH in this session."
    err "Fix:"
    err "  pipx ensurepath"
    err "Then open a new terminal. In this one you can run:"
    err "  export PATH=\"${apps_bin}:\$PATH\""
    err ""
    "${apps_bin}/${APP_NAME}" --help
    return 0
  fi

  err ""
  err "${APP_NAME}: command not found after install."
  err "The package may have installed, but your shell cannot see it yet."
  err "Run:"
  err "  pipx ensurepath"
  err "Then open a new terminal and try:"
  err "  ${APP_NAME} --help"
  err "If that still fails: pipx list"
  if [[ "$apps_bin" != "$DEFAULT_PIPX_BIN_DIR" ]]; then
    err "pipx app directory is ${apps_bin} (PIPX_BIN_DIR / pipx environment)."
  fi
  return 1
}

usage() {
  cat <<EOF
Install ${APP_NAME} on macOS with pipx (self-healing).

Usage:
  bash scripts/install-macos.sh
  curl -fsSL https://raw.githubusercontent.com/eddiehorihan/weather-cli/main/scripts/install-macos.sh | bash

Options:
  --help       Show this help
  --self-test  Run installer logic checks (no Homebrew, no network)
EOF
}

run_self_test() {
  local failed=0
  local msg
  local tmpdir
  local logf
  local pep_msg

  msg='pipx needs uv>=0.9.17, but /opt/homebrew/bin/uv reports 0.9.11'
  if should_retry_with_pip_backend "$msg"; then
    log "ok: detects Eddie uv-version error"
  else
    err "FAIL: did not detect uv-version error"
    failed=1
  fi

  msg='ERROR: Package weather-cli already installed'
  if should_retry_with_pip_backend "$msg"; then
    err "FAIL: false positive on already-installed"
    failed=1
  else
    log "ok: no false positive on already-installed"
  fi

  if version_lt "0.9.11" "0.9.17"; then
    log "ok: 0.9.11 < 0.9.17"
  else
    err "FAIL: version_lt 0.9.11 0.9.17"
    failed=1
  fi
  if version_lt "0.9.17" "0.9.17"; then
    err "FAIL: 0.9.17 should not be < 0.9.17"
    failed=1
  else
    log "ok: 0.9.17 is not < 0.9.17"
  fi

  pep_msg=$(print_pipx_fix "error: externally-managed-environment" 2>&1)
  if printf '%s' "$pep_msg" | grep -qi 'pipx' && ! printf '%s' "$pep_msg" | grep -qi 'break-system-packages'; then
    log "ok: PEP 668 hint uses pipx, not break-system-packages"
  else
    err "FAIL: PEP 668 hint"
    failed=1
  fi

  tmpdir=$(mktemp -d)
  logf="${tmpdir}/pipx.log"
  cat > "${tmpdir}/pipx" <<'MOCK'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${WEATHER_CLI_PIPX_LOG}"
for arg in "$@"; do
  if [[ "$arg" == "ensurepath" ]]; then
    exit 0
  fi
done
backend=0
prev=""
for arg in "$@"; do
  if [[ "$prev" == "--backend" && "$arg" == "pip" ]]; then
    backend=1
  fi
  prev="$arg"
done
if [[ "$backend" -eq 0 ]]; then
  echo "pipx needs uv>=0.9.17, but /opt/homebrew/bin/uv reports 0.9.11" >&2
  exit 1
fi
exit 0
MOCK
  chmod +x "${tmpdir}/pipx"

  # Exercise the failure → --backend pip retry, not the proactive uv check.
  uv_is_too_old() { return 1; }

  WEATHER_CLI_PIPX="${tmpdir}/pipx"
  WEATHER_CLI_PIPX_LOG="$logf"
  export WEATHER_CLI_PIPX WEATHER_CLI_PIPX_LOG

  if pipx_install_weather_cli; then
    if grep -q -- '--backend pip' "$logf"; then
      log "ok: uv error retried with --backend pip"
    else
      err "FAIL: retry did not pass --backend pip"
      err "pipx invocations:"
      cat "$logf" >&2 || true
      failed=1
    fi
  else
    err "FAIL: install function did not recover from uv error"
    err "pipx invocations:"
    cat "$logf" >&2 || true
    failed=1
  fi

  rm -rf "$tmpdir"
  unset WEATHER_CLI_PIPX WEATHER_CLI_PIPX_LOG

  if ! test_custom_pipx_bin_dir; then
    failed=1
  fi

  if [[ "$failed" -ne 0 ]]; then
    err "self-test failed"
    return 1
  fi
  log "self-test passed"
  return 0
}

# Covers Codex P2: honor PIPX_BIN_DIR / `pipx environment` instead of
# assuming ~/.local/bin, and put that dir on PATH before verify.
test_custom_pipx_bin_dir() {
  local failed=0
  local tmpdir custom mock got saved_path
  local saved_pipx_bin_dir="${PIPX_BIN_DIR-}"
  saved_path="$PATH"
  tmpdir=$(mktemp -d)
  custom="${tmpdir}/custom-bin"
  mkdir -p "$custom"

  cat > "${custom}/${APP_NAME}" <<'FAKE'
#!/bin/sh
echo "weather-cli fake --help"
exit 0
FAKE
  chmod +x "${custom}/${APP_NAME}"

  mock="${tmpdir}/pipx-no-env"
  cat > "$mock" <<'MOCK'
#!/usr/bin/env bash
echo "unknown command: environment" >&2
exit 2
MOCK
  chmod +x "$mock"
  WEATHER_CLI_PIPX="$mock"
  unset PIPX_BIN_DIR
  export WEATHER_CLI_PIPX
  got=$(resolve_pipx_bin_dir)
  if [[ "$got" == "$DEFAULT_PIPX_BIN_DIR" ]]; then
    log "ok: default pipx bin dir is ~/.local/bin"
  else
    err "FAIL: default bin dir: got ${got}"
    failed=1
  fi

  PIPX_BIN_DIR="$custom"
  export PIPX_BIN_DIR
  got=$(resolve_pipx_bin_dir)
  if [[ "$got" == "$custom" ]]; then
    log "ok: PIPX_BIN_DIR env used when pipx environment is unavailable"
  else
    err "FAIL: PIPX_BIN_DIR fallback: got ${got} want ${custom}"
    failed=1
  fi

  mock="${tmpdir}/pipx-env"
  cat > "$mock" <<MOCK
#!/usr/bin/env bash
if [[ "\$1" == "environment" ]]; then
  if [[ "\${2:-}" == "--value" && "\${3:-}" == "PIPX_BIN_DIR" ]]; then
    printf '%s\n' "${custom}"
    exit 0
  fi
  printf 'PIPX_BIN_DIR=%s\n' "${custom}"
  exit 0
fi
exit 0
MOCK
  chmod +x "$mock"
  WEATHER_CLI_PIPX="$mock"
  PIPX_BIN_DIR="${tmpdir}/should-not-win"
  export WEATHER_CLI_PIPX PIPX_BIN_DIR
  got=$(resolve_pipx_bin_dir)
  if [[ "$got" == "$custom" ]]; then
    log "ok: prefers pipx environment --value PIPX_BIN_DIR"
  else
    err "FAIL: pipx environment: got ${got} want ${custom}"
    failed=1
  fi

  mock="${tmpdir}/pipx-env-plain"
  cat > "$mock" <<MOCK
#!/usr/bin/env bash
if [[ "\$1" == "environment" ]]; then
  if [[ "\${2:-}" == "--value" ]]; then
    echo "unrecognized arguments: --value" >&2
    exit 2
  fi
  printf 'PIPX_HOME=/tmp/pipx\nPIPX_BIN_DIR=%s\n' "${custom}"
  exit 0
fi
exit 0
MOCK
  chmod +x "$mock"
  WEATHER_CLI_PIPX="$mock"
  unset PIPX_BIN_DIR
  export WEATHER_CLI_PIPX
  got=$(resolve_pipx_bin_dir)
  if [[ "$got" == "$custom" ]]; then
    log "ok: parses PIPX_BIN_DIR= from pipx environment"
  else
    err "FAIL: parse environment dump: got ${got} want ${custom}"
    failed=1
  fi

  PATH="/usr/bin:/bin"
  export PATH
  WEATHER_CLI_PIPX="${tmpdir}/pipx-env"
  export WEATHER_CLI_PIPX
  unset PIPX_BIN_DIR
  if verify_weather_cli; then
    if command -v "$APP_NAME" >/dev/null 2>&1; then
      log "ok: verify finds ${APP_NAME} on custom PIPX_BIN_DIR"
    else
      err "FAIL: verify succeeded but ${APP_NAME} not on PATH"
      failed=1
    fi
  else
    err "FAIL: verify with custom PIPX_BIN_DIR"
    failed=1
  fi

  PATH="$saved_path"
  export PATH
  unset WEATHER_CLI_PIPX
  if [[ -n "$saved_pipx_bin_dir" ]]; then
    PIPX_BIN_DIR="$saved_pipx_bin_dir"
    export PIPX_BIN_DIR
  else
    unset PIPX_BIN_DIR
  fi
  rm -rf "$tmpdir"

  if [[ "$failed" -ne 0 ]]; then
    return 1
  fi
  return 0
}

main() {
  case "${1:-}" in
    --help|-h)
      usage
      return 0
      ;;
    --self-test)
      run_self_test
      return $?
      ;;
    "")
      ;;
    *)
      err "Unknown option: $1"
      usage
      return 1
      ;;
  esac

  ensure_macos
  log "weather-cli macOS installer"
  ensure_homebrew
  ensure_pipx
  ensure_pipx_path
  pipx_install_weather_cli
  verify_weather_cli
}

main "$@"
