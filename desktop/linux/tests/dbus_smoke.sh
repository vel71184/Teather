#!/bin/sh
set -eu

if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
  exec dbus-run-session -- "$0"
fi

repo=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
work=$(mktemp -d)
daemon_pid=

cleanup() {
  if [ -n "$daemon_pid" ] && kill -0 "$daemon_pid" 2>/dev/null; then
    kill "$daemon_pid"
    wait "$daemon_pid" || true
  fi
  rm -rf -- "$work"
}
trap cleanup EXIT HUP INT TERM

mkdir -m 0700 "$work/config" "$work/runtime"
export XDG_CONFIG_HOME="$work/config"
export XDG_RUNTIME_DIR="$work/runtime"
export PYTHONPATH="$repo/desktop/linux"

python3 -m teather.daemon &
daemon_pid=$!

attempt=0
while [ "$attempt" -lt 50 ]; do
  if python3 -m teather.cli status --json > "$work/status.json" 2>/dev/null; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 0.1
done
[ "$attempt" -lt 50 ] || {
  echo "Teather D-Bus service did not become ready" >&2
  exit 1
}

python3 -c 'import json,sys; value=json.load(open(sys.argv[1], encoding="utf-8")); assert value["state"] == "disconnected"' "$work/status.json"
python3 -m teather.cli diagnose --json > "$work/diagnose.json"
python3 -c 'import json,sys; value=json.load(open(sys.argv[1], encoding="utf-8")); assert "ready" in value and "issues" in value and "usable_nameservers" in value' "$work/diagnose.json"

echo "D-Bus status and diagnose smoke test passed"
