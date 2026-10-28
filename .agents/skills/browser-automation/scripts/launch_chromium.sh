#!/usr/bin/env bash
# Launch Chromium with remote debugging so Browser Use can attach over CDP.
# Idempotent: does nothing if a debuggable browser already answers on the port.
#
# Usage: launch_chromium.sh [--headless] [--port 9222] [--profile DIR]
set -euo pipefail

PORT=9222
PROFILE="${HOME}/.cache/vibecode-chromium-profile"
HEADLESS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --headless) HEADLESS=1; shift ;;
    --port) PORT="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

VERSION_URL="http://127.0.0.1:${PORT}/json/version"

if curl -fsS -m 2 "$VERSION_URL" >/dev/null 2>&1; then
  echo "Chromium already listening on port ${PORT}"
  curl -fsS "$VERSION_URL"
  exit 0
fi

BIN=""
for candidate in chromium chromium-browser google-chrome; do
  if command -v "$candidate" >/dev/null 2>&1; then BIN="$candidate"; break; fi
done
if [[ -z "$BIN" ]]; then
  echo "No chromium/chrome binary found on PATH" >&2
  exit 1
fi

mkdir -p "$PROFILE"

ARGS=(
  "--remote-debugging-port=${PORT}"
  "--remote-debugging-address=127.0.0.1"   # never expose CDP beyond localhost
  "--user-data-dir=${PROFILE}"             # required: Chromium ignores the debug port on the default profile
  "--no-first-run"
  "--no-default-browser-check"
)
if [[ "$HEADLESS" -eq 1 ]]; then ARGS+=("--headless=new"); fi

nohup "$BIN" "${ARGS[@]}" >/tmp/chromium-cdp.log 2>&1 &
echo "Started ${BIN} (pid $!), log: /tmp/chromium-cdp.log"

for _ in $(seq 1 30); do
  if curl -fsS -m 2 "$VERSION_URL" >/dev/null 2>&1; then
    echo "Ready: ${VERSION_URL}"
    exit 0
  fi
  sleep 0.5
done

echo "Chromium did not expose port ${PORT} in time; see /tmp/chromium-cdp.log" >&2
exit 1
