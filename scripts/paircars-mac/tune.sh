#!/usr/bin/env bash
# Raise the P-AIRCARS worker ceiling inside the running paircars container.
# Does not resize the virtual machine and does not touch the default profile.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PROFILE=paircars
CONTAINER=paircars
CTX=(docker --context "colima-$PROFILE")

if ! colima status --profile "$PROFILE" >/dev/null 2>&1; then
  echo "Colima profile '$PROFILE' is not running." >&2
  exit 1
fi
"${CTX[@]}" start "$CONTAINER" >/dev/null
"${CTX[@]}" exec "$CONTAINER" mkdir -p /tmp/paircars-mac
"${CTX[@]}" cp "$HERE/macos_fixes.py" "$CONTAINER:/tmp/paircars-mac/macos_fixes.py"
"${CTX[@]}" cp "$HERE/mac_resources.py" "$CONTAINER:/tmp/paircars-mac/mac_resources.py"
"${CTX[@]}" exec "$CONTAINER" /opt/miniforge3/envs/paircars/bin/python \
  /tmp/paircars-mac/macos_fixes.py patch-code
"${CTX[@]}" exec -i -u paircars -e HOME=/home/paircars "$CONTAINER" \
  /opt/miniforge3/envs/paircars/bin/python - <<'PY'
import psutil
import paircars_mac_resources as m

cpu, mem = m.clamp_fracs(0.8, 0.8)
n = psutil.cpu_count()
total = psutil.virtual_memory().total / 1024**3
print(f"guest cpus: {n}")
print(f"guest memory GiB: {total:.2f}")
print(f"worker cpu fraction: {cpu:.4f} -> {max(1, int(n * cpu))} cpus")
print(f"worker memory fraction: {mem:.4f} -> {round(total * mem, 2)} GiB")
PY
